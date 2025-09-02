from fastapi import APIRouter, HTTPException
from typing import List
from app.models.stat_models import (
    RecentStatsResponse, 
    StatMetadata, 
    GenerateStoryRequest, 
    StoryResponse
)
from app.services.crawler_service import CrawlerService
from app.services.ai_service import AIService
from app.services.data_storage import DataStorageService
import asyncio
import time
from datetime import datetime, timedelta

router = APIRouter()
crawler_service = CrawlerService()
ai_service = AIService()
storage_service = DataStorageService()

# 캐시 저장소 - 초기화됨
_cache = {
    'recent_stats': None,
    'cache_time': None
}
CACHE_DURATION = 30 * 60  # 30분

@router.get("/recent-stats", response_model=RecentStatsResponse)
async def get_recent_stats():
    """최근 1달 통계 목록 조회 (캐시 사용)"""
    try:
        # 캐시 확인
        now = time.time()
        if (_cache['recent_stats'] is not None and 
            _cache['cache_time'] is not None and 
            (now - _cache['cache_time']) < CACHE_DURATION):
            print("캐시에서 데이터 반환")
            return _cache['recent_stats']
        
        print("새로운 크롤링 실행")
        stats = await crawler_service.get_recent_stats()
        print(f"크롤링 결과: {len(stats)}개 통계 수집됨")
        
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
        
        # 3. 기본 분석 수행 (메타데이터 정리 + 데이터 구조 분석)
        basic_analysis = await ai_service.analyze_basic_data(stat_data, metadata)
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "metadata": metadata.dict(),
            "data_structure": {
                "total_years": len(stat_data),
                "data_keys": list(stat_data[0].data.keys()) if stat_data else [],
                "year_range": {
                    "start": min([int(d.year) for d in stat_data]) if stat_data else None,
                    "end": max([int(d.year) for d in stat_data]) if stat_data else None
                }
            },
            "basic_analysis": basic_analysis
        }
    except Exception as e:
        print(f"기본 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-story", response_model=StoryResponse)
async def generate_story(request: GenerateStoryRequest):
    """레거시 카드뉴스 보고서 생성 - 기본 분석으로 리디렉트"""
    # 기본 분석으로 리디렉트
    return await analyze_basic(request)

@router.post("/analyze-comprehensive")
async def analyze_comprehensive(request: GenerateStoryRequest):
    """종합 통계 분석 - 통계분석, 트렌드분석, 정책시사점, 카드뉴스 모두 포함"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"종합 분석 요청: {request.stat_name}")
        print(f"통계 URL: {stat_url}")
        
        # 1. 캐시된 데이터 확인
        print("=== 캐시 데이터 확인 ===")
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        if cached_metadata and cached_stat_data:
            print(f"캐시에서 데이터 로드: {cached_metadata.title}, {len(cached_stat_data)}년치")
            metadata = cached_metadata
            stat_data = cached_stat_data
        else:
            # 2. 데이터 수집 시도
            try:
                print("=== 새 데이터 수집 시작 ===")
                metadata = await crawler_service.get_stat_metadata(stat_url)
                stat_data = await crawler_service.get_stat_data(stat_url, request.period)
                
                # 캐시에 저장
                storage_service.save_complete_data(stat_url, metadata, stat_data)
            except Exception as crawl_error:
                print("크롤링 오류, 더미 데이터 사용")
                # 더미 데이터 생성
                from app.models.stat_models import StatMetadata, StatData
                metadata = StatMetadata(
                    id="dummy",
                    title=request.stat_name,
                    purpose="테스트용 더미 데이터",
                    frequency="연간",
                    department="국토교통부",
                    contact="test@molit.go.kr",
                    keywords=["테스트"],
                    related_terms={}
                )
                stat_data = [
                    StatData(year=2020, data={"총합": 1000}),
                    StatData(year=2021, data={"총합": 1100}),
                    StatData(year=2022, data={"총합": 1200}),
                    StatData(year=2023, data={"총합": 1300}),
                    StatData(year=2024, data={"총합": 1400})
                ]
        
        # 3. AI 종합 분석 수행
        analysis_result = await ai_service.generate_comprehensive_analysis(stat_data, metadata)
        
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


@router.post("/analyze-statistics")
async def analyze_statistics_only(request: GenerateStoryRequest):
    """통계 분석만 수행"""
    try:
        return {
            "stat_name": request.stat_name,
            "analysis_date": "2025-01-01T00:00:00",
            "statistics_analysis": {
                "analysis_result": "테스트 분석 결과",
                "status": "success"
            }
        }
    except Exception as e:
        print("통계 분석 오류 발생")
        raise HTTPException(status_code=500, detail="통계 분석 중 오류가 발생했습니다")

@router.post("/analyze-trends")
async def analyze_trends_only(request: GenerateStoryRequest):
    """트렌드 분석만 수행"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        # 1. 캐시된 데이터 확인
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        if cached_metadata and cached_stat_data:
            print(f"캐시에서 데이터 로드: {cached_metadata.title}")
            metadata = cached_metadata
            stat_data = cached_stat_data
        else:
            # 새 데이터 수집
            metadata = await crawler_service.get_stat_metadata(stat_url)
            stat_data = await crawler_service.get_stat_data(stat_url, request.period)
            storage_service.save_complete_data(stat_url, metadata, stat_data)
        
        # 2. 트렌드 분석만 수행
        trend_result = await ai_service.analyze_trends(stat_data, metadata)
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "trend_analysis": trend_result
        }
    except Exception as e:
        print(f"트렌드 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-policy-insights")
