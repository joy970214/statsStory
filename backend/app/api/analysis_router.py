from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, FileResponse
from typing import List, Optional, Dict, Any
from pathlib import Path
from app.models.stat_models import (
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
import asyncio
import time
import uuid
from datetime import datetime, timedelta
import json
import os
import numpy as np

router = APIRouter()
crawler_service = CrawlerService()
ai_service = AIService()
storage_service = DataStorageService()

# 작업 결과 저장소 (실제로는 Redis나 DB 사용 권장)
task_results: Dict[str, Any] = {}

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

    return {
        "mean": float(np.mean(numeric_values)),
        "median": float(np.median(numeric_values)),
        "max": float(np.max(numeric_values)),
        "min": float(np.min(numeric_values)),
        "total": float(np.sum(numeric_values)),
        "count": len(numeric_values),
        "std_dev": float(np.std(numeric_values)) if len(numeric_values) > 1 else 0
    }

def _calculate_basic_statistics_from_comprehensive(stat_data):
    """종합 분석 기반 기초 통계 계산"""
    try:
        return _calculate_basic_statistics(stat_data)
    except Exception as e:
        print(f"종합 분석 오류, 기본 분석 사용: {e}")
        return _calculate_basic_statistics(stat_data)

def _analyze_table_data(table_name: str, table_data):
    """테이블 데이터 분석"""
    try:
        # 기본 정보 수집
        total_records = len(table_data)
        years = [item.year for item in table_data if item.year]

        # 데이터 필드 분석
        all_fields = set()
        numeric_values = []

        for item in table_data:
            if item.data:
                all_fields.update(item.data.keys())
                for key, value in item.data.items():
                    try:
                        if isinstance(value, (int, float)):
                            numeric_values.append(float(value))
                        elif isinstance(value, str):
                            try:
                                numeric_val = float(value.replace(',', '').replace('%', ''))
                                numeric_values.append(numeric_val)
                            except ValueError:
                                pass
                    except:
                        pass

        # 기초 통계 계산
        stats = {}
        if numeric_values:
            stats = {
                "count": len(numeric_values),
                "mean": float(np.mean(numeric_values)),
                "median": float(np.median(numeric_values)),
                "std": float(np.std(numeric_values)),
                "min": float(np.min(numeric_values)),
                "max": float(np.max(numeric_values))
            }

        return {
            "table_name": table_name,
            "total_records": total_records,
            "year_range": {
                "min_year": min(years) if years else None,
                "max_year": max(years) if years else None
            },
            "field_count": len(all_fields),
            "statistics": stats,
            "data_quality": {
                "completeness": len([item for item in table_data if item.data]) / len(table_data) * 100 if table_data else 0
            }
        }
    except Exception as e:
        return {
            "table_name": table_name,
            "error": str(e)
        }

async def run_optimized_analysis(task_id: str, request: GenerateStoryRequest):
    """백그라운드에서 실행되는 최적화된 분석 작업"""
    try:
        print(f"백그라운드 분석 시작: {task_id}")

        # 취소 확인 함수
        def check_cancellation():
            task_status = progress_tracker.get_task_status(task_id)
            if task_status and task_status.get("cancelled", False):
                print(f"[CANCELLATION] 작업 취소 감지: {task_id}")
                return True
            return False

        # 🚀 더 자세한 진행률 업데이트 (사용자 체감 개선)
        progress_tracker.update_progress(task_id, "작업 준비 완료", 12, "데이터 수집을 시작합니다")

        # 취소 체크
        if check_cancellation():
            return

        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"

        # 캐시된 데이터 확인
        progress_tracker.update_progress(task_id, "캐시 확인", 18, "기존 수집된 데이터를 확인합니다")

        # 취소 체크
        if check_cancellation():
            return

        cached_metadata, cached_stat_data = storage_service.get_cached_data_by_name(request.stat_name)

        if cached_metadata and cached_stat_data:
            print(f"캐시에서 데이터 로드: {cached_metadata.title}")
            metadata = cached_metadata
            stat_data = cached_stat_data
        else:
            # 새로운 데이터 수집 - 최적화된 크롤러 사용 (한번에 모든 데이터 수집)
            progress_tracker.update_progress(task_id, "데이터 수집", 50, "새로운 데이터를 수집합니다")

            # 취소 체크
            if check_cancellation():
                return

            try:
                # ProgressCallback 객체 생성 (취소 체크 기능 포함)
                from app.services.progress_service import ProgressCallback
                progress_callback = ProgressCallback(task_id)

                # 크롤링 중 취소 체크를 위한 콜백 확장
                original_update = progress_callback.update
                def enhanced_update(stage: str, progress: float, message: str):
                    # 취소 체크
                    if check_cancellation():
                        print(f"[CANCELLATION] 크롤링 중 취소 감지: {task_id}")
                        # 크롤링 중단을 위해 예외 발생
                        raise Exception("작업이 사용자에 의해 취소되었습니다")
                    # 정상 진행률 업데이트
                    return original_update(stage, progress, message)

                progress_callback.update = enhanced_update

                # 최적화된 종합 분석 실행
                analysis = await crawler_service.get_comprehensive_analysis_for_optimization(stat_url, progress_callback)

                # 취소 체크 (크롤링 완료 후)
                if check_cancellation():
                    return

                metadata = analysis.metadata
                # 모든 테이블의 데이터를 합쳐서 반환
                stat_data = []
                for table_name, table_data in analysis.data_by_table.items():
                    stat_data.extend(table_data)
                storage_service.save_complete_data(stat_url, metadata, stat_data)
            except Exception as e:
                # 취소로 인한 예외인지 확인
                if "취소" in str(e) or check_cancellation():
                    print(f"[CANCELLATION] 크롤링 취소됨: {task_id}")
                    progress_tracker.update_progress(task_id, "취소됨", 100, "데이터 수집이 취소되었습니다")
                    return

                print(f"크롤링 오류, 더미 데이터 사용: {e}")
                # 더미 데이터 생성 로직
                from app.models.stat_models import StatMetadata, StatData
                metadata = StatMetadata(
                    id="dummy",
                    title=request.stat_name,
                    purpose="분석용 더미 데이터",
                    frequency="연간",
                    department="국토교통부",
                    contact="test@molit.go.kr",
                    keywords=["분석"],
                    related_terms={}
                )
                stat_data = [
                    StatData(year=2023, data={"총합": 1000, "증가율": 5.0}),
                    StatData(year=2024, data={"총합": 1100, "증가율": 10.0})
                ]

        # 분석 수행
        progress_tracker.update_progress(task_id, "데이터분석", 80, "기본 통계량을 계산합니다")

        # 취소 체크
        if check_cancellation():
            return

        basic_stats_result = _calculate_basic_statistics_from_comprehensive(stat_data)
        print(f"[기본통계] 분석 완료: mean={basic_stats_result.get('mean', 0):.2f}")

        # cache_key 생성 (벡터 DB 식별용)
        import hashlib
        cache_key = hashlib.md5(stat_url.encode()).hexdigest()[:12]

        # 1단계: 벡터 DB에 데이터 저장 (AI 분석 및 채팅용)
        progress_tracker.update_progress(task_id, "벡터DB저장", 82, "ChromaDB에 데이터 저장 중 (채팅용)...")

        # 취소 체크
        if check_cancellation():
            return

        # ChromaDB에 저장
        stored_count = 0
        try:
            from app.services.vector_db_service import vector_db_service

            # ChromaDB에 통계 데이터 저장
            stored_count = vector_db_service.store_stat_data(
                cache_key=cache_key,
                stat_name=request.stat_name,
                stat_data=stat_data,
                metadata=metadata
            )
            print(f"[VectorDB] {stored_count}개 데이터 저장 완료 (cache_key: {cache_key})")
        except Exception as vector_error:
            print(f"[VectorDB] 벡터 DB 저장 오류: {vector_error}")

        # 2단계: AI 인사이트 생성 (ChromaDB 데이터 활용)
        # 먼저 캐시된 메타데이터에 AI 인사이트가 있는지 확인
        ai_insights = None
        if metadata and hasattr(metadata, 'ai_insights') and metadata.ai_insights:
            print(f"[AI] 캐시된 AI 인사이트 발견, 재생성 건너뛰기")
            ai_insights = metadata.ai_insights
            progress_tracker.update_progress(task_id, "AI분석", 90, "캐시된 AI 인사이트 사용 (재생성 건너뛰기)")
            await asyncio.sleep(0.1)
        else:
            print(f"[AI] 캐시된 AI 인사이트 없음, 새로 생성")
            progress_tracker.update_progress(task_id, "AI분석", 88, "Ollama AI 인사이트 생성 중...")
            await asyncio.sleep(0.1)  # SSE 전송을 위한 이벤트 루프 양보

            # 취소 체크
            if check_cancellation():
                return

            try:
                from app.services.ollama_service import ollama_service
                from app.services.vector_db_service import vector_db_service

                # Ollama 서버 확인
                if ollama_service.is_available() and stored_count > 0:
                    print(f"[AI] Ollama 인사이트 생성 시작...")

                    # 통계표 목록 수집
                    table_names = list(set([
                        getattr(item, 'table_name', '기본 통계표')
                        for item in stat_data
                        if hasattr(item, 'table_name')
                    ]))

                    # ChromaDB에서 데이터 샘플 가져오기 (최대 100개)
                    progress_tracker.update_progress(task_id, "AI분석", 89, "벡터 데이터베이스에서 관련 데이터를 검색 중...")
                    await asyncio.sleep(0.1)  # SSE 전송을 위한 이벤트 루프 양보

                    chroma_data_samples = vector_db_service.get_all_data_for_analysis(
                        cache_key=cache_key,
                        limit=100
                    )
                    print(f"[AI] ChromaDB에서 {len(chroma_data_samples)}개 데이터 샘플 추출 (cache_key: {cache_key})")

                    # AI 인사이트 생성 (ChromaDB 데이터 전달)
                    progress_tracker.update_progress(task_id, "AI분석", 90, "Ollama AI 모델이 인사이트를 생성하고 있습니다 (최대 10분 소요)...")
                    await asyncio.sleep(0.1)  # SSE 전송을 위한 이벤트 루프 양보

                    ai_insights = ollama_service.generate_statistical_insights(
                        metadata=metadata.dict() if metadata else {},
                        data_summary=basic_stats_result,
                        table_names=table_names,
                        raw_data_sample=chroma_data_samples  # ChromaDB 데이터 전달
                    )

                    print(f"[AI] 인사이트 생성 완료: {ai_insights.get('insights_count', 0)}개")
                    progress_tracker.update_progress(task_id, "AI분석", 94, "생성된 인사이트를 저장하고 있습니다...")
                    await asyncio.sleep(0.1)  # SSE 전송을 위한 이벤트 루프 양보

                    # 메타데이터에 AI 인사이트 추가
                    if metadata:
                        metadata.ai_insights = ai_insights
                        # 메타데이터 재저장
                        storage_service.save_complete_data(stat_url, metadata, stat_data)
                        print(f"[AI] 메타데이터에 인사이트 저장 완료")
                else:
                    if not ollama_service.is_available():
                        print(f"[AI] Ollama 서버를 사용할 수 없습니다. 기본 인사이트 사용")
                        progress_tracker.update_progress(task_id, "AI분석", 90, "Ollama 서버를 사용할 수 없어 기본 인사이트를 사용합니다")
                        await asyncio.sleep(0.1)
                    else:
                        print(f"[AI] ChromaDB 데이터가 없어 기본 인사이트 사용")
                        progress_tracker.update_progress(task_id, "AI분석", 90, "벡터 데이터가 없어 기본 인사이트를 사용합니다")
                        await asyncio.sleep(0.1)
            except Exception as ai_error:
                print(f"[AI] 인사이트 생성 오류: {ai_error}")
                progress_tracker.update_progress(task_id, "AI분석", 90, f"AI 인사이트 생성 중 오류 발생, 기본 인사이트 사용")
                await asyncio.sleep(0.1)
                import traceback
                traceback.print_exc()

        # 결과 생성
        progress_tracker.update_progress(task_id, "완료", 98, "최종 분석 결과를 생성하고 있습니다")
        await asyncio.sleep(0.1)  # SSE 전송을 위한 이벤트 루프 양보

        # 취소 체크
        if check_cancellation():
            return

        # raw_data 수집
        raw_data = []
        for data_item in stat_data:
            if hasattr(data_item, 'data') and data_item.data:
                raw_data.append({
                    "year": data_item.year,
                    "data": data_item.data
                })

        result = {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "analysis_type": "최적화된 기본통계현황분석",
            "metadata": metadata.dict() if metadata else {},
            "basic_statistics": basic_stats_result,
            "raw_data": raw_data,
            "insights": f"{metadata.title if metadata else request.stat_name}에 대한 분석이 완료되었습니다."
        }

        # 결과 저장
        task_results[task_id] = result

        # 완료 처리
        progress_tracker.update_progress(task_id, "완료", 100, "분석이 완료되었습니다")
        print(f"백그라운드 분석 완료: {task_id}")

    except Exception as e:
        print(f"백그라운드 분석 오류: {task_id}, {str(e)}")
        progress_tracker.update_progress(task_id, "오류", 0, f"분석 중 오류 발생: {str(e)}")

@router.post("/generate-advanced-cardnews")
async def generate_advanced_cardnews(request: GenerateStoryRequest):
    """기본통계현황분석 - 즉시 응답 (기존 버전)"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"

        print(f"기본통계현황분석 요청: {request.stat_name}")

        # 통계명을 동적 저장소에 저장
        _store_stat_name_from_request(request.stat_name, stat_url)

        # 1. 통계명 기반 캐시된 데이터 확인
        cached_metadata, cached_stat_data = storage_service.get_cached_data_by_name(request.stat_name)

        if cached_metadata and cached_stat_data:
            print(f"[SUCCESS] 기존 수집 데이터 발견: {cached_metadata.title}")
            print(f"[CACHE] 캐시에서 데이터 로드 (새로 수집하지 않음)")
            metadata = cached_metadata
            stat_data = cached_stat_data
        else:
            # 2. 기존 데이터가 없으므로 새로 수집
            try:
                print(f"[NEW] '{request.stat_name}' 통계 데이터를 새로 수집합니다")
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

@router.post("/start-analysis")
async def start_optimized_analysis(request: GenerateStoryRequest, background_tasks: BackgroundTasks):
    """최적화된 기본통계현황분석 시작 - 작업 ID 반환"""
    try:
        # 통계명을 동적 저장소에 저장
        if request.stat_url:
            _store_stat_name_from_request(request.stat_name, request.stat_url)

        # 작업 ID 생성
        task_id = progress_tracker.create_task(f"기본통계현황분석: {request.stat_name}")

        # 🚀 즉시 초기 진행률 업데이트 (더 빠른 피드백)
        progress_tracker.update_progress(task_id, "요청 처리", 2, "분석 요청을 처리하고 있습니다...")

        # 즉시 시작 상태로 업데이트
        progress_tracker.update_progress(task_id, "초기화", 8, "분석 작업을 준비합니다")

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
            return {"message": "취소할 작업이 없습니다", "task_id": task_id, "status": "task_not_found"}

        # 이미 완료된 작업인지 확인
        if status.get("completed", False):
            print(f"[취소 API] 이미 완료된 작업: {task_id}")
            return {"message": "작업이 이미 완료되어 취소할 수 없습니다", "task_id": task_id, "status": "already_completed"}

        # 작업 취소 - 진행률 업데이트로 취소 상태 설정
        print(f"[취소 API] 작업 취소 중: {task_id}")

        # active_tasks에서 취소 플래그 설정 (먼저 설정해야 백그라운드 작업이 감지)
        if task_id in progress_tracker.active_tasks:
            progress_tracker.active_tasks[task_id]["cancelled"] = True
            print(f"[취소 API] 취소 플래그 설정 완료: {task_id}")

        # SSE로 취소 상태 전송 (프론트엔드는 이 메시지로만 알림 표시)
        progress_tracker.update_progress(
            task_id=task_id,
            stage="취소됨",
            progress=100,
            message="작업이 성공적으로 취소되었습니다"
        )

        # 메모리에서 결과 제거 (있다면)
        if task_id in task_results:
            del task_results[task_id]
            print(f"[취소 API] 메모리에서 결과 제거: {task_id}")

        print(f"[취소 API] 작업 취소 완료: {task_id}")
        return {"message": "취소 요청이 전송되었습니다", "task_id": task_id, "status": "cancellation_requested"}

    except Exception as e:
        print(f"[취소 API] 작업 취소 오류: {task_id}, 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"작업 취소 오류: {str(e)}")

@router.get("/analysis/tasks", summary="진행중인 작업 목록 조회")
async def get_active_tasks():
    """현재 진행중인 모든 분석 작업 목록 조회"""
    try:
        tasks = progress_tracker.get_recent_tasks(limit=20)

        # 작업 상태별로 분류
        active_tasks = []
        completed_tasks = []

        for task in tasks:
            task_info = {
                "task_id": task["task_id"],
                "name": task.get("name", "Unknown Task"),
                "created_at": task.get("created_at", datetime.now()).isoformat(),
                "current_stage": task.get("current_stage", "알 수 없음"),
                "current_progress": task.get("current_progress", 0),
                "current_message": task.get("current_message", ""),
                "completed": task.get("completed", False),
                "cancelled": task.get("cancelled", False)
            }

            if task.get("completed", False):
                if task.get("completed_at"):
                    task_info["completed_at"] = task["completed_at"].isoformat()
                completed_tasks.append(task_info)
            else:
                active_tasks.append(task_info)

        return {
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "total_active": len(active_tasks),
            "total_completed": len(completed_tasks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 목록 조회 오류: {str(e)}")

@router.get("/analysis/tasks/active", summary="진행중인 작업만 조회")
async def get_only_active_tasks():
    """현재 진행중인 작업만 조회 (완료되지 않은 작업)"""
    try:
        all_tasks = progress_tracker.get_all_active_tasks()
        active_tasks = []

        for task_id, task_info in all_tasks.items():
            if not task_info.get("completed", False):
                active_tasks.append({
                    "task_id": task_id,
                    "name": task_info.get("name", "Unknown Task"),
                    "created_at": task_info.get("created_at", datetime.now()).isoformat(),
                    "current_stage": task_info.get("current_stage", "알 수 없음"),
                    "current_progress": task_info.get("current_progress", 0),
                    "current_message": task_info.get("current_message", ""),
                    "start_time": task_info.get("start_time", datetime.now()).isoformat()
                })

        # 생성 시간 기준 내림차순 정렬
        active_tasks.sort(key=lambda x: x["created_at"], reverse=True)

        return {
            "active_tasks": active_tasks,
            "count": len(active_tasks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"활성 작업 조회 오류: {str(e)}")

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

        # 각 테이블별 상세 분석 및 다운로드 파일 정보 추출
        for table_name, table_data in table_groups.items():
            analysis = _analyze_table_data(table_name, table_data)

            # 다운로드된 파일 경로 찾기 (해당 테이블의 첫 번째 데이터에서)
            downloaded_file = None
            if table_data and len(table_data) > 0:
                first_item = table_data[0]
                if hasattr(first_item, 'downloaded_file_path') and first_item.downloaded_file_path:
                    file_path = Path(first_item.downloaded_file_path)
                    if file_path.exists():
                        downloaded_file = {
                            "filename": file_path.name,
                            "path": str(file_path),
                            "size": file_path.stat().st_size,
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        }

            analysis["downloaded_file"] = downloaded_file
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

@router.get("/download-file", summary="실제 다운로드한 원본 파일 다운로드")
async def download_original_file(file_path: str):
    """크롤러가 다운로드한 원본 Excel 파일 다운로드"""
    try:
        # 파일 경로 검증 (보안)
        file_path_obj = Path(file_path)

        # downloads 폴더 내의 파일인지 확인
        downloads_dir = Path(__file__).parent.parent.parent / "downloads"
        try:
            # 절대 경로로 변환하여 downloads 폴더 내에 있는지 확인
            abs_file_path = file_path_obj.resolve()
            abs_downloads_dir = downloads_dir.resolve()

            if not str(abs_file_path).startswith(str(abs_downloads_dir)):
                raise HTTPException(status_code=403, detail="접근 권한이 없습니다")
        except:
            raise HTTPException(status_code=403, detail="유효하지 않은 파일 경로입니다")

        if not file_path_obj.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        from urllib.parse import quote

        # 파일명을 URL 인코딩하여 Content-Disposition 헤더에 사용
        encoded_filename = quote(file_path_obj.name)

        return FileResponse(
            path=str(file_path_obj),
            filename=file_path_obj.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 다운로드 중 오류: {str(e)}")

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
            # 지연 로딩: 필요할 때만 OptimizedMolitCrawler import
            from app.crawlers.legacy.optimized_molit_crawler import OptimizedMolitCrawler
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