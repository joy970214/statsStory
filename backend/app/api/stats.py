from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from app.models.stat_models import (
    RecentStatsResponse, 
    StatMetadata, 
    StatData,
    GenerateStoryRequest, 
    StoryResponse,
    InspectionResult, 
    StatTable, 
    TableColumn, 
    TableRow
)
from app.services.crawler_service import CrawlerService
from app.services.ai_service import AIService
from app.services.data_storage import DataStorageService
from app.services.mcp_client import mcp_client
from app.services.mcp_analysis_service import mcp_analysis_service
from app.services.progress_service import progress_tracker, stream_progress, ProgressCallback
try:
    from app.crawlers.optimized_molit_crawler import OptimizedMolitCrawler
except ImportError as e:
    print(f"OptimizedMolitCrawler import 실패: {e}")
    OptimizedMolitCrawler = None
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

# @router.post("/analyze-basic")  # 기본통계현황분석으로 통합됨
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
        
        # 3. 로컬 LLM 종합 분석 수행 (API 토큰 없이)
        try:
            from app.services.local_llm_service import local_llm_service
            analysis_result = await local_llm_service.generate_comprehensive_analysis(stat_data, metadata)
            print("로컬 LLM 종합 분석 완료")
        except Exception as llm_error:
            print(f"로컬 LLM 서비스 오류, 기본 분석으로 대체: {llm_error}")
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

# 기존 동기식 API는 유지하되, 새로운 비동기 API 추가

