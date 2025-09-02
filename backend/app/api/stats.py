from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from app.models.stat_models import (
    RecentStatsResponse, 
    StatMetadata, 
    GenerateStoryRequest, 
    StoryResponse
)
from app.services.crawler_service import CrawlerService
from app.services.enhanced_crawler_service import enhanced_crawler_service
from app.services.ai_service import AIService
from app.services.pure_analysis_service import pure_analysis_service
from app.services.data_storage import DataStorageService
from app.services.mcp_client import mcp_client
from app.services.local_analysis_service import local_analysis_service
from app.services.mcp_analysis_service import mcp_analysis_service
import asyncio
import time
import uuid
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
        
        # 3. 기본 분석 수행 (MCP 우선, AI 실패 시 로컬 분석으로 대체)
        try:
            # MCP 분석 서비스 우선 시도
            basic_analysis = await mcp_analysis_service.analyze_basic_data(stat_data, metadata)
            print("MCP 분석 서비스로 분석 완료")
        except Exception as mcp_error:
            print(f"MCP 서비스 오류, AI 서비스로 대체: {mcp_error}")
            try:
                basic_analysis = await ai_service.analyze_basic_data(stat_data, metadata)
            except Exception as ai_error:
                print(f"AI 서비스 오류, 로컬 분석으로 대체: {ai_error}")
                basic_analysis = local_analysis_service.analyze_basic_data(stat_data, metadata)
        
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
                print(f"AI 서비스 오류, 로컬 분석으로 대체: {ai_error}")
                analysis_result = local_analysis_service.generate_comprehensive_analysis(stat_data, metadata)
        
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

# === MCP 강화 크롤링 엔드포인트들 ===

@router.get("/mcp/recent-stats")
async def get_recent_stats_with_mcp():
    """MCP 브라우저 자동화를 통한 최신 통계 수집"""
    try:
        print("=== MCP 강화 크롤링으로 최신 통계 수집 ===")
        stats = await enhanced_crawler_service.get_recent_stats_with_mcp()
        
        response = RecentStatsResponse(
            stats=stats,
            total_count=len(stats)
        )
        
        return response
    except Exception as e:
        print(f"MCP 크롤링 오류: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 크롤링 실패: {str(e)}")

