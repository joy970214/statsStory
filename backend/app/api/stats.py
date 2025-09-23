from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pathlib import Path
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
from app.services.stat_name_storage import stat_name_storage
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


def _store_stat_name_from_request(stat_name: str, stat_url: str):
    """요청에서 받은 통계명을 동적 저장소에 저장"""
    try:
        import re
        if 'hRsId=' in stat_url:
            hrsid_match = re.search(r'hRsId=(\d+)', stat_url)
            if hrsid_match and stat_name:
                hrsid = hrsid_match.group(1)
                # 기존에 저장된 통계명과 다르거나 없는 경우에만 저장
                existing_name = stat_name_storage.get_stat_name(hrsid)
                if not existing_name or existing_name != stat_name:
                    stat_name_storage.store_stat_name(hrsid, stat_name)
                    print(f"통계명 동적 저장: {hrsid} -> {stat_name}")
                else:
                    print(f"이미 동일한 통계명 저장됨: {hrsid} -> {stat_name}")
    except Exception as e:
        print(f"통계명 저장 중 오류: {e}")

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

        # 통계명을 동적 저장소에 저장
        _store_stat_name_from_request(request.stat_name, stat_url)

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


# 기존 동기식 API는 유지하되, 새로운 비동기 API 추가

@router.post("/generate-advanced-cardnews")
async def generate_advanced_cardnews(request: GenerateStoryRequest):
    """기본통계현황분석 - 즉시 응답 (기존 버전)"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"

        print(f"기본통계현황분석 요청: {request.stat_name}")

        # 통계명을 동적 저장소에 저장
        _store_stat_name_from_request(request.stat_name, stat_url)

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
        
        # 3. 기초통계 분석 수행 (개선된 분석 함수 사용)
        try:
            # 우리가 구현한 종합 분석 함수 사용
            basic_stats_result = _calculate_basic_statistics_from_comprehensive(stat_data)
            print("개선된 기초통계 분석 완료")
        except Exception as e:
            print(f"기초통계 분석 오류, 기본 분석으로 대체: {e}")
            # 기본 통계 분석 수행
            basic_stats_result = _calculate_basic_statistics(stat_data)
        
        # 4. 분석 요약 생성
        analysis_summary = {
            "analysis_period": f"{min([d.year for d in stat_data])} - {max([d.year for d in stat_data])}" if stat_data else "N/A",
            "total_data_points": len(stat_data),
            "data_completeness": "완료",
            "analysis_quality": "높음"
        }
        
        # 5. raw_data 수집 (실제 수집된 데이터)
        raw_data = []
        raw_data_by_table = {}
        try:
            # stat_data에서 raw_data 추출
            for data_item in stat_data:
                if hasattr(data_item, 'data') and data_item.data:
                    table_name = getattr(data_item, 'table_name', f"통계표 {data_item.year}")
                    raw_data.append({
                        "table_name": table_name,
                        "year": data_item.year,
                        "data": data_item.data
                    })
                    if table_name not in raw_data_by_table:
                        raw_data_by_table[table_name] = []
                    raw_data_by_table[table_name].append({
                        "table_name": table_name,
                        "year": data_item.year,
                        "data": data_item.data
                    })
        except Exception as raw_error:
            print(f"raw_data 수집 오류: {raw_error}")

        # 6. 메타데이터에 새로운 필드들 추가 (통계정보, 관련용어 등)
        enhanced_metadata = metadata.dict() if metadata else {}
        if metadata:
            # 새로 수집된 메타데이터 필드들 추가
            enhanced_metadata.update({
                "search_field": getattr(metadata, 'search_field', None),
                "responsible_department": getattr(metadata, 'responsible_department', None),
                "statistical_info": getattr(metadata, 'statistical_info', {}),
                "major_items": getattr(metadata, 'major_items', {}),
                "meaning_analysis": getattr(metadata, 'meaning_analysis', {}),
                "terminology": getattr(metadata, 'terminology', {})
            })

        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "analysis_type": "기본통계현황분석",
            "metadata": enhanced_metadata,
            "analysis_summary": analysis_summary,
            "basic_statistics": basic_stats_result,
            "raw_data": raw_data,
            "raw_data_by_table": raw_data_by_table,
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
        # 통계명을 동적 저장소에 저장
        if request.stat_url:
            _store_stat_name_from_request(request.stat_name, request.stat_url)

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
        # SSE 연결이 먼저 완료되도록 2초 지연
        print(f"[TASK] 분석 시작 전 SSE 연결 대기: {task_id}")
        await asyncio.sleep(2)

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
        
        # URL로 찾지 못한 경우 stat_name으로 검색 (정확한 제목 일치 확인)
        if not cached_metadata or not cached_stat_data:
            print(f"  - trying_name_search: {request.stat_name}")
            cached_metadata, cached_stat_data, found_url = storage_service.find_data_by_name(request.stat_name)
            print(f"  - cache_loaded_by_name: metadata={cached_metadata is not None}, data={cached_stat_data is not None}")

            # 제목이 유연하게 일치하는지 확인
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
                    print(f"  - title_mismatch: 요청='{request.stat_name}' (정규화: '{normalized_request}'), 실제='{actual_title}' (정규화: '{normalized_actual}')")
                    cached_metadata = None
                    cached_stat_data = None
                elif found_url:
                    print(f"  - title_match_success: 요청='{request.stat_name}', 실제='{actual_title}'")
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

        # URL 검증 및 제안
        from app.services.url_validator import URLValidator
        url_validator = URLValidator()

        # 수집된 테이블명 추출 (다양한 데이터 타입 지원)
        collected_table_names = []
        try:
            if hasattr(analysis_result, 'collected_tables'):
                collected_table_names = [table.table_name for table in analysis_result.collected_tables]
            elif hasattr(analysis_result, 'data_by_table'):
                collected_table_names = list(analysis_result.data_by_table.keys())
            elif isinstance(analysis_result, list):
                # 캐시된 데이터 (리스트 형태)인 경우
                collected_table_names = [item.table_name for item in analysis_result if hasattr(item, 'table_name')]
        except Exception as e:
            print(f"테이블명 추출 중 오류: {e}")

        validation_result = url_validator.validate_url_and_suggest(stat_url, collected_table_names, request.stat_name)

        # 검증 결과 로깅
        if validation_result.get("url_mismatch"):
            print(f"⚠️ URL 불일치 감지:")
            print(f"  요청 URL: {stat_url}")
            print(f"  수집된 테이블: {collected_table_names}")
            if validation_result.get("correct_url"):
                print(f"  올바른 URL: {validation_result['correct_url']}")
                print(f"  올바른 통계명: {validation_result['detected_stat_name']}")
        else:
            print(f"✅ URL 검증 통과: {stat_url}")
        
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
            "url_validation": {
                "is_valid": validation_result.get("is_valid", True),
                "warnings": validation_result.get("validation_warnings", []),
                "url_mismatch": validation_result.get("url_mismatch", False),
                "correct_url": validation_result.get("correct_url"),
                "detected_stat_name": validation_result.get("detected_stat_name"),
                "validation_message": url_validator.format_validation_message(validation_result)
            },
            "insights": f"{analysis_result.stat_title}에 대한 기초통계 현황 분석이 완료되었습니다.",
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
    
    # 3. 데이터 샘플 (원본 테이블 형태)
    data_samples = []
    original_table_format = None

    # _table_data에서 원본 테이블 형태 생성 시도
    for item in table_data:
        if hasattr(item, 'data') and item.data and '_table_data' in item.data:
            try:
                original_table_format = _generate_original_table_format(item.data['_table_data'])
                break
            except Exception as e:
                print(f"원본 테이블 형태 생성 실패: {e}")

    # 기존 샘플 데이터도 유지 (백업용)
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
    
    result = {
        "table_name": table_name,
        "data_overview": data_overview,
        "basic_statistics": basic_statistics,
        "data_samples": data_samples,
        "distribution_characteristics": distribution_characteristics,
        "objective_summary": objective_summary
    }

    # 원본 테이블 형태가 생성되었으면 추가
    if original_table_format:
        result["original_table_format"] = original_table_format

    return result

def _generate_original_table_format(table_data_str):
    """_table_data를 원본 테이블 형태로 변환"""
    try:
        import json
        import ast

        # JSON 문자열 또는 파이썬 표현식 파싱
        if isinstance(table_data_str, str):
            try:
                # JSON으로 파싱 시도
                table_data = json.loads(table_data_str)
            except json.JSONDecodeError:
                # JSON 파싱 실패시 ast.literal_eval 시도
                table_data = ast.literal_eval(table_data_str)
        else:
            table_data = table_data_str

        # 테이블 구조 분석
        headers = []
        data_rows = []

        # 헤더 찾기
        header_row = None
        for row in table_data:
            if row.get('is_header', False):
                header_row = row
                break

        if header_row:
            # 헤더 셀들을 col_index 순으로 정렬
            header_cells = sorted(header_row.get('cells', []), key=lambda x: x.get('col_index', 0))
            headers = [cell.get('value', {}).get('value', f"컬럼{cell.get('col_index', 0)}") for cell in header_cells]

        # 데이터 행 처리 (최대 10행만)
        data_row_count = 0
        for row in table_data:
            if not row.get('is_header', False) and data_row_count < 10:
                cells = row.get('cells', [])
                if cells:  # 빈 행이 아닌 경우만
                    # 셀들을 col_index 순으로 정렬
                    sorted_cells = sorted(cells, key=lambda x: x.get('col_index', 0))

                    # 행 데이터 구성
                    row_data = {}
                    for i, cell in enumerate(sorted_cells):
                        col_name = headers[i] if i < len(headers) else f"컬럼{i+1}"
                        cell_value = cell.get('value', {})

                        row_data[col_name] = {
                            'value': cell_value.get('value', ''),
                            'unit': cell_value.get('unit', 'text'),
                            'raw': cell_value.get('raw', '')
                        }

                    if row_data:  # 빈 행이 아닌 경우만 추가
                        data_rows.append(row_data)
                        data_row_count += 1

        return {
            'headers': headers,
            'data_rows': data_rows,
            'total_rows': len(data_rows),
            'display_note': '원본 사이트 테이블 형태로 표시 (최대 10행)'
        }

    except Exception as e:
        print(f"원본 테이블 형태 생성 중 오류: {e}")
        return None


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
    table_counter = 1
    for data_item in stat_data:
        table_name = getattr(data_item, 'table_name', None)

        # 실제 수집된 테이블명 사용 - 키워드 추가하지 않음
        if not table_name or table_name.strip() in ['', '기본 통계표']:
            # 테이블명이 완전히 없는 경우만 기본명 사용
            table_name = f"통계표 {table_counter}"
            table_counter += 1
        # 실제 수집된 테이블명이 있으면 그대로 사용 (키워드 추가 제거)

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
    """종합 분석 결과에서 기초 통계 추출 (대폭 개선된 버전)"""
    try:
        # 수집된 데이터에서 숫자 데이터 추출 - 더 포괄적인 파싱
        all_numeric_values = []

        print("=== 기초통계 계산 시작 ===")

        for table_name, table_data_list in analysis_result.data_by_table.items():
            print(f"테이블 '{table_name}' 처리 중 ({len(table_data_list)}개 데이터)")

            for data_item in table_data_list:
                if data_item.data:
                    # 기본 데이터 필드에서 숫자 추출
                    for key, value in data_item.data.items():
                        try:
                            # 딕셔너리 형태의 값 처리
                            if isinstance(value, dict) and value.get("unit") == "number":
                                numeric_val = value.get("value")
                                if isinstance(numeric_val, (int, float)):
                                    all_numeric_values.append(numeric_val)

                            # 직접적인 숫자 값 처리
                            elif isinstance(value, (int, float)):
                                all_numeric_values.append(value)

                            # JSON 문자열 처리 (_table_data 필드) - 더 상세하게
                            elif isinstance(value, str) and key == "_table_data":
                                try:
                                    import json
                                    table_data = json.loads(value)
                                    if isinstance(table_data, list):
                                        for row in table_data:
                                            if isinstance(row, dict) and 'cells' in row:
                                                for cell in row.get('cells', []):
                                                    if isinstance(cell, dict) and 'value' in cell:
                                                        cell_value = cell['value']
                                                        if isinstance(cell_value, dict):
                                                            if cell_value.get('unit') == 'number':
                                                                numeric_val = cell_value.get('value')
                                                                if isinstance(numeric_val, (int, float)):
                                                                    all_numeric_values.append(numeric_val)
                                except Exception as json_error:
                                    print(f"JSON 파싱 오류: {json_error}")
                                    continue

                            # 문자열에서 숫자 추출 시도
                            elif isinstance(value, str) and value.strip():
                                # 쉼표가 포함된 숫자 처리 (예: "21,400")
                                try:
                                    clean_value = value.replace(',', '').replace(' ', '').strip()
                                    if clean_value.lstrip('-').replace('.', '').isdigit():
                                        numeric_val = float(clean_value)
                                        all_numeric_values.append(numeric_val)
                                except:
                                    continue

                        except Exception as extract_error:
                            continue

        print(f"1차 추출된 숫자 데이터 개수: {len(all_numeric_values)}")

        # 유효한 숫자만 필터링 (NaN, Infinity 제거)
        valid_numeric_values = []
        for val in all_numeric_values:
            try:
                if isinstance(val, (int, float)) and not (val != val or val == float('inf') or val == float('-inf')):
                    valid_numeric_values.append(float(val))
            except:
                continue

        print(f"유효한 숫자 데이터 개수: {len(valid_numeric_values)}")

        # 이상값 필터링 (너무 극단적인 값 제거)
        if len(valid_numeric_values) > 10:
            # IQR 방식으로 이상값 제거
            import numpy as np
            q1 = np.percentile(valid_numeric_values, 25)
            q3 = np.percentile(valid_numeric_values, 75)
            iqr = q3 - q1
            lower_bound = q1 - 3 * iqr  # 3*IQR로 느슨하게 설정
            upper_bound = q3 + 3 * iqr

            filtered_values = [val for val in valid_numeric_values if lower_bound <= val <= upper_bound]

            print(f"이상값 제거 후: {len(filtered_values)}개 (제거된: {len(valid_numeric_values) - len(filtered_values)}개)")
            valid_numeric_values = filtered_values

        print(f"최종 숫자 데이터 개수: {len(valid_numeric_values)}")
        if len(valid_numeric_values) > 0:
            print(f"샘플 값들: {sorted(valid_numeric_values)[:10]}")  # 정렬된 처음 10개 출력

        if valid_numeric_values:
            import numpy as np

            result = {
                "mean": float(np.mean(valid_numeric_values)),
                "median": float(np.median(valid_numeric_values)),
                "max": float(np.max(valid_numeric_values)),
                "min": float(np.min(valid_numeric_values)),
                "total": float(np.sum(valid_numeric_values)),
                "count": len(valid_numeric_values)
            }

            print(f"계산된 기초통계:")
            print(f"  - 평균: {result['mean']:.2f}")
            print(f"  - 중위수: {result['median']:.2f}")
            print(f"  - 최댓값: {result['max']:.2f}")
            print(f"  - 최솟값: {result['min']:.2f}")
            print(f"  - 총합: {result['total']:.2f}")
            print(f"  - 개수: {result['count']}")

            return result
        else:
            print("계산할 수 있는 숫자 데이터가 없습니다")
            return {
                "mean": 0, "median": 0, "max": 0, "min": 0, "total": 0, "count": 0
            }
    except Exception as e:
        print(f"기초통계 계산 오류: {e}")
        import traceback
        traceback.print_exc()
        return {
            "mean": 0, "median": 0, "max": 0, "min": 0, "total": 0, "count": 0
        }

# 작업 결과 저장소 (실제로는 Redis나 DB 사용 권장)
task_results: Dict[str, Any] = {}

# 필요한 import 추가
import json
import os

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

@router.delete("/analysis/cancel/{task_id}")
async def cancel_analysis(task_id: str):
    """분석 작업 취소"""
    try:
        # 진행률 추적기에서 작업 상태 확인
        status = progress_tracker.get_task_status(task_id)

        if not status:
            # 작업이 없어도 성공으로 처리 (이미 완료되었거나 만료된 경우)
            print(f"[취소 API] 작업을 찾을 수 없음: {task_id} - 이미 완료되었거나 만료된 것으로 간주")
            return {"message": "작업이 이미 완료되었거나 존재하지 않습니다", "task_id": task_id}

        # 이미 완료된 작업인지 확인
        if status.get("completed", False):
            print(f"[취소 API] 이미 완료된 작업: {task_id}")
            return {"message": "이미 완료된 작업입니다", "task_id": task_id}

        # 작업 취소 - 진행률 업데이트로 취소 상태 설정
        print(f"[취소 API] 작업 취소 중: {task_id}")
        progress_tracker.update_progress(
            task_id=task_id,
            stage="cancelled",
            progress=100,
            message="사용자에 의해 취소됨"
        )

        # active_tasks에서 취소 플래그 설정
        if task_id in progress_tracker.active_tasks:
            progress_tracker.active_tasks[task_id]["cancelled"] = True

        # 메모리에서 결과 제거 (있다면)
        if task_id in task_results:
            del task_results[task_id]
            print(f"[취소 API] 메모리에서 결과 제거: {task_id}")

        print(f"[취소 API] 작업 취소 완료: {task_id}")
        return {"message": "작업이 취소되었습니다", "task_id": task_id}

    except Exception as e:
        print(f"[취소 API] 작업 취소 오류: {task_id}, 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"작업 취소 오류: {str(e)}")

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
    """기본 통계 분석 수행 - _table_data JSON 구조 파싱 지원"""
    if not stat_data:
        return {
            "mean": 0,
            "median": 0,
            "max": 0,
            "min": 0,
            "total": 0,
            "count": 0
        }

    # 모든 숫자 데이터를 수집
    numeric_values = []

    for item in stat_data:
        if item.data:
            # _table_data가 있는 경우 JSON 파싱
            if '_table_data' in item.data:
                try:
                    import json
                    table_data_str = item.data['_table_data']
                    table_data = json.loads(table_data_str)

                    # 각 행의 셀에서 숫자 데이터 추출
                    for row in table_data:
                        if 'cells' in row:
                            for cell in row['cells']:
                                if 'value' in cell and isinstance(cell['value'], dict):
                                    cell_value = cell['value']
                                    if cell_value.get('unit') == 'number' and isinstance(cell_value.get('value'), (int, float)):
                                        numeric_values.append(cell_value['value'])
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"_table_data 파싱 오류: {e}")
                    continue

            # 기존 방식으로도 데이터 수집 (호환성 유지)
            for key, value in item.data.items():
                if key.startswith('_'):  # _table_data, _table_headers 등은 건너뛰기
                    continue

                try:
                    # 문자열인 경우 숫자로 변환 시도
                    if isinstance(value, str):
                        cleaned = value.replace(',', '').replace('%', '').strip()
                        numeric_value = float(cleaned)
                        numeric_values.append(numeric_value)
                    elif isinstance(value, (int, float)):
                        numeric_values.append(float(value))
                except (ValueError, TypeError):
                    # 숫자로 변환할 수 없는 경우 무시
                    continue

    # 통계 계산
    if not numeric_values:
        return {
            "mean": 0,
            "median": 0,
            "max": 0,
            "min": 0,
            "total": 0,
            "count": 0,
            "std_dev": 0
        }

    import numpy as np

    return {
        "mean": float(np.mean(numeric_values)),
        "median": float(np.median(numeric_values)),
        "max": float(np.max(numeric_values)),
        "min": float(np.min(numeric_values)),
        "total": float(np.sum(numeric_values)),
        "count": len(numeric_values),
        "std_dev": float(np.std(numeric_values)) if len(numeric_values) > 1 else 0
    }

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
        table_counter = 1
        for data_item in stat_data:
            table_name = getattr(data_item, 'table_name', None)

            # 실제 수집된 테이블명 사용 - 키워드 추가하지 않음
            if not table_name or table_name.strip() in ['', '기본 통계표']:
                # 테이블명이 완전히 없는 경우만 기본명 사용
                table_name = f"통계표 {table_counter}"
                table_counter += 1
            # 실제 수집된 테이블명이 있으면 그대로 사용 (키워드 추가 제거)

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

# ===== 새로운 통계표명 기반 분석 API들 =====

@router.get("/stats-list", summary="수집된 통계표 목록 조회")
async def get_collected_stats_list():
    """수집된 모든 통계표의 실제 통계표명 목록 반환"""
    try:
        storage_service = DataStorageService()
        stats_list = []

        # 모든 메타데이터 파일 확인
        if not os.path.exists(storage_service.metadata_dir):
            return {"message": "수집된 통계표가 없습니다", "stats": []}

        for filename in os.listdir(storage_service.metadata_dir):
            if not filename.endswith('_metadata.json'):
                continue

            file_path = os.path.join(storage_service.metadata_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                metadata_dict = data['metadata']
                cache_key = data['cache_key']

                # 통계 데이터 로드하여 기본 정보 확인
                stat_url = data['stat_url']
                stat_data = storage_service.load_statistics(stat_url)

                # 데이터 필드 분석
                total_fields = 0
                numeric_fields = 0
                text_fields = 0
                table_names = set()

                if stat_data:
                    for item in stat_data:
                        if hasattr(item, 'table_name') and item.table_name:
                            table_names.add(item.table_name)
                        if item.data:
                            total_fields += len(item.data)
                            for key, value in item.data.items():
                                try:
                                    if isinstance(value, (int, float)):
                                        numeric_fields += 1
                                    elif isinstance(value, str):
                                        try:
                                            float(value.replace(',', '').replace('%', ''))
                                            numeric_fields += 1
                                        except ValueError:
                                            text_fields += 1
                                    else:
                                        text_fields += 1
                                except:
                                    text_fields += 1

                stat_info = {
                    "stat_name": metadata_dict.get('title', 'Unknown'),
                    "cache_key": cache_key,
                    "stat_url": stat_url,
                    "department": metadata_dict.get('department', ''),
                    "keywords": metadata_dict.get('keywords', []),
                    "total_data_points": len(stat_data) if stat_data else 0,
                    "data_fields_info": {
                        "total_fields": total_fields,
                        "numeric_fields": numeric_fields,
                        "text_fields": text_fields
                    },
                    "table_names": list(table_names),
                    "saved_at": data.get('saved_at', '')
                }

                stats_list.append(stat_info)

            except Exception as e:
                print(f"메타데이터 파일 처리 오류: {filename} -> {e}")
                continue

        # 저장 시간 기준 내림차순 정렬
        stats_list.sort(key=lambda x: x['saved_at'], reverse=True)

        return {
            "total_collected_stats": len(stats_list),
            "stats": stats_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계표 목록 조회 오류: {str(e)}")

@router.get("/stats-detail/{stat_name}", summary="통계표명별 상세 정보")
async def get_stat_detail_by_name(stat_name: str):
    """실제 통계표명으로 상세 정보 조회 - 총 데이터 필드, 숫자/텍스트 데이터 구분, 샘플 데이터"""
    try:
        storage_service = DataStorageService()
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)

        if not metadata or not stat_data:
            raise HTTPException(status_code=404, detail="해당 통계표 데이터를 찾을 수 없습니다")

        # 통계표별로 데이터 그룹화
        table_groups = {}
        table_counter = 1
        for data_item in stat_data:
            table_name = getattr(data_item, 'table_name', None)

            # 테이블명이 없거나 기본값인 경우 개선된 이름 사용
            if not table_name or table_name in ['', '기본 통계표']:
                # 메타데이터에서 키워드 사용하여 의미있는 이름 생성
                if metadata and metadata.keywords:
                    table_name = f"{metadata.keywords[0]} 통계표 {table_counter}"
                else:
                    table_name = f"통계표 {table_counter}"
                table_counter += 1
            elif table_name.startswith('테이블') and table_name[2:].isdigit():
                # "테이블1", "테이블2" 같은 기본값 개선
                if metadata and metadata.keywords:
                    table_name = f"{metadata.keywords[0]} {table_name}"
                else:
                    table_name = f"수집된 {table_name}"

            if table_name not in table_groups:
                table_groups[table_name] = []
            table_groups[table_name].append(data_item)

        # 각 통계표별 상세 분석
        tables_detail = {}
        for table_name, table_data in table_groups.items():
            # 데이터 필드 분석
            all_fields = set()
            numeric_fields = set()
            text_fields = set()

            for item in table_data:
                if item.data:
                    all_fields.update(item.data.keys())
                    for key, value in item.data.items():
                        try:
                            if isinstance(value, (int, float)):
                                numeric_fields.add(key)
                            elif isinstance(value, str):
                                try:
                                    float(value.replace(',', '').replace('%', ''))
                                    numeric_fields.add(key)
                                except ValueError:
                                    text_fields.add(key)
                            else:
                                text_fields.add(key)
                        except:
                            text_fields.add(key)

            # 샘플 데이터 (처음 3개)
            sample_data = []
            for i, item in enumerate(table_data[:3]):
                sample = {
                    "sample_index": i + 1,
                    "year": item.year,
                    "data_preview": {}
                }

                if item.data:
                    # 중요한 필드 우선 (숫자 데이터 먼저)
                    sorted_fields = sorted(item.data.items(),
                                         key=lambda x: (x[0] not in numeric_fields, x[0]))

                    for key, value in sorted_fields[:5]:  # 최대 5개 필드
                        sample["data_preview"][key] = {
                            "value": value,
                            "type": "numeric" if key in numeric_fields else "text"
                        }

                sample_data.append(sample)

            tables_detail[table_name] = {
                "total_records": len(table_data),
                "year_range": {
                    "min_year": min([item.year for item in table_data]) if table_data else None,
                    "max_year": max([item.year for item in table_data]) if table_data else None
                },
                "data_fields": {
                    "total_fields": len(all_fields),
                    "numeric_fields": list(numeric_fields),
                    "text_fields": list(text_fields),
                    "numeric_count": len(numeric_fields),
                    "text_count": len(text_fields)
                },
                "sample_data": sample_data
            }

        return {
            "stat_name": stat_name,
            "stat_url": stat_url,
            "metadata": {
                "title": metadata.title,
                "department": metadata.department,
                "keywords": metadata.keywords,
                "purpose": getattr(metadata, 'purpose', None),
                "frequency": getattr(metadata, 'frequency', None),
                "contact": getattr(metadata, 'contact', None),
                "search_field": getattr(metadata, 'search_field', None),
                "responsible_department": getattr(metadata, 'responsible_department', None),
                "statistical_info": getattr(metadata, 'statistical_info', None),
                "major_items": getattr(metadata, 'major_items', None),
                "meaning_analysis": getattr(metadata, 'meaning_analysis', None),
                "terminology": getattr(metadata, 'terminology', None),
                "related_terms": getattr(metadata, 'related_terms', None)
            },
            "total_tables": len(tables_detail),
            "total_data_points": len(stat_data),
            "tables_detail": tables_detail
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계표 상세 정보 조회 오류: {str(e)}")

@router.get("/stats-distribution/{stat_name}", summary="통계표별 데이터 분포 특성 분석")
async def get_stat_distribution_analysis(stat_name: str):
    """통계표명별 데이터 분포 특성 및 통계적 특성 분석"""
    try:
        storage_service = DataStorageService()
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)

        if not metadata or not stat_data:
            raise HTTPException(status_code=404, detail="해당 통계표 데이터를 찾을 수 없습니다")

        # 통계표별 분포 분석
        table_groups = {}
        table_counter = 1
        for data_item in stat_data:
            table_name = getattr(data_item, 'table_name', None)

            # 실제 수집된 테이블명 사용 - 키워드 추가하지 않음
            if not table_name or table_name.strip() in ['', '기본 통계표']:
                # 테이블명이 완전히 없는 경우만 기본명 사용
                table_name = f"통계표 {table_counter}"
                table_counter += 1
            # 실제 수집된 테이블명이 있으면 그대로 사용 (키워드 추가 제거)

            if table_name not in table_groups:
                table_groups[table_name] = []
            table_groups[table_name].append(data_item)

        distribution_analysis = {}

        for table_name, table_data in table_groups.items():
            # 숫자 데이터 수집
            numeric_values = []
            field_distributions = {}

            for item in table_data:
                if item.data:
                    for key, value in item.data.items():
                        if key not in field_distributions:
                            field_distributions[key] = {"values": [], "type": "unknown"}

                        try:
                            if isinstance(value, (int, float)):
                                numeric_val = float(value)
                                numeric_values.append(numeric_val)
                                field_distributions[key]["values"].append(numeric_val)
                                field_distributions[key]["type"] = "numeric"
                            elif isinstance(value, str):
                                try:
                                    numeric_val = float(value.replace(',', '').replace('%', ''))
                                    numeric_values.append(numeric_val)
                                    field_distributions[key]["values"].append(numeric_val)
                                    field_distributions[key]["type"] = "numeric"
                                except ValueError:
                                    field_distributions[key]["values"].append(value)
                                    field_distributions[key]["type"] = "text"
                            else:
                                field_distributions[key]["values"].append(str(value))
                                field_distributions[key]["type"] = "text"
                        except:
                            field_distributions[key]["values"].append(str(value))
                            field_distributions[key]["type"] = "text"

            # 기초 통계 계산
            basic_stats = {}
            if numeric_values:
                import numpy as np
                basic_stats = {
                    "count": len(numeric_values),
                    "mean": float(np.mean(numeric_values)),
                    "median": float(np.median(numeric_values)),
                    "std": float(np.std(numeric_values)),
                    "min": float(np.min(numeric_values)),
                    "max": float(np.max(numeric_values)),
                    "quartiles": {
                        "q1": float(np.percentile(numeric_values, 25)),
                        "q2": float(np.percentile(numeric_values, 50)),
                        "q3": float(np.percentile(numeric_values, 75))
                    },
                    "skewness": float(np.mean(((np.array(numeric_values) - np.mean(numeric_values)) / np.std(numeric_values)) ** 3)) if len(numeric_values) > 2 else 0
                }

            # 필드별 상세 분포
            field_stats = {}
            for field_name, field_info in field_distributions.items():
                if field_info["type"] == "numeric" and len(field_info["values"]) > 0:
                    values = field_info["values"]
                    import numpy as np
                    field_stats[field_name] = {
                        "type": "numeric",
                        "count": len(values),
                        "mean": float(np.mean(values)),
                        "std": float(np.std(values)),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "range": float(np.max(values) - np.min(values)),
                        "coefficient_of_variation": float(np.std(values) / np.mean(values)) if np.mean(values) != 0 else 0
                    }
                elif field_info["type"] == "text":
                    values = field_info["values"]
                    unique_values = list(set(values))
                    field_stats[field_name] = {
                        "type": "text",
                        "count": len(values),
                        "unique_count": len(unique_values),
                        "most_common": max(set(values), key=values.count) if values else None,
                        "sample_values": unique_values[:5]
                    }

            # 데이터 품질 평가
            data_quality = {
                "completeness": len([item for item in table_data if item.data]) / len(table_data) * 100 if table_data else 0,
                "consistency": len([f for f, info in field_distributions.items() if info["type"] != "unknown"]) / len(field_distributions) * 100 if field_distributions else 0,
                "numeric_ratio": len([f for f, info in field_distributions.items() if info["type"] == "numeric"]) / len(field_distributions) * 100 if field_distributions else 0
            }

            distribution_analysis[table_name] = {
                "basic_statistics": basic_stats,
                "field_statistics": field_stats,
                "data_quality": data_quality,
                "distribution_characteristics": {
                    "total_numeric_values": len(numeric_values),
                    "data_variability": "높음" if basic_stats.get("std", 0) / basic_stats.get("mean", 1) > 0.5 else "낮음" if basic_stats.get("std", 0) / basic_stats.get("mean", 1) < 0.2 else "보통",
                    "distribution_type": "정규분포 유사" if abs(basic_stats.get("skewness", 0)) < 0.5 else "치우침 분포"
                }
            }

        return {
            "stat_name": stat_name,
            "analysis_type": "데이터 분포 특성 분석",
            "total_tables": len(distribution_analysis),
            "analysis_date": datetime.now().isoformat(),
            "distribution_analysis": distribution_analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분포 특성 분석 오류: {str(e)}")

@router.get("/stats-summary/{stat_name}", summary="통계표별 객관적 현황 요약")
async def get_stat_objective_summary(stat_name: str):
    """통계표명별 객관적이고 구체적인 현황 요약 제공"""
    try:
        storage_service = DataStorageService()
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)

        if not metadata or not stat_data:
            raise HTTPException(status_code=404, detail="해당 통계표 데이터를 찾을 수 없습니다")

        # 통계표별 객관적 요약 생성
        table_groups = {}
        table_counter = 1
        for data_item in stat_data:
            table_name = getattr(data_item, 'table_name', None)

            # 실제 수집된 테이블명 사용 - 키워드 추가하지 않음
            if not table_name or table_name.strip() in ['', '기본 통계표']:
                # 테이블명이 완전히 없는 경우만 기본명 사용
                table_name = f"통계표 {table_counter}"
                table_counter += 1
            # 실제 수집된 테이블명이 있으면 그대로 사용 (키워드 추가 제거)

            if table_name not in table_groups:
                table_groups[table_name] = []
            table_groups[table_name].append(data_item)

        table_summaries = {}

        for table_name, table_data in table_groups.items():
            # 기본 정보 수집
            years = [item.year for item in table_data if item.year]
            total_records = len(table_data)

            # 데이터 필드 분석
            all_fields = set()
            numeric_values = []
            field_analysis = {}

            for item in table_data:
                if item.data:
                    all_fields.update(item.data.keys())
                    for key, value in item.data.items():
                        if key not in field_analysis:
                            field_analysis[key] = {"numeric_values": [], "text_values": [], "type": "unknown"}

                        try:
                            if isinstance(value, (int, float)):
                                numeric_val = float(value)
                                numeric_values.append(numeric_val)
                                field_analysis[key]["numeric_values"].append(numeric_val)
                                field_analysis[key]["type"] = "numeric"
                            elif isinstance(value, str):
                                try:
                                    numeric_val = float(value.replace(',', '').replace('%', ''))
                                    numeric_values.append(numeric_val)
                                    field_analysis[key]["numeric_values"].append(numeric_val)
                                    field_analysis[key]["type"] = "numeric"
                                except ValueError:
                                    field_analysis[key]["text_values"].append(value)
                                    field_analysis[key]["type"] = "text"
                        except:
                            field_analysis[key]["text_values"].append(str(value))
                            field_analysis[key]["type"] = "text"

            # 객관적 현황 요약 생성
            summary_parts = []

            # 1. 기본 현황
            summary_parts.append(f"'{table_name}' 통계표는 총 {total_records}개의 데이터 레코드를 포함합니다.")

            if years:
                if min(years) == max(years):
                    summary_parts.append(f"{min(years)}년 기준 데이터입니다.")
                else:
                    summary_parts.append(f"{min(years)}년부터 {max(years)}년까지 {max(years) - min(years) + 1}년간의 시계열 데이터입니다.")

            # 2. 데이터 구성
            numeric_fields = [k for k, v in field_analysis.items() if v["type"] == "numeric"]
            text_fields = [k for k, v in field_analysis.items() if v["type"] == "text"]

            summary_parts.append(f"총 {len(all_fields)}개 데이터 필드 중 {len(numeric_fields)}개는 수치형, {len(text_fields)}개는 텍스트형 데이터입니다.")

            # 3. 수치 데이터 특성
            if numeric_values:
                import numpy as np
                mean_val = np.mean(numeric_values)
                median_val = np.median(numeric_values)
                max_val = np.max(numeric_values)
                min_val = np.min(numeric_values)
                std_val = np.std(numeric_values)

                summary_parts.append(f"수치 데이터의 평균은 {mean_val:,.1f}, 중앙값은 {median_val:,.1f}이며, {min_val:,.1f}에서 {max_val:,.1f}까지의 범위를 가집니다.")

                # 변동성 평가
                cv = std_val / mean_val if mean_val != 0 else 0
                if cv < 0.1:
                    variability = "매우 안정적"
                elif cv < 0.3:
                    variability = "안정적"
                elif cv < 0.7:
                    variability = "변동성이 있는"
                else:
                    variability = "변동성이 매우 큰"

                summary_parts.append(f"데이터 변동성은 {variability} 특성을 보입니다 (변동계수: {cv:.3f}).")

            # 4. 핵심 필드 식별
            if numeric_fields:
                # 가장 변동이 큰 필드와 안정적인 필드 찾기
                field_variations = {}
                for field in numeric_fields:
                    values = field_analysis[field]["numeric_values"]
                    if len(values) > 1:
                        cv = np.std(values) / np.mean(values) if np.mean(values) != 0 else 0
                        field_variations[field] = cv

                if field_variations:
                    most_variable = max(field_variations, key=field_variations.get)
                    most_stable = min(field_variations, key=field_variations.get)
                    summary_parts.append(f"'{most_variable}' 필드가 가장 변동성이 크며, '{most_stable}' 필드가 가장 안정적입니다.")

            # 5. 데이터 품질 평가
            completeness = len([item for item in table_data if item.data and any(item.data.values())]) / len(table_data) * 100
            summary_parts.append(f"데이터 완성도는 {completeness:.1f}%입니다.")

            # 6. 주요 통계 지표 (상위 3개 필드)
            key_insights = []
            for field in numeric_fields[:3]:
                values = field_analysis[field]["numeric_values"]
                if len(values) > 1:
                    total = sum(values)
                    avg = np.mean(values)
                    growth = ((values[-1] - values[0]) / values[0] * 100) if len(values) > 1 and values[0] != 0 else 0
                    key_insights.append(f"'{field}': 총합 {total:,.0f}, 평균 {avg:,.1f}, 증감률 {growth:+.1f}%")

            if key_insights:
                summary_parts.append("주요 지표별 현황: " + ", ".join(key_insights[:2]))

            objective_summary = " ".join(summary_parts)

            table_summaries[table_name] = {
                "objective_summary": objective_summary,
                "key_metrics": {
                    "total_records": total_records,
                    "year_span": max(years) - min(years) + 1 if years else 0,
                    "field_count": len(all_fields),
                    "numeric_field_count": len(numeric_fields),
                    "data_completeness": completeness,
                    "key_numeric_fields": numeric_fields[:5]
                },
                "data_insights": key_insights
            }

        return {
            "stat_name": stat_name,
            "analysis_type": "객관적 현황 요약",
            "metadata": {
                "title": metadata.title,
                "department": metadata.department,
                "keywords": metadata.keywords,
                "purpose": getattr(metadata, 'purpose', None),
                "frequency": getattr(metadata, 'frequency', None),
                "contact": getattr(metadata, 'contact', None),
                "search_field": getattr(metadata, 'search_field', None),
                "responsible_department": getattr(metadata, 'responsible_department', None),
                "statistical_info": getattr(metadata, 'statistical_info', None),
                "major_items": getattr(metadata, 'major_items', None),
                "meaning_analysis": getattr(metadata, 'meaning_analysis', None),
                "terminology": getattr(metadata, 'terminology', None),
                "related_terms": getattr(metadata, 'related_terms', None)
            },
            "total_tables": len(table_summaries),
            "analysis_date": datetime.now().isoformat(),
            "table_summaries": table_summaries
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"객관적 현황 요약 생성 오류: {str(e)}")

@router.get("/stats/suggest-urls", summary="통계명으로 URL 제안")
async def suggest_urls_by_name(stat_name: str):
    """통계명을 기반으로 올바른 URL들을 제안"""
    try:
        from app.services.url_validator import URLValidator

        url_validator = URLValidator()
        suggestions = url_validator.suggest_urls_by_name(stat_name)

        return {
            "stat_name": stat_name,
            "suggestions": [
                {
                    "rsid": stat.rsid,
                    "name": stat.name,
                    "category": stat.category,
                    "description": stat.description,
                    "keywords": stat.keywords,
                    "url": stat.correct_url
                }
                for stat in suggestions
            ],
            "total_suggestions": len(suggestions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL 제안 생성 오류: {str(e)}")

@router.get("/stats/available", summary="사용 가능한 모든 통계 목록")
async def get_available_stats():
    """사용 가능한 모든 국토교통부 통계 목록"""
    try:
        from app.services.url_validator import URLValidator

        url_validator = URLValidator()
        all_stats = url_validator.get_all_available_stats()

        return {
            "available_stats": [
                {
                    "rsid": stat.rsid,
                    "name": stat.name,
                    "category": stat.category,
                    "description": stat.description,
                    "keywords": stat.keywords,
                    "url": stat.correct_url
                }
                for stat in all_stats
            ],
            "total_count": len(all_stats)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 목록 조회 오류: {str(e)}")

@router.delete("/stats/{cache_key}", summary="수집된 통계표 삭제")
async def delete_collected_stat(cache_key: str):
    """수집된 통계표 삭제 - 메타데이터, 통계 데이터, Excel 파일 모두 삭제"""
    try:
        print(f"통계표 삭제 시작: {cache_key}")

        # 삭제할 파일들 목록
        files_to_delete = [
            Path(f"data/metadata/{cache_key}_metadata.json"),
            Path(f"data/statistics/{cache_key}_stats.json"),
            Path(f"data/excel/{cache_key}_data.xlsx")
        ]

        deleted_files = []
        errors = []

        # 각 파일 삭제 시도
        for file_path in files_to_delete:
            try:
                if file_path.exists():
                    file_path.unlink()  # 파일 삭제
                    deleted_files.append(str(file_path))
                    print(f"파일 삭제 완료: {file_path}")
                else:
                    print(f"파일이 존재하지 않음: {file_path}")
            except Exception as delete_error:
                error_msg = f"파일 삭제 실패 ({file_path}): {delete_error}"
                errors.append(error_msg)
                print(error_msg)

        # 결과 생성
        if deleted_files and not errors:
            result = {
                "success": True,
                "message": f"통계표 '{cache_key}'가 성공적으로 삭제되었습니다.",
                "deleted_files": deleted_files,
                "cache_key": cache_key
            }
            print(f"통계표 삭제 완료: {cache_key}")
        elif deleted_files and errors:
            result = {
                "success": True,
                "message": f"통계표 '{cache_key}'가 부분적으로 삭제되었습니다.",
                "deleted_files": deleted_files,
                "errors": errors,
                "cache_key": cache_key
            }
            print(f"통계표 부분 삭제: {cache_key}")
        else:
            result = {
                "success": False,
                "message": f"통계표 '{cache_key}'를 삭제할 파일을 찾을 수 없습니다.",
                "errors": errors if errors else ["삭제할 파일이 없습니다."],
                "cache_key": cache_key
            }
            print(f"통계표 삭제 실패: {cache_key}")

        return result

    except Exception as e:
        print(f"통계표 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=f"통계표 삭제 중 오류가 발생했습니다: {str(e)}")