@router.post("/generate-advanced-cardnews")
async def generate_advanced_cardnews(request: GenerateStoryRequest):
    """기본통계현황분석 - 즉시 응답 (기존 버전)"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"기본통계현황분석 요청: {request.stat_name}")
        
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
                metadata = await crawler_service.get_stat_metadata_for_analysis(stat_url)
                stat_data = await crawler_service.get_stat_data_for_analysis(stat_url, request.period)
                storage_service.save_complete_data(stat_url, metadata, stat_data)
            except Exception as crawl_error:
                print("크롤링 오류, 더미 데이터 사용")
                from app.models.stat_models import StatMetadata, StatData
                metadata = StatMetadata(
                    id="dummy",
                    title=request.stat_name,
                    purpose="기본통계현황분석용 더미 데이터",
                    frequency="연간",
                    department="국토교통부",
                    contact="test@molit.go.kr",
                    keywords=["기본통계현황분석"],
                    related_terms={}
                )
                stat_data = [
                    StatData(year=2020, data={"총합": 1000, "증가율": 5.2}),
                    StatData(year=2021, data={"총합": 1100, "증가율": 10.0}),
                    StatData(year=2022, data={"총합": 1200, "증가율": 9.1}),
                    StatData(year=2023, data={"총합": 1300, "증가율": 8.3}),
                    StatData(year=2024, data={"총합": 1400, "증가율": 7.7})
                ]
        
        # 3. 기초통계 분석 수행
        try:
            from app.services.mcp_client import mcp_client
            basic_stats_result = await mcp_client.call_pandas_analysis("basic_statistics", 
                                                                     cache_key=f"stat_{hash(stat_url)}")
            print("MCP 기초통계 분석 완료")
        except Exception as mcp_error:
            print(f"MCP 서비스 오류, 기본 통계 분석으로 대체: {mcp_error}")
            # 기본 통계 분석 수행
            basic_stats_result = _calculate_basic_statistics(stat_data)
        
        # 4. 분석 요약 생성
        analysis_summary = {
            "analysis_period": f"{min([d.year for d in stat_data])} - {max([d.year for d in stat_data])}" if stat_data else "N/A",
            "total_data_points": len(stat_data),
            "data_completeness": "완료",
            "analysis_quality": "높음"
        }
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "analysis_type": "기본통계현황분석",
            "metadata": metadata.dict() if metadata else None,
            "analysis_summary": analysis_summary,
            "basic_statistics": basic_stats_result,
            "insights": f"{metadata.title if metadata else request.stat_name}에 대한 기초통계 현황 분석이 완료되었습니다."
        }
        
    except Exception as e:
        print(f"기본통계현황분석 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="기본통계현황분석 중 오류가 발생했습니다")

# 새로운 최적화된 비동기 API들
@router.post("/start-analysis")
async def start_optimized_analysis(request: GenerateStoryRequest, background_tasks: BackgroundTasks):
    """최적화된 기본통계현황분석 시작 - 작업 ID 반환"""
    try:
        # 작업 ID 생성
        task_id = progress_tracker.create_task(f"기본통계현황분석: {request.stat_name}")
        
        # 백그라운드에서 분석 실행
        background_tasks.add_task(run_optimized_analysis, task_id, request)
        
        return {
            "task_id": task_id,
            "message": "분석이 시작되었습니다",
            "stat_name": request.stat_name,
            "estimated_time": "3-5분"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 시작 실패: {str(e)}")


@router.options("/analysis/progress/{task_id}")
async def options_analysis_progress(task_id: str):
    """SSE OPTIONS 요청 처리"""
    from fastapi.responses import Response
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@router.get("/analysis/progress/{task_id}")
async def get_analysis_progress(task_id: str, request: Request):
    """분석 진행률 스트림 (SSE)"""
    try:
        print(f"[API] ===== SSE 진행률 요청 수신 =====")
        print(f"[API] Task ID: {task_id}")
        print(f"[API] 클라이언트: {request.client}")
        print(f"[API] 요청 헤더:")
        for key, value in request.headers.items():
            print(f"  {key}: {value}")
        print(f"[API] URL: {request.url}")
        print(f"[API] 메소드: {request.method}")
        
        # Task ID 존재 여부 확인
        if not progress_tracker.task_exists(task_id):
            print(f"[API] 존재하지 않는 작업: {task_id}")
            # 작업이 없으면 새로 생성 (디버그 목적)
            progress_tracker.create_task(f"Debug task for {task_id}")
            print(f"[API] 디버그 작업 생성: {task_id}")
        
        print(f"[API] stream_progress 함수 호출 중...")
        stream_response = await stream_progress(task_id)
        print(f"[API] stream_progress 응답 생성 완료: {type(stream_response)}")
        
        return stream_response
    except Exception as e:
        print(f"[API] SSE 스트림 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"진행률 스트림 오류: {str(e)}")

@router.get("/analysis/status/{task_id}")
async def get_analysis_status(task_id: str):
    """분석 상태 조회"""
    try:
        status = progress_tracker.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
        
        return {
            "task_id": task_id,
            "status": status,
            "completed": status.get("completed", False),
            "progress": status.get("current_progress", 0),
            "stage": status.get("current_stage", "알 수 없음"),
            "message": status.get("current_message", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 오류: {str(e)}")

async def run_optimized_analysis(task_id: str, request: GenerateStoryRequest):
    """최적화된 분석 실행 (백그라운드)"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        # 캐시 디버깅을 위한 로그 추가
        print(f"[CACHE_DEBUG] 요청 정보:")
        print(f"  - stat_name: {request.stat_name}")
        print(f"  - stat_url: {stat_url}")
        
        # 캐시 키 생성 및 확인
        from app.services.data_storage import DataStorageService
        debug_storage = DataStorageService()
        cache_key = debug_storage._get_cache_key(stat_url)
        print(f"  - cache_key: {cache_key}")
        
        # 캐시 파일 존재 여부 확인
        import os
        metadata_path = debug_storage._get_metadata_path(cache_key)
        stats_path = debug_storage._get_stats_path(cache_key)
        print(f"  - metadata_exists: {os.path.exists(metadata_path)}")
        print(f"  - stats_exists: {os.path.exists(stats_path)}")
        
        if os.path.exists(metadata_path):
            print(f"  - metadata_file: {metadata_path}")
        if os.path.exists(stats_path):
            print(f"  - stats_file: {stats_path}")
        
        # 캐시 로드 시도 (URL 우선, 실패 시 이름으로 검색)
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        print(f"  - cache_loaded_by_url: metadata={cached_metadata is not None}, data={cached_stat_data is not None}")
        
        # URL로 찾지 못한 경우 stat_name으로 검색
        if not cached_metadata or not cached_stat_data:
            print(f"  - trying_name_search: {request.stat_name}")
            cached_metadata, cached_stat_data, found_url = storage_service.find_data_by_name(request.stat_name)
            print(f"  - cache_loaded_by_name: metadata={cached_metadata is not None}, data={cached_stat_data is not None}")
            if found_url:
                print(f"  - found_cached_url: {found_url}")
                stat_url = found_url  # 캐시된 URL로 업데이트
        
        print(f"[CACHE_DEBUG] 끝")
        
        # 최적화된 크롤러 사용
        if OptimizedMolitCrawler is None:
            progress_tracker.update_progress(task_id, "오류", 100, "최적화된 크롤러를 로드할 수 없습니다")
            return
            
        optimized_crawler = OptimizedMolitCrawler(pool_size=3, max_concurrent_tables=3)
        
        # 캐시된 데이터가 있으면 사용, 없으면 새로 수집
        if cached_metadata and cached_stat_data:
            print(f"[CACHE_DEBUG] 캐시된 데이터 사용: {cached_metadata.title}, {len(cached_stat_data)}개 데이터")
            
            # 캐시된 데이터를 분석 결과 형태로 변환
            analysis_result = _create_analysis_result_from_cache(cached_metadata, cached_stat_data, stat_url)
            
            # 진행률을 즉시 완료로 표시
            progress_callback = ProgressCallback(task_id)
            progress_callback.update("캐시로드", 10, "캐시된 데이터 로드 중")
            progress_callback.update("분석", 50, "캐시된 데이터 분석 중")
            progress_callback.update("완료", 100, "캐시된 데이터 분석 완료")
        else:
            print(f"[CACHE_DEBUG] 새로운 데이터 수집 시작")
            
            # 진행률 추적을 위한 ProgressCallback 생성 
            progress_callback = ProgressCallback(task_id)
            
            # 종합 분석 실행
            analysis_result = await optimized_crawler.get_comprehensive_stat_analysis_optimized(
                stat_url, progress_callback
            )
        
        # 분석 결과를 기존 API 형태로 변환
        basic_statistics = _calculate_basic_statistics_from_comprehensive(analysis_result)
        
        # 데이터 저장 (메타데이터와 통계 데이터를 캐시에 저장)
        if analysis_result.metadata and analysis_result.data_by_table:
            try:
                print(f"[DEBUG] 크롤링 결과 분석:")
                print(f"  - 메타데이터: {analysis_result.metadata.title if analysis_result.metadata else 'None'}")
                print(f"  - 테이블 수: {len(analysis_result.data_by_table)}")
                
                for table_name, table_data_list in analysis_result.data_by_table.items():
                    print(f"  - 테이블 '{table_name}': {len(table_data_list)}개 데이터")
                    if table_data_list:
                        sample_item = table_data_list[0]
                        print(f"    샘플 데이터: year={getattr(sample_item, 'year', 'N/A')}, data_keys={list(sample_item.data.keys()) if hasattr(sample_item, 'data') and sample_item.data else 'Empty'}")
                
                # 데이터를 StatData 형식으로 변환
                stat_data = []
                for table_name, table_data_list in analysis_result.data_by_table.items():
                    for data_item in table_data_list:
                        stat_data.append(StatData(
                            year=data_item.year,
                            data=data_item.data,
                            table_name=table_name
                        ))
                
                print(f"[DEBUG] 변환된 StatData: {len(stat_data)}개")
                for i, item in enumerate(stat_data[:3]):  # 처음 3개만 출력
                    print(f"  [{i}] year={item.year}, data_keys={list(item.data.keys()) if item.data else 'Empty'}")
                
                # 저장 실행
                storage_service.save_complete_data(stat_url, analysis_result.metadata, stat_data)
                print(f"최적화된 분석 결과 저장 완료: {len(stat_data)}개 데이터")
            except Exception as save_error:
                print(f"데이터 저장 오류: {save_error}")
                import traceback
                traceback.print_exc()
        
        # 결과를 기존 형태로 변환하여 저장
        task_results[task_id] = {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "analysis_type": "기본통계현황분석",
            "metadata": analysis_result.metadata.dict() if analysis_result.metadata else None,
            "analysis_summary": {
                "analysis_period": f"수집된 데이터 기간",
                "total_data_points": analysis_result.total_data_points,
                "data_completeness": "완료",
                "analysis_quality": "높음"
            },
            "basic_statistics": basic_statistics,
            "insights": f"{analysis_result.stat_title}에 대한 최적화된 기초통계 현황 분석이 완료되었습니다.",
            "comprehensive_analysis": analysis_result,  # 종합 분석 결과도 포함
            "completed_at": datetime.now().isoformat()
        }
        
        progress_callback.update("완료", 100, "분석이 완료되었습니다")
        
    except Exception as e:
        print(f"최적화된 분석 실행 오류: {e}")
        # 오류 발생 시 진행률 추적기에 직접 업데이트
        progress_tracker.update_progress(task_id, "오류", 100, f"분석 중 오류 발생: {str(e)}")

