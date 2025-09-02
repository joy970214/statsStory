import aiohttp
import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from app.models.stat_models import StatItem, StatMetadata, StatData


class SimpleMolitCrawler:
    """기존 최신통계 목록 기능을 위한 간단한 크롤러"""
    
    def __init__(self):
        self.base_url = "https://stat.molit.go.kr"
        self.recent_stats_url = f"{self.base_url}/portal/cate/newStatView.do?tab=recentStat"
        
    def _setup_selenium_driver(self):
        """Selenium 드라이버 설정"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        
        return driver

    async def get_recent_stats(self) -> List[StatItem]:
        """최근 1달 통계 목록 수집"""
        driver = None
        try:
            print("국토교통부 통계포털 접속 중...")
            
            driver = self._setup_selenium_driver()
            driver.get(self.recent_stats_url)
            
            # 페이지 로드 대기
            await asyncio.sleep(5)
            
            stats = []
            
            # 통계 목록 테이블 찾기
            try:
                # 다양한 테이블 선택자 시도
                table_selectors = [
                    "table.list",
                    "table[summary*='통계']",
                    ".data-table",
                    "table",
                    ".list-table"
                ]
                
                stat_table = None
                for selector in table_selectors:
                    tables = driver.find_elements(By.CSS_SELECTOR, selector)
                    if tables:
                        stat_table = tables[0]
                        break
                
                if stat_table:
                    rows = stat_table.find_elements(By.TAG_NAME, "tr")
                    
                    for i, row in enumerate(rows[1:], 1):  # 헤더 제외
                        if i > 20:  # 최대 20개로 제한
                            break
                            
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 3:
                                # 기본 정보 추출
                                title = cells[0].text.strip()
                                publish_date = cells[1].text.strip() if len(cells) > 1 else "2024-01-01"
                                department = cells[2].text.strip() if len(cells) > 2 else "국토교통부"
                                
                                # URL 추출 시도
                                url_element = cells[0].find_elements(By.TAG_NAME, "a")
                                url = ""
                                if url_element:
                                    href = url_element[0].get_attribute('href')
                                    if href:
                                        url = href if href.startswith('http') else urljoin(self.base_url, href)
                                
                                if title and title != "통계명":  # 헤더가 아닌 경우
                                    stats.append(StatItem(
                                        id=f"stat_{i}",
                                        title=title,
                                        publish_date=publish_date,
                                        category="통계",
                                        department=department,
                                        url=url or f"{self.base_url}/portal/cate/statView.do",
                                        stat_field="통계"
                                    ))
                                    
                        except Exception as row_error:
                            print(f"행 처리 오류 (행 {i}): {row_error}")
                            continue
                
                print(f"총 {len(stats)}개 통계 수집 완료")
                
            except Exception as table_error:
                print(f"테이블 처리 오류: {table_error}")
                
        except Exception as e:
            print(f"최근 통계 수집 오류: {e}")
            
        finally:
            if driver:
                driver.quit()
        
        # 데이터가 없으면 더미 데이터 반환
        if not stats:
            print("데이터 수집 실패, 더미 데이터 반환")
            stats = [
                StatItem(
                    id="dummy_1",
                    title="주택 관련 통계",
                    publish_date="2024-01-15",
                    category="주택",
                    department="국토교통부",
                    url="https://stat.molit.go.kr/portal/cate/statView.do",
                    stat_field="주택"
                ),
                StatItem(
                    id="dummy_2", 
                    title="교통 관련 통계",
                    publish_date="2024-01-10",
                    category="교통",
                    department="국토교통부",
                    url="https://stat.molit.go.kr/portal/cate/statView.do",
                    stat_field="교통"
                ),
                StatItem(
                    id="dummy_3",
                    title="건설 관련 통계", 
                    publish_date="2024-01-05",
                    category="건설",
                    department="국토교통부",
                    url="https://stat.molit.go.kr/portal/cate/statView.do",
                    stat_field="건설"
                )
            ]
            
        return stats

    async def get_stat_metadata(self, stat_url: str) -> StatMetadata:
        """기본 메타데이터 반환 (분석용으로는 개선된 크롤러 사용)"""
        return StatMetadata(
            id="basic",
            title="통계 제목",
            purpose="기본 메타데이터",
            frequency="정기",
            department="국토교통부",
            contact="담당자",
            keywords=[],
            related_terms={},
            url=stat_url
        )

    async def get_stat_data(self, stat_url: str, period: str = "5years") -> List[StatData]:
        """기본 데이터 반환 (분석용으로는 개선된 크롤러 사용)"""
        return [
            StatData(year=2020, data={"기본": 1000}),
            StatData(year=2021, data={"기본": 1100}),
            StatData(year=2022, data={"기본": 1200}),
            StatData(year=2023, data={"기본": 1300}),
            StatData(year=2024, data={"기본": 1400})
        ]