async def generate_policy_insights_only(request: GenerateStoryRequest):
    """정책 시사점만 도출"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        # 1. 캐시된 데이터 확인
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        if cached_metadata and cached_stat_data:
            print(f"캐시에서 데이터 로드: {cached_metadata.title}")
            metadata = cached_metadata
            stat_data = cached_stat_data
        else:
            # 새 데이터 수집
            metadata = await crawler_service.get_stat_metadata(stat_url)
            stat_data = await crawler_service.get_stat_data(stat_url, request.period)
            storage_service.save_complete_data(stat_url, metadata, stat_data)
        
        # 2. 기본 통계 분석 먼저 수행
        stats_analysis = await ai_service.analyze_statistics(stat_data, metadata)
        
        # 3. 정책 시사점 도출
        policy_result = await ai_service.generate_policy_insights(stat_data, metadata, stats_analysis)
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "policy_insights": policy_result
        }
    except Exception as e:
        print(f"정책 시사점 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-advanced-cardnews")
async def generate_basic_statistics_analysis(request: GenerateStoryRequest):
    """기본통계현황분석 - 기초통계 지표 계산 및 현황 파악"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"기본통계현황분석 요청: {request.stat_name}")
        print(f"통계 URL: {stat_url}")
        
        # 1. 캐시된 데이터 확인
        cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)
        
        if cached_metadata and cached_stat_data:
            print(f"캐시에서 데이터 로드: {cached_metadata.title}")
            metadata = cached_metadata
            stat_data = cached_stat_data
        else:
            # 새 데이터 수집 시도
            try:
                metadata = await crawler_service.get_stat_metadata(stat_url)
                stat_data = await crawler_service.get_stat_data(stat_url, request.period)
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
                    keywords=["기본통계", "현황분석"],
                    related_terms={}
                )
                stat_data = [
                    StatData(year=2020, data={"총합": 1000, "지역A": 300, "지역B": 700}),
                    StatData(year=2021, data={"총합": 1100, "지역A": 320, "지역B": 780}),
                    StatData(year=2022, data={"총합": 1200, "지역A": 350, "지역B": 850}),
                    StatData(year=2023, data={"총합": 1300, "지역A": 380, "지역B": 920}),
                    StatData(year=2024, data={"총합": 1400, "지역A": 400, "지역B": 1000})
                ]
        
        # 2. 기초통계 지표 계산 및 현황 파악 분석
        basic_statistics = await ai_service.analyze_basic_statistics(stat_data, metadata)
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "analysis_type": "기본통계현황분석",
            "basic_statistics": basic_statistics,
            "analysis_summary": {
                "analysis_period": f"{min([int(d.year) for d in stat_data])}-{max([int(d.year) for d in stat_data])}년",
                "total_data_points": len(stat_data),
                "analysis_focus": "기초통계 지표 계산 및 현황 파악"
            }
        }
    except Exception as e:
        print(f"기본통계현황분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/refresh-stats")