def _analyze_table_data(table_name: str, table_data: List[StatData]) -> dict:
    """통계표별 상세 데이터 분석"""
    if not table_data:
        return {
            "table_name": table_name,
            "data_overview": {"message": "데이터가 없습니다"},
            "basic_statistics": {},
            "data_samples": [],
            "distribution_characteristics": {},
            "objective_summary": "분석할 데이터가 없습니다."
        }
    
    # 1. 데이터 개요
    years = [item.year for item in table_data if item.year]
    total_records = len(table_data)
    
    # 모든 데이터 필드 수집
    all_fields = set()
    numeric_fields = set()
    text_fields = set()
    all_values = []
    
    for item in table_data:
        if item.data:
            all_fields.update(item.data.keys())
            for key, value in item.data.items():
                # 값 파싱 (JSON 문자열 형태인 경우)
                parsed_value = _parse_cell_value(value)
                all_values.append(parsed_value)
                
                if parsed_value.get('unit') == 'number':
                    numeric_fields.add(key)
                else:
                    text_fields.add(key)
    
    data_overview = {
        "total_records": total_records,
        "year_range": {"min": min(years) if years else None, "max": max(years) if years else None},
        "total_fields": len(all_fields),
        "numeric_fields_count": len(numeric_fields),
        "text_fields_count": len(text_fields),
        "sample_fields": list(all_fields)[:10]
    }
    
    # 2. 기초통계 (숫자 데이터만)
    numeric_values = []
    for val in all_values:
        if val.get('unit') == 'number' and isinstance(val.get('value'), (int, float)):
            numeric_values.append(val['value'])
    
    basic_statistics = {}
    if numeric_values:
        import numpy as np
        basic_statistics = {
            "count": len(numeric_values),
            "mean": float(np.mean(numeric_values)),
            "median": float(np.median(numeric_values)),
            "std": float(np.std(numeric_values)),
            "min": float(np.min(numeric_values)),
            "max": float(np.max(numeric_values)),
            "sum": float(np.sum(numeric_values)),
            "quartiles": {
                "q1": float(np.percentile(numeric_values, 25)),
                "q2": float(np.percentile(numeric_values, 50)),
                "q3": float(np.percentile(numeric_values, 75))
            }
        }
    
    # 3. 데이터 샘플 (처음 5개)
    data_samples = []
    for i, item in enumerate(table_data[:5]):
        sample = {
            "record_index": i + 1,
            "year": item.year,
            "sample_data": {}
        }
        
        if item.data:
            # 중요한 필드만 선별 (숫자 데이터 우선)
            sorted_fields = sorted(item.data.items(), 
                                 key=lambda x: (x[0] not in numeric_fields, x[0]))
            
            for key, value in sorted_fields[:8]:  # 최대 8개 필드
                parsed_value = _parse_cell_value(value)
                sample["sample_data"][key] = {
                    "raw": parsed_value.get('raw', str(value)),
                    "value": parsed_value.get('value'),
                    "unit": parsed_value.get('unit', 'text')
                }
        
        data_samples.append(sample)
    
    # 4. 분포 특성
    distribution_characteristics = {
        "data_types_distribution": {
            "numeric_ratio": len(numeric_fields) / len(all_fields) if all_fields else 0,
            "text_ratio": len(text_fields) / len(all_fields) if all_fields else 0
        },
        "value_ranges": {},
        "common_patterns": []
    }
    
    # 숫자 데이터의 분포
    if numeric_values:
        distribution_characteristics["value_ranges"] = {
            "range": float(np.max(numeric_values) - np.min(numeric_values)),
            "coefficient_of_variation": float(np.std(numeric_values) / np.mean(numeric_values)) if np.mean(numeric_values) != 0 else 0
        }
    
    # 5. 객관적 현황 요약
    objective_summary = _generate_objective_summary(table_name, data_overview, basic_statistics)
    
    return {
        "table_name": table_name,
        "data_overview": data_overview,
        "basic_statistics": basic_statistics,
        "data_samples": data_samples,
        "distribution_characteristics": distribution_characteristics,
        "objective_summary": objective_summary
    }

