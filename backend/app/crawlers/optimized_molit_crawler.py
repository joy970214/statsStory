import aiohttp
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Tuple, Optional, Callable
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from app.models.stat_models import StatMetadata, StatData
from app.services.progress_service import progress_tracker
try:
    from app.models.stat_models import ComprehensiveStatAnalysis
except ImportError:
    # ComprehensiveStatAnalysis가 없는 경우 기본 구현 사용
    from datetime import datetime
    from typing import List, Dict, Any
    from dataclasses import dataclass
    
    @dataclass
    class ComprehensiveStatAnalysis:
        stat_url: str
        stat_title: str
        metadata: StatMetadata
        collected_tables: List[str]
        data_by_table: Dict[str, List[StatData]]
        total_data_points: int
        collection_summary: Dict[str, Any]
        analysis_insights: List[str]
        created_at: datetime
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class BrowserPool:
    """브라우저 풀 관리자 - 브라우저 재사용으로 성능 향상"""
    
    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.available_browsers = queue.Queue()
        self.total_browsers = 0
        self.lock = threading.Lock()
        
    def _create_browser(self) -> webdriver.Chrome:
        """브라우저 인스턴스 생성"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 안정성 개선 옵션
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-crash-reporter')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--memory-pressure-off')
        chrome_options.add_argument('--max_old_space_size=4096')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)  # 타임아웃 증가
        driver.implicitly_wait(10)  # 암시적 대기 추가
        
        return driver
    
    def get_browser(self) -> webdriver.Chrome:
        """브라우저 인스턴스 가져오기"""
        try:
            return self.available_browsers.get_nowait()
        except queue.Empty:
            with self.lock:
                if self.total_browsers < self.pool_size:
                    driver = self._create_browser()
                    self.total_browsers += 1
                    return driver
                else:
                    # 풀이 가득 찬 경우 대기
                    return self.available_browsers.get()
    
    def return_browser(self, driver: webdriver.Chrome):
        """브라우저 인스턴스 반환"""
        try:
            # 브라우저 상태 초기화
            driver.delete_all_cookies()
            self.available_browsers.put(driver)
        except Exception as e:
            print(f"브라우저 반환 중 오류: {e}")
            # 문제가 있는 브라우저는 종료하고 새로 생성
            try:
                driver.quit()
            except:
                pass
            with self.lock:
                self.total_browsers -= 1
    
    def cleanup(self):
        """모든 브라우저 인스턴스 정리"""
        while not self.available_browsers.empty():
            try:
                driver = self.available_browsers.get_nowait()
                driver.quit()
            except:
                pass


class ProgressCallback:
    """진행률 콜백 인터페이스 - 전역 progress_tracker와 연동"""
    
    def __init__(self, task_id: Optional[str] = None, callback_fn: Optional[Callable[[str, float, str], None]] = None):
        self.task_id = task_id
        self.callback_fn = callback_fn
        self.start_time = datetime.now()
    
    def update(self, stage: str, progress: float, message: str):
        # 전역 progress_tracker에 업데이트
        if self.task_id:
            print(f"[PROGRESS] task_id={self.task_id}, stage={stage}, progress={progress}, message={message}")
            # 예상 남은 시간 계산
            estimated_remaining_time = None
            if progress > 0:
                elapsed_time = (datetime.now() - self.start_time).total_seconds()
                if elapsed_time > 0:
                    total_estimated_time = elapsed_time * (100 / progress)
                    estimated_remaining_time = int(total_estimated_time - elapsed_time)
            
            progress_tracker.update_progress(
                self.task_id, 
                stage, 
                progress, 
                message,
                estimated_remaining_time
            )
            print(f"[PROGRESS] progress_tracker.update_progress 호출 완료")
        
        # 추가 콜백 함수 실행
        if self.callback_fn:
            self.callback_fn(stage, progress, message)
        else:
            print(f"[{progress:.1f}%] {stage}: {message}")


class OptimizedMolitCrawler:
    """최적화된 국토교통부 통계포털 크롤러 - 브라우저 풀링 및 병렬 처리"""
    
    def __init__(self, pool_size: int = 3, max_concurrent_tables: int = 3):
        self.base_url = "https://stat.molit.go.kr"
        self.browser_pool = BrowserPool(pool_size)
        self.max_concurrent_tables = max_concurrent_tables
        
    def __del__(self):
        """소멸자 - 브라우저 풀 정리"""
        if hasattr(self, 'browser_pool'):
            self.browser_pool.cleanup()

    async def get_comprehensive_stat_analysis_optimized(
        self, 
        stat_url: str, 
        progress_callback: Optional[ProgressCallback] = None
    ) -> ComprehensiveStatAnalysis:
        """최적화된 종합 통계 분석 - 병렬 처리 및 실시간 진행률"""
        
        if not progress_callback:
            progress_callback = ProgressCallback()
            
        print(f"최적화된 종합 통계 분석 시작: {stat_url}")
        progress_callback.update("초기화", 0, "분석 시작")
        
        try:
            # 1단계: 메타데이터 수집 (5%)
            progress_callback.update("메타데이터", 5, "통계 메타데이터 수집 중")
            metadata = await self._get_metadata_fast(stat_url)
            
            # 2단계: 통계표 목록과 조건 분석 (15%)
            progress_callback.update("통계표목록", 15, "통계표 목록 및 조건 분석 중")
            stat_tables_with_conditions = await self._get_stat_tables_with_conditions(stat_url)
            
            total_tables = len(stat_tables_with_conditions)
            progress_callback.update("통계표목록", 20, f"{total_tables}개 통계표 발견 (조건 분석 완료)")
            
            if total_tables == 0:
                progress_callback.update("완료", 100, "수집할 통계표가 없습니다")
                return self._create_empty_analysis(stat_url, metadata)
            
            # 3단계: 조건별 데이터 수집 (20% -> 90%)
            progress_callback.update("데이터수집", 20, f"병렬 데이터 수집 시작 ({total_tables}개 통계표)")
            
            data_by_table, collection_summary = await self._collect_tables_with_conditions_parallel(
                stat_url, stat_tables_with_conditions, progress_callback
            )
            
            # 4단계: 분석 인사이트 생성 (95%)
            progress_callback.update("분석", 95, "분석 인사이트 생성 중")
            insights = await self._generate_analysis_insights(metadata, data_by_table, collection_summary)
            
            # 5단계: 최종 결과 생성 (100%)
            total_data_points = sum(len(table_data) for table_data in data_by_table.values())
            
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
            
            progress_callback.update("완료", 100, 
                f"분석 완료: {len(data_by_table)}개 테이블, {total_data_points}개 데이터 포인트")
            
            return analysis_result
            
        except Exception as e:
            progress_callback.update("오류", 100, f"분석 실패: {str(e)}")
            print(f"최적화된 종합 분석 실패: {e}")
            return self._create_error_analysis(stat_url, str(e))

    async def _get_metadata_fast(self, stat_url: str) -> StatMetadata:
        """빠른 메타데이터 수집"""
        driver = self.browser_pool.get_browser()
        try:
            driver.get(stat_url)
            await asyncio.sleep(1)  # 대기 시간 단축
            
            # 기본값 설정
            page_title = driver.title
            metadata_info = {
                'title': page_title if page_title else "통계명",
                'purpose': '통계 작성 목적',
                'frequency': '정기',
                'department': '국토교통부',
                'contact': '담당자 연락처',
                'keywords': [],
                'related_terms': {},
                'url': stat_url
            }
            
            # 메타데이터 수집: 통계정보 + 관련용어 탭
            try:
                metadata_info = await self._collect_metadata_comprehensive(driver)
            except Exception as e:
                print(f"메타데이터 수집 실패: {e}")
                # 기본값 유지
            
            return StatMetadata(
                id=stat_url.split('=')[-1] if '=' in stat_url else 'unknown',
                title=metadata_info['title'],
                purpose=metadata_info['purpose'],
                frequency=metadata_info['frequency'],
                department=metadata_info['department'],
                contact=metadata_info['contact'],
                keywords=metadata_info['keywords'],
                related_terms=metadata_info['related_terms'],
                url=stat_url
            )
            
        finally:
            self.browser_pool.return_browser(driver)

    async def _get_available_tables_fast(self, stat_url: str) -> List[Dict[str, str]]:
        """빠른 통계표 목록 수집"""
        driver = self.browser_pool.get_browser()
        try:
            driver.get(stat_url)
            await asyncio.sleep(1)
            
            # 통계표보기 탭으로 이동
            try:
                table_view_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계표') and contains(text(), '보기')]"))
                )
                table_view_tab.click()
                await asyncio.sleep(1)
            except:
                pass  # 이미 선택되어 있을 수 있음
            
            # #sFormId 셀렉트에서 옵션 수집
            stat_tables = []
            try:
                select_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "sFormId"))
                )
                
                select = Select(select_element)
                options = select.options
                
                for option in options:
                    option_text = option.text.strip()
                    option_value = option.get_attribute('value')
                    
                    if option_text and '(종료)' not in option_text and option_value:
                        stat_tables.append({
                            'name': option_text,
                            'value': option_value,
                            'form_id': option_value
                        })
                        
            except Exception as e:
                print(f"통계표 목록 수집 실패: {e}")
            
            return stat_tables
            
        finally:
            self.browser_pool.return_browser(driver)

    async def _collect_tables_parallel(
        self, 
        stat_url: str, 
        available_tables: List[Dict[str, str]], 
        progress_callback: ProgressCallback
    ) -> Tuple[Dict[str, List[StatData]], Dict[str, Any]]:
        """병렬 통계표 데이터 수집"""
        
        data_by_table = {}
        collection_summary = {
            "total_tables": len(available_tables),
            "successful_tables": 0,
            "failed_tables": 0,
            "period_types": {},
            "data_quality_scores": []
        }
        
        # 동시 처리할 통계표 수 제한 (너무 많으면 메모리 부족)
        max_concurrent = min(self.max_concurrent_tables, len(available_tables))
        
        # 진행률 추적
        completed_tables = 0
        progress_start = 20  # 데이터 수집 시작점
        progress_range = 70  # 데이터 수집 구간 (20% -> 90%)
        
        # 세마포어로 동시 실행 제한
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def collect_single_table(table_info: Dict[str, str]) -> Tuple[str, List[StatData]]:
            """개별 통계표 수집 (세마포어 사용)"""
            async with semaphore:
                table_name = table_info['name']
                try:
                    table_data = await self._collect_single_table_optimized(stat_url, table_info)
                    return table_name, table_data
                except Exception as e:
                    print(f"통계표 '{table_name}' 수집 실패: {e}")
                    return table_name, []
        
        # 모든 통계표를 병렬로 처리
        tasks = [collect_single_table(table_info) for table_info in available_tables]
        
        # 완료된 작업들을 순서대로 처리
        for coro in asyncio.as_completed(tasks):
            table_name, table_data = await coro
            completed_tables += 1
            
            # 진행률 업데이트
            progress = progress_start + (completed_tables / len(available_tables)) * progress_range
            progress_callback.update("데이터수집", progress, 
                f"통계표 '{table_name}' 수집 완료 ({completed_tables}/{len(available_tables)})")
            
            # 결과 처리
            if table_data:
                # 품질 점수 계산 및 설정
                for data_item in table_data:
                    data_item.table_name = table_name
                    data_item.data_quality_score = await self._calculate_data_quality_score(data_item)
                    collection_summary["data_quality_scores"].append(data_item.data_quality_score)
                
                data_by_table[table_name] = table_data
                collection_summary["successful_tables"] += 1
                
                # 기간 유형 집계
                for item in table_data:
                    period_type = getattr(item, 'period_type', None) or "알 수 없음"
                    collection_summary["period_types"][period_type] = collection_summary["period_types"].get(period_type, 0) + 1
                    
            else:
                collection_summary["failed_tables"] += 1
        
        return data_by_table, collection_summary

    async def _collect_single_table_optimized(self, stat_url: str, table_info: Dict[str, str]) -> List[StatData]:
        """최적화된 개별 통계표 데이터 수집"""
        driver = self.browser_pool.get_browser()
        try:
            driver.get(stat_url)
            await asyncio.sleep(1)  # 대기 시간 단축
            
            # 통계표보기 탭으로 이동
            try:
                table_view_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계표') and contains(text(), '보기')]"))
                )
                table_view_tab.click()
                await asyncio.sleep(1)
            except:
                pass
            
            # 특정 통계표 선택
            select_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "sFormId"))
            )
            select = Select(select_element)
            select.select_by_value(table_info['value'])
            await asyncio.sleep(1)
            
            # 기간별 데이터 수집 (최적화)
            return await self._collect_table_data_optimized(driver, table_info)
            
        except Exception as e:
            print(f"최적화된 개별 테이블 수집 실패: {e}")
            return []
        finally:
            self.browser_pool.return_browser(driver)

    async def _collect_table_data_optimized(self, driver, table_info: Dict[str, str]) -> List[StatData]:
        """최적화된 테이블 데이터 수집 - 샘플링 및 빠른 처리"""
        try:
            # 기간 선택 요소 찾기
            period_data = []
            
            # 년도 선택 드롭다운 찾기 (빠른 검색)
            year_selects = driver.find_elements(By.CSS_SELECTOR, "select[name*='year'], select[id*='year']")
            
            if not year_selects:
                # 백업 검색
                period_selects = driver.find_elements(By.CSS_SELECTOR, "select")[:3]  # 처음 3개만 검사
                for select_elem in period_selects:
                    try:
                        select_options = Select(select_elem).options[:5]  # 처음 5개 옵션만 검사
                        if any('20' in opt.text for opt in select_options):
                            year_selects.append(select_elem)
                            break
                    except:
                        continue
            
            if year_selects:
                year_select = Select(year_selects[0])
                available_periods = []
                
                for option in year_select.options:
                    option_text = option.text.strip()
                    if option_text and '20' in option_text:
                        available_periods.append({
                            'text': option_text,
                            'value': option.get_attribute('value')
                        })
                
                # 기간 유형 판단 및 샘플링
                period_type, target_periods = await self._determine_period_type_and_sample(available_periods)
                
                # 최대 3개 기간만 처리 (성능 최적화)
                target_periods = target_periods[:3]
                
                # 각 기간별 데이터 수집
                for period_info in target_periods:
                    try:
                        year_select.select_by_value(period_info['value'])
                        await asyncio.sleep(0.5)  # 대기 시간 단축
                        
                        # 조회 버튼 찾기 및 클릭
                        search_btn = await self._find_search_button_fast(driver)
                        if search_btn:
                            search_btn.click()
                            await asyncio.sleep(1.5)  # 데이터 로딩 대기 시간 단축
                        
                        # 테이블 데이터 추출
                        table_data = await self._extract_table_data_fast(driver, period_info['text'])
                        if table_data:
                            table_data.period_type = period_type
                            period_data.append(table_data)
                            
                    except Exception as period_error:
                        print(f"기간 {period_info['text']} 처리 실패: {period_error}")
                        continue
            
            return period_data
            
        except Exception as e:
            print(f"최적화된 테이블 데이터 수집 실패: {e}")
            return []

    async def _determine_period_type_and_sample(self, available_periods: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
        """기간 유형 판단 및 샘플링 (성능 최적화)"""
        if not available_periods:
            return "알 수 없음", []
        
        # 빠른 패턴 분석
        monthly_count = sum(1 for p in available_periods if len(p['text']) >= 6 and p['text'].replace('-', '').isdigit())
        yearly_count = sum(1 for p in available_periods if len(p['text']) == 4 and p['text'].isdigit())
        
        total_periods = len(available_periods)
        
        if monthly_count > total_periods * 0.5:
            period_type = "월간"
            # 최근 6개월만 (성능 최적화)
            target_periods = available_periods[-6:]
        elif yearly_count > total_periods * 0.5:
            period_type = "년간"
            # 최근 3년만 (성능 최적화)
            target_periods = available_periods[-3:]
        else:
            period_type = "혼합"
            # 최근 5개만
            target_periods = available_periods[-5:]
        
        return period_type, target_periods

    async def _find_search_button_fast(self, driver) -> Optional[Any]:
        """빠른 조회 버튼 찾기"""
        # 가장 일반적인 패턴만 빠르게 검색
        button_patterns = [
            "//input[@type='button' and contains(@value, '조회')]",
            "//button[contains(text(), '조회')]",
            "//input[@id='btnSearch']",
            "//button[@id='btnSearch']"
        ]
        
        for pattern in button_patterns:
            try:
                element = driver.find_element(By.XPATH, pattern)
                if element.is_displayed() and element.is_enabled():
                    return element
            except:
                continue
        
        return None

    async def _extract_table_data_fast(self, driver, period_text: str) -> Optional[StatData]:
        """빠른 테이블 데이터 추출 - IBSheet 데이터 포함"""
        try:
            await asyncio.sleep(2)  # 데이터 로딩 대기 (IBSheet 로딩 시간 고려)
            
            extracted_data = {}
            
            # 1. IBSheet 데이터 추출 시도
            ibsheet_data = await self._extract_ibsheet_data(driver)
            if ibsheet_data:
                extracted_data.update(ibsheet_data)
                print(f"IBSheet에서 {len(ibsheet_data)}개 데이터 추출 성공")
            
            # 2. 기존 정적 테이블 추출 (fallback)
            if len(extracted_data) < 5:
                potential_tables = driver.find_elements(By.CSS_SELECTOR, "table[border], .table, table[cellpadding]")
                
                if not potential_tables:
                    potential_tables = driver.find_elements(By.TAG_NAME, "table")[:3]  # 처음 3개만
                
                for table in potential_tables[:2]:  # 최대 2개 테이블만 처리
                    try:
                        rows = table.find_elements(By.TAG_NAME, "tr")[:10]  # 최대 10개 행만
                        
                        for i, row in enumerate(rows):
                            cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
                            
                            if len(cells) == 2:  # 키-값 형태
                                key = cells[0].text.strip()
                                value_text = cells[1].text.strip()
                                if key and value_text and key != value_text:
                                    extracted_data[key] = await self._convert_cell_value_fast(value_text)
                            
                            elif len(cells) > 2 and i > 0:  # 다중 열 (헤더 제외)
                                first_cell = cells[0].text.strip()
                                if first_cell:
                                    for j, cell in enumerate(cells[1:3]):  # 최대 2개 값만
                                        value_text = cell.text.strip()
                                        if value_text:
                                            key = f"{first_cell}_{j+1}"
                                            extracted_data[key] = await self._convert_cell_value_fast(value_text)
                        
                        if len(extracted_data) >= 5:  # 충분한 데이터가 있으면 중단
                            break
                            
                    except Exception:
                        continue
            
            # 연도 추출
            year = await self._extract_year_from_period_fast(period_text)
            
            return StatData(
                year=year,
                data=extracted_data,
                table_name="",
                period_text=period_text,
                raw_data_count=len(extracted_data)
            )
            
        except Exception as e:
            print(f"빠른 테이블 데이터 추출 실패: {e}")
            return None

    async def _convert_cell_value_fast(self, value_text: str) -> Dict[str, Any]:
        """빠른 셀 값 변환"""
        if not value_text:
            return {"value": "", "unit": "text", "raw": value_text}
        
        # 간단한 숫자 변환만 시도
        cleaned = value_text.replace(',', '').strip()
        
        try:
            if '.' in cleaned:
                return {"value": float(cleaned), "unit": "number", "raw": value_text}
            elif cleaned.replace('-', '').isdigit():
                return {"value": int(cleaned), "unit": "number", "raw": value_text}
        except:
            pass
        
        return {"value": value_text, "unit": "text", "raw": value_text}

    async def _extract_year_from_period_fast(self, period_text: str) -> int:
        """빠른 연도 추출"""
        if len(period_text) == 4 and period_text.isdigit():
            return int(period_text)
        elif len(period_text) == 6 and period_text.isdigit():
            return int(period_text[:4])
        
        # 간단한 정규식만 사용
        import re
        match = re.search(r'20\d{2}', period_text)
        if match:
            return int(match.group())
        
        return 2025  # 기본값

    async def _calculate_data_quality_score(self, data_item: StatData) -> float:
        """데이터 품질 점수 계산"""
        score = 0.0
        
        # 간단한 품질 평가
        if data_item.raw_data_count and data_item.raw_data_count > 5:
            score += 0.5
        
        if data_item.data and len(data_item.data) > 0:
            score += 0.3
        
        if 2020 <= data_item.year <= 2025:
            score += 0.2
        
        return min(score, 1.0)

    async def _generate_analysis_insights(self, metadata: StatMetadata, data_by_table: Dict[str, List[StatData]], collection_summary: Dict[str, Any]) -> List[str]:
        """분석 인사이트 생성"""
        insights = []
        
        total_tables = collection_summary.get("total_tables", 0)
        successful_tables = collection_summary.get("successful_tables", 0)
        
        if total_tables > 0:
            success_rate = (successful_tables / total_tables) * 100
            insights.append(f"통계표 수집 성공률: {success_rate:.1f}% ({successful_tables}/{total_tables})")
        
        if data_by_table:
            insights.append(f"총 {len(data_by_table)}개 통계표에서 데이터 수집 완료")
        
        return insights

    def _create_empty_analysis(self, stat_url: str, metadata: StatMetadata) -> ComprehensiveStatAnalysis:
        """빈 분석 결과 생성"""
        return ComprehensiveStatAnalysis(
            stat_url=stat_url,
            stat_title=metadata.title,
            metadata=metadata,
            collected_tables=[],
            data_by_table={},
            total_data_points=0,
            collection_summary={"message": "수집할 통계표가 없습니다"},
            analysis_insights=["수집 가능한 통계표가 없습니다"],
            created_at=datetime.now()
        )

    def _create_error_analysis(self, stat_url: str, error_msg: str) -> ComprehensiveStatAnalysis:
        """오류 분석 결과 생성"""
        return ComprehensiveStatAnalysis(
            stat_url=stat_url,
            stat_title="분석 실패",
            metadata=StatMetadata(id="error", title="분석 실패", purpose="오류 발생"),
            collected_tables=[],
            data_by_table={},
            total_data_points=0,
            collection_summary={"error": error_msg},
            analysis_insights=[f"분석 중 오류 발생: {error_msg}"],
            created_at=datetime.now()
        )

    async def _extract_ibsheet_data(self, driver) -> Dict[str, Any]:
        """IBSheet에서 동적 데이터 추출"""
        try:
            # 1. doSearch() 함수 실행하여 데이터 로드
            try:
                driver.execute_script("if (typeof doSearch === 'function') doSearch();")
                await asyncio.sleep(3)  # 데이터 로딩 대기
            except Exception as e:
                print(f"doSearch() 실행 실패: {e}")
            
            # 2. IBSheet 객체에서 데이터 직접 추출
            ibsheet_data = {}
            
            # IBSheet 로딩 대기 (더 긴 시간)
            await asyncio.sleep(3)
            
            # sheet01 객체에서 데이터 가져오기
            try:
                # 여러 IBSheet 객체 이름 시도
                row_count_script = """
                var sheetNames = ['sheet01', 'Sheet1', 'ibsheet', 'IBSheet', 'mainSheet'];
                var rowCount = 0;
                var foundSheet = null;
                
                for (var name of sheetNames) {
                    try {
                        if (typeof window[name] !== 'undefined' && window[name].GetDataRowCount) {
                            rowCount = window[name].GetDataRowCount();
                            foundSheet = name;
                            console.log('Found IBSheet:', name, 'with', rowCount, 'rows');
                            break;
                        }
                    } catch(e) {
                        console.log('Error checking', name, ':', e);
                    }
                }
                
                return {rowCount: rowCount, sheetName: foundSheet};
                """
                result = driver.execute_script(row_count_script)
                row_count = result.get('rowCount', 0) if isinstance(result, dict) else 0
                sheet_name = result.get('sheetName') if isinstance(result, dict) else None
                
                print(f"IBSheet 데이터 행 수: {row_count} (사용된 시트: {sheet_name})")
                
                if row_count > 0 and sheet_name:
                    # 컬럼 헤더 가져오기 (발견된 시트 이름 사용)
                    col_script = f"""
                    var sheetObj = window['{sheet_name}'];
                    if (sheetObj && sheetObj.GetColName) {{
                        var cols = [];
                        try {{
                            for (var i = 0; i < 20; i++) {{  // 최대 20개 컬럼
                                var colName = sheetObj.GetColName(i);
                                if (colName && colName.trim() !== '') {{
                                    cols.push(colName);
                                }} else if (i > 5) {{  // 5개 연속 빈 컬럼이면 중단
                                    break;
                                }}
                            }}
                        }} catch(e) {{
                            console.log('Column error:', e);
                        }}
                        return cols;
                    }}
                    return [];
                    """
                    columns = driver.execute_script(col_script)
                    print(f"IBSheet 컬럼: {columns}")
                    
                    # 데이터 추출 (최대 20개 행, 효율적으로)
                    max_rows = min(row_count, 20)
                    max_cols = min(len(columns), 10)
                    
                    # 한번에 여러 셀 데이터 가져오기
                    batch_script = f"""
                    var sheetObj = window['{sheet_name}'];
                    var batchData = [];
                    
                    if (sheetObj && sheetObj.GetCellValue) {{
                        for (var row = 0; row < {max_rows}; row++) {{
                            var rowData = [];
                            for (var col = 0; col < {max_cols}; col++) {{
                                try {{
                                    var value = sheetObj.GetCellValue(row, col);
                                    rowData.push(value || '');
                                }} catch(e) {{
                                    rowData.push('');
                                }}
                            }}
                            batchData.push(rowData);
                        }}
                    }}
                    
                    return batchData;
                    """
                    
                    batch_data = driver.execute_script(batch_script)
                    print(f"IBSheet 배치 데이터 수집: {len(batch_data) if batch_data else 0}개 행")
                    
                    # 배치 데이터를 딕셔너리로 변환
                    if batch_data:
                        for row_idx, row_data in enumerate(batch_data):
                            for col_idx, value in enumerate(row_data):
                                if col_idx < len(columns) and value and str(value).strip():
                                    col_name = columns[col_idx]
                                    key = f"{col_name}_{row_idx+1}" if row_idx > 0 else col_name
                                    ibsheet_data[key] = await self._convert_cell_value_fast(str(value))
                    
            except Exception as e:
                print(f"IBSheet 데이터 추출 오류: {e}")
            
            # 3. 생성된 HTML 테이블에서도 데이터 추출 (IBSheet가 HTML로 렌더링한 경우)
            try:
                # IBSheet가 생성한 테이블 찾기
                ibsheet_tables = driver.find_elements(By.CSS_SELECTOR, "[id*='sheet'], [class*='sheet'], .ibsheet")
                for table in ibsheet_tables:
                    try:
                        # 테이블 내의 셀 데이터 추출
                        cells = table.find_elements(By.CSS_SELECTOR, "td, .cell")  # 전체 셀
                        for i, cell in enumerate(cells):
                            cell_text = cell.text.strip()
                            if cell_text and len(cell_text) > 0:
                                # 숫자나 의미있는 데이터인 경우만 추출
                                if any(char.isdigit() for char in cell_text) or len(cell_text.split()) <= 3:
                                    key = f"ibsheet_cell_{i}"
                                    ibsheet_data[key] = await self._convert_cell_value_fast(cell_text)
                    except:
                        continue
                        
            except Exception as e:
                print(f"IBSheet HTML 테이블 추출 오류: {e}")
            
            return ibsheet_data
            
        except Exception as e:
            print(f"IBSheet 데이터 추출 전체 오류: {e}")
            return {}

    async def _collect_metadata_comprehensive(self, driver) -> dict:
        """통계정보 + 관련용어 탭에서 메타데이터 종합 수집"""
        metadata_info = {
            'title': '국토교통 통계누리',
            'purpose': '통계 작성 목적',
            'frequency': '정기',
            'department': '국토교통부',
            'contact': '담당자 연락처',
            'keywords': [],
            'related_terms': {}
        }
        
        try:
            # 1. 통계정보 탭 수집
            stat_info_tab = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계정보')]"))
            )
            stat_info_tab.click()
            await asyncio.sleep(1)
            
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
                        elif '작성주기' in key or '작성빈도' in key:
                            metadata_info['frequency'] = value
                        elif '작성기관' in key or '담당부서' in key:
                            metadata_info['department'] = value
                        elif '연락처' in key or '담당자' in key:
                            metadata_info['contact'] = value
                            
                    except:
                        continue
            
            # 2. 관련용어 탭 수집
            try:
                related_terms_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '관련용어')]"))
                )
                related_terms_tab.click()
                await asyncio.sleep(1)
                
                # 관련용어 테이블에서 용어 추출
                terms_tables = driver.find_elements(By.TAG_NAME, "table")
                for table in terms_tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 2:
                                term = cells[0].text.strip()
                                definition = cells[1].text.strip()
                                if term and definition:
                                    metadata_info['related_terms'][term] = definition
                                    metadata_info['keywords'].append(term)
                        except:
                            continue
                            
            except Exception as e:
                print(f"관련용어 탭 수집 실패: {e}")
                
        except Exception as e:
            print(f"통계정보 탭 수집 실패: {e}")
            
        return metadata_info

    async def _get_stat_tables_with_conditions(self, stat_url: str) -> List[Dict[str, Any]]:
        """통계표 목록과 각 표의 조건 분석"""
        driver = self.browser_pool.get_browser()
        try:
            driver.get(stat_url)
            await asyncio.sleep(1)
            
            # 통계표보기 탭으로 이동
            try:
                table_view_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계표') and contains(text(), '보기')]"))
                )
                table_view_tab.click()
                await asyncio.sleep(1)
            except:
                pass
            
            stat_tables = []
            
            # #sFormId 셀렉트에서 옵션들 수집
            try:
                select_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "sFormId"))
                )
                
                select = Select(select_element)
                options = select.options
                
                for option in options:
                    option_text = option.text.strip()
                    option_value = option.get_attribute('value')
                    
                    if option_text and '(종료)' not in option_text and option_value:
                        # 통계표명 분석
                        table_info = {
                            'name': option_text,
                            'value': option_value,
                            'form_id': option_value,
                            'is_regional': '_시도별' in option_text,
                            'is_yearly': '_연도별' in option_text,
                            'requires_date_range': False  # 기본값
                        }
                        
                        stat_tables.append(table_info)
                        
            except Exception as e:
                print(f"통계표 목록 수집 실패: {e}")
            
            return stat_tables
            
        finally:
            self.browser_pool.return_browser(driver)

    async def _collect_table_data_with_conditions(self, stat_url: str, table_info: Dict[str, Any]) -> List[StatData]:
        """통계표 조건에 따른 데이터 수집"""
        driver = self.browser_pool.get_browser()
        try:
            driver.get(stat_url)
            await asyncio.sleep(1)
            
            # 통계표보기 탭으로 이동
            try:
                table_view_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계표') and contains(text(), '보기')]"))
                )
                table_view_tab.click()
                await asyncio.sleep(1)
            except:
                pass
            
            # 통계표 선택
            try:
                select_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "sFormId"))
                )
                select = Select(select_element)
                select.select_by_value(table_info['form_id'])
                await asyncio.sleep(1)
            except Exception as e:
                print(f"통계표 선택 실패: {e}")
                return []
            
            # 날짜 형식 자동 감지
            date_format = await self._detect_date_format(driver)
            print(f"감지된 날짜 형식: {date_format}")
            
            # API 수집을 임시 비활성화 (안정성을 위해 IBSheet 방식만 사용)
            # TODO: API 엔드포인트가 안정화되면 다시 활성화
            api_disabled = True
            
            if not api_disabled:
                # API 기반 데이터 수집 우선 시도
                try:
                    # 현재 날짜 기본값 설정 (최신 1개월)
                    from datetime import datetime
                    current_date = datetime.now()
                    current_month = current_date.strftime('%Y%m')
                    
                    # 조건부 날짜 설정
                    if table_info['is_regional'] or '시·군·구별' in table_info['name']:
                        # 지역별: 현재 월
                        start_date = end_date = current_month
                        print(f"지역별 API 데이터 수집: {table_info['name']} ({current_month})")
                    
                    elif table_info['is_yearly'] or await self._should_use_date_range(driver):
                        # 연도별: 5년치 범위 계산
                        if date_format == "YYYY":
                            start_date = str(current_date.year - 4)
                            end_date = str(current_date.year)
                        else:
                            # YYYYMM 형식으로 5년 전부터
                            start_year = current_date.year - 4
                            start_date = f"{start_year}01"
                            end_date = current_month
                        print(f"연도별 API 데이터 수집: {table_info['name']} ({start_date}~{end_date})")
                    else:
                        # 기본: 현재 월
                        start_date = end_date = current_month
                        print(f"기본 API 데이터 수집: {table_info['name']} ({current_month})")
                    
                    # API를 통한 데이터 수집 시도
                    api_result = await self._collect_table_data_via_api(stat_url, table_info, start_date, end_date)
                    
                    if api_result:
                        print(f"API 데이터 수집 성공: {len(api_result)}개")
                        return api_result
                    else:
                        print("API 수집 실패, 기존 방식으로 fallback")
                    
                except Exception as e:
                    print(f"API 수집 중 오류: {e}, 기존 방식으로 fallback")
            
            # IBSheet 기반 데이터 수집 (메인 방식)
            print(f"IBSheet 데이터 수집 시작: {table_info['name']}")
            
            if table_info['is_regional'] or '시·군·구별' in table_info['name']:
                print(f"지역별 데이터 수집: {table_info['name']}")
                await self._click_search_button(driver)
                return await self._extract_current_data(driver, table_info['name'])
                
            elif table_info['is_yearly'] or await self._should_use_date_range(driver):
                print(f"연도별/날짜범위 데이터 수집: {table_info['name']}")
                return await self._collect_data_with_date_range(driver, table_info['name'], date_format)
                
            else:
                print(f"[Fallback] 기본 데이터 수집: {table_info['name']}")
                await self._click_search_button(driver)
                return await self._extract_current_data(driver, table_info['name'])
                
        finally:
            self.browser_pool.return_browser(driver)

    async def _should_use_date_range(self, driver) -> bool:
        """날짜 범위 설정이 필요한지 판단"""
        try:
            # 현재 IBSheet 데이터 확인
            data_dict = await self._extract_ibsheet_data(driver)
            
            # 행열 데이터가 17개 이하인지 확인
            if len(data_dict) > 17:
                return False
            
            # 년도 형식이 있는지 확인 (YYYY 형식)
            for value in data_dict.values():
                if isinstance(value, str):
                    # 4자리 숫자가 년도인지 확인 (1900-2100 범위)
                    import re
                    year_pattern = r'\b(19\d\d|20\d\d|21\d\d)\b'
                    if re.search(year_pattern, value):
                        print(f"년도 형식 발견: {value}")
                        return True
                        
            return False
            
        except Exception as e:
            print(f"날짜 범위 판단 오류: {e}")
            return False

    async def _collect_data_with_date_range(self, driver, table_name: str, date_format: str = "YYYYMM") -> List[StatData]:
        """5년치 데이터 수집 (#sStart, #sEnd 설정)"""
        try:
            from datetime import datetime, timedelta
            
            # 5년치 날짜 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*5)
            
            # 날짜 형식에 따른 포맷 설정
            if date_format == "YYYY":
                start_value = start_date.strftime('%Y')
                end_value = end_date.strftime('%Y')
            elif date_format == "YYYY-MM":
                start_value = start_date.strftime('%Y-%m').replace('-0', '-')  # 01 -> 1
                end_value = end_date.strftime('%Y-%m').replace('-0', '-')
            elif date_format == "YYYYMM":
                start_value = start_date.strftime('%Y%m')
                end_value = end_date.strftime('%Y%m')
            else:
                start_value = start_date.strftime('%Y%m')  # 기본값
                end_value = end_date.strftime('%Y%m')
            
            print(f"날짜 범위 설정 ({date_format}): {start_value} ~ {end_value}")
            
            # #sStart와 #sEnd 설정
            try:
                start_element = driver.find_element(By.ID, "sStart")
                start_element.clear()
                start_element.send_keys(start_value)
                
                end_element = driver.find_element(By.ID, "sEnd")
                end_element.clear()
                end_element.send_keys(end_value)
                
                # 조회 버튼 클릭
                await self._click_search_button(driver)
                
            except Exception as e:
                print(f"날짜 범위 설정 실패: {e}")
            
            # 데이터 추출
            return await self._extract_current_data(driver, table_name)
            
        except Exception as e:
            print(f"날짜 범위 데이터 수집 실패: {e}")
            return []

    async def _extract_current_data(self, driver, table_name: str) -> List[StatData]:
        """현재 화면의 데이터 추출"""
        try:
            # doSearch() 실행하여 데이터 로딩
            driver.execute_script("if (typeof doSearch === 'function') doSearch();")
            await asyncio.sleep(1)
            
            # IBSheet 데이터 추출
            data_dict = await self._extract_ibsheet_data(driver)
            
            if not data_dict:
                print(f"데이터 추출 실패: {table_name}")
                return []
            
            print(f"데이터 추출 성공: {table_name} ({len(data_dict)}개 데이터)")
            
            # StatData 객체로 변환 (올바른 모델 구조 사용)
            from datetime import datetime
            current_year = datetime.now().year
            
            # 데이터를 Dict 형태로 변환
            converted_data = {}
            for key, value in data_dict.items():
                converted_data[key] = str(value)
            
            # 단일 StatData 객체 생성 (기존 모델 구조에 맞게)
            stat_data = StatData(
                year=current_year,
                data=converted_data,
                table_name=table_name,
                period_text=f"{datetime.now().strftime('%Y-%m')}",
                raw_data_count=len(data_dict)
            )
            
            return [stat_data]
            
        except Exception as e:
            print(f"현재 데이터 추출 오류: {e}")
            return []

    async def _collect_tables_with_conditions_parallel(
        self, 
        stat_url: str, 
        stat_tables_with_conditions: List[Dict[str, Any]], 
        progress_callback: ProgressCallback
    ) -> Tuple[Dict[str, List[StatData]], Dict[str, Any]]:
        """조건부 병렬 통계표 데이터 수집"""
        
        data_by_table = {}
        collection_summary = {
            "total_tables": len(stat_tables_with_conditions),
            "collected_tables": 0,
            "regional_tables": 0,
            "yearly_tables": 0,
            "date_range_tables": 0,
            "default_tables": 0,
            "total_data_points": 0,
            "errors": []
        }
        
        # 각 통계표를 순차적으로 처리 (조건별 처리가 복잡해서 병렬보다는 순차 처리)
        for i, table_info in enumerate(stat_tables_with_conditions):
            try:
                table_name = table_info['name']
                progress_callback.update(
                    "데이터수집", 
                    20 + (i * 70 // len(stat_tables_with_conditions)), 
                    f"수집 중: {table_name}"
                )
                
                print(f"통계표 수집 시작: {table_name} (조건: 시도별={table_info['is_regional']}, 연도별={table_info['is_yearly']})")
                
                # 조건에 따른 데이터 수집
                table_data = await self._collect_table_data_with_conditions(stat_url, table_info)
                
                if table_data:
                    data_by_table[table_name] = table_data
                    collection_summary["collected_tables"] += 1
                    collection_summary["total_data_points"] += len(table_data)
                    
                    # 조건별 통계
                    if table_info['is_regional']:
                        collection_summary["regional_tables"] += 1
                    elif table_info['is_yearly']:
                        collection_summary["yearly_tables"] += 1
                        collection_summary["date_range_tables"] += 1
                    else:
                        collection_summary["default_tables"] += 1
                    
                    print(f"통계표 수집 완료: {table_name} ({len(table_data)}개 데이터)")
                else:
                    print(f"통계표 수집 실패: {table_name}")
                    collection_summary["errors"].append(f"데이터 수집 실패: {table_name}")
                
            except Exception as e:
                error_msg = f"통계표 '{table_info.get('name', 'Unknown')}' 처리 오류: {e}"
                print(error_msg)
                collection_summary["errors"].append(error_msg)
        
        progress_callback.update("데이터수집", 90, f"데이터 수집 완료 ({collection_summary['collected_tables']}개 통계표)")
        
        return data_by_table, collection_summary

    async def _detect_date_format(self, driver) -> str:
        """날짜 입력 필드 형식 자동 감지"""
        try:
            # #sStart 필드 확인
            start_element = driver.find_element(By.ID, "sStart")
            
            # placeholder나 기본값 확인
            placeholder = start_element.get_attribute("placeholder") or ""
            value = start_element.get_attribute("value") or ""
            
            # 형식 판단
            if "-" in placeholder or "-" in value:
                return "YYYY-MM"
            elif len(placeholder) == 6 or len(value) == 6:
                return "YYYYMM"
            elif len(placeholder) == 4 or len(value) == 4:
                return "YYYY"
            else:
                # 기본값은 YYYYMM
                return "YYYYMM"
                
        except Exception as e:
            print(f"날짜 형식 감지 실패: {e}")
            return "YYYYMM"  # 기본값

    async def _click_search_button(self, driver):
        """조회/검색 버튼 클릭"""
        try:
            # 다양한 조회 버튼 패턴 시도
            button_selectors = [
                "//input[@value='조회']",
                "//input[@value='검색']",
                "//button[contains(text(), '조회')]",
                "//button[contains(text(), '검색')]",
                "//a[contains(@onclick, 'doSearch')]"
            ]
            
            for selector in button_selectors:
                try:
                    search_button = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    search_button.click()
                    print(f"조회 버튼 클릭 성공: {selector}")
                    await asyncio.sleep(2)  # 데이터 로딩 대기
                    return
                except:
                    continue
            
            # 버튼을 찾지 못한 경우 JavaScript doSearch() 직접 호출
            driver.execute_script("if (typeof doSearch === 'function') doSearch();")
            print("JavaScript doSearch() 호출")
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"조회 버튼 클릭 실패: {e}")

    async def _extract_data_via_api(self, driver, form_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """AJAX API를 통한 직접 데이터 추출"""
        try:
            import aiohttp
            import json
            
            # 현재 페이지의 쿠키와 세션 가져오기
            cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
            
            # API 요청을 위한 세션 생성
            async with aiohttp.ClientSession(cookies=cookies) as session:
                
                # 1. 실제 국토교통부 통계누리 API 구조에 맞게 수정
                # FormId를 hFormId로 변경하고 실제 API 경로 사용
                columns_url = f"https://stat.molit.go.kr/portal/cate/getData.do?hFormId={form_id}&searchCondition=basic"
                print(f"컬럼 정보 요청: {columns_url}")
                
                # User-Agent와 Referer 헤더 추가
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': f'https://stat.molit.go.kr/portal/cate/statView.do?hFormId={form_id}',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'XMLHttpRequest'
                }
                
                async with session.get(columns_url, headers=headers) as response:
                    print(f"컬럼 응답 상태: {response.status}")
                    text_content = await response.text()
                    print(f"컬럼 응답 내용 (처음 200자): {text_content[:200]}")
                    
                    try:
                        columns_data = await response.json()
                    except Exception as e:
                        print(f"컬럼 JSON 파싱 실패: {e}")
                        try:
                            import json
                            columns_data = json.loads(text_content)
                        except Exception as e2:
                            print(f"텍스트 JSON 파싱도 실패: {e2}")
                            columns_data = {'result': False}
                
                # 2. 실제 데이터 요청 (국토교통부 실제 API 형식)
                data_url = f"https://stat.molit.go.kr/portal/cate/getData.do?hFormId={form_id}&searchCondition=data&startPeriod={start_date}&endPeriod={end_date}"
                print(f"데이터 요청: {data_url}")
                
                async with session.get(data_url, headers=headers) as response:
                    print(f"데이터 응답 상태: {response.status}")
                    text_content = await response.text()
                    print(f"데이터 응답 내용 (처음 200자): {text_content[:200]}")
                    
                    try:
                        data_response = await response.json()
                    except Exception as e:
                        print(f"데이터 JSON 파싱 실패: {e}")
                        try:
                            import json
                            data_response = json.loads(text_content)
                        except Exception as e2:
                            print(f"텍스트 JSON 파싱도 실패: {e2}")
                            data_response = {'result': False}
                
                # 3. 데이터 구조화
                if columns_data.get('result') and data_response.get('result'):
                    return self._structure_api_data(columns_data.get('data', []), data_response.get('data', []))
                else:
                    print("API 응답 실패")
                    return {}
                    
        except Exception as e:
            print(f"API 데이터 추출 오류: {e}")
            return {}

    def _structure_api_data(self, columns: List[Dict], data_rows: List[Dict]) -> Dict[str, Any]:
        """API 응답 데이터를 구조화된 형태로 변환"""
        try:
            # 컬럼 헤더 매핑
            column_headers = {}
            for col in columns:
                col_id = str(col.get('DATA_DIV_ID', ''))
                col_name = col.get('DATA_DIV_NM', f'컬럼_{col_id}')
                column_headers[col_id] = col_name
            
            print(f"컬럼 헤더: {column_headers}")
            
            # 데이터 행 처리
            structured_data = {
                'headers': column_headers,
                'rows': [],
                'total_rows': len(data_rows),
                'summary': {}
            }
            
            for row in data_rows:
                structured_row = {}
                for key, value in row.items():
                    header_name = column_headers.get(key, f'컬럼_{key}')
                    structured_row[header_name] = value
                structured_data['rows'].append(structured_row)
            
            # 간단한 통계 요약
            if structured_data['rows']:
                first_row = structured_data['rows'][0]
                structured_data['summary'] = {
                    'period': first_row.get(column_headers.get('0', '기간'), ''),
                    'total_records': len(structured_data['rows']),
                    'columns': list(column_headers.values())
                }
            
            print(f"구조화된 데이터: {len(structured_data['rows'])}개 행")
            return structured_data
            
        except Exception as e:
            print(f"데이터 구조화 오류: {e}")
            return {}

    async def _get_form_id_from_url(self, stat_url: str) -> str:
        """URL에서 hFormId 추출"""
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(stat_url)
            params = parse_qs(parsed.query)
            form_id = params.get('hFormId', [''])[0]
            print(f"추출된 FormId: {form_id}")
            return form_id
        except Exception as e:
            print(f"FormId 추출 실패: {e}")
            return ""

    async def _collect_table_data_via_api(self, stat_url: str, table_info: Dict[str, Any], start_date: str, end_date: str) -> List[StatData]:
        """API를 통한 통계표 데이터 수집"""
        try:
            # URL에서 기본 FormId 추출
            base_form_id = await self._get_form_id_from_url(stat_url)
            
            # 통계표별 FormId 사용 (있으면)
            form_id = table_info.get('form_id', base_form_id)
            
            if not form_id:
                print(f"FormId를 찾을 수 없습니다: {table_info.get('name')}")
                return []
            
            print(f"API 데이터 수집 시작: {table_info.get('name')} (FormId: {form_id})")
            
            # 브라우저를 통해 쿠키/세션 확보 후 API 호출
            driver = self.browser_pool.get_browser()
            try:
                driver.get(stat_url)
                await asyncio.sleep(1)
                
                # API를 통한 데이터 추출
                api_data = await self._extract_data_via_api(driver, form_id, start_date, end_date)
                
                if not api_data or not api_data.get('rows'):
                    print(f"API 데이터 수집 실패: {table_info.get('name')}")
                    return []
                
                # StatData 객체로 변환 (올바른 모델 구조 사용)
                from datetime import datetime
                table_name = table_info.get('name', f'FormId_{form_id}')
                
                # API 데이터를 Dict 형태로 변환
                converted_data = {}
                data_count = 0
                
                for i, row in enumerate(api_data['rows']):
                    for header, value in row.items():
                        if value and str(value).strip():  # 빈 값 제외
                            key = f"{header}_{i}" if i > 0 else header
                            converted_data[key] = str(value)
                            data_count += 1
                
                # 단일 StatData 객체 생성 (기존 모델 구조에 맞게)
                current_year = datetime.now().year
                stat_data = StatData(
                    year=current_year,
                    data=converted_data,
                    table_name=table_name,
                    period_text=api_data['summary'].get('period', ''),
                    raw_data_count=data_count
                )
                
                print(f"API 데이터 수집 완료: {table_name} ({data_count}개 데이터)")
                return [stat_data]
                
            finally:
                self.browser_pool.return_browser(driver)
                
        except Exception as e:
            print(f"API 통계표 데이터 수집 오류: {e}")
            return []

    async def _extract_data_via_api_direct(self, form_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """직접 API 호출 (브라우저 세션 없이)"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # 1. 컬럼 정보 요청
                columns_url = f"https://stat.molit.go.kr/portal/stat/columns.do?formId={form_id}&styleNum=1"
                
                async with session.get(columns_url) as response:
                    if response.status != 200:
                        print(f"컬럼 API 호출 실패: {response.status}")
                        return {}
                    # content-type을 무시하고 강제로 JSON 파싱
                    try:
                        columns_data = await response.json()
                    except Exception:
                        # JSON 파싱 실패 시 텍스트로 받아서 JSON 변환 시도
                        text_content = await response.text()
                        import json
                        columns_data = json.loads(text_content)
                
                # 2. 데이터 요청
                data_url = f"https://stat.molit.go.kr/portal/stat/data.do?formId={form_id}&styleNum=1&apprYn=Y&startDate={start_date}&endDate={end_date}"
                
                async with session.get(data_url) as response:
                    if response.status != 200:
                        print(f"데이터 API 호출 실패: {response.status}")
                        return {}
                    # content-type을 무시하고 강제로 JSON 파싱
                    try:
                        data_response = await response.json()
                    except Exception:
                        # JSON 파싱 실패 시 텍스트로 받아서 JSON 변환 시도
                        text_content = await response.text()
                        import json
                        data_response = json.loads(text_content)
                
                # 3. 데이터 구조화
                if columns_data.get('result') and data_response.get('result'):
                    return self._structure_api_data(columns_data.get('data', []), data_response.get('data', []))
                else:
                    print(f"API 응답 실패: columns={columns_data.get('result')}, data={data_response.get('result')}")
                    return {}
                    
        except Exception as e:
            print(f"직접 API 호출 오류: {e}")
            return {}