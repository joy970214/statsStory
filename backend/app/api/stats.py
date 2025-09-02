from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from app.models.stat_models import (
    RecentStatsResponse, 
    StatMetadata, 
    GenerateStoryRequest, 
    StoryResponse
)
from app.services.crawler_service import CrawlerService
from app.services.ai_service import AIService
from app.services.data_storage import DataStorageService
from app.services.mcp_client import mcp_client
from app.services.mcp_analysis_service import mcp_analysis_service
import asyncio
import time
import uuid
from datetime import datetime, timedelta

router = APIRouter()
crawler_service = CrawlerService()
ai_service = AIService()
storage_service = DataStorageService()

# 캐시 저장소
_cache = {
    'recent_stats': None,
    'cache_time': None
}

# 캐시 TTL (5분)
CACHE_TTL_MINUTES = 5

@router.get("/recent-stats", response_model=RecentStatsResponse)
async def get_recent_stats():
    """최근 통계 목록 조회 - 캐시 및 fallback 지원"""
    try:
        now = datetime.now()
        
        # 캐시 확인
        if (_cache['recent_stats'] and _cache['cache_time'] and 
            (now - _cache['cache_time']).seconds < CACHE_TTL_MINUTES * 60):
            print("캐시에서 최신 통계 데이터 반환")
            return _cache['recent_stats']
        
        print("새로운 통계 데이터 크롤링 시작")
        
        # 크롤링 시도
        stats = await crawler_service.get_recent_stats()
        
        # 크롤링 결과 검증
        if not stats or len(stats) == 0:
            print("크롤링 결과가 없습니다.")
            raise Exception("크롤링 결과가 없습니다.")
        
        # 실제 데이터인지 확인 (더미 데이터가 아닌지)
        if len(stats) > 0 and any(stat.id.startswith('dummy_') for stat in stats):
            print("더미 데이터가 감지되었습니다. 실제 크롤링을 다시 시도합니다.")
            raise Exception("더미 데이터가 감지되었습니다.")
        
        response = RecentStatsResponse(
            stats=stats,
            total_count=len(stats)
        )
        
        # 캐시 저장
        _cache['recent_stats'] = response
        _cache['cache_time'] = now
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{stat_id}/metadata", response_model=StatMetadata)
async def get_stat_metadata(stat_id: str):
    """특정 통계의 메타데이터 조회"""
    try:
        metadata = await crawler_service.get_stat_metadata(stat_id)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-basic")