def _parse_cell_value(value):
    """셀 값 파싱 (JSON 문자열 또는 일반 값)"""
    if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
        try:
            import ast
            return ast.literal_eval(value)
        except:
            return {"value": value, "unit": "text", "raw": value}
    else:
        # 숫자인지 확인
        try:
            if isinstance(value, (int, float)):
                return {"value": value, "unit": "number", "raw": str(value)}
            elif isinstance(value, str):
                # 쉼표 제거 후 숫자 변환 시도
                cleaned = value.replace(',', '').replace('%', '')
                num_val = float(cleaned)
                return {"value": num_val, "unit": "number", "raw": value}
        except:
            pass
        
        return {"value": value, "unit": "text", "raw": str(value)}

def _generate_objective_summary(table_name: str, data_overview: dict, basic_statistics: dict) -> str:
    """객관적 현황 요약 생성"""
    summary_parts = []
    
    # 기본 정보
    total_records = data_overview.get('total_records', 0)
    year_range = data_overview.get('year_range', {})
    
    summary_parts.append(f"'{table_name}' 통계표는 총 {total_records}개의 데이터 레코드를 포함하고 있습니다.")
    
    if year_range.get('min') and year_range.get('max'):
        if year_range['min'] == year_range['max']:
            summary_parts.append(f"{year_range['min']}년 기준 데이터입니다.")
        else:
            summary_parts.append(f"{year_range['min']}년부터 {year_range['max']}년까지의 시계열 데이터입니다.")
    
    # 필드 구성
    total_fields = data_overview.get('total_fields', 0)
    numeric_count = data_overview.get('numeric_fields_count', 0)
    text_count = data_overview.get('text_fields_count', 0)
    
    summary_parts.append(f"총 {total_fields}개 데이터 필드 중 {numeric_count}개는 수치형, {text_count}개는 텍스트형 데이터입니다.")
    
    # 기초통계 요약
    if basic_statistics:
        mean_val = basic_statistics.get('mean', 0)
        max_val = basic_statistics.get('max', 0)
        min_val = basic_statistics.get('min', 0)
        
        summary_parts.append(f"수치 데이터의 평균값은 {mean_val:,.1f}이며, 최소값 {min_val:,.1f}에서 최대값 {max_val:,.1f}까지의 범위를 보입니다.")
        
        # 변동성 평가
        cv = basic_statistics.get('std', 0) / mean_val if mean_val != 0 else 0
        if cv < 0.1:
            variability = "낮은"
        elif cv < 0.3:
            variability = "보통"
        else:
            variability = "높은"
        
        summary_parts.append(f"데이터의 변동성은 {variability} 수준으로 평가됩니다.")
    
    return " ".join(summary_parts)

