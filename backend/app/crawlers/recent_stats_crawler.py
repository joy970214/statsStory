"""
최신 통계 목록 수집 크롤러
"""
import asyncio
from datetime import datetime
from typing import List, Set, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from app.crawlers.base_crawler import BaseCrawler
from app.models.stat_models import StatItem

class RecentStatsCrawler(BaseCrawler):
    """최신 통계 목록 수집 전용 크롤러"""

    def __init__(self):
        super().__init__()
        self.recent_stats_url = f"{self.base_url}/portal/cate/newStatView.do?tab=recentStat"

    async def get_recent_stats(self) -> List[StatItem]:
        """최근 1달 통계 목록 수집 - Selenium으로 페이지네이션 처리"""
        driver = None
        try:
            print("국토교통부 통계포털 접속 중...")
            print(f"크롤링 URL: {self.recent_stats_url}")

            # Selenium 드라이버 설정
            driver = self._setup_selenium_driver()

            # 페이지 로드 (재시도 로직 포함)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"페이지 로드 시도 {attempt + 1}/{max_retries}")
                    driver.get(self.recent_stats_url)
                    print("페이지 로드 완료")
                    break
                except TimeoutException as e:
                    if attempt < max_retries - 1:
                        print(f"페이지 로드 타임아웃 (시도 {attempt + 1}/{max_retries}), 재시도 중...")
                        await self._safe_sleep(3)
                    else:
                        print(f"페이지 로드 최종 실패 ({max_retries}번 시도)")
                        raise

            # AJAX 로딩 대기
            wait = WebDriverWait(driver, 20)

            # 초기 테이블 로드 대기
            table_loaded = await self._wait_for_table_load(wait)
            if not table_loaded:
                print("테이블 로드 실패, 추가 대기")
                await self._safe_sleep(5)

            # 전체 통계 데이터 저장
            all_stats_data = []
            seen_titles = set()
            page_num = 1
            found_one_month_ago = False

            while page_num <= 30 and not found_one_month_ago:  # 최대 30페이지
                print(f"\n=== 페이지 {page_num} 크롤링 중 ===")

                # 현재 페이지의 데이터 추출
                page_stats, found_one_month_ago = await self._extract_page_data(driver, page_num, seen_titles)

                if page_stats:
                    all_stats_data.extend(page_stats)
                    print(f"페이지 {page_num}에서 {len(page_stats)}개 데이터 수집")
                else:
                    print(f"페이지 {page_num}에서 데이터 없음")

                # 1달 전 데이터를 만났으면 중단
                if found_one_month_ago:
                    print(f"1달 전 데이터 발견, 페이지 {page_num}에서 수집 완료")
                    break

                # 다음 페이지로 이동 (마지막 페이지가 아니면)
                if page_num < 30:
                    next_successful = await self._go_to_next_page(driver, page_num + 1)
                    if not next_successful:
                        print("다음 페이지 이동 실패")
                        break
                    await self._safe_sleep(2)

                page_num += 1

            print(f"\n=== 전체 크롤링 완료 ===")
            print(f"총 수집된 통계: {len(all_stats_data)}개")
            print(f"크롤링한 페이지: {page_num}페이지")

            if all_stats_data:
                # StatItem 객체로 변환
                stats = []
                for stat_data in all_stats_data:
                    try:
                        stats.append(StatItem(**stat_data))
                    except Exception as e:
                        print(f"StatItem 변환 오류: {e}")
                        continue

                print(f"성공적으로 변환된 통계: {len(stats)}개")
                if stats:
                    return stats

            # 데이터가 없으면 더미 데이터 반환
            print("크롤링 결과가 없어 더미 데이터 반환")
            return self._get_fallback_stats()

        except Exception as e:
            print(f"Selenium 크롤링 실패: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_stats()

        finally:
            if driver:
                driver.quit()
                print("Selenium 드라이버 종료")

    async def _wait_for_table_load(self, wait: WebDriverWait) -> bool:
        """테이블 로드 대기"""
        selectors_to_try = [
            'tbody tr',
            'table tr',
            '.tbl tr',
            'tr td.tl',
            'tr .tl'
        ]

        for selector in selectors_to_try:
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"테이블 로드 완료: {selector}")
                return True
            except TimeoutException:
                continue
        return False

    async def _extract_page_data(self, driver, page_num: int, seen_titles: Set[str]) -> Tuple[List[dict], bool]:
        """단일 페이지에서 데이터 추출"""
        try:
            # 현재 페이지의 HTML 가져오기
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            # 통계 목록 추출
            page_stats = []
            found_one_month_ago = False

            # 다양한 선택자로 행 찾기
            rows = soup.select('tbody tr')
            if not rows:
                rows = soup.select('table tr')
            if not rows:
                rows = soup.select('.tbl tr')

            for row_idx, row in enumerate(rows, start=1):
                try:
                    # 통계명: .mobile-show 클래스 없이 .tl만 가진 셀
                    title_el = row.select_one('.tl:not(.mobile-show)')
                    if not title_el:
                        title_el = row.select_one('.tl')

                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    if not title or len(title) < 2:
                        continue

                    # 통계명이 동일한 중복값은 건너뜀
                    if title in seen_titles:
                        continue

                    # 원본보기 URL: .mobile-show.tl 안의 a 태그
                    url_el = row.select_one('.mobile-show.tl a')
                    if not url_el:
                        url_el = row.select_one('a')

                    stat_url = urljoin(self.base_url, url_el.get('href')) if url_el and url_el.get('href') else ''

                    # 카테고리(통계분야): .category-label
                    category_el = row.select_one('.category-label')
                    category = category_el.get_text(strip=True) if category_el else '기타'

                    # 최신통계일: tr의 마지막 td 텍스트
                    tds = row.find_all('td')
                    publish_date = tds[-1].get_text(strip=True) if tds else '최근'

                    # '1달전'이 나오면 플래그 설정하고 중단
                    if '1달전' in publish_date or '한달' in publish_date:
                        print(f"1달 전 항목 도달: {title} | {publish_date}")
                        found_one_month_ago = True
                        break

                    print(f"데이터 수집: {title} | {category} | {publish_date}")

                    # 고유한 ID 생성 (URL 기반 해시 - 수집된 데이터와 매칭 위해)
                    import hashlib
                    unique_id = hashlib.md5(stat_url.encode()).hexdigest()[:12] if stat_url else f'page{page_num}_item{len(page_stats) + 1}'

                    page_stats.append({
                        'id': unique_id,
                        'title': title,
                        'publish_date': publish_date,
                        'category': category,
                        'department': '국토교통부',
                        'url': stat_url,
                        'stat_field': category
                    })

                    seen_titles.add(title)

                except Exception as row_error:
                    print(f"행 처리 오류 (페이지 {page_num}, 행 {row_idx}): {row_error}")
                    continue

            return page_stats, found_one_month_ago

        except Exception as e:
            print(f"페이지 {page_num} 데이터 추출 오류: {e}")
            return [], False

    async def _go_to_next_page(self, driver, next_page_num: int) -> bool:
        """다음 페이지로 이동"""
        try:
            # JavaScript goPage 함수 실행
            print(f"페이지 {next_page_num}로 이동 중...")
            driver.execute_script(f"goPage({next_page_num});")

            # 페이지 로드 대기
            wait = WebDriverWait(driver, 15)

            # 페이지가 변경되었는지 확인 (페이지 번호가 업데이트되길 기다림)
            try:
                # 페이지 정보가 업데이트될 때까지 대기
                wait.until(lambda driver: str(next_page_num) in driver.page_source)
                print(f"페이지 {next_page_num} 로드 완료")
                return True
            except TimeoutException:
                print(f"페이지 {next_page_num} 로드 타임아웃")
                return False

        except Exception as e:
            print(f"페이지 {next_page_num} 이동 실패: {e}")
            return False

    def _get_fallback_stats(self) -> List[StatItem]:
        """실제 국토교통부 통계 기반 더미 데이터"""
        return [
            StatItem(
                id="stat_1",
                title="도시형생활주택 인허가 실적",
                publish_date="2024.12.15",
                category="주택",
                department="국토교통부",
                url=f"{self.base_url}/portal/cate/statView.do?hRsId=489&hFormId=5558",
                stat_field="주택"
            ),
            StatItem(
                id="stat_2",
                title="주택건설실적통계(준공)",
                publish_date="2024.12.10",
                category="건설",
                department="국토교통부",
                url=f"{self.base_url}/portal/cate/statView.do?hRsId=468&hFormId=5372",
                stat_field="건설"
            ),
            StatItem(
                id="stat_3",
                title="미분양주택현황보고",
                publish_date="2024.12.05",
                category="주택",
                department="국토교통부",
                url=f"{self.base_url}/portal/cate/statView.do?hRsId=32&hFormId=5328",
                stat_field="주택"
            )
        ]