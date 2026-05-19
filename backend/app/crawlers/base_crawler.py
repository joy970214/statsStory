"""
기본 크롤러 클래스 - Selenium 드라이버 설정 공통 로직
"""
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import asyncio


def _resolve_chrome_binary() -> str | None:
    """CHROME_BINARY 환경변수 → 사용자 영역 추출 경로 → None(기본 탐색) 순으로 해석"""
    env_path = os.environ.get("CHROME_BINARY")
    if env_path and Path(env_path).exists():
        return env_path
    local_path = Path.home() / "chrome" / "opt" / "google" / "chrome" / "google-chrome"
    if local_path.exists():
        return str(local_path)
    return None


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

        chrome_binary = _resolve_chrome_binary()
        if chrome_binary:
            chrome_options.binary_location = chrome_binary

        # Selenium Manager(셀레늄 4.6+ 내장)가 설치된 Chrome 버전에 맞는 ChromeDriver를 자동 해석
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)  # 타임아웃 30초 → 60초로 증가

        return driver

    async def _safe_sleep(self, seconds: float):
        """비동기 sleep"""
        await asyncio.sleep(seconds)