"""
모듈화된 국토교통부 크롤러 - 기능별로 분리된 크롤러들을 통합
"""
from typing import List

from app.crawlers.recent_stats_crawler import RecentStatsCrawler
from app.crawlers.metadata_crawler import MetadataCrawler
from app.crawlers.data_crawler import DataCrawler
from app.models.stat_models import StatItem, StatMetadata, StatData

class ModularMolitCrawler:
    """모듈화된 국토교통부 크롤러"""

    def __init__(self):
        self.recent_stats_crawler = RecentStatsCrawler()
        self.metadata_crawler = MetadataCrawler()
        self.data_crawler = DataCrawler()

    async def get_recent_stats(self) -> List[StatItem]:
        """최근 통계 목록 조회"""
        return await self.recent_stats_crawler.get_recent_stats()

    async def get_stat_metadata(self, stat_url: str) -> StatMetadata:
        """통계 메타데이터 조회"""
        return await self.metadata_crawler.get_stat_metadata(stat_url)

    async def get_stat_data(self, stat_url: str, period: str = "5years") -> List[StatData]:
        """통계 데이터 조회"""
        return await self.data_crawler.get_stat_data(stat_url, period)