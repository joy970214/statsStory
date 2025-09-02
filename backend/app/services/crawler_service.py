from typing import List
from app.crawlers.molit_crawler import MolitCrawler
from app.models.stat_models import StatItem, StatMetadata, StatData

class CrawlerService:
    def __init__(self):
        self.molit_crawler = MolitCrawler()
    
    async def get_recent_stats(self) -> List[StatItem]:
        """최근 통계 목록 조회"""
        return await self.molit_crawler.get_recent_stats()
    
    async def get_stat_metadata(self, stat_url: str) -> StatMetadata:
        """통계 메타데이터 조회"""
        return await self.molit_crawler.get_stat_metadata(stat_url)
    
    async def get_stat_data(self, stat_url: str, period: str = "5years") -> List[StatData]:
        """통계 데이터 조회"""
        return await self.molit_crawler.get_stat_data(stat_url, period)