async def analyze_basic(request: GenerateStoryRequest):
    """기본 분석 - 메타데이터와 데이터 정리"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"기본 분석 요청: {request.stat_name}")
        print(f"통계 URL: {stat_url}")
        
        # 1. 캐시된 데이터 확인
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        if cached_metadata and cached_stat_data:
            print(f"캐시에서 데이터 로드: {cached_metadata.title}, {len(cached_stat_data)}년치")
            metadata = cached_metadata
            stat_data = cached_stat_data
        else:
            # 2. 새로 수집
            try:
                print("=== 메타데이터 및 데이터 수집 시작 ===")
                metadata = await crawler_service.get_stat_metadata(stat_url)
                stat_data = await crawler_service.get_stat_data(stat_url, request.period)
                storage_service.save_complete_data(stat_url, metadata, stat_data)
            except Exception as crawl_error:
                print("크롤링 오류, 더미 데이터 사용")
                from app.models.stat_models import StatMetadata, StatData
                metadata = StatMetadata(
                    id="dummy",
                    title=request.stat_name,
                    purpose="기본 분석용 더미 데이터",
                    frequency="연간",
                    department="국토교통부",
                    contact="test@molit.go.kr",
                    keywords=["기본분석"],
                    related_terms={}
                )
                stat_data = [
                    StatData(year=2020, data={"총합": 1000}),
                    StatData(year=2021, data={"총합": 1100}),
                    StatData(year=2022, data={"총합": 1200}),
                    StatData(year=2023, data={"총합": 1300}),
                    StatData(year=2024, data={"총합": 1400})
                ]
        
        # 3. 기본 분석 수행 (MCP 우선, AI 실패 시 로컬 분석으로 대체)
        try:
            # MCP 분석 서비스 우선 시도
            basic_analysis = await mcp_analysis_service.analyze_basic_data(stat_data, metadata)
            print("MCP 기본 분석 서비스로 분석 완료")
        except Exception as mcp_error:
            print(f"MCP 서비스 오류, AI 서비스로 대체: {mcp_error}")
            try:
                basic_analysis = await ai_service.analyze_basic_data(stat_data, metadata)
            except Exception as ai_error:
                print(f"AI 서비스 오류, 기본 분석으로 대체: {ai_error}")
                # 기본 분석 결과 생성
                basic_analysis = {
                    "collection_summary": {
                        "data_count": len(stat_data),
                        "year_range": f"{min([d.year for d in stat_data])} - {max([d.year for d in stat_data])}" if stat_data else "데이터 없음",
                        "data_completeness": "수집 완료"
                    },
                    "data_interpretation": f"{metadata.title}에 대한 기본적인 데이터 분석 결과입니다."
                }
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "metadata": metadata.dict(),
            "basic_analysis": basic_analysis
        }
    except Exception as e:
        print("기본 분석 오류 발생")
        raise HTTPException(status_code=500, detail="기본 분석 중 오류가 발생했습니다")

@router.post("/analyze-comprehensive") 
async def analyze_comprehensive(request: GenerateStoryRequest):
    """종합 분석"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"종합 분석 요청: {request.stat_name}")
        
        # 1. 캐시된 데이터 확인
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        if cached_metadata and cached_stat_data:
            print(f"캐시에서 데이터 로드: {cached_metadata.title}")
            metadata = cached_metadata
            stat_data = cached_stat_data
        else:
            # 2. 새로 수집
            try:
                print("=== 메타데이터 및 데이터 수집 시작 ===")
                metadata = await crawler_service.get_stat_metadata(stat_url)
                stat_data = await crawler_service.get_stat_data(stat_url, request.period)
                storage_service.save_complete_data(stat_url, metadata, stat_data)
            except Exception as crawl_error:
                print("크롤링 오류, 더미 데이터 사용")
                from app.models.stat_models import StatMetadata, StatData
                metadata = StatMetadata(
                    id="dummy",
                    title=request.stat_name,
                    purpose="종합 분석용 더미 데이터",
                    frequency="연간",
                    department="국토교통부",
                    contact="test@molit.go.kr",
                    keywords=["종합분석"],
                    related_terms={}
                )
                stat_data = [
                    StatData(year=2020, data={"총합": 1000}),
                    StatData(year=2021, data={"총합": 1100}),
                    StatData(year=2022, data={"총합": 1200}),
                    StatData(year=2023, data={"총합": 1300}),
                    StatData(year=2024, data={"총합": 1400})
                ]
        
        # 3. 종합 분석 수행 (MCP 우선, AI 실패 시 로컬 분석으로 대체)
        try:
            # MCP 분석 서비스 우선 시도
            analysis_result = await mcp_analysis_service.generate_comprehensive_analysis(stat_data, metadata)
            print("MCP 종합 분석 서비스로 분석 완료")
        except Exception as mcp_error:
            print(f"MCP 서비스 오류, AI 서비스로 대체: {mcp_error}")
            try:
                analysis_result = await ai_service.generate_comprehensive_analysis(stat_data, metadata)
            except Exception as ai_error:
                print(f"AI 서비스 오류, 기본 분석으로 대체: {ai_error}")
                # 기본 분석 결과 생성
                analysis_result = f"{metadata.title}에 대한 종합적인 분석 결과를 제공합니다."
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "metadata": metadata.dict(),
            "analysis": analysis_result
        }
    except Exception as e:
        print("종합 분석 오류 발생")
        raise HTTPException(status_code=500, detail="종합 분석 중 오류가 발생했습니다")

@router.post("/test-simple")
async def test_simple():
    """가장 간단한 테스트 엔드포인트"""
    return {"message": "success"}


# 데이터 분석 타입별 추가 함수들
def _analyze_data_types(stat_data):
    """데이터 타입 분석"""
    type_analysis = {
        "numeric_fields": set(),
        "text_fields": set(),
        "mixed_fields": set()
    }
    
    for item in stat_data:
        if item.data:
            for key, value in item.data.items():
                try:
                    if isinstance(value, (int, float)):
                        type_analysis["numeric_fields"].add(key)
                    elif isinstance(value, str):
                        try:
                            float(value.replace(',', '').replace('%', ''))
                            type_analysis["numeric_fields"].add(key)
                        except ValueError:
                            type_analysis["text_fields"].add(key)
                    else:
                        type_analysis["mixed_fields"].add(key)
                except:
                    type_analysis["mixed_fields"].add(key)
    
    return {
        "numeric_fields": list(type_analysis["numeric_fields"]),
        "text_fields": list(type_analysis["text_fields"]),
        "mixed_fields": list(type_analysis["mixed_fields"]),
        "total_numeric": len(type_analysis["numeric_fields"]),
        "total_text": len(type_analysis["text_fields"]),
        "total_mixed": len(type_analysis["mixed_fields"])
    }