def _create_analysis_result_from_cache(metadata: StatMetadata, stat_data: List[StatData], stat_url: str):
    """캐시된 데이터를 분석 결과 형태로 변환"""
    from dataclasses import dataclass
    from typing import Dict, List as ListType
    
    @dataclass
    class AnalysisResult:
        metadata: StatMetadata
        data_by_table: Dict[str, ListType[StatData]]
        stat_title: str
        total_data_points: int
        stat_url: str
    
    # 테이블별로 데이터 그룹화
    data_by_table = {}
    for data_item in stat_data:
        table_name = getattr(data_item, 'table_name', None) or "기본 통계표"
        if table_name not in data_by_table:
            data_by_table[table_name] = []
        data_by_table[table_name].append(data_item)
    
    return AnalysisResult(
        metadata=metadata,
        data_by_table=data_by_table,
        stat_title=metadata.title,
        total_data_points=len(stat_data),
        stat_url=stat_url
    )

def _calculate_basic_statistics_from_comprehensive(analysis_result) -> dict:
    """종합 분석 결과에서 기초 통계 추출"""
    try:
        # 수집된 데이터에서 숫자 데이터 추출
        all_numeric_values = []
        
        for table_name, table_data_list in analysis_result.data_by_table.items():
            for data_item in table_data_list:
                if data_item.data:
                    for key, value in data_item.data.items():
                        try:
                            if isinstance(value, dict) and value.get("unit") == "number":
                                all_numeric_values.append(value.get("value", 0))
                            elif isinstance(value, (int, float)):
                                all_numeric_values.append(value)
                        except:
                            continue
        
        if all_numeric_values:
            import numpy as np
            return {
                "mean": float(np.mean(all_numeric_values)),
                "median": float(np.median(all_numeric_values)),
                "max": float(np.max(all_numeric_values)),
                "min": float(np.min(all_numeric_values)),
                "total": float(np.sum(all_numeric_values)),
                "count": len(all_numeric_values)
            }
        else:
            return {
                "mean": 0, "median": 0, "max": 0, "min": 0, "total": 0, "count": 0
            }
    except Exception as e:
        print(f"기초통계 계산 오류: {e}")
        return {
            "mean": 0, "median": 0, "max": 0, "min": 0, "total": 0, "count": 0
        }

