import aiohttp
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from app.models.stat_models import StatMetadata, StatData, ComprehensiveStatAnalysis


class ImprovedMolitCrawler:
    """개선된 국토교통부 통계포털 크롤러 - 정확한 탭별 데이터 수집"""
    
    def __init__(self):
        self.base_url = "https://stat.molit.go.kr"
        
    def _setup_selenium_driver(self):
        """Selenium 드라이버 설정"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        
        return driver

    async def get_stat_metadata(self, stat_url: str) -> StatMetadata:
        """통계정보와 관련용어 탭에서 메타데이터 수집 - 개선된 버전"""
        driver = None
        try:
            print(f"메타데이터 수집 시작: {stat_url}")
            driver = self._setup_selenium_driver()
            driver.get(stat_url)
            await asyncio.sleep(3)
            
            # 페이지 제목에서 통계명 추출 시도
            page_title = driver.title
            extracted_title = page_title if page_title else "통계명"
            
            # 기본값 설정
            metadata_info = {
                'title': extracted_title,
                'purpose': '통계 작성 목적',
                'frequency': '정기',
                'department': '국토교통부',
                'contact': '담당자 연락처',
                'keywords': [],
                'related_terms': {},
                'url': stat_url
            }
            
            # 1. 통계정보 탭에서 메타데이터 수집
            try:
                print("통계정보 탭 데이터 수집 중...")
                stat_info_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계정보')]"))
                )
                stat_info_tab.click()
                await asyncio.sleep(2)
                
                # 통계정보 테이블에서 정보 추출
                info_tables = driver.find_elements(By.TAG_NAME, "table")
                for table in info_tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        try:
                            th = row.find_element(By.TAG_NAME, "th")
                            td = row.find_element(By.TAG_NAME, "td")
                            key = th.text.strip()
                            value = td.text.strip()
                            
                            if '통계명' in key:
                                metadata_info['title'] = value
                            elif '작성목적' in key:
                                metadata_info['purpose'] = value
                            elif '작성주기' in key:
                                metadata_info['frequency'] = value
                            elif '작성기관' in key or '담당부서' in key:
                                metadata_info['department'] = value
                            elif '연락처' in key or '전화' in key:
                                metadata_info['contact'] = value
                                
                        except NoSuchElementException:
                            continue
                            
            except Exception as e:
                print(f"통계정보 탭 수집 실패: {e}")
            
            # 2. 관련용어 탭에서 용어 수집
            try:
                print("관련용어 탭 데이터 수집 중...")
                related_terms_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '관련용어')]"))
                )
                related_terms_tab.click()
                await asyncio.sleep(2)
                
                # 관련용어 테이블에서 용어와 정의 추출
                terms_tables = driver.find_elements(By.TAG_NAME, "table")
                for table in terms_tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 2:
                                term = cells[0].text.strip()
                                definition = cells[1].text.strip()
                                if term and definition and len(term) < 30:
                                    metadata_info['related_terms'][term] = definition
                                    metadata_info['keywords'].append(term)
                                    
                        except Exception:
                            continue
                            
            except Exception as e:
                print(f"관련용어 탭 수집 실패: {e}")
            
            print(f"메타데이터 수집 완료: {metadata_info['title']}")
            print(f"키워드 {len(metadata_info['keywords'])}개, 관련용어 {len(metadata_info['related_terms'])}개")
            
            return StatMetadata(
                id=stat_url.split('=')[-1] if '=' in stat_url else 'unknown',
                title=metadata_info['title'],
                purpose=metadata_info['purpose'],
                frequency=metadata_info['frequency'],
                department=metadata_info['department'],
                contact=metadata_info['contact'],
                keywords=metadata_info['keywords'][:10],
                related_terms=metadata_info['related_terms'],
                url=stat_url
            )
            
        except Exception as e:
            print(f"메타데이터 수집 전체 오류: {e}")
            return StatMetadata(
                id="error",
                title="메타데이터 수집 실패",
                purpose="수집 중 오류 발생",
                frequency="알 수 없음",
                department="국토교통부",
                contact="수집 실패",
                keywords=[],
                related_terms={},
                url=stat_url
            )
        finally:
            if driver:
                driver.quit()

    async def get_available_stat_tables(self, stat_url: str) -> List[Dict[str, str]]:
        """통계표보기 탭에서 #sFormId 셀렉트의 옵션들 수집 (종료 제외)"""
        driver = None
        try:
            print(f"통계표 목록 수집 시작: {stat_url}")
            driver = self._setup_selenium_driver()
            driver.get(stat_url)
            await asyncio.sleep(3)
            
            # 통계표보기 탭으로 이동 (기본적으로 선택되어 있을 수 있음)
            try:
                table_view_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계표') and contains(text(), '보기')]"))
                )
                table_view_tab.click()
                await asyncio.sleep(2)
            except:
                print("통계표보기 탭이 이미 선택되어 있거나 찾을 수 없음")
            
            # #sFormId 셀렉트 요소 찾기
            stat_tables = []
            try:
                select_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "sFormId"))
                )
                
                select = Select(select_element)
                options = select.options
                
                for option in options:
                    option_text = option.text.strip()
                    option_value = option.get_attribute('value')
                    
                    # (종료)가 포함된 옵션은 제외
                    if option_text and '(종료)' not in option_text and option_value:
                        stat_tables.append({
                            'name': option_text,
                            'value': option_value,
                            'form_id': option_value
                        })
                        print(f"통계표 발견: {option_text} (ID: {option_value})")
                
            except Exception as e:
                print(f"#sFormId 셀렉트 요소 접근 실패: {e}")
            
            print(f"수집 가능한 통계표: {len(stat_tables)}개")
            return stat_tables
            
        except Exception as e:
            print(f"통계표 목록 수집 오류: {e}")
            return []
        finally:
            if driver:
                driver.quit()

    async def get_stat_data(self, stat_url: str, period: str = "5years") -> List[StatData]:
        """통계표보기 탭에서 실제 통계 데이터 수집"""
        driver = None
        try:
            print(f"통계 데이터 수집 시작: {stat_url}")
            driver = self._setup_selenium_driver()
            driver.get(stat_url)
            await asyncio.sleep(3)
            
            # 통계표보기 탭으로 이동
            try:
                table_view_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계표') and contains(text(), '보기')]"))
                )
                table_view_tab.click()
                await asyncio.sleep(2)
            except:
                print("통계표보기 탭 접근 실패 또는 이미 선택됨")
            
            all_stat_data = []
            
            # 1. 사용 가능한 통계표 목록 가져오기
            stat_tables = await self._get_stat_tables_from_current_page(driver)
            
            # 2. 각 통계표별로 데이터 수집
            for table_info in stat_tables:
                try:
                    print(f"통계표 '{table_info['name']}' 데이터 수집 중...")
                    
                    # 통계표 선택
                    select_element = driver.find_element(By.ID, "sFormId")
                    select = Select(select_element)
                    select.select_by_value(table_info['value'])
                    await asyncio.sleep(2)
                    
                    # 기간 형태 확인 및 데이터 수집
                    table_data = await self._collect_table_data(driver, table_info, period)
                    
                    # 통계표명과 함께 데이터 저장
                    for data_item in table_data:
                        data_item.table_name = table_info['name']  # 통계표명 추가
                        all_stat_data.append(data_item)
                    
                except Exception as table_error:
                    print(f"통계표 '{table_info['name']}' 수집 실패: {table_error}")
                    continue
            
            print(f"총 {len(all_stat_data)}개 데이터 수집 완료")
            return all_stat_data
            
        except Exception as e:
            print(f"통계 데이터 수집 전체 오류: {e}")
            # 더미 데이터 반환
            return [
                StatData(year=2020, data={"샘플": 1000}, table_name="샘플 통계표"),
                StatData(year=2021, data={"샘플": 1100}, table_name="샘플 통계표"),
                StatData(year=2022, data={"샘플": 1200}, table_name="샘플 통계표"),
                StatData(year=2023, data={"샘플": 1300}, table_name="샘플 통계표"),
                StatData(year=2024, data={"샘플": 1400}, table_name="샘플 통계표")
            ]
        finally:
            if driver:
                driver.quit()

    async def _get_stat_tables_from_current_page(self, driver) -> List[Dict[str, str]]:
        """현재 페이지에서 #sFormId 셀렉트의 통계표 목록 수집"""
        stat_tables = []
        try:
            select_element = driver.find_element(By.ID, "sFormId")
            select = Select(select_element)
            options = select.options
            
            for option in options:
                option_text = option.text.strip()
                option_value = option.get_attribute('value')
                
                # (종료)가 포함된 옵션은 제외
                if option_text and '(종료)' not in option_text and option_value:
                    stat_tables.append({
                        'name': option_text,
                        'value': option_value
                    })
                    
        except Exception as e:
            print(f"통계표 목록 수집 실패: {e}")
            
        return stat_tables

    async def _collect_table_data(self, driver, table_info: Dict[str, str], period: str) -> List[StatData]:
        """선택된 통계표에서 기간별 데이터 수집"""
        try:
            # 기간 선택 요소 찾기
            period_data = []
            
            # 년도 선택 드롭다운 찾기
            try:
                year_selects = driver.find_elements(By.CSS_SELECTOR, "select[name*='year'], select[id*='year'], select[id*='Year']")
                
                if not year_selects:
                    # 다른 기간 선택 방식 찾기
                    period_selects = driver.find_elements(By.CSS_SELECTOR, "select")
                    for select_elem in period_selects:
                        try:
                            select_options = Select(select_elem).options
                            # 연도나 날짜 형태의 옵션이 있는지 확인
                            if any('20' in opt.text for opt in select_options):
                                year_selects.append(select_elem)
                                break
                        except:
                            continue
                
                if year_selects:
                    # 첫 번째 연도 선택 드롭다운 사용
                    year_select = Select(year_selects[0])
                    available_periods = []
                    
                    for option in year_select.options:
                        option_text = option.text.strip()
                        if option_text and '20' in option_text:
                            available_periods.append({
                                'text': option_text,
                                'value': option.get_attribute('value')
                            })
                    
                    # 기간 형태 판단 (년간 vs 월간) - 개선된 로직
                    period_type, target_periods = await self._determine_period_type_and_select(available_periods)
                    print(f"{period_type} 데이터 감지, {len(target_periods)}개 기간 수집예정")
                    
                    # 각 기간별로 데이터 수집
                    for period_info in target_periods:
                        try:
                            # 기간 선택
                            year_select.select_by_value(period_info['value'])
                            await asyncio.sleep(1)
                            
                            # 조회 버튼 찾기 및 클릭 (개선된 다양한 패턴 지원)
                            search_btn = await self._find_search_button(driver)
                            print(f"조회 버튼 검색 결과: {'발견' if search_btn else '미발견'}")
                            
                            if search_btn:
                                search_btn.click()
                                await asyncio.sleep(3)  # 데이터 로딩 대기 시간 증가
                                print(f"조회 버튼 클릭 완료: {period_info['text']}")
                            else:
                                print(f"조회 버튼을 찾을 수 없음: {period_info['text']}")
                            
                            # 테이블 데이터 추출
                            table_data = await self._extract_table_data(driver, period_info['text'])
                            if table_data:
                                period_data.append(table_data)
                                
                        except Exception as period_error:
                            print(f"기간 {period_info['text']} 데이터 수집 실패: {period_error}")
                            continue
                
                else:
                    print("기간 선택 요소를 찾을 수 없음")
                    
            except Exception as e:
                print(f"기간 선택 처리 실패: {e}")
            
            return period_data
            
        except Exception as e:
            print(f"테이블 데이터 수집 실패: {e}")
            return []

    async def _find_search_button(self, driver):
        """조회 버튼을 찾는 개선된 메서드"""
        # 1. 일반적인 조회 버튼 패턴들
        button_patterns = [
            # 한국어 조회 버튼
            "//input[@type='button' and contains(@value, '조회')]",
            "//input[@type='submit' and contains(@value, '조회')]",
            "//button[contains(text(), '조회')]",
            "//a[contains(text(), '조회')]",
            
            # ID/클래스 기반
            "//input[@id='btnSearch']",
            "//button[@id='btnSearch']",
            "//input[@id='searchBtn']", 
            "//button[@id='searchBtn']",
            "//*[@class='btn-search']",
            "//*[contains(@class, 'search')]",
            
            # onclick 속성 기반
            "//*[@onclick and contains(@onclick, 'search')]",
            "//*[@onclick and contains(@onclick, 'Search')]",
            "//*[@onclick and contains(@onclick, '조회')]",
            
            # value 속성이 조회인 모든 input
            "//input[contains(@value, '조회')]",
            
            # 영어 버튼들도 지원
            "//input[@type='button' and contains(@value, 'Search')]",
            "//button[contains(text(), 'Search')]"
        ]
        
        for pattern in button_patterns:
            try:
                elements = driver.find_elements(By.XPATH, pattern)
                for element in elements:
                    # 요소가 보이고 클릭 가능한지 확인
                    if element.is_displayed() and element.is_enabled():
                        print(f"조회 버튼 발견: {pattern}")
                        return element
            except Exception as e:
                continue
        
        # 2. 폼 내의 첫 번째 submit 버튼 찾기 (fallback)
        try:
            forms = driver.find_elements(By.TAG_NAME, "form")
            for form in forms:
                submit_buttons = form.find_elements(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
                for btn in submit_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        print("폼 내 submit 버튼 사용")
                        return btn
        except Exception as e:
            pass
        
        # 3. 마지막 시도: 모든 버튼 중에서 찾기
        try:
            all_buttons = driver.find_elements(By.TAG_NAME, "button") + driver.find_elements(By.CSS_SELECTOR, "input[type='button'], input[type='submit']")
            for btn in all_buttons:
                btn_text = btn.get_attribute('value') or btn.text or ""
                if any(keyword in btn_text for keyword in ['조회', 'search', 'Search', '검색']):
                    if btn.is_displayed() and btn.is_enabled():
                        print(f"일반 검색으로 버튼 발견: {btn_text}")
                        return btn
        except Exception as e:
            pass
        
        print("조회 버튼을 찾을 수 없음")
        return None

    async def _determine_period_type_and_select(self, available_periods: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
        """기간 유형을 판단하고 적절한 수집 기간을 선택"""
        if not available_periods:
            return "알 수 없음", []
        
        # 패턴 분석
        monthly_count = 0
        yearly_count = 0
        quarterly_count = 0
        
        for period in available_periods:
            text = period['text'].strip()
            # 월간: 202304, 2023년04월, 2023-04 등
            if (len(text) == 6 and text.isdigit()) or \
               ('월' in text and len(text) <= 10) or \
               ('-' in text and len(text.split('-')) == 2 and len(text.split('-')[1]) <= 2):
                monthly_count += 1
            # 년간: 2023, 2023년 등  
            elif (len(text) == 4 and text.isdigit()) or \
                 (text.replace('년', '').isdigit() and len(text.replace('년', '')) == 4):
                yearly_count += 1
            # 분기: 2023Q1, 2023년1분기 등
            elif 'Q' in text or '분기' in text:
                quarterly_count += 1
        
        # 유형 결정 및 수집 기간 선택
        total_periods = len(available_periods)
        
        if monthly_count > total_periods * 0.5:  # 50% 이상이 월간
            period_type = "월간"
            # 최근 12개월 또는 사용 가능한 모든 기간
            target_periods = available_periods[-12:] if total_periods >= 12 else available_periods
            
        elif yearly_count > total_periods * 0.5:  # 50% 이상이 년간
            period_type = "년간" 
            # 최근 5년 또는 사용 가능한 모든 기간 (2023, 2024, 2025 우선)
            current_year = 2025
            preferred_years = [str(year) for year in range(current_year-4, current_year+1)]  # 2021-2025
            
            # 우선순위: 최근 5년 데이터
            priority_periods = []
            other_periods = []
            
            for period in available_periods:
                text = period['text'].strip()
                year_text = text.replace('년', '')
                if any(pref_year in year_text for pref_year in preferred_years):
                    priority_periods.append(period)
                else:
                    other_periods.append(period)
            
            # 최근 5년 데이터 우선, 부족하면 다른 데이터로 보완
            target_periods = priority_periods[-5:] if priority_periods else available_periods[-5:]
            
        elif quarterly_count > total_periods * 0.3:  # 30% 이상이 분기
            period_type = "분기"
            # 최근 8분기 (2년치)
            target_periods = available_periods[-8:] if total_periods >= 8 else available_periods
            
        else:
            period_type = "혼합"
            # 최근 데이터 위주로 선택
            target_periods = available_periods[-10:] if total_periods >= 10 else available_periods
        
        return period_type, target_periods

    async def _extract_table_data(self, driver, period_text: str) -> StatData:
        """현재 표시된 테이블에서 데이터 추출 - 개선된 다중 표 형태 처리"""
        try:
            # 데이터 로딩 완료까지 대기 (추가)
            await asyncio.sleep(2)
            
            # 데이터 테이블 찾기 - 우선순위 및 필터링 강화
            potential_tables = await self._find_data_tables(driver)
            
            extracted_data = {}
            table_count = 0
            
            for table in potential_tables:
                try:
                    # 테이블 유효성 검사
                    if not await self._is_valid_data_table(table):
                        continue
                        
                    table_data = await self._parse_table_structure_enhanced(table)
                    if table_data:
                        extracted_data.update(table_data)
                        table_count += 1
                        print(f"테이블 {table_count}에서 {len(table_data)}개 데이터 추출")
                    
                except Exception as table_error:
                    print(f"테이블 파싱 오류: {table_error}")
                    continue
            
            # 연도 추출 로직 개선
            year = await self._extract_year_from_period(period_text)
            
            print(f"총 {len(extracted_data)}개 데이터 항목 추출 완료 (연도: {year})")
            
            return StatData(
                year=year,
                data=extracted_data,
                table_name="",  # 나중에 설정됨
                period_text=period_text,
                raw_data_count=len(extracted_data)  # 디버깅용
            )
            
        except Exception as e:
            print(f"테이블 데이터 추출 실패: {e}")
            return StatData(year=2024, data={}, table_name="", period_text=period_text)

    async def _find_data_tables(self, driver):
        """데이터 테이블 찾기 - 우선순위별 검색"""
        potential_tables = []
        
        # 1. 특정 클래스/ID의 테이블 (우선순위 높음)
        high_priority_selectors = [
            "table.table",
            "table.data-table", 
            "table.result-table",
            "table[id*='data']",
            "table[id*='result']",
            "table[class*='data']",
            ".content table",  # 콘텐츠 영역의 테이블
            "#content table"
        ]
        
        for selector in high_priority_selectors:
            try:
                tables = driver.find_elements(By.CSS_SELECTOR, selector)
                potential_tables.extend(tables)
            except:
                continue
        
        # 2. 중간 우선순위: border나 특정 속성을 가진 테이블
        medium_priority_selectors = [
            "table[border]",
            "table[cellpadding]", 
            "table[width]"
        ]
        
        for selector in medium_priority_selectors:
            try:
                tables = driver.find_elements(By.CSS_SELECTOR, selector)
                for table in tables:
                    if table not in potential_tables:
                        potential_tables.append(table)
            except:
                continue
        
        # 3. 낮은 우선순위: 모든 테이블에서 유효한 것만
        if not potential_tables:
            all_tables = driver.find_elements(By.TAG_NAME, "table")
            for table in all_tables:
                rows = table.find_elements(By.TAG_NAME, "tr") 
                if len(rows) >= 2:  # 최소 헤더 + 1개 행
                    potential_tables.append(table)
        
        # 중복 제거
        unique_tables = []
        for table in potential_tables:
            if table not in unique_tables:
                unique_tables.append(table)
                
        print(f"발견된 테이블 수: {len(unique_tables)}")
        return unique_tables

    async def _is_valid_data_table(self, table) -> bool:
        """테이블이 유효한 데이터 테이블인지 검사"""
        try:
            rows = table.find_elements(By.TAG_NAME, "tr")
            if len(rows) < 2:  # 최소 헤더 + 데이터 행
                return False
                
            # 테이블이 너무 작으면 제외 (네비게이션 테이블 등)
            if len(rows) == 1:
                return False
            
            # 각 행의 셀 수 확인
            cell_counts = []
            for row in rows[:3]:  # 처음 3행만 검사
                cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
                cell_counts.append(len(cells))
            
            # 셀이 없거나 너무 적으면 제외
            if max(cell_counts) < 2:
                return False
            
            # 테이블 크기 확인 (너무 작은 레이아웃 테이블 제외)
            try:
                table_size = table.size
                if table_size['width'] < 100 or table_size['height'] < 50:
                    return False
            except:
                pass  # 크기 확인 실패 시 넘어감
                
            return True
            
        except Exception as e:
            return False

    async def _parse_table_structure_enhanced(self, table) -> Dict[str, Any]:
        """개선된 테이블 구조 파싱"""
        try:
            rows = table.find_elements(By.TAG_NAME, "tr")
            if not rows:
                return {}
            
            parsed_data = {}
            
            # 테이블 유형 분석
            table_type = await self._analyze_table_type(table, rows)
            print(f"테이블 유형: {table_type}")
            
            if table_type == "key_value":
                parsed_data = await self._parse_key_value_table(rows)
            elif table_type == "multi_column":
                parsed_data = await self._parse_multi_column_table(rows)
            elif table_type == "matrix":
                parsed_data = await self._parse_matrix_table(rows) 
            else:
                # 기본 파싱
                parsed_data = await self._parse_generic_table(rows)
            
            return parsed_data
            
        except Exception as e:
            print(f"개선된 테이블 파싱 실패: {e}")
            return {}

    async def _extract_year_from_period(self, period_text: str) -> int:
        """기간 텍스트에서 연도 추출 - 개선된 로직"""
        import re
        current_year = 2025  # 기본값
        
        try:
            # 패턴 1: 4자리 연도 (2023, 2024 등)
            if len(period_text) == 4 and period_text.isdigit():
                return int(period_text)
            
            # 패턴 2: 6자리 월간 (202304 -> 2023)
            if len(period_text) == 6 and period_text.isdigit():
                return int(period_text[:4])
            
            # 패턴 3: "2023년" 형태
            year_pattern = re.search(r'(\d{4})년?', period_text)
            if year_pattern:
                return int(year_pattern.group(1))
            
            # 패턴 4: "2023-04" 형태
            date_pattern = re.search(r'(\d{4})-\d{2}', period_text)
            if date_pattern:
                return int(date_pattern.group(1))
            
            # 패턴 5: "2023Q1" 형태
            quarter_pattern = re.search(r'(\d{4})Q\d', period_text)
            if quarter_pattern:
                return int(quarter_pattern.group(1))
            
            # 패턴 6: 일반적인 20xx 패턴
            general_pattern = re.search(r'20(\d{2})', period_text)
            if general_pattern:
                return int("20" + general_pattern.group(1))
                
        except ValueError:
            pass
            
        return current_year

    async def _analyze_table_type(self, table, rows) -> str:
        """테이블 유형 분석"""
        if len(rows) < 2:
            return "unknown"
        
        # 첫 번째 행 분석
        first_row_cells = rows[0].find_elements(By.TAG_NAME, "th") + rows[0].find_elements(By.TAG_NAME, "td")
        second_row_cells = rows[1].find_elements(By.TAG_NAME, "th") + rows[1].find_elements(By.TAG_NAME, "td")
        
        first_row_count = len(first_row_cells)
        second_row_count = len(second_row_cells)
        
        # 2열 테이블 (key-value 형태)
        if first_row_count == 2 and second_row_count == 2:
            return "key_value"
        
        # 다중 열이지만 일정한 패턴
        elif first_row_count > 2 and first_row_count == second_row_count:
            # 첫 번째 열이 텍스트, 나머지가 숫자면 multi_column
            try:
                first_cell_text = first_row_cells[0].text.strip()
                if first_cell_text and not first_cell_text.replace(',', '').isdigit():
                    return "multi_column"
            except:
                pass
            return "matrix"
        
        return "generic"

    async def _parse_key_value_table(self, rows) -> Dict[str, Any]:
        """키-값 형태 테이블 파싱"""
        data = {}
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
            if len(cells) == 2:
                key = cells[0].text.strip()
                value_text = cells[1].text.strip()
                if key and value_text and key != value_text:
                    value = await self._convert_cell_value_enhanced(value_text)
                    data[key] = value
        return data

    async def _parse_multi_column_table(self, rows) -> Dict[str, Any]:
        """다중 열 테이블 파싱"""
        data = {}
        header_row = None
        
        # 헤더 찾기
        for i, row in enumerate(rows):
            th_cells = row.find_elements(By.TAG_NAME, "th")
            if th_cells:
                header_row = i
                break
        
        if header_row is not None:
            headers = [cell.text.strip() for cell in rows[header_row].find_elements(By.TAG_NAME, "th")]
            
            # 데이터 행 처리
            for row_idx in range(header_row + 1, len(rows)):
                cells = rows[row_idx].find_elements(By.TAG_NAME, "td")
                if cells and len(cells) > 0:
                    row_key = cells[0].text.strip() if cells[0].text.strip() else f"행_{row_idx}"
                    
                    for col_idx in range(1, min(len(cells), len(headers))):
                        if col_idx < len(headers):
                            cell_value = cells[col_idx].text.strip()
                            if cell_value:
                                key = f"{row_key}_{headers[col_idx]}"
                                value = await self._convert_cell_value_enhanced(cell_value)
                                data[key] = value
        
        return data

    async def _parse_matrix_table(self, rows) -> Dict[str, Any]:
        """매트릭스 형태 테이블 파싱"""
        data = {}
        # 매트릭스 형태는 기본 파싱과 동일하게 처리
        return await self._parse_generic_table(rows)

    async def _parse_generic_table(self, rows) -> Dict[str, Any]:
        """일반 테이블 파싱"""
        data = {}
        for i, row in enumerate(rows):
            cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
            for j, cell in enumerate(cells):
                cell_text = cell.text.strip()
                if cell_text:
                    key = f"셀_{i}_{j}_{cell_text[:10]}"  # 셀 위치와 내용으로 키 생성
                    value = await self._convert_cell_value_enhanced(cell_text)
                    data[key] = value
        return data

    async def _convert_cell_value_enhanced(self, value_text: str) -> Any:
        """개선된 셀 값 변환"""
        if not value_text:
            return ""
        
        # 공백 및 특수문자 정리
        cleaned = value_text.replace(',', '').replace('원', '').replace('건', '').replace('개', '').strip()
        
        # 퍼센트 처리
        if '%' in value_text:
            try:
                num_part = cleaned.replace('%', '')
                return {"value": float(num_part), "unit": "%", "raw": value_text}
            except ValueError:
                return {"value": value_text, "unit": "text", "raw": value_text}
        
        # 숫자 변환 시도
        try:
            if '.' in cleaned:
                num_val = float(cleaned)
                return {"value": num_val, "unit": "number", "raw": value_text}
            elif cleaned.replace('-', '').replace('+', '').isdigit():
                num_val = int(cleaned)
                return {"value": num_val, "unit": "number", "raw": value_text}
        except ValueError:
            pass
        
        # 문자열 그대로 반환
        return {"value": value_text, "unit": "text", "raw": value_text}

    async def get_comprehensive_stat_analysis(self, stat_url: str) -> ComprehensiveStatAnalysis:
        """종합 통계 분석 - 메타데이터와 모든 통계표 데이터 수집"""
        from datetime import datetime
        
        print(f"종합 통계 분석 시작: {stat_url}")
        
        try:
            # 1. 메타데이터 수집
            print("1단계: 메타데이터 수집")
            metadata = await self.get_stat_metadata(stat_url)
            
            # 2. 사용 가능한 통계표 목록 수집
            print("2단계: 통계표 목록 수집")
            available_tables = await self.get_available_stat_tables(stat_url)
            
            # 3. 각 통계표별 데이터 수집
            print("3단계: 통계표별 데이터 수집")
            data_by_table = {}
            total_data_points = 0
            collection_summary = {
                "total_tables": len(available_tables),
                "successful_tables": 0,
                "failed_tables": 0,
                "period_types": {},
                "data_quality_scores": []
            }
            
            for table_info in available_tables:
                table_name = table_info['name']
                print(f"통계표 '{table_name}' 데이터 수집 중...")
                
                try:
                    # 개별 통계표 데이터 수집
                    table_data = await self._collect_single_table_data(stat_url, table_info)
                    
                    if table_data:
                        # 추가 정보 설정
                        for data_item in table_data:
                            data_item.table_name = table_name
                            # 데이터 품질 점수 계산
                            data_item.data_quality_score = await self._calculate_data_quality_score(data_item)
                            collection_summary["data_quality_scores"].append(data_item.data_quality_score)
                        
                        data_by_table[table_name] = table_data
                        total_data_points += sum(len(item.data) for item in table_data)
                        collection_summary["successful_tables"] += 1
                        
                        # 기간 유형 집계
                        for item in table_data:
                            period_type = item.period_type or "알 수 없음"
                            collection_summary["period_types"][period_type] = collection_summary["period_types"].get(period_type, 0) + 1
                        
                        print(f"  ✓ 성공: {len(table_data)}개 기간 데이터 수집")
                    else:
                        collection_summary["failed_tables"] += 1
                        print(f"  ✗ 실패: 데이터 없음")
                        
                except Exception as table_error:
                    collection_summary["failed_tables"] += 1
                    print(f"  ✗ 실패: {table_error}")
                    continue
            
            # 4. 분석 인사이트 생성
            print("4단계: 분석 인사이트 생성")
            insights = await self._generate_analysis_insights(metadata, data_by_table, collection_summary)
            
            # 5. 종합 분석 결과 생성
            analysis_result = ComprehensiveStatAnalysis(
                stat_url=stat_url,
                stat_title=metadata.title,
                metadata=metadata,
                collected_tables=list(data_by_table.keys()),
                data_by_table=data_by_table,
                total_data_points=total_data_points,
                collection_summary=collection_summary,
                analysis_insights=insights,
                created_at=datetime.now()
            )
            
            print(f"종합 분석 완료: {len(data_by_table)}개 테이블, {total_data_points}개 데이터 포인트")
            return analysis_result
            
        except Exception as e:
            print(f"종합 통계 분석 실패: {e}")
            # 실패 시 기본 결과 반환
            return ComprehensiveStatAnalysis(
                stat_url=stat_url,
                stat_title="분석 실패",
                metadata=StatMetadata(id="error", title="분석 실패", purpose="오류 발생"),
                collected_tables=[],
                data_by_table={},
                total_data_points=0,
                collection_summary={"error": str(e)},
                analysis_insights=["분석 중 오류가 발생했습니다."],
                created_at=datetime.now()
            )

    async def _collect_single_table_data(self, stat_url: str, table_info: Dict[str, str]) -> List[StatData]:
        """개별 통계표 데이터 수집"""
        driver = None
        try:
            driver = self._setup_selenium_driver()
            driver.get(stat_url)
            await asyncio.sleep(3)
            
            # 통계표보기 탭으로 이동
            try:
                table_view_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계표') and contains(text(), '보기')]"))
                )
                table_view_tab.click()
                await asyncio.sleep(2)
            except:
                pass
            
            # 특정 통계표 선택
            select_element = driver.find_element(By.ID, "sFormId")
            select = Select(select_element)
            select.select_by_value(table_info['value'])
            await asyncio.sleep(2)
            
            # 해당 테이블의 데이터 수집
            return await self._collect_table_data(driver, table_info, "5years")
            
        except Exception as e:
            print(f"개별 테이블 수집 실패: {e}")
            return []
        finally:
            if driver:
                driver.quit()

    async def _calculate_data_quality_score(self, data_item: StatData) -> float:
        """데이터 품질 점수 계산 (0-1 범위)"""
        score = 0.0
        total_checks = 5
        
        # 1. 데이터 항목 수 (많을수록 좋음)
        if data_item.raw_data_count and data_item.raw_data_count > 10:
            score += 0.3
        elif data_item.raw_data_count and data_item.raw_data_count > 5:
            score += 0.2
        elif data_item.raw_data_count and data_item.raw_data_count > 0:
            score += 0.1
        
        # 2. 숫자 데이터 비율
        if data_item.data:
            numeric_count = sum(1 for v in data_item.data.values() 
                              if isinstance(v, dict) and v.get("unit") in ["number", "%"])
            numeric_ratio = numeric_count / len(data_item.data) if data_item.data else 0
            score += numeric_ratio * 0.3
        
        # 3. 테이블명 존재
        if data_item.table_name and data_item.table_name.strip():
            score += 0.1
        
        # 4. 기간 정보 완성도
        if data_item.period_text and data_item.period_type:
            score += 0.15
        elif data_item.period_text or data_item.period_type:
            score += 0.1
        
        # 5. 연도 정보 유효성
        if 2020 <= data_item.year <= 2025:
            score += 0.15
        
        return min(score, 1.0)  # 최대 1.0으로 제한

    async def _generate_analysis_insights(self, metadata: StatMetadata, data_by_table: Dict[str, List[StatData]], collection_summary: Dict[str, Any]) -> List[str]:
        """분석 인사이트 생성"""
        insights = []
        
        # 수집 성공률
        total_tables = collection_summary.get("total_tables", 0)
        successful_tables = collection_summary.get("successful_tables", 0)
        if total_tables > 0:
            success_rate = (successful_tables / total_tables) * 100
            insights.append(f"통계표 수집 성공률: {success_rate:.1f}% ({successful_tables}/{total_tables})")
        
        # 데이터 기간 분포
        period_types = collection_summary.get("period_types", {})
        if period_types:
            main_period_type = max(period_types.items(), key=lambda x: x[1])[0]
            insights.append(f"주요 데이터 기간 유형: {main_period_type}")
        
        # 데이터 품질
        quality_scores = collection_summary.get("data_quality_scores", [])
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            insights.append(f"평균 데이터 품질 점수: {avg_quality:.2f}/1.0")
        
        # 가장 데이터가 풍부한 테이블
        if data_by_table:
            richest_table = max(data_by_table.items(), 
                               key=lambda x: sum(len(item.data) for item in x[1]))
            insights.append(f"가장 풍부한 데이터 테이블: {richest_table[0]}")
        
        # 키워드 기반 인사이트
        if metadata.keywords:
            insights.append(f"주요 키워드: {', '.join(metadata.keywords[:3])}")
        
        return insights
    
    def _parse_table_structure(self, table) -> Dict[str, Any]:
        """다양한 테이블 구조를 파싱하여 데이터 추출"""
        try:
            rows = table.find_elements(By.TAG_NAME, "tr")
            if not rows:
                return {}
            
            # 테이블 구조 분석
            parsed_data = {}
            
            # 1. 헤더 행 찾기
            header_row = None
            header_cells = []
            
            for i, row in enumerate(rows):
                th_cells = row.find_elements(By.TAG_NAME, "th")
                td_cells = row.find_elements(By.TAG_NAME, "td")
                
                # th가 있으면 헤더로 간주
                if th_cells:
                    header_row = i
                    header_cells = [cell.text.strip() for cell in th_cells]
                    break
                # 첫 번째 행이 모두 텍스트면 헤더로 간주
                elif i == 0 and td_cells and all(self._is_text_cell(cell) for cell in td_cells):
                    header_row = i
                    header_cells = [cell.text.strip() for cell in td_cells]
            
            # 2. 데이터 행 처리
            data_start_row = (header_row + 1) if header_row is not None else 0
            
            for row_idx in range(data_start_row, len(rows)):
                row = rows[row_idx]
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    cells = row.find_elements(By.TAG_NAME, "th")
                
                if len(cells) >= 2:
                    # 다양한 테이블 형태 처리
                    row_data = self._process_table_row(cells, header_cells)
                    parsed_data.update(row_data)
            
            return parsed_data
            
        except Exception as e:
            print(f"테이블 구조 파싱 실패: {e}")
            return {}
    
    def _is_text_cell(self, cell) -> bool:
        """셀이 텍스트 셀인지 (숫자가 아닌) 판단"""
        text = cell.text.strip()
        if not text:
            return True
        
        # 숫자로만 구성되어 있으면 False
        try:
            float(text.replace(',', '').replace('%', '').replace('원', ''))
            return False
        except ValueError:
            return True
    
    def _process_table_row(self, cells, header_cells: List[str]) -> Dict[str, Any]:
        """테이블 행을 처리하여 데이터 딕셔너리로 변환"""
        row_data = {}
        
        try:
            if len(cells) == 2:
                # 2열 테이블: 항목명 - 값
                item_name = cells[0].text.strip()
                item_value = cells[1].text.strip()
                
                if item_name and item_value and item_name != item_value:
                    processed_value = self._convert_cell_value(item_value)
                    row_data[item_name] = processed_value
                    
            elif len(cells) > 2:
                # 다중 열 테이블
                first_cell = cells[0].text.strip()
                
                # 첫 번째 셀이 분류명이고 나머지가 값들인 경우
                if first_cell and self._is_text_cell(cells[0]):
                    for i in range(1, len(cells)):
                        value_text = cells[i].text.strip()
                        if value_text:
                            # 헤더가 있으면 헤더명 사용, 없으면 인덱스 사용
                            if header_cells and i < len(header_cells):
                                key = f"{first_cell}_{header_cells[i]}"
                            else:
                                key = f"{first_cell}_{i}"
                            
                            processed_value = self._convert_cell_value(value_text)
                            row_data[key] = processed_value
                
                # 모든 셀이 값인 경우 (헤더가 별도로 있음)
                elif header_cells and len(header_cells) == len(cells):
                    for i, cell in enumerate(cells):
                        value_text = cell.text.strip()
                        if value_text and header_cells[i]:
                            processed_value = self._convert_cell_value(value_text)
                            row_data[header_cells[i]] = processed_value
        
        except Exception as e:
            print(f"테이블 행 처리 실패: {e}")
        
        return row_data
    
    def _convert_cell_value(self, value_text: str) -> Any:
        """셀 값을 적절한 타입으로 변환"""
        if not value_text:
            return ""
        
        # 공통 정리
        cleaned = value_text.replace(',', '').replace('원', '').replace('건', '').strip()
        
        # 퍼센트 처리
        if '%' in value_text:
            try:
                return float(cleaned.replace('%', ''))
            except ValueError:
                return value_text
        
        # 숫자 변환 시도
        try:
            # 정수 확인
            if '.' not in cleaned and cleaned.replace('-', '').replace('+', '').isdigit():
                return int(cleaned)
            # 소수 확인
            else:
                return float(cleaned)
        except ValueError:
            # 문자열 그대로 반환
            return value_text