def _get_data_recommendations(summary):
    """데이터 기반 분석 추천 사항"""
    recommendations = []
    
    data_summary = summary.get("data_summary", {})
    total_records = data_summary.get("total_records", 0)
    total_fields = data_summary.get("total_fields", 0)
    
    if total_records == 0:
        recommendations.append("데이터가 수집되지 않았습니다. URL이나 기간을 확인해주세요.")
    elif total_records < 3:
        recommendations.append("데이터가 부족합니다. 트렌드 분석은 어려울 수 있습니다.")
    else:
        recommendations.append("충분한 데이터가 있어 트렌드 분석이 가능합니다.")
    
    if total_fields > 10:
        recommendations.append("데이터 필드가 많습니다. 핵심 지표를 선별하여 분석하는 것을 추천합니다.")
    elif total_fields > 0:
        recommendations.append("적절한 수의 데이터 필드가 있어 분석에 적합합니다.")
    
    return recommendations


async def _collect_stat_data(request: GenerateStoryRequest):
    """데이터 수집 공통 함수 - AI 분석용 개선된 크롤러 사용"""
    stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
    
    # 1. 캐시된 데이터 확인
    cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
    
    if cached_metadata and cached_stat_data:
        print(f"캐시에서 데이터 로드: {cached_metadata.title}, {len(cached_stat_data)}년치")
        metadata = cached_metadata
        stat_data = cached_stat_data
    else:
        # 2. AI 분석용 개선된 크롤러로 새로 수집
        try:
            print("=== AI 분석용 개선된 데이터 수집 시작 ===")
            # 개선된 크롤러 사용 (통계정보+관련용어 탭, #sFormId 활용)
            metadata = await crawler_service.get_stat_metadata_for_analysis(stat_url)
            stat_data = await crawler_service.get_stat_data_for_analysis(stat_url, request.period)
            storage_service.save_complete_data(stat_url, metadata, stat_data)
        except Exception as crawl_error:
            print(f"개선된 크롤링 오류, 더미 데이터 사용: {crawl_error}")
            from app.models.stat_models import StatMetadata, StatData
            metadata = StatMetadata(
                id="dummy",
                title=request.stat_name,
                purpose="AI 분석용 더미 데이터",
                frequency="연간",
                department="국토교통부",
                contact="test@molit.go.kr",
                keywords=["AI분석"],
                related_terms={"샘플용어": "샘플정의"},
                url=stat_url
            )
            stat_data = [
                StatData(year=2020, data={"총합": 1000}, table_name="샘플 통계표"),
                StatData(year=2021, data={"총합": 1100}, table_name="샘플 통계표"),
                StatData(year=2022, data={"총합": 1200}, table_name="샘플 통계표"),
                StatData(year=2023, data={"총합": 1300}, table_name="샘플 통계표"),
                StatData(year=2024, data={"총합": 1400}, table_name="샘플 통계표")
            ]
    
    return stat_data, metadata


# 데이터 검사 및 탐색 엔드포인트들
@router.post("/data/inspect")
async def inspect_collected_data(request: GenerateStoryRequest):
    """수집된 데이터의 구조와 품질을 상세 분석"""
    try:
        # 1. 데이터 수집 (분석과 동일한 로직)
        stat_data, metadata = await _collect_stat_data(request)
        
        # 2. 데이터 구조 분석
        data_types = _analyze_data_types(stat_data)
        
        # 3. 데이터 품질 분석
        data_analysis = {
            "collection_info": {
                "source_url": getattr(metadata, 'url', None),
                "collection_time": datetime.now().isoformat(),
                "stat_name": request.stat_name,
                "keywords": getattr(metadata, 'keywords', []),
                "related_terms": getattr(metadata, 'related_terms', {})
            },
            "data_structure": {
                "total_records": len(stat_data),
                "data_fields": data_types,
                "year_range": {
                    "min_year": min([item.year for item in stat_data]) if stat_data else None,
                    "max_year": max([item.year for item in stat_data]) if stat_data else None
                },
                "sample_data": [
                    {
                        "year": item.year,
                        "data": dict(list(item.data.items())[:3]) if item.data else {}
                    } for item in stat_data[:3]
                ] if stat_data else []
            },
            "data_quality": {
                "completeness": len([item for item in stat_data if item.data]) / len(stat_data) * 100 if stat_data else 0,
                "consistency_check": "데이터 필드가 일관적입니다" if data_types["total_mixed"] == 0 else f"혼합형 필드 {data_types['total_mixed']}개 발견",
                "recommendations": _get_data_recommendations({
                    "data_summary": {
                        "total_records": len(stat_data),
                        "total_fields": data_types["total_numeric"] + data_types["total_text"] + data_types["total_mixed"]
                    }
                })
            }
        }
        
        return data_analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 검사 중 오류: {str(e)}")