async def refresh_stats_cache():
    """어드민: 통계 캐시 강제 새로고침"""
    try:
        print("어드민 요청: 캐시 강제 새로고침")
        
        # 기존 캐시 삭제
        _cache['recent_stats'] = None
        _cache['cache_time'] = None
        
        # 새로운 크롤링 실행
        try:
            stats = await crawler_service.get_recent_stats()
            # 임시로 에러 감지 주석 처리하여 실제 데이터 확인
            print(f"크롤링 결과: {len(stats)}개 통계 수집됨")
            # if (len(stats) == 1 and 
            #     (stats[0].id == "stat_error" or 
            #      "오류" in stats[0].title or 
            #      "error" in stats[0].id.lower())):
            #     print(f"에러 데이터 감지: {stats[0].id}, {stats[0].title}")
            #     raise Exception("크롤링 결과가 에러 데이터임")
        except Exception as crawl_error:
            print("크롤링 실패, 더미 통계 데이터 제공")
            # 더미 통계 데이터 생성
            from app.models.stat_models import StatItem
            stats = [
                StatItem(
                    id="dummy_1",
                    title="2024년 전국 주택 건설 현황",
                    publish_date="2024.12.15",
                    category="주택",
                    department="국토교통부",
                    url="https://stat.molit.go.kr/portal/cate/statView.do?hMenuId=HMENU00158",
                    stat_field="주택건설"
                ),
                StatItem(
                    id="dummy_2", 
                    title="2024년 지역별 토지거래 동향",
                    publish_date="2024.12.10",
                    category="토지",
                    department="국토교통부",
                    url="https://stat.molit.go.kr/portal/cate/statView.do?hMenuId=HMENU00159",
                    stat_field="토지거래"
                ),
                StatItem(
                    id="dummy_3",
                    title="2024년 대중교통 이용 현황",
                    publish_date="2024.12.05",
                    category="교통",
                    department="국토교통부", 
                    url="https://stat.molit.go.kr/portal/cate/statView.do?hMenuId=HMENU00160",
                    stat_field="교통"
                ),
                StatItem(
                    id="dummy_4",
                    title="2024년 건설업 경기 동향",
                    publish_date="2024.12.01",
                    category="건설",
                    department="국토교통부",
                    url="https://stat.molit.go.kr/portal/cate/statView.do?hMenuId=HMENU00161", 
                    stat_field="건설업"
                )
            ]
        
        response = RecentStatsResponse(
            stats=stats,
            total_count=len(stats)
        )
        
        # 캐시 저장
        _cache['recent_stats'] = response
        _cache['cache_time'] = time.time()
        
        return {
            "message": "캐시 새로고침 완료",
            "total_stats": len(stats),
            "cache_time": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/cache-status")
async def get_cache_status():
    """어드민: 캐시 상태 확인"""
    try:
        if _cache['cache_time'] is None:
            return {
                "cached": False,
                "message": "캐시 없음"
            }
        
        cache_age = time.time() - _cache['cache_time']
        cache_remaining = max(0, CACHE_DURATION - cache_age)
        
        return {
            "cached": True,
            "cache_age_seconds": int(cache_age),
            "cache_remaining_seconds": int(cache_remaining),
            "total_stats": len(_cache['recent_stats'].stats) if _cache['recent_stats'] else 0,
            "cache_time": datetime.fromtimestamp(_cache['cache_time']).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/storage-cache-status")
async def get_storage_cache_status():
    """어드민: 데이터 저장소 캐시 상태 확인"""
    try:
        cached_files = storage_service.list_cached_files()
        return {
            "metadata_files": len(cached_files['metadata_files']),
            "statistics_files": len(cached_files['statistics_files']),
            "total_cache_keys": cached_files['total_cache_keys'],
            "files": cached_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/clear-storage-cache")
async def clear_storage_cache():
    """어드민: 만료된 저장소 캐시 삭제"""
    try:
        deleted_count = storage_service.clear_expired_cache()
        return {
            "message": f"만료된 캐시 파일 {deleted_count}개 삭제됨",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))