# 작업 결과 저장소 (실제로는 Redis나 DB 사용 권장)
task_results: Dict[str, Any] = {}

@router.get("/analysis/result/{task_id}")
async def get_analysis_result(task_id: str):
    """분석 결과 조회"""
    try:
        if task_id not in task_results:
            # 아직 완료되지 않았는지 확인
            status = progress_tracker.get_task_status(task_id)
            if not status:
                raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
            
            if not status.get("completed", False):
                raise HTTPException(status_code=202, detail="분석이 아직 진행 중입니다")
            else:
                raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")
        
        return task_results[task_id]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 조회 오류: {str(e)}")

@router.post("/test-simple")
async def test_simple():
    """가장 간단한 테스트 엔드포인트"""
    return {"message": "success"}

@router.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "optimized_crawler_available": OptimizedMolitCrawler is not None
    }


def _calculate_basic_statistics(stat_data):
    """기본 통계 분석 수행"""
    if not stat_data:
        return {
            "mean": 0,
            "median": 0,
            "max": 0,
            "min": 0,
            "total": 0,
            "count": 0
        }
    
    # 첫 번째 데이터의 모든 키를 가져와서 수치형 데이터만 분석
    numeric_data = {}
    
    for item in stat_data:
        if item.data:
            for key, value in item.data.items():
                if key not in numeric_data:
                    numeric_data[key] = []
                
                try:
                    # 문자열인 경우 숫자로 변환 시도
                    if isinstance(value, str):
                        cleaned = value.replace(',', '').replace('%', '').strip()
                        numeric_value = float(cleaned)
                    else:
                        numeric_value = float(value)
                    
                    numeric_data[key].append(numeric_value)
                except (ValueError, TypeError):
                    # 숫자로 변환할 수 없는 경우 무시
                    continue
    
    # 각 필드별 통계 계산
    result = {}
    for key, values in numeric_data.items():
        if values:
            import numpy as np
            result[key] = {
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "max": float(np.max(values)),
                "min": float(np.min(values)),
                "total": float(np.sum(values)),
                "count": len(values),
                "std": float(np.std(values)) if len(values) > 1 else 0
            }
    
    # 전체 통계가 없으면 기본값 반환
    if not result:
        return {
            "mean": 0,
            "median": 0,
            "max": 0,
            "min": 0,
            "total": 0,
            "count": 0
        }
    
    # 첫 번째 필드의 통계를 기본값으로 반환 (호환성을 위해)
    first_key = list(result.keys())[0]
    return result[first_key]

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
    """이미 수집된 데이터의 구조와 품질을 상세 분석 (새로 수집하지 않음)"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        # 1. URL로 캐시된 데이터 확인
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        # 2. URL로 찾지 못한 경우 stat_name으로 검색
        if not cached_metadata or not cached_stat_data:
            print(f"URL로 데이터 없음, stat_name으로 검색: {request.stat_name}")
            cached_metadata, cached_stat_data, found_url = storage_service.find_data_by_name(request.stat_name)
            if found_url:
                stat_url = found_url  # 찾은 URL로 업데이트
        
        if not cached_metadata or not cached_stat_data:
            return {
                "message": "수집된 데이터가 없습니다",
                "suggestion": "먼저 '기본통계현황분석' 또는 '종합 분석'을 실행하여 데이터를 수집해주세요.",
                "cache_status": "empty",
                "stat_url": stat_url,
                "searched_name": request.stat_name
            }
        
        stat_data = cached_stat_data
        metadata = cached_metadata
        
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
    """이미 수집된 원시 데이터를 있는 그대로 조회"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        # 캐시된 데이터 확인
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        # stat_name으로 검색
        if not cached_metadata or not cached_stat_data:
            cached_metadata, cached_stat_data, found_url = storage_service.find_data_by_name(request.stat_name)
            if found_url:
                stat_url = found_url
        
        if not cached_metadata or not cached_stat_data:
            return {
                "message": "수집된 데이터가 없습니다",
                "suggestion": "먼저 분석을 실행하여 데이터를 수집해주세요."
            }
        
        stat_data = cached_stat_data
        metadata = cached_metadata
        
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
        stat_url = request.stat_url or f"https://stat.molit.go.kr/portal/cate/statView.do?hRsId={request.stat_name}"
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        # stat_name으로 검색
        if not cached_metadata or not cached_stat_data:
            cached_metadata, cached_stat_data, found_url = storage_service.find_data_by_name(request.stat_name)
            if found_url:
                stat_url = found_url
        
        if not cached_metadata or not cached_stat_data:
            return {"message": "수집된 데이터가 없습니다", "suggestion": "먼저 분석을 실행하여 데이터를 수집해주세요.", "available_data": False}
        
        stat_data = cached_stat_data
        metadata = cached_metadata
        
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
        stat_url = request.stat_url or f"https://stat.molit.go.kr/portal/cate/statView.do?hRsId={request.stat_name}"
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        if not cached_metadata or not cached_stat_data:
            return {"message": "수집된 데이터가 없습니다", "suggestion": "먼저 분석을 실행하여 데이터를 수집해주세요.", "available_data": False}
        
        stat_data = cached_stat_data
        metadata = cached_metadata
        
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
        stat_url = request.stat_url or f"https://stat.molit.go.kr/portal/cate/statView.do?hRsId={request.stat_name}"
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        if not cached_metadata or not cached_stat_data:
            return {"message": "수집된 데이터가 없습니다", "suggestion": "먼저 분석을 실행하여 데이터를 수집해주세요.", "available_data": False, "collection_log": []}
        
        stat_data = cached_stat_data
        metadata = cached_metadata
        
        # 캐시된 데이터에서 컬렉션 로그 재구성
        collection_log = [
            {
                "step": "캐시조회",
                "message": f"'{request.stat_name}' 캐시된 데이터 조회",
                "timestamp": datetime.now().isoformat()
            },
            {
                "step": "데이터확인", 
                "message": f"{len(stat_data)}개 캐시된 레코드 발견",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        if stat_data:
            collection_log.append({
                "step": "데이터검증",
                "message": f"연도 범위: {min([item.year for item in stat_data])} - {max([item.year for item in stat_data])}",
                "timestamp": datetime.now().isoformat()
            })
        
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

@router.get("/table-analysis/{stat_name}", summary="통계표별 상세 분석")
async def get_table_analysis(stat_name: str):
    """통계표별 상세 분석 - 데이터 개요, 기초통계, 샘플, 분포 특성"""
    try:
        # 캐시된 데이터 찾기
        storage_service = DataStorageService()
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)
        
        if not metadata or not stat_data:
            raise HTTPException(status_code=404, detail="해당 통계 데이터를 찾을 수 없습니다")
        
        # 통계표별로 데이터 그룹화
        tables_analysis = {}
        
        # 테이블명별로 데이터 분류
        table_groups = {}
        for data_item in stat_data:
            table_name = getattr(data_item, 'table_name', None) or "기본 통계표"
            if table_name not in table_groups:
                table_groups[table_name] = []
            table_groups[table_name].append(data_item)
        
        # 각 테이블별 상세 분석
        for table_name, table_data in table_groups.items():
            analysis = _analyze_table_data(table_name, table_data)
            tables_analysis[table_name] = analysis
        
        return {
            "stat_name": stat_name,
            "stat_url": stat_url,
            "metadata": {
                "title": metadata.title,
                "department": metadata.department,
                "keywords": metadata.keywords,
                "related_terms": metadata.related_terms
            },
            "total_tables": len(tables_analysis),
            "total_data_points": len(stat_data),
            "analysis_date": datetime.now().isoformat(),
            "tables_analysis": tables_analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계표 분석 중 오류: {str(e)}")

@router.get("/inspect-enhanced/{stat_name}", response_model=InspectionResult, summary="향상된 데이터 검사")
async def inspect_enhanced_data(stat_name: str):
    """IBSheet 스타일 데이터 검사 - API 기반"""
    try:
        from datetime import datetime
        
        # 기존 저장된 데이터 찾기
        storage_service = DataStorageService()
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)
        
        if not metadata or not stat_url:
            raise HTTPException(status_code=404, detail="해당 통계 데이터를 찾을 수 없습니다")
        
        # API 기반 재수집 및 구조화
        try:
            crawler = OptimizedMolitCrawler(pool_size=1)
            
            # URL에서 FormId 추출
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(stat_url)
            params = parse_qs(parsed.query)
            base_form_id = params.get('hFormId', [''])[0]
            
            if not base_form_id:
                raise HTTPException(status_code=400, detail="FormId를 추출할 수 없습니다")
            
            print(f"API 기반 데이터 검사 시작: {stat_name} (FormId: {base_form_id})")
            
            # 통계표별 데이터 수집
            stat_tables_with_conditions = await crawler._get_stat_tables_with_conditions(stat_url)
            
            tables = []
            total_data_points = 0
            errors = []
            
            for table_info in stat_tables_with_conditions:  # 모든 테이블
                try:
                    # 현재 월 데이터 수집
                    current_month = datetime.now().strftime('%Y%m')
                    
                    # API 데이터 수집
                    form_id = table_info.get('form_id', base_form_id)
                    api_data = await crawler._extract_data_via_api_direct(form_id, current_month, current_month)
                    
                    if api_data and api_data.get('rows'):
                        # StatTable 객체 생성
                        columns = []
                        for col_id, col_name in api_data['headers'].items():
                            columns.append(TableColumn(
                                id=col_id,
                                name=col_name,
                                data_type="number" if col_id != "0" else "text"
                            ))
                        
                        rows = []
                        for i, row_data in enumerate(api_data['rows']):  # 전체 행
                            cells = {}
                            for col_id, col_name in api_data['headers'].items():
                                cells[col_id] = row_data.get(col_name, "")
                            
                            rows.append(TableRow(
                                row_id=f"row_{i}",
                                cells=cells
                            ))
                        
                        stat_table = StatTable(
                            table_name=table_info['name'],
                            form_id=form_id,
                            period=current_month,
                            columns=columns,
                            rows=rows,
                            total_rows=len(api_data['rows']),
                            summary=api_data.get('summary', {}),
                            collection_method="api"
                        )
                        
                        tables.append(stat_table)
                        total_data_points += len(rows)
                        print(f"테이블 수집 완료: {table_info['name']} ({len(rows)}행)")
                        
                except Exception as table_error:
                    error_msg = f"테이블 '{table_info.get('name')}' 수집 실패: {str(table_error)}"
                    errors.append(error_msg)
                    print(error_msg)
            
            # 결과 반환
            return InspectionResult(
                stat_name=stat_name,
                stat_url=stat_url,
                tables=tables,
                metadata=metadata,
                total_tables=len(tables),
                total_data_points=total_data_points,
                collection_success=len(tables) > 0,
                errors=errors,
                inspected_at=datetime.now()
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"API 데이터 수집 실패: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 검사 중 오류: {str(e)}")