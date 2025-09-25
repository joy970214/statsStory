from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
from app.models.stat_models import GenerateStoryRequest
from app.services.crawler_service import CrawlerService
from app.services.ai_service import AIService
from app.services.data_storage import DataStorageService
from datetime import datetime

router = APIRouter()
crawler_service = CrawlerService()
ai_service = AIService()
storage_service = DataStorageService()

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

        # stat_name으로 검색 (정확히 일치하는 것만)
        if not cached_metadata or not cached_stat_data:
            cached_metadata, cached_stat_data, found_url = storage_service.find_data_by_name(request.stat_name)
            if found_url:
                # 실제 메타데이터의 title이 요청한 stat_name과 유연하게 일치하는지 확인
                if cached_metadata and hasattr(cached_metadata, 'title'):
                    actual_title = cached_metadata.title

                    # 제목 정규화 함수 (괄호 제거, 공백 제거)
                    def normalize_title(title: str) -> str:
                        import re
                        # 괄호와 그 안의 내용 제거
                        normalized = re.sub(r'\([^)]*\)', '', title)
                        # 연속된 공백을 하나로 변경하고 앞뒤 공백 제거
                        normalized = re.sub(r'\s+', ' ', normalized).strip()
                        return normalized

                    normalized_actual = normalize_title(actual_title)
                    normalized_request = normalize_title(request.stat_name)

                    # 정규화된 제목으로 비교 (포함 관계도 확인)
                    is_match = (
                        normalized_actual == normalized_request or
                        normalized_request in normalized_actual or
                        normalized_actual in normalized_request
                    )

                    if not is_match:
                        print(f"제목 불일치: 요청='{request.stat_name}' (정규화: '{normalized_request}'), 실제='{actual_title}' (정규화: '{normalized_actual}')")
                        cached_metadata = None
                        cached_stat_data = None
                    else:
                        print(f"제목 매칭 성공: 요청='{request.stat_name}', 실제='{actual_title}'")
                        stat_url = found_url

        if not cached_metadata or not cached_stat_data:
            return {
                "message": f"'{request.stat_name}' 데이터가 수집되지 않았습니다",
                "suggestion": f"'{request.stat_name}' 통계를 먼저 분석하여 데이터를 수집해주세요."
            }

        stat_data = cached_stat_data
        metadata = cached_metadata

        # raw_data 구성
        raw_data = [
            {
                "year": item.year,
                "data": item.data,
                "table_name": getattr(item, 'table_name', None)
            } for item in stat_data
        ]

        # raw_data_by_table 구성 (테이블별 그룹화)
        raw_data_by_table = {}

        # 메타데이터에서 실제 통계명 가져오기
        actual_stat_title = getattr(metadata, 'title', None) or request.stat_name

        for item in raw_data:
            table_name = item.get('table_name')

            # table_name이 없거나 기본값인 경우 메타데이터의 title 사용
            if not table_name or table_name in ['', '기본 통계표']:
                # 기간 정보 추가 (년도 범위 자동 계산)
                years = [int(item.get('year', 0)) for item in raw_data if item.get('year')]
                if years:
                    min_year = min(years)
                    max_year = max(years)
                    # YYYYMM 형식을 YYYY로 변환
                    if min_year > 10000:  # YYYYMM 형식인 경우
                        min_year = min_year // 100
                        max_year = max_year // 100
                    table_name = f"{actual_stat_title} ({min_year:04d}01 ~ {max_year:04d}08)"
                else:
                    table_name = actual_stat_title

            if table_name not in raw_data_by_table:
                raw_data_by_table[table_name] = []
            raw_data_by_table[table_name].append(item)

        return {
            "metadata": {
                "stat_name": request.stat_name,
                "collection_time": datetime.now().isoformat(),
                "source_info": getattr(metadata, 'url', None)
            },
            "raw_data": raw_data,
            "raw_data_by_table": raw_data_by_table
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