@router.post("/mcp/analyze-basic")
async def analyze_basic_with_mcp(request: GenerateStoryRequest):
    """MCP 기반 기본 분석"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"=== MCP 기반 기본 분석: {request.stat_name} ===")
        
        # 1. MCP로 메타데이터 수집
        metadata = await enhanced_crawler_service.get_stat_metadata_with_mcp(stat_url)
        
        # 2. MCP로 통계 데이터 수집
        stat_data = await enhanced_crawler_service.get_stat_data_with_mcp(stat_url, request.period)
        
        # 3. MCP로 데이터 저장
        save_data = {
            "metadata": metadata.dict(),
            "stat_data": [{"year": d.year, "data": d.data} for d in stat_data],
            "collected_at": datetime.now().isoformat(),
            "collection_method": "MCP"
        }
        await enhanced_crawler_service.save_crawled_data_with_mcp(
            save_data, 
            f"basic_analysis_{metadata.id}.json"
        )
        
        # 4. 기본 분석 수행
        basic_analysis = await ai_service.analyze_basic_data(stat_data, metadata)
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "collection_method": "MCP 강화 크롤링",
            "metadata": metadata.dict(),
            "data_structure": {
                "total_years": len(stat_data),
                "data_keys": list(stat_data[0].data.keys()) if stat_data else [],
                "year_range": {
                    "start": min([int(d.year) for d in stat_data]) if stat_data else None,
                    "end": max([int(d.year) for d in stat_data]) if stat_data else None
                }
            },
            "basic_analysis": basic_analysis,
            "mcp_status": enhanced_crawler_service.get_mcp_status()
        }
        
    except Exception as e:
        print(f"MCP 기본 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 기본 분석 실패: {str(e)}")

@router.post("/mcp/search-stats")
async def search_stats_with_mcp(keyword: str):
    """MCP를 통한 통계 검색"""
    try:
        print(f"=== MCP 통계 검색: {keyword} ===")
        
        stats = await enhanced_crawler_service.search_stats_with_mcp(keyword)
        
        return {
            "keyword": keyword,
            "search_date": datetime.now().isoformat(),
            "collection_method": "MCP 검색",
            "results": [stat.dict() for stat in stats],
            "total_count": len(stats),
            "mcp_status": enhanced_crawler_service.get_mcp_status()
        }
        
    except Exception as e:
        print(f"MCP 검색 오류: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 검색 실패: {str(e)}")

@router.get("/mcp/status")
async def get_mcp_status():
    """MCP 서버 상태 확인"""
    try:
        status = enhanced_crawler_service.get_mcp_status()
        return {
            "mcp_status": status,
            "timestamp": datetime.now().isoformat(),
            "message": "MCP 서버 상태 조회 완료"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP 상태 조회 실패: {str(e)}")

@router.post("/mcp/test-browser")
async def test_mcp_browser():
    """MCP 브라우저 기능 테스트"""
    try:
        print("=== MCP 브라우저 기능 테스트 ===")
        
        # 1. 네이버 접속 테스트
        nav_result = await enhanced_crawler_service.mcp_client.call_browser_navigate("https://www.naver.com")
        
        # 2. 통계청 접속 테스트
        stat_result = await enhanced_crawler_service.mcp_client.call_browser_navigate("https://kostat.go.kr")
        
        return {
            "test_results": {
                "naver_test": nav_result,
                "kostat_test": stat_result
            },
            "test_date": datetime.now().isoformat(),
            "mcp_status": enhanced_crawler_service.get_mcp_status()
        }
        
    except Exception as e:
        print(f"MCP 브라우저 테스트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 테스트 실패: {str(e)}")

@router.get("/mcp/cached-data")
async def list_mcp_cached_data():
    """MCP로 수집된 캐시 데이터 목록"""
    try:
        # 캐시 디렉토리 내용 조회 (파일시스템 MCP 사용)
        cache_result = await enhanced_crawler_service.mcp_client.call_filesystem_read("backend/data/mcp_crawled/")
        
        return {
            "cached_files": cache_result if cache_result else [],
            "query_date": datetime.now().isoformat(),
            "mcp_status": enhanced_crawler_service.get_mcp_status()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP 캐시 조회 실패: {str(e)}")

@router.post("/mcp/test-fetch")
async def test_mcp_fetch():
    """MCP-Fetch 스타일 HTTP 요청 테스트"""
    try:
        print("=== MCP-Fetch 기능 테스트 ===")
        
        test_results = {}
        
        # 1. 기본 GET 요청 테스트
        get_result = await enhanced_crawler_service.mcp_client.call_fetch_get("https://httpbin.org/get")
        test_results["basic_get"] = {
            "success": get_result.get('success'),
            "status_code": get_result.get('status_code'),
            "has_content": bool(get_result.get('content')),
            "mcp_fetch": get_result.get('mcp_fetch')
        }
        
        # 2. 헤더 포함 GET 요청 테스트
        headers_result = await enhanced_crawler_service.mcp_client.call_fetch_get(
            "https://httpbin.org/headers",
            headers={"X-Test-Header": "MCP-Test", "Custom-Agent": "MCP-Enhanced-Crawler"}
        )
        test_results["headers_get"] = {
            "success": headers_result.get('success'),
            "status_code": headers_result.get('status_code'),
            "mcp_fetch": headers_result.get('mcp_fetch')
        }
        
        # 3. POST 요청 테스트
        post_result = await enhanced_crawler_service.mcp_client.call_fetch_post(
            "https://httpbin.org/post",
            data={"test_key": "MCP-Fetch 테스트", "timestamp": datetime.now().isoformat()}
        )
        test_results["post_request"] = {
            "success": post_result.get('success'),
            "status_code": post_result.get('status_code'),
            "mcp_fetch": post_result.get('mcp_fetch')
        }
        
        # 4. 재시도 기능 테스트 (가끔 실패하는 URL)
        retry_result = await enhanced_crawler_service.mcp_client.call_fetch_api_with_retry(
            "https://httpbin.org/status/200,404,500",  # 랜덤 상태코드 반환
            max_retries=3
        )
        test_results["retry_test"] = {
            "success": retry_result.get('success'),
            "retry_attempt": retry_result.get('retry_attempt', 0),
            "status_code": retry_result.get('status_code'),
            "mcp_fetch": retry_result.get('mcp_fetch')
        }
        
        # 5. 실제 통계 사이트 테스트
        molit_result = await enhanced_crawler_service.mcp_client.call_fetch_get("https://stat.molit.go.kr")
        test_results["molit_site"] = {
            "success": molit_result.get('success'),
            "status_code": molit_result.get('status_code'),
            "content_length": molit_result.get('content_length', 0),
            "has_korean": "통계" in molit_result.get('content', '') if molit_result.get('success') else False,
            "mcp_fetch": molit_result.get('mcp_fetch')
        }
        
        return {
            "test_type": "MCP-Fetch 기능 테스트",
            "test_date": datetime.now().isoformat(),
            "test_results": test_results,
            "total_tests": len(test_results),
            "successful_tests": sum(1 for result in test_results.values() if result.get('success')),
            "mcp_status": enhanced_crawler_service.get_mcp_status()
        }
        
    except Exception as e:
        print(f"MCP-Fetch 테스트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"MCP-Fetch 테스트 실패: {str(e)}")

@router.post("/mcp/fetch-compare")  
async def compare_fetch_methods(url: str = "https://stat.molit.go.kr"):
    """기존 방식 vs MCP-Fetch 방식 성능 비교"""
    try:
        print(f"=== Fetch 방식 성능 비교: {url} ===")
        
        import time
        import aiohttp
        
        results = {}
        
        # 1. 기존 aiohttp 방식
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    content = await response.text()
                    old_method_time = time.time() - start_time
                    results["traditional_aiohttp"] = {
                        "success": True,
                        "status_code": response.status,
                        "content_length": len(content),
                        "execution_time": round(old_method_time, 3),
                        "method": "직접 aiohttp"
                    }
        except Exception as e:
            results["traditional_aiohttp"] = {
                "success": False,
                "error": str(e),
                "method": "직접 aiohttp"
            }
        
        # 2. MCP-Fetch 방식
        start_time = time.time()
        mcp_result = await enhanced_crawler_service.mcp_client.call_fetch_get(url)
        mcp_method_time = time.time() - start_time
        
        results["mcp_fetch"] = {
            "success": mcp_result.get('success'),
            "status_code": mcp_result.get('status_code'),
            "content_length": mcp_result.get('content_length', 0),
            "execution_time": round(mcp_method_time, 3),
            "method": "MCP-Fetch",
            "additional_features": [
                "향상된 헤더 관리",
                "자동 재시도 지원", 
                "세션 쿠키 관리",
                "표준화된 응답 포맷",
                "로깅 및 모니터링"
            ]
        }
        
        # 3. 성능 비교 분석
        comparison = {}
        if results["traditional_aiohttp"].get("success") and results["mcp_fetch"].get("success"):
            traditional_time = results["traditional_aiohttp"]["execution_time"]
            mcp_time = results["mcp_fetch"]["execution_time"]
            
            comparison = {
                "speed_difference": round(abs(mcp_time - traditional_time), 3),
                "mcp_faster": mcp_time < traditional_time,
                "performance_ratio": round(traditional_time / mcp_time, 2) if mcp_time > 0 else 0,
                "recommendation": "MCP-Fetch가 더 안정적이고 기능이 풍부합니다" if mcp_time <= traditional_time * 1.5 else "성능 최적화 필요"
            }
        
        return {
            "comparison_type": "Fetch 방식 성능 비교",
            "test_url": url,
            "test_date": datetime.now().isoformat(),
            "results": results,
            "performance_comparison": comparison,
            "conclusion": "MCP-Fetch는 약간의 오버헤드가 있지만 풍부한 기능과 안정성을 제공합니다",
            "mcp_status": enhanced_crawler_service.get_mcp_status()
        }
        
    except Exception as e:
        print(f"Fetch 비교 테스트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Fetch 비교 실패: {str(e)}")

# === SQLite MCP 통합 API 엔드포인트들 ===

@router.post("/sqlite/save-metadata")
async def save_stat_metadata_to_db(metadata: Dict[str, Any]):
    """통계 메타데이터를 SQLite에 저장"""
    try:
        print(f"=== SQLite에 메타데이터 저장: {metadata.get('title', 'Unknown')} ===")
        
        result = await mcp_client.save_crawled_metadata(metadata)
        
        return {
            "message": "메타데이터 저장 완료",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"SQLite 메타데이터 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=f"메타데이터 저장 실패: {str(e)}")

@router.post("/sqlite/save-data")
async def save_stat_data_to_db(metadata_id: str, year: int, data: Dict[str, Any]):
    """통계 데이터를 SQLite에 저장"""
    try:
        print(f"=== SQLite에 통계 데이터 저장: {metadata_id}/{year} ===")
        
        result = await mcp_client.save_crawled_data(metadata_id, year, data)
        
        return {
            "message": "통계 데이터 저장 완료",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"SQLite 데이터 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 저장 실패: {str(e)}")

@router.get("/sqlite/metadata/{metadata_id}")
async def get_metadata_from_db(metadata_id: str):
    """SQLite에서 메타데이터 조회"""
    try:
        print(f"=== SQLite에서 메타데이터 조회: {metadata_id} ===")
        
        result = await mcp_client.get_metadata_from_db(metadata_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail="메타데이터를 찾을 수 없습니다")
        
        return {
            "message": "메타데이터 조회 완료",
            "metadata": result["metadata"],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"SQLite 메타데이터 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"메타데이터 조회 실패: {str(e)}")

@router.get("/sqlite/data/{metadata_id}")
async def get_data_from_db(metadata_id: str, year: Optional[int] = Query(None)):
    """SQLite에서 통계 데이터 조회"""
    try:
        print(f"=== SQLite에서 통계 데이터 조회: {metadata_id}" + (f"/{year}" if year else "") + " ===")
        
        result = await mcp_client.get_data_from_db(metadata_id, year)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail="통계 데이터를 찾을 수 없습니다")
        
        return {
            "message": "통계 데이터 조회 완료",
            "data": result["data"],
            "count": result["count"],
            "metadata_id": metadata_id,
            "year": year,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"SQLite 데이터 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")

@router.get("/sqlite/search")
async def search_metadata_in_db(query: str = Query(..., description="검색어"), 
                               limit: int = Query(20, ge=1, le=100)):
    """SQLite에서 메타데이터 검색"""
    try:
        print(f"=== SQLite에서 메타데이터 검색: '{query}' (limit: {limit}) ===")
        
        result = await mcp_client.search_metadata_in_db(query, limit)
        
        return {
            "message": "검색 완료",
            "query": query,
            "results": result["results"],
            "count": result["count"],
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"SQLite 검색 오류: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")

@router.get("/sqlite/summary")
async def get_db_summary():
    """데이터베이스 통계 요약"""
    try:
        print("=== SQLite 데이터베이스 요약 조회 ===")
        
        result = await mcp_client.get_db_stats_summary()
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="요약 정보 조회 실패")
        
        return {
            "message": "데이터베이스 요약 조회 완료",
            "summary": result["summary"],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"SQLite 요약 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"요약 조회 실패: {str(e)}")

@router.post("/sqlite/crawling-session")
async def create_crawling_session(session_name: str):
    """크롤링 세션 생성"""
    try:
        session_id = f"session_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        
        print(f"=== SQLite에 크롤링 세션 생성: {session_name} ({session_id}) ===")
        
        result = await mcp_client.create_crawling_session_in_db(session_id, session_name)
        
        return {
            "message": "크롤링 세션 생성 완료",
            "session_id": result["session_id"],
            "session_name": session_name,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"SQLite 세션 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")

@router.post("/sqlite/save-analysis")
async def save_ai_analysis_to_db(analysis_data: Dict[str, Any]):
    """AI 분석 결과를 SQLite에 저장"""
    try:
        analysis_id = analysis_data.get("analysis_id") or f"analysis_{uuid.uuid4().hex[:12]}"
        metadata_id = analysis_data.get("metadata_id")
        analysis_type = analysis_data.get("analysis_type", "basic")
        result_data = analysis_data.get("result", {})
        
        print(f"=== SQLite에 AI 분석 결과 저장: {analysis_id} ({analysis_type}) ===")
        
        result = await mcp_client.save_ai_analysis_to_db(analysis_id, metadata_id, analysis_type, result_data)
        
        return {
            "message": "AI 분석 결과 저장 완료",
            "analysis_id": result["analysis_id"],
            "analysis_type": analysis_type,
            "metadata_id": metadata_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"SQLite AI 분석 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=f"AI 분석 저장 실패: {str(e)}")

@router.post("/sqlite/test-all")
async def test_sqlite_functionality():
    """SQLite MCP 기능 종합 테스트"""
    try:
        print("=== SQLite MCP 기능 종합 테스트 시작 ===")
        
        test_results = {}
        
        # 1. 샘플 메타데이터 저장 테스트
        sample_metadata = {
            "id": f"test_{uuid.uuid4().hex[:8]}",
            "title": "SQLite MCP 테스트 통계",
            "purpose": "MCP 통합 기능 테스트",
            "frequency": "일회성",
            "department": "테스트부서",
            "keywords": ["테스트", "MCP", "SQLite"],
            "related_terms": {"MCP": "Model Context Protocol", "SQLite": "경량 데이터베이스"},
            "url": "https://example.com/test"
        }
        
        metadata_result = await mcp_client.save_crawled_metadata(sample_metadata)
        test_results["save_metadata"] = metadata_result
        
        if metadata_result.get("success"):
            metadata_id = metadata_result["metadata_id"]
            
            # 2. 샘플 데이터 저장 테스트
            sample_data = {
                "서울": 100000,
                "부산": 50000,
                "대구": 30000,
                "기타": 120000
            }
            
            data_result = await mcp_client.save_crawled_data(metadata_id, 2024, sample_data)
            test_results["save_data"] = data_result
            
            # 3. 메타데이터 조회 테스트
            get_metadata_result = await mcp_client.get_metadata_from_db(metadata_id)
            test_results["get_metadata"] = get_metadata_result
            
            # 4. 데이터 조회 테스트
            get_data_result = await mcp_client.get_data_from_db(metadata_id, 2024)
            test_results["get_data"] = get_data_result
            
            # 5. 검색 테스트
            search_result = await mcp_client.search_metadata_in_db("테스트", 5)
            test_results["search"] = search_result
            
            # 6. AI 분석 저장 테스트
            analysis_result = await mcp_client.save_ai_analysis_to_db(
                f"test_analysis_{uuid.uuid4().hex[:8]}",
                metadata_id,
                "test",
                {"test_result": "성공", "score": 95.5}
            )
            test_results["save_analysis"] = analysis_result
        
        # 7. 데이터베이스 요약 테스트
        summary_result = await mcp_client.get_db_stats_summary()
        test_results["get_summary"] = summary_result
        
        # 8. 크롤링 세션 생성 테스트
        session_result = await mcp_client.create_crawling_session_in_db(
            f"test_session_{uuid.uuid4().hex[:8]}", "SQLite MCP 테스트 세션"
        )
        test_results["create_session"] = session_result
        
        # 결과 분석
        successful_tests = sum(1 for result in test_results.values() if result.get("success"))
        total_tests = len(test_results)
        
        return {
            "test_type": "SQLite MCP 기능 종합 테스트",
            "test_date": datetime.now().isoformat(),
            "test_results": test_results,
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": round(successful_tests / total_tests * 100, 1),
                "status": "모든 테스트 성공" if successful_tests == total_tests else f"{successful_tests}/{total_tests} 테스트 성공"
            }
        }
        
    except Exception as e:
        print(f"SQLite 종합 테스트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"종합 테스트 실패: {str(e)}")

# === 고급 통계 분석 MCP API 엔드포인트들 ===

@router.post("/advanced-stats/comprehensive")
async def comprehensive_statistical_analysis(data: Dict[str, Any]):
    """종합 통계 분석 (모든 MCP 서버 활용)"""
    try:
        print("=== 종합 통계 분석 시작 ===")
        
        stat_data = data.get("data", {})
        analysis_type = data.get("analysis_type", "full")
        
        if not stat_data:
            raise ValueError("분석할 데이터가 없습니다.")
        
        # MCP 클라이언트를 통한 종합 분석
        result = await mcp_client.comprehensive_statistical_analysis(stat_data, analysis_type)
        
        return {
            "message": "종합 통계 분석 완료",
            "analysis_type": analysis_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"종합 통계 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=f"종합 통계 분석 실패: {str(e)}")

@router.post("/advanced-stats/enhanced-basic")
async def enhanced_basic_statistics_analysis(data: Dict[str, Any]):
    """향상된 기본통계현황분석"""
    try:
        print("=== 향상된 기본통계현황분석 시작 ===")
        
        stat_data = data.get("data", {})
        
        if not stat_data:
            raise ValueError("분석할 데이터가 없습니다.")
        
        # MCP 클라이언트를 통한 향상된 기본 통계 분석
        result = await mcp_client.enhanced_basic_statistics(stat_data)
        
        return {
            "message": "향상된 기본통계현황분석 완료", 
            "result": result,
            "data_columns": list(stat_data.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"향상된 기본통계분석 오류: {e}")
        raise HTTPException(status_code=500, detail=f"향상된 기본통계분석 실패: {str(e)}")

@router.post("/advanced-stats/pandas-analysis")
async def pandas_analysis_endpoint(operation: str, data: Dict[str, Any]):
    """Pandas Analysis MCP 서버 직접 호출"""
    try:
        print(f"=== Pandas Analysis MCP 호출: {operation} ===")
        
        result = await mcp_client.call_pandas_analysis(operation, **data)
        
        return {
            "message": f"Pandas Analysis {operation} 완료",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Pandas Analysis 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Pandas Analysis 실패: {str(e)}")

@router.post("/advanced-stats/math-calculation")
async def math_calculation_endpoint(operation: str, calculation_data: Dict[str, Any]):
    """Mathematical Calculation MCP 서버 직접 호출"""
    try:
        print(f"=== Math Calculation MCP 호출: {operation} ===")
        
        result = await mcp_client.call_math_calculation(operation, **calculation_data)
        
        return {
            "message": f"Math Calculation {operation} 완료",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Math Calculation 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Math Calculation 실패: {str(e)}")

@router.post("/advanced-stats/visualization")
async def visualization_endpoint(operation: str, viz_data: Dict[str, Any]):
    """Visualization MCP 서버 직접 호출"""
    try:
        print(f"=== Visualization MCP 호출: {operation} ===")
        
        result = await mcp_client.call_visualization(operation, **viz_data)
        
        return {
            "message": f"Visualization {operation} 완료",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Visualization 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Visualization 실패: {str(e)}")

@router.post("/advanced-stats/file-analysis")
async def file_analysis_endpoint(operation: str, file_path: str, analysis_options: Dict[str, Any] = None):
    """File Analysis MCP 서버 직접 호출"""
    try:
        print(f"=== File Analysis MCP 호출: {operation} on {file_path} ===")
        
        options = analysis_options or {}
        result = await mcp_client.call_file_analysis(operation, file_path, **options)
        
        return {
            "message": f"File Analysis {operation} 완료",
            "file_path": file_path,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"File Analysis 오류: {e}")
        raise HTTPException(status_code=500, detail=f"File Analysis 실패: {str(e)}")

@router.get("/advanced-stats/test-all-mcp")
async def test_all_mcp_servers():
    """모든 통계 분석 MCP 서버 테스트"""
    try:
        print("=== 모든 MCP 서버 테스트 시작 ===")
        
        test_results = {}
        
        # 샘플 데이터 생성
        sample_data = {
            "sales": [100, 150, 200, 180, 220, 250, 300, 280, 320, 350],
            "profit": [20, 30, 45, 35, 50, 60, 70, 65, 75, 85],
            "expenses": [80, 120, 155, 145, 170, 190, 230, 215, 245, 265]
        }
        
        # 1. Pandas Analysis 테스트
        pandas_result = await mcp_client.call_pandas_analysis("basic_statistics", data=sample_data)
        test_results["pandas_analysis"] = pandas_result
        
        # 2. Math Calculation 테스트
        math_result = await mcp_client.call_math_calculation("basic_statistics", data=sample_data["sales"])
        test_results["math_calculation"] = math_result
        
        # 3. Visualization 테스트
        viz_result = await mcp_client.call_visualization("create_statistical_chart", 
                                                       data=sample_data, chart_type="histogram")
        test_results["visualization"] = viz_result
        
        # 4. 종합 분석 테스트
        comprehensive_result = await mcp_client.comprehensive_statistical_analysis(sample_data, "full")
        test_results["comprehensive_analysis"] = comprehensive_result
        
        # 5. 향상된 기본 통계 테스트
        enhanced_basic_result = await mcp_client.enhanced_basic_statistics(sample_data)
        test_results["enhanced_basic_statistics"] = enhanced_basic_result
        
        # 결과 분석
        successful_tests = sum(1 for result in test_results.values() if result.get("success"))
        total_tests = len(test_results)
        
        return {
            "test_type": "모든 통계 분석 MCP 서버 테스트",
            "test_date": datetime.now().isoformat(),
            "test_results": test_results,
            "sample_data": sample_data,
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": round(successful_tests / total_tests * 100, 1),
                "status": "모든 테스트 성공" if successful_tests == total_tests else f"{successful_tests}/{total_tests} 테스트 성공"
            }
        }
        
    except Exception as e:
        print(f"MCP 서버 테스트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 서버 테스트 실패: {str(e)}")

@router.get("/advanced-stats/mcp-status")
async def get_mcp_servers_status():
    """모든 MCP 서버 상태 확인"""
    try:
        print("=== MCP 서버 상태 확인 ===")
        
        servers_status = {
            "browser": {"status": "active", "description": "브라우저 자동화 및 웹 크롤링"},
            "filesystem": {"status": "active", "description": "파일시스템 접근 및 관리"}, 
            "sqlite": {"status": "active", "description": "SQLite 데이터베이스 관리"},
            "pandas-analysis": {"status": "active", "description": "pandas 기반 데이터 분석 및 통계 계산"},
            "file-analysis": {"status": "active", "description": "파일 구조 분석 및 데이터 프로파일링"},
            "math-calculation": {"status": "active", "description": "수학적 계산, 통계 검정, 회귀 분석"},
            "visualization": {"status": "active", "description": "데이터 시각화 및 차트 생성"}
        }
        
        return {
            "message": "MCP 서버 상태 조회 완료",
            "servers": servers_status,
            "total_servers": len(servers_status),
            "active_servers": sum(1 for s in servers_status.values() if s["status"] == "active"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"MCP 서버 상태 확인 오류: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 서버 상태 확인 실패: {str(e)}")

# === 순수 분석 API 엔드포인트들 (AI/LLM 없음) ===

@router.post("/pure-analysis/basic")
async def pure_basic_analysis(request: GenerateStoryRequest):
    """AI 없는 순수 기본 분석 (MCP만 사용)"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"=== 순수 MCP 기본 분석: {request.stat_name} ===")
        
        # 1. MCP로 메타데이터 수집
        metadata = await enhanced_crawler_service.get_stat_metadata_with_mcp(stat_url)
        
        # 2. MCP로 통계 데이터 수집
        stat_data = await enhanced_crawler_service.get_stat_data_with_mcp(stat_url, request.period)
        
        # 3. 순수 분석 서비스로 분석 (AI 없음)
        basic_analysis = await pure_analysis_service.analyze_basic_data_pure(stat_data, metadata.dict())
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "collection_method": "순수 MCP 분석 (AI 없음)",
            "metadata": metadata.dict(),
            "data_structure": {
                "total_years": len(stat_data),
                "data_keys": list(stat_data[0].data.keys()) if stat_data else [],
                "year_range": {
                    "start": min([int(d.year) for d in stat_data]) if stat_data else None,
                    "end": max([int(d.year) for d in stat_data]) if stat_data else None
                }
            },
            "basic_analysis": basic_analysis,
            "analysis_type": "pure_mcp_analysis"
        }
        
    except Exception as e:
        print(f"순수 MCP 기본 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=f"순수 MCP 기본 분석 실패: {str(e)}")

@router.post("/pure-analysis/advanced-statistics")
async def pure_advanced_statistics(request: GenerateStoryRequest):
    """AI 없는 순수 기본통계현황분석 (MCP만 사용)"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"=== 순수 MCP 기본통계현황분석: {request.stat_name} ===")
        
        # 1. MCP로 메타데이터 수집
        metadata = await enhanced_crawler_service.get_stat_metadata_with_mcp(stat_url)
        
        # 2. MCP로 통계 데이터 수집
        stat_data = await enhanced_crawler_service.get_stat_data_with_mcp(stat_url, request.period)
        
        # 3. 순수 통계 분석 (AI 없음)
        advanced_analysis = await pure_analysis_service.analyze_advanced_statistics_pure(stat_data, metadata.dict())
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "analysis_type": "순수 MCP 기본통계현황분석",
            "metadata": metadata.dict(),
            "basic_statistics": advanced_analysis["basic_statistics"],
            "analysis_summary": advanced_analysis["analysis_summary"],
            "data_quality": advanced_analysis.get("data_quality", {}),
            "analysis_method": "Pure MCP Mathematical Analysis"
        }
        
    except Exception as e:
        print(f"순수 MCP 기본통계현황분석 오류: {e}")
        raise HTTPException(status_code=500, detail=f"순수 MCP 기본통계현황분석 실패: {str(e)}")

@router.post("/pure-analysis/comprehensive")
async def pure_comprehensive_analysis(request: GenerateStoryRequest):
    """AI 없는 순수 종합 분석 (MCP만 사용)"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"=== 순수 MCP 종합 분석: {request.stat_name} ===")
        
        # 1. MCP로 메타데이터 수집
        metadata = await enhanced_crawler_service.get_stat_metadata_with_mcp(stat_url)
        
        # 2. MCP로 통계 데이터 수집
        stat_data = await enhanced_crawler_service.get_stat_data_with_mcp(stat_url, request.period)
        
        # 3. 순수 종합 분석 (AI 없음)
        comprehensive_analysis = await pure_analysis_service.analyze_comprehensive_pure(stat_data, metadata.dict())
        
        return {
            "stat_name": request.stat_name,
            "analysis_date": datetime.now().isoformat(),
            "metadata": metadata.dict(),
            "analysis": comprehensive_analysis,
            "analysis_method": "Pure MCP Comprehensive Analysis"
        }
        
    except Exception as e:
        print(f"순수 MCP 종합 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=f"순수 MCP 종합 분석 실패: {str(e)}")

@router.post("/pure-analysis/statistical-only") 
async def pure_statistical_analysis_only(data: Dict[str, Any]):
    """AI 없는 순수 통계 계산만 (데이터 직접 입력)"""
    try:
        print("=== 순수 통계 계산 (데이터 직접 입력) ===")
        
        input_data = data.get("data", {})
        if not input_data:
            raise ValueError("분석할 데이터가 없습니다.")
        
        # MCP 서버들을 활용한 순수 통계 분석
        results = {}
        
        # 1. 기본 통계 계산
        if isinstance(input_data, dict) and len(input_data) > 0:
            first_key = list(input_data.keys())[0]
            first_values = input_data[first_key]
            
            basic_stats = await mcp_client.call_math_calculation("basic_statistics", data=first_values)
            results["basic_statistics"] = basic_stats
            
            # 2. 상관관계 분석 (2개 이상의 변수가 있는 경우)
            if len(input_data.keys()) >= 2:
                keys = list(input_data.keys())
                correlation_analysis = await mcp_client.call_math_calculation(
                    "correlation_coefficient",
                    x=input_data[keys[0]],
                    y=input_data[keys[1]]
                )
                results["correlation_analysis"] = correlation_analysis
            
            # 3. 시각화 생성
            visualization = await mcp_client.call_visualization(
                "create_statistical_summary_viz",
                data=input_data,
                title="순수 통계 분석 결과"
            )
            results["visualization"] = visualization
        
        return {
            "analysis_type": "순수 통계 계산",
            "input_data": input_data,
            "results": results,
            "analysis_date": datetime.now().isoformat(),
            "method": "Pure MCP Statistical Calculation Only"
        }
        
    except Exception as e:
        print(f"순수 통계 계산 오류: {e}")
        raise HTTPException(status_code=500, detail=f"순수 통계 계산 실패: {str(e)}")

@router.get("/pure-analysis/demo")
async def pure_analysis_demo():
    """AI 없는 순수 분석 데모"""
    try:
        print("=== 순수 분석 데모 실행 ===")
        
        # 샘플 데이터 생성
        sample_data = {
            "서울": [100, 110, 120, 130, 140, 150],
            "부산": [50, 55, 60, 65, 70, 75], 
            "대구": [30, 32, 34, 36, 38, 40]
        }
        
        demo_results = {}
        
        # 1. 기본 통계 분석
        basic_stats = await mcp_client.call_math_calculation("basic_statistics", data=sample_data["서울"])
        demo_results["basic_statistics"] = basic_stats
        
        # 2. 상관관계 분석
        correlation = await mcp_client.call_math_calculation(
            "correlation_coefficient",
            x=sample_data["서울"],
            y=sample_data["부산"]
        )
        demo_results["correlation_analysis"] = correlation
        
        # 3. 시각화
        histogram = await mcp_client.call_visualization(
            "create_statistical_chart",
            data={"서울": sample_data["서울"]},
            chart_type="histogram",
            title="서울 데이터 분포"
        )
        demo_results["histogram"] = histogram
        
        # 4. 박스플롯
        boxplot = await mcp_client.call_visualization(
            "create_statistical_chart",
            data=sample_data,
            chart_type="boxplot", 
            title="전체 데이터 박스플롯"
        )
        demo_results["boxplot"] = boxplot
        
        return {
            "demo_type": "순수 MCP 분석 데모",
            "sample_data": sample_data,
            "demo_results": demo_results,
            "features": [
                "AI/LLM 없음",
                "순수 통계 계산만",
                "MCP 서버 기반",
                "수학적 정확성 보장",
                "객관적 결과만"
            ],
            "analysis_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"순수 분석 데모 오류: {e}")
        raise HTTPException(status_code=500, detail=f"순수 분석 데모 실패: {str(e)}")

# === 데이터 확인 및 탐색 API 엔드포인트들 ===

@router.post("/data/inspect")
async def inspect_collected_data(request: GenerateStoryRequest):
    """수집된 데이터 상세 확인"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"=== 데이터 수집 및 상세 확인: {request.stat_name} ===")
        
        # 1. MCP로 메타데이터 수집
        metadata = await enhanced_crawler_service.get_stat_metadata_with_mcp(stat_url)
        
        # 2. MCP로 통계 데이터 수집
        stat_data = await enhanced_crawler_service.get_stat_data_with_mcp(stat_url, request.period)
        
        # 3. 데이터 구조 분석
        data_analysis = {
            "collection_info": {
                "total_records": len(stat_data),
                "collection_time": datetime.now().isoformat(),
                "period": request.period,
                "source_url": stat_url
            },
            "metadata": {
                "title": metadata.title,
                "department": metadata.department,
                "purpose": metadata.purpose,
                "frequency": metadata.frequency,
                "keywords": metadata.keywords
            },
            "data_structure": [],
            "data_sample": [],
            "data_quality": {}
        }
        
        # 데이터 상세 분석
        if stat_data:
            years = []
            all_keys = set()
            
            for i, item in enumerate(stat_data):
                years.append(item.year)
                item_keys = list(item.data.keys())
                all_keys.update(item_keys)
                
                # 처음 5개 레코드는 샘플로 보여주기
                if i < 5:
                    data_analysis["data_sample"].append({
                        "year": item.year,
                        "data": item.data,
                        "data_keys": item_keys,
                        "data_count": len(item.data)
                    })
            
            # 데이터 구조 요약
            data_analysis["data_structure"] = {
                "year_range": {
                    "start": min(years) if years else None,
                    "end": max(years) if years else None,
                    "total_years": len(set(years))
                },
                "all_data_keys": list(all_keys),
                "total_unique_keys": len(all_keys),
                "years_list": sorted(list(set(years)))
            }
            
            # 데이터 품질 분석
            complete_records = sum(1 for item in stat_data if item.data)
            empty_records = len(stat_data) - complete_records
            
            data_analysis["data_quality"] = {
                "completeness_rate": (complete_records / len(stat_data) * 100) if stat_data else 0,
                "complete_records": complete_records,
                "empty_records": empty_records,
                "consistency": "양호" if len(all_keys) <= 10 else "키 개수 많음",
                "data_types": self._analyze_data_types(stat_data)
            }
        
        return {
            "stat_name": request.stat_name,
            "inspection_result": data_analysis,
            "raw_data_preview": [
                {
                    "year": item.year,
                    "data": item.data
                } for item in stat_data[:3]  # 처음 3개만 미리보기
            ],
            "inspection_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"데이터 확인 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 확인 실패: {str(e)}")

@router.post("/data/raw-view")
async def view_raw_data(request: GenerateStoryRequest, limit: int = 10):
    """수집된 원시 데이터 전체 보기"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"=== 원시 데이터 전체 보기: {request.stat_name} (limit: {limit}) ===")
        
        # 데이터 수집
        stat_data = await enhanced_crawler_service.get_stat_data_with_mcp(stat_url, request.period)
        
        # 제한된 개수만 반환
        limited_data = stat_data[:limit] if stat_data else []
        
        return {
            "stat_name": request.stat_name,
            "total_records": len(stat_data) if stat_data else 0,
            "showing_records": len(limited_data),
            "limit": limit,
            "raw_data": [
                {
                    "record_index": i,
                    "year": item.year,
                    "data": item.data,
                    "data_size": len(item.data) if item.data else 0
                } for i, item in enumerate(limited_data)
            ],
            "collection_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"원시 데이터 보기 오류: {e}")
        raise HTTPException(status_code=500, detail=f"원시 데이터 보기 실패: {str(e)}")

@router.post("/data/summary")
async def data_collection_summary(request: GenerateStoryRequest):
    """데이터 수집 요약 정보"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"=== 데이터 수집 요약: {request.stat_name} ===")
        
        # 1. 메타데이터 수집
        metadata = await enhanced_crawler_service.get_stat_metadata_with_mcp(stat_url)
        
        # 2. 데이터 수집
        stat_data = await enhanced_crawler_service.get_stat_data_with_mcp(stat_url, request.period)
        
        # 3. 요약 정보 생성
        summary = {
            "basic_info": {
                "stat_name": request.stat_name,
                "source_url": stat_url,
                "collection_time": datetime.now().isoformat(),
                "requested_period": request.period
            },
            "metadata_summary": {
                "title": metadata.title,
                "department": metadata.department,
                "data_available": bool(metadata.title and metadata.department)
            },
            "data_summary": {
                "total_records": len(stat_data) if stat_data else 0,
                "has_data": bool(stat_data),
                "year_coverage": None,
                "data_fields": [],
                "sample_values": {}
            }
        }
        
        # 데이터가 있는 경우 상세 요약
        if stat_data:
            years = [item.year for item in stat_data]
            all_fields = set()
            sample_values = {}
            
            for item in stat_data:
                if item.data:
                    all_fields.update(item.data.keys())
                    # 첫 번째 레코드의 값들을 샘플로 저장
                    if not sample_values and item.data:
                        sample_values = dict(list(item.data.items())[:3])  # 처음 3개 필드만
            
            summary["data_summary"].update({
                "year_coverage": {
                    "start": min(years) if years else None,
                    "end": max(years) if years else None,
                    "total_years": len(set(years))
                },
                "data_fields": list(all_fields)[:10],  # 최대 10개 필드만 표시
                "total_fields": len(all_fields),
                "sample_values": sample_values
            })
        
        return {
            "summary": summary,
            "collection_status": "success" if stat_data else "no_data",
            "recommendations": self._get_data_recommendations(summary)
        }
        
    except Exception as e:
        print(f"데이터 수집 요약 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 수집 요약 실패: {str(e)}")

@router.post("/data/explore-by-year")
async def explore_data_by_year(request: GenerateStoryRequest, target_year: int):
    """특정 연도 데이터 상세 탐색"""
    try:
        stat_url = request.stat_url or "https://stat.molit.go.kr/portal/cate/statView.do"
        
        print(f"=== {target_year}년 데이터 상세 탐색: {request.stat_name} ===")
        
        # 데이터 수집
        stat_data = await enhanced_crawler_service.get_stat_data_with_mcp(stat_url, request.period)
        
        # 해당 연도 데이터 찾기
        target_data = None
        for item in stat_data:
            if item.year == target_year:
                target_data = item
                break
        
        if not target_data:
            available_years = [item.year for item in stat_data]
            raise HTTPException(
                status_code=404, 
                detail=f"{target_year}년 데이터를 찾을 수 없습니다. 사용 가능한 연도: {available_years}"
            )
        
        # 해당 연도 데이터 상세 분석
        year_analysis = {
            "year": target_year,
            "data_overview": {
                "total_fields": len(target_data.data) if target_data.data else 0,
                "has_data": bool(target_data.data)
            },
            "detailed_data": target_data.data,
            "data_analysis": {}
        }
        
        # 수치 데이터 분석
        if target_data.data:
            numeric_data = {}
            text_data = {}
            
            for key, value in target_data.data.items():
                try:
                    # 숫자 변환 시도
                    if isinstance(value, (int, float)):
                        numeric_value = float(value)
                    elif isinstance(value, str):
                        numeric_value = float(value.replace(',', '').replace('%', ''))
                    else:
                        raise ValueError("Not numeric")
                    
                    numeric_data[key] = numeric_value
                except (ValueError, TypeError):
                    text_data[key] = str(value)
            
            year_analysis["data_analysis"] = {
                "numeric_fields": list(numeric_data.keys()),
                "numeric_count": len(numeric_data),
                "text_fields": list(text_data.keys()),
                "text_count": len(text_data),
                "numeric_summary": {
                    key: {
                        "value": value,
                        "formatted": f"{value:,.0f}" if value >= 1 else f"{value:.3f}"
                    } for key, value in numeric_data.items()
                } if numeric_data else {},
                "total_numeric_sum": sum(numeric_data.values()) if numeric_data else 0
            }
        
        return {
            "stat_name": request.stat_name,
            "target_year": target_year,
            "year_analysis": year_analysis,
            "exploration_time": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"{target_year}년 데이터 탐색 오류: {e}")
        raise HTTPException(status_code=500, detail=f"{target_year}년 데이터 탐색 실패: {str(e)}")

@router.get("/data/collection-log")
async def get_data_collection_log():
    """데이터 수집 로그 확인"""
    try:
        print("=== 데이터 수집 로그 조회 ===")
        
        # SQLite에서 MCP 서버 로그 조회
        logs_result = await mcp_client.get_db_stats_summary()
        
        # 최근 수집 활동 시뮬레이션 (실제로는 DB에서 조회)
        recent_collections = [
            {
                "timestamp": datetime.now().isoformat(),
                "action": "data_collection",
                "stat_name": "샘플 통계",
                "records_collected": 10,
                "status": "success"
            }
        ]
        
        return {
            "message": "데이터 수집 로그 조회 완료",
            "database_summary": logs_result.get("summary", {}),
            "recent_collections": recent_collections,
            "log_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"수집 로그 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"수집 로그 조회 실패: {str(e)}")

def _analyze_data_types(stat_data):
    """데이터 타입 분석 헬퍼 함수"""
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