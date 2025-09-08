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
        # 성능 최적화
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-logging')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(15)  # 페이지 로딩 시간 단축
        
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
    """진행률 콜백 인터페이스"""
    
    def __init__(self, callback_fn: Optional[Callable[[str, float, str], None]] = None):
        self.callback_fn = callback_fn
    
    def update(self, stage: str, progress: float, message: str):
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
            
            # sheet01 객체에서 데이터 가져오기
            try:
                # IBSheet의 데이터 행 수 확인
                row_count_script = """
                if (typeof sheet01 !== 'undefined' && sheet01.GetDataRowCount) {
                    return sheet01.GetDataRowCount();
                }
                return 0;
                """
                row_count = driver.execute_script(row_count_script)
                print(f"IBSheet 데이터 행 수: {row_count}")
                
                if row_count > 0:
                    # 컬럼 헤더 가져오기
                    col_script = """
                    if (typeof sheet01 !== 'undefined' && sheet01.GetColName) {
                        var cols = [];
                        try {
                            for (var i = 0; i < 10; i++) {  // 최대 10개 컬럼
                                var colName = sheet01.GetColName(i);
                                if (colName) cols.push(colName);
                            }
                        } catch(e) {}
                        return cols;
                    }
                    return [];
                    """
                    columns = driver.execute_script(col_script)
                    print(f"IBSheet 컬럼: {columns}")
                    
                    # 데이터 추출 (최대 10개 행)
                    for row in range(min(row_count, 10)):
                        for col_idx, col_name in enumerate(columns[:5]):  # 최대 5개 컬럼
                            try:
                                value_script = f"""
                                if (typeof sheet01 !== 'undefined' && sheet01.GetCellValue) {{
                                    return sheet01.GetCellValue({row}, {col_idx});
                                }}
                                return null;
                                """
                                value = driver.execute_script(value_script)
                                
                                if value is not None and str(value).strip():
                                    key = f"{col_name}_{row+1}" if row > 0 else col_name
                                    ibsheet_data[key] = await self._convert_cell_value_fast(str(value))
                                    
                            except Exception as e:
                                continue
                    
            except Exception as e:
                print(f"IBSheet 데이터 추출 오류: {e}")
            
            # 3. 생성된 HTML 테이블에서도 데이터 추출 (IBSheet가 HTML로 렌더링한 경우)
            try:
                # IBSheet가 생성한 테이블 찾기
                ibsheet_tables = driver.find_elements(By.CSS_SELECTOR, "[id*='sheet'], [class*='sheet'], .ibsheet")
                for table in ibsheet_tables:
                    try:
                        # 테이블 내의 셀 데이터 추출
                        cells = table.find_elements(By.CSS_SELECTOR, "td, .cell")[:20]  # 최대 20개 셀
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
            
            # 조건부 데이터 처리
            if table_info['is_regional'] or '시·군·구별' in table_info['name']:
                # _시도별, 시·군·구별: 현재 조회된 데이터 그대로 수집
                print(f"지역별 데이터 수집: {table_info['name']}")
                await self._click_search_button(driver)  # 조회 버튼 클릭
                return await self._extract_current_data(driver, table_info['name'])
                
            elif table_info['is_yearly'] or await self._should_use_date_range(driver):
                # _연도별이거나 조건에 맞으면 5년치 데이터 수집
                print(f"연도별/날짜범위 데이터 수집: {table_info['name']}")
                return await self._collect_data_with_date_range(driver, table_info['name'], date_format)
                
            else:
                # 기본 데이터 수집
                print(f"기본 데이터 수집: {table_info['name']}")
                await self._click_search_button(driver)  # 조회 버튼 클릭
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
            
            # StatData 객체로 변환
            stat_data_list = []
            for key, value in data_dict.items():
                stat_data = StatData(
                    category=table_name,
                    subcategory=key,
                    value=str(value),
                    unit="",
                    period=""
                )
                stat_data_list.append(stat_data)
            
            return stat_data_list
            
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