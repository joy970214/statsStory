"""
기본 크롤러 클래스 - Selenium 드라이버 설정 공통 로직
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import asyncio

class BaseCrawler:
    """Selenium 기반 크롤러의 기본 클래스"""

    def __init__(self):
        self.base_url = "https://stat.molit.go.kr"

    def _setup_selenium_driver(self):
        """Selenium 드라이버 설정"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 백그라운드 실행
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # ChromeDriver 자동 설치 및 서비스 설정
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)  # 타임아웃 30초 → 60초로 증가

        return driver

    async def _safe_sleep(self, seconds: float):
        """비동기 sleep"""
        await asyncio.sleep(seconds)