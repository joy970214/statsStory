from typing import List
from app.crawlers.molit_crawler import MolitCrawler
from app.crawlers.improved_molit_crawler import ImprovedMolitCrawler
from app.models.stat_models import StatItem, StatMetadata, StatData

class CrawlerService:
    def __init__(self):
        self.molit_crawler = MolitCrawler()  # 기존 크롤러 (최신통계 목록용)
        self.improved_crawler = ImprovedMolitCrawler()  # AI 분석 전용
    
    async def get_recent_stats(self) -> List[StatItem]:
        """최근 통계 목록 조회 - 기존 크롤러 사용 (복원됨)"""
        return await self.molit_crawler.get_recent_stats()
    
    async def get_stat_metadata(self, stat_url: str) -> StatMetadata:
        """통계 메타데이터 조회 - 기존 크롤러 사용"""
        return await self.molit_crawler.get_stat_metadata(stat_url)
    
    async def get_stat_data(self, stat_url: str, period: str = "5years") -> List[StatData]:
        """통계 데이터 조회 - 기존 크롤러 사용"""
        return await self.molit_crawler.get_stat_data(stat_url, period)
    
    # AI 분석 전용 메서드들
    async def get_stat_metadata_for_analysis(self, stat_url: str) -> StatMetadata:
        """AI 분석용 메타데이터 수집 - 개선된 크롤러 사용 (통계정보+관련용어 탭)"""
        return await self.improved_crawler.get_stat_metadata(stat_url)
    
    async def get_stat_data_for_analysis(self, stat_url: str, period: str = "5years") -> List[StatData]:
        """AI 분석용 데이터 수집 - 개선된 크롤러 사용 (#sFormId 활용)"""
        return await self.improved_crawler.get_stat_data(stat_url, period)
    
    async def get_available_stat_tables(self, stat_url: str) -> List[dict]:
        """사용 가능한 통계표 목록 조회 - AI 분석용"""
        return await self.improved_crawler.get_available_stat_tables(stat_url)