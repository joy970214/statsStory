from typing import List
from app.crawlers.modular_molit_crawler import ModularMolitCrawler
from app.crawlers.legacy.molit_crawler import MolitCrawler
from app.crawlers.legacy.optimized_molit_crawler import OptimizedMolitCrawler
from app.models.stat_models import StatItem, StatMetadata, StatData

class CrawlerService:
    def __init__(self):
        self.modular_crawler = ModularMolitCrawler()  # 모듈화된 크롤러 (메인)
        # 레거시 크롤러들 (백업용, 필요시에만 사용)
        self.legacy_crawler = None  # 지연 로딩
        self.optimized_crawler = None  # 지연 로딩
    
    def _get_legacy_crawler(self):
        """지연 로딩: 필요할 때만 레거시 크롤러 인스턴스 생성"""
        if self.legacy_crawler is None:
            self.legacy_crawler = MolitCrawler()
        return self.legacy_crawler

    def _get_optimized_crawler(self):
        """지연 로딩: 필요할 때만 최적화된 크롤러 인스턴스 생성"""
        if self.optimized_crawler is None:
            self.optimized_crawler = OptimizedMolitCrawler()
        return self.optimized_crawler

    async def get_recent_stats(self) -> List[StatItem]:
        """최근 통계 목록 조회 - 모듈화된 크롤러 우선 사용"""
        try:
            return await self.modular_crawler.get_recent_stats()
        except Exception as e:
            print(f"모듈화된 크롤러 실패, 레거시 크롤러로 전환: {e}")
            return await self._get_legacy_crawler().get_recent_stats()

    async def get_stat_metadata(self, stat_url: str) -> StatMetadata:
        """통계 메타데이터 조회 - 모듈화된 크롤러 우선 사용"""
        try:
            return await self.modular_crawler.get_stat_metadata(stat_url)
        except Exception as e:
            print(f"모듈화된 크롤러 실패, 레거시 크롤러로 전환: {e}")
            return await self._get_legacy_crawler().get_stat_metadata(stat_url)

    async def get_stat_data(self, stat_url: str, period: str = "5years") -> List[StatData]:
        """통계 데이터 조회 - 모듈화된 크롤러 우선 사용"""
        try:
            return await self.modular_crawler.get_stat_data(stat_url, period)
        except Exception as e:
            print(f"모듈화된 크롤러 실패, 레거시 크롤러로 전환: {e}")
            return await self._get_legacy_crawler().get_stat_data(stat_url, period)
    # AI 분석 전용 메서드들
    async def get_comprehensive_analysis_for_optimization(self, stat_url: str, progress_callback=None):
        """최적화된 종합 분석 - 한번의 호출로 메타데이터와 데이터 모두 수집"""
        optimized = self._get_optimized_crawler()
        analysis = await optimized.get_comprehensive_stat_analysis_optimized(stat_url, progress_callback)
        return analysis

    async def get_stat_metadata_for_analysis(self, stat_url: str) -> StatMetadata:
        """AI 분석용 메타데이터 수집 - 모듈화된 크롤러 우선 사용"""
        try:
            return await self.modular_crawler.get_stat_metadata(stat_url)
        except Exception as e:
            print(f"모듈화된 크롤러 실패, 레거시 크롤러로 전환: {e}")
            return await self._get_legacy_crawler().get_stat_metadata(stat_url)

    async def get_stat_data_for_analysis(self, stat_url: str, period: str = "5years") -> List[StatData]:
        """AI 분석용 데이터 수집 - 모듈화된 크롤러 우선 사용"""
        try:
            return await self.modular_crawler.get_stat_data(stat_url, period)
        except Exception as e:
            print(f"모듈화된 크롤러 실패, 레거시 크롤러로 전환: {e}")
            return await self._get_legacy_crawler().get_stat_data(stat_url, period)

    async def get_available_stat_tables(self, stat_url: str) -> List[dict]:
        """사용 가능한 통계표 목록 조회 - AI 분석용"""
        # OptimizedMolitCrawler의 내부 메소드 사용 (지연 로딩)
        optimized = self._get_optimized_crawler()
        return await optimized._get_stat_tables_with_conditions(stat_url)