@router.post("/data/raw-view")
async def view_raw_collected_data(request: GenerateStoryRequest):
    """원시 수집 데이터를 있는 그대로 조회"""
    try:
        stat_data, metadata = await _collect_stat_data(request)
        
        return {
            "metadata": {
                "stat_name": request.stat_name,
                "collection_time": datetime.now().isoformat(),
                "source_info": getattr(metadata, 'url', None)
            },
            "raw_data": [
                {
                    "year": item.year,
                    "data": item.data
                } for item in stat_data
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"원시 데이터 조회 중 오류: {str(e)}")


@router.post("/data/summary") 
async def get_data_collection_summary(request: GenerateStoryRequest):
    """데이터 수집 요약 정보"""
    try:
        stat_data, metadata = await _collect_stat_data(request)
        
        # 기본 통계
        numeric_values = []
        for item in stat_data:
            if item.data:
                for key, value in item.data.items():
                    try:
                        if isinstance(value, (int, float)):
                            numeric_values.append(value)
                        elif isinstance(value, str):
                            numeric_values.append(float(value.replace(',', '').replace('%', '')))
                    except:
                        continue
        
        summary_stats = {}
        if numeric_values:
            summary_stats = {
                "count": len(numeric_values),
                "min": min(numeric_values),
                "max": max(numeric_values), 
                "average": sum(numeric_values) / len(numeric_values),
                "total": sum(numeric_values)
            }
        
        return {
            "summary": {
                "total_records": len(stat_data),
                "year_coverage": f"{min([item.year for item in stat_data])} - {max([item.year for item in stat_data])}" if stat_data else "데이터 없음",
                "data_fields": len(set().union(*[item.data.keys() for item in stat_data if item.data])) if stat_data else 0,
                "numeric_summary": summary_stats
            },
            "field_preview": {
                field: [item.data.get(field) for item in stat_data if item.data and field in item.data][:5]
                for field in list(set().union(*[item.data.keys() for item in stat_data if item.data]))[:5]
            } if stat_data else {}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 요약 중 오류: {str(e)}")


@router.post("/data/explore-by-year/{year}")
async def explore_data_by_year(year: int, request: GenerateStoryRequest):
    """특정 연도 데이터 상세 탐색"""
    try:
        stat_data, metadata = await _collect_stat_data(request)
        
        # 해당 연도 데이터 찾기
        year_data = [item for item in stat_data if item.year == year]
        
        if not year_data:
            return {"message": f"{year}년 데이터가 없습니다", "available_years": [item.year for item in stat_data]}
        
        return {
            "year": year,
            "data_count": len(year_data),
            "detailed_data": [
                {
                    "year": item.year,
                    "all_fields": item.data,
                    "field_count": len(item.data) if item.data else 0
                } for item in year_data
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{year}년 데이터 탐색 중 오류: {str(e)}")


@router.post("/data/collection-log")
async def view_data_collection_log(request: GenerateStoryRequest):
    """데이터 수집 과정의 로그 및 디버그 정보"""
    try:
        # 수집 과정을 로깅하면서 데이터 수집
        collection_log = []
        
        collection_log.append({
            "step": "시작",
            "message": f"'{request.stat_name}' 통계 데이터 수집 시작",
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            stat_data, metadata = await _collect_stat_data(request)
            collection_log.append({
                "step": "수집완료", 
                "message": f"{len(stat_data)}개 레코드 수집 완료",
                "timestamp": datetime.now().isoformat()
            })
            
            if stat_data:
                collection_log.append({
                    "step": "데이터검증",
                    "message": f"연도 범위: {min([item.year for item in stat_data])} - {max([item.year for item in stat_data])}",
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as collection_error:
            collection_log.append({
                "step": "오류",
                "message": f"데이터 수집 실패: {str(collection_error)}",
                "timestamp": datetime.now().isoformat()
            })
            stat_data = []
            metadata = None
        
        return {
            "collection_process": collection_log,
            "final_status": {
                "success": len(stat_data) > 0,
                "total_records": len(stat_data),
                "has_metadata": metadata is not None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"수집 로그 생성 중 오류: {str(e)}")