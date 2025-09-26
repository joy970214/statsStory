"""
통계 메타데이터 수집 크롤러
"""
import asyncio
from typing import Dict, List
from bs4 import BeautifulSoup

from app.crawlers.base_crawler import BaseCrawler
from app.models.stat_models import StatMetadata

class MetadataCrawler(BaseCrawler):
    """통계 메타데이터 수집 전용 크롤러"""

    def __init__(self):
        super().__init__()

    async def get_stat_metadata(self, stat_url: str) -> StatMetadata:
        """통계 메타데이터 수집 - Selenium으로 실제 상세 데이터 크롤링"""
        driver = None
        try:
            print(f"메타데이터 수집 시작: {stat_url}")

            # Selenium 드라이버 설정
            driver = self._setup_selenium_driver()

            # 통계 상세 페이지 로드
            driver.get(stat_url)
            await self._safe_sleep(3)

            # HTML 가져오기
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            # 기본값 설정
            metadata = {
                'title': "통계명",
                'purpose': "통계 작성 목적",
                'frequency': "정기",
                'contact': "담당자 연락처",
                'department': "국토교통부",
                'keywords': [],
                'related_terms': {},
                'search_field': ""
            }

            # 1. 통계정보 탭에서 메타데이터 추출
            print("통계정보 탭 데이터 추출 중...")
            metadata = await self._extract_basic_info(soup, metadata)

            # 2. 관련용어 탭 데이터 추출 시도
            print("관련용어 탭 데이터 추출 시도...")
            metadata = await self._extract_related_terms(driver, soup, metadata)

            # 3. 제목에서 키워드 자동 추출 (백업)
            if not metadata['keywords'] and metadata['title']:
                metadata['keywords'] = self._extract_keywords_from_title(metadata['title'])

            # 검색분야도 키워드에 추가
            if metadata['search_field'] and metadata['search_field'] not in metadata['keywords']:
                metadata['keywords'].append(metadata['search_field'])

            print(f"최종 수집된 메타데이터:")
            print(f"  제목: {metadata['title']}")
            print(f"  목적: {metadata['purpose']}")
            print(f"  주기: {metadata['frequency']}")
            print(f"  부서: {metadata['department']}")
            print(f"  키워드: {metadata['keywords']}")
            print(f"  관련용어: {len(metadata['related_terms'])}개")

            return StatMetadata(
                id=stat_url.split('=')[-1] if '=' in stat_url else 'unknown',
                title=metadata['title'],
                purpose=metadata['purpose'],
                frequency=metadata['frequency'],
                department=metadata['department'],
                contact=metadata['contact'],
                keywords=metadata['keywords'][:10],  # 최대 10개로 제한
                related_terms=metadata['related_terms']
            )

        except Exception as e:
            print(f"메타데이터 수집 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류 시 기본값 반환
            return StatMetadata(
                id="unknown",
                title="통계명",
                purpose="통계 작성 목적",
                frequency="정기",
                department="국토교통부",
                contact="담당자 연락처",
                keywords=["통계"],
                related_terms={}
            )

        finally:
            if driver:
                driver.quit()
                print("메타데이터 수집용 드라이버 종료")

    async def _extract_basic_info(self, soup: BeautifulSoup, metadata: Dict) -> Dict:
        """기본 통계정보 추출"""
        # 통계명 추출 (페이지 제목이나 h1, h2, h3 태그에서)
        title_selectors = ['h1', 'h2', 'h3', '.title', '.stat-title']
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element and title_element.get_text(strip=True):
                metadata['title'] = title_element.get_text(strip=True)
                print(f"통계명 발견: {metadata['title']}")
                break

        # 검색분야, 담당부서, 통계개요에서 th-td 쌍 추출
        info_tables = soup.find_all('table')
        for table in info_tables:
            rows = table.find_all('tr')
            for row in rows:
                ths = row.find_all('th')
                tds = row.find_all('td')

                if len(ths) == 1 and len(tds) == 1:
                    key = ths[0].get_text(strip=True)
                    value = tds[0].get_text(strip=True)

                    if '검색분야' in key or '통계분야' in key:
                        metadata['search_field'] = value
                        print(f"검색분야: {value}")
                    elif '담당부서' in key or '작성기관' in key:
                        metadata['department'] = value
                        print(f"담당부서: {value}")
                    elif '통계개요' in key or '작성목적' in key:
                        metadata['purpose'] = value
                        print(f"통계개요/목적: {value}")
                    elif '작성주기' in key or '공표주기' in key:
                        metadata['frequency'] = value
                        print(f"작성주기: {value}")
                    elif '담당자' in key or '연락처' in key:
                        metadata['contact'] = value
                        print(f"담당자 연락처: {value}")

        return metadata

    async def _extract_related_terms(self, driver, soup: BeautifulSoup, metadata: Dict) -> Dict:
        """관련용어 정보 추출"""
        try:
            # 관련용어 탭 또는 버튼 찾기
            related_tab_selectors = [
                'a[href*="related"]',
                'button[onclick*="related"]',
                '.tab-related',
                '[data-tab="related"]'
            ]

            for selector in related_tab_selectors:
                tab_element = driver.find_elements("css selector", selector)
                if tab_element:
                    print("관련용어 탭 발견, 클릭 시도")
                    tab_element[0].click()
                    await self._safe_sleep(2)
                    break

            # 관련용어 탭이 로드된 후 HTML 다시 가져오기
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            # 주요항목, 의미분석, 관련용어 추출
            term_tables = soup.find_all('table')
            for table in term_tables:
                rows = table.find_all('tr')
                for row in rows:
                    ths = row.find_all('th')
                    tds = row.find_all('td')

                    if len(ths) == 1 and len(tds) == 1:
                        key = ths[0].get_text(strip=True)
                        value = tds[0].get_text(strip=True)

                        if '주요항목' in key:
                            metadata['related_terms']['주요항목'] = value
                            # 주요항목에서 키워드 추출
                            metadata['keywords'].extend([kw.strip() for kw in value.split(',') if kw.strip()])
                            print(f"주요항목: {value}")
                        elif '의미분석' in key or '정의' in key:
                            metadata['related_terms']['의미분석'] = value
                            print(f"의미분석: {value}")
                        elif '관련용어' in key:
                            metadata['related_terms']['관련용어'] = value
                            print(f"관련용어: {value}")

        except Exception as tab_error:
            print(f"관련용어 탭 처리 중 오류: {tab_error}")

        return metadata

    def _extract_keywords_from_title(self, title: str) -> List[str]:
        """제목에서 키워드 자동 추출"""
        keyword_patterns = ['주택', '건설', '교통', '도로', '철도', '항공', '토지', '자동차', '건축', '부동산']
        return [kw for kw in keyword_patterns if kw in title]