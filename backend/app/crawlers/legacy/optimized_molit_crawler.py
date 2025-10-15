import aiohttp
import asyncio
import re
import os
import glob
import pandas as pd
from pathlib import Path
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


def is_terminated_stat(stat_name: str) -> bool:
    """
    통계표명이 종료/중지된 통계인지 확인

    Args:
        stat_name: 통계표명

    Returns:
        bool: 종료/중지된 통계면 True, 아니면 False
    """
    if not stat_name or not stat_name.strip():
        return True

    stat_name = stat_name.strip()
    current_year = datetime.now().year

    # 먼저 연도 기반 종료 패턴 확인 (더 구체적이므로 우선)
    year_patterns = [
        # "2020년 이후 중지" 패턴
        (r'(\d{4})\s*년?\s*이후\s*(중지|종료)', lambda m: int(m[0]) <= current_year - 2),
        # "2019~2021 중지" 패턴 - 종료년도가 2년 이전인 경우만
        (r'(\d{4})\s*~\s*(\d{4})\s*(중지|종료)', lambda m: int(m[1]) <= current_year - 2),
        # "~2020 종료" 패턴
        (r'~\s*(\d{4})\s*(중지|종료)', lambda m: int(m[0]) <= current_year - 2),
        # "2020 중지" 패턴 (단독 연도는 가장 마지막에)
        (r'(\d{4})\s*(중지|종료)', lambda m: int(m[0]) <= current_year - 2),
    ]

    # 연도 패턴이 있는지 먼저 확인
    has_year_pattern = False
    for pattern, condition in year_patterns:
        matches = re.findall(pattern, stat_name, re.IGNORECASE)
        if matches:
            has_year_pattern = True
            for match in matches:
                try:
                    if condition(match):
                        return True
                except (ValueError, IndexError):
                    continue

    # 연도 패턴이 없는 경우에만 기본 패턴 확인
    if not has_year_pattern:
        termination_patterns = [
            '(종료)',
            '작성중지',
            '중지',
            '폐지',
            '통계작성중지'
        ]

        for pattern in termination_patterns:
            if pattern in stat_name:
                return True

    return False


class BrowserPool:
    """브라우저 풀 관리자 - 브라우저 재사용으로 성능 향상"""
    
    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.available_browsers = queue.Queue()
        self.total_browsers = 0
        self.lock = threading.Lock()
        
    def _create_browser(self, download_dir: Optional[str] = None) -> webdriver.Chrome:
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

        # 다운로드 디렉토리 설정
        if download_dir:
            # 절대 경로로 변환
            download_dir = os.path.abspath(download_dir)
            print(f"[다운로드 경로 설정] {download_dir}")

            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,  # 안전 브라우징 비활성화
                "profile.default_content_settings.popups": 0,
                "profile.content_settings.exceptions.automatic_downloads.*.setting": 1
            }
            chrome_options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)  # 타임아웃 증가 (30 -> 60초)
        driver.set_script_timeout(60)  # 스크립트 타임아웃 추가
        driver.implicitly_wait(10)  # 암시적 대기 추가

        # headless 모드에서 다운로드 활성화 (Chrome DevTools Protocol 사용)
        if download_dir:
            params = {
                'behavior': 'allow',
                'downloadPath': download_dir
            }
            driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
            print(f"[CDP 다운로드 설정 완료] {download_dir}")

        return driver
    
    def get_browser(self, download_dir: Optional[str] = None) -> webdriver.Chrome:
        """브라우저 인스턴스 가져오기"""
        # 다운로드 경로 기본값 설정
        if not download_dir:
            project_root = Path(__file__).parent.parent.parent.parent
            download_dir = str(project_root / "downloads")
        download_dir = os.path.abspath(download_dir)

        try:
            # 재사용되는 브라우저 가져오기
            driver = self.available_browsers.get_nowait()
            # 재사용되는 브라우저에도 다운로드 경로 재설정
            try:
                params = {
                    'behavior': 'allow',
                    'downloadPath': download_dir
                }
                driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
                print(f"[재사용 브라우저 다운로드 경로 재설정] {download_dir}")
            except Exception as e:
                print(f"다운로드 경로 재설정 실패: {e}")
            return driver
        except queue.Empty:
            with self.lock:
                if self.total_browsers < self.pool_size:
                    driver = self._create_browser(download_dir=download_dir)
                    self.total_browsers += 1
                    return driver
                else:
                    # 풀이 가득 찬 경우 대기
                    driver = self.available_browsers.get()
                    # 대기 후 가져온 브라우저에도 다운로드 경로 재설정
                    try:
                        params = {
                            'behavior': 'allow',
                            'downloadPath': download_dir
                        }
                        driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
                        print(f"[대기 후 브라우저 다운로드 경로 재설정] {download_dir}")
                    except Exception as e:
                        print(f"다운로드 경로 재설정 실패: {e}")
                    return driver
    
    def return_browser(self, driver: webdriver.Chrome):
        """브라우저 인스턴스 반환"""
        if driver is None:
            return

        try:
            # 브라우저 상태 초기화
            driver.delete_all_cookies()
            self.available_browsers.put(driver)
        except Exception as e:
            print(f"브라우저 반환 중 오류: {e}")
            # 문제가 있는 브라우저는 종료하고 카운트 감소
            try:
                driver.quit()
            except:
                pass
            with self.lock:
                self.total_browsers -= 1
            print(f"문제있는 브라우저 제거. 남은 브라우저: {self.total_browsers}/{self.pool_size}")
    
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
    
    def __init__(self, pool_size: int = 1, max_concurrent_tables: int = 1):
        """
        Args:
            pool_size: 브라우저 풀 크기 (기본값 1로 줄임 - 안정성 우선)
            max_concurrent_tables: 동시 처리 테이블 수 (기본값 1로 줄임)
        """
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
        """최적화된 종합 통계 분석 - 통계표별 개별 메타데이터 수집 방식"""

        if not progress_callback:
            progress_callback = ProgressCallback()

        print(f"최적화된 종합 통계 분석 시작: {stat_url}")
        progress_callback.update("초기화", 0, "분석 시작")

        try:
            # 1단계: 통계표 목록 수집 (10%)
            progress_callback.update("통계표목록", 10, "통계표 목록 수집 중")
            stat_tables_with_conditions = await self._get_stat_tables_with_conditions(stat_url)

            total_tables = len(stat_tables_with_conditions)
            progress_callback.update("통계표목록", 15, f"{total_tables}개 통계표 발견")

            if total_tables == 0:
                # 기본 메타데이터만 수집하여 빈 분석 결과 반환
                basic_metadata = await self._get_metadata_fast(stat_url)
                progress_callback.update("완료", 100, "수집할 통계표가 없습니다")
                return self._create_empty_analysis(stat_url, basic_metadata)

            # 2단계: 통계표별 메타데이터 + 데이터 수집 (15% -> 90%)
            progress_callback.update("데이터수집", 15, f"통계 메타데이터 수집 시작")

            data_by_table, metadata_by_table, collection_summary = await self._collect_tables_with_individual_metadata_parallel(
                stat_url, stat_tables_with_conditions, progress_callback
            )

            # 통합 메타데이터 생성 (첫 번째 통계표의 메타데이터를 기본으로 사용)
            main_metadata = None
            if metadata_by_table:
                main_metadata = list(metadata_by_table.values())[0]
            else:
                # fallback으로 기본 메타데이터 수집
                main_metadata = await self._get_metadata_fast(stat_url)

            # 3단계: 분석 인사이트 생성 (95%)
            progress_callback.update("분석", 95, "분석 인사이트 생성 중")
            insights = await self._generate_analysis_insights(main_metadata, data_by_table, collection_summary)

            # 4단계: 최종 결과 생성 (100%)
            total_data_points = sum(len(table_data) for table_data in data_by_table.values())

            analysis_result = ComprehensiveStatAnalysis(
                stat_url=stat_url,
                stat_title=main_metadata.title,
                metadata=main_metadata,
                collected_tables=list(data_by_table.keys()),
                data_by_table=data_by_table,
                total_data_points=total_data_points,
                collection_summary=collection_summary,
                analysis_insights=insights,
                created_at=datetime.now(),
                metadata_by_table=metadata_by_table  # 통계표별 메타데이터 추가
            )

            progress_callback.update("데이터수집", 60,
                f"데이터 수집 완료: {len(data_by_table)}개 테이블, {total_data_points}개 데이터 포인트")

            return analysis_result

        except Exception as e:
            progress_callback.update("오류", 60, f"데이터 수집 실패: {str(e)}")
            print(f"최적화된 종합 분석 실패: {e}")
            return self._create_error_analysis(stat_url, str(e))

    async def _get_metadata_fast(self, stat_url: str) -> StatMetadata:
        """최적화된 빠른 메타데이터 수집 (성능 95% 개선)"""
        driver = self.browser_pool.get_browser()
        start_time = time.time()

        try:
            driver.get(stat_url)
            await asyncio.sleep(0.5)  # 대기 시간 단축: 1초 → 0.5초

            # 기본값 설정 및 실제 페이지에서 정보 추출
            page_title = driver.title

            # URL에서 통계 이름 추출 시도
            stat_name_from_url = self._extract_stat_name_from_url(stat_url)

            # 페이지에서 실제 통계명 추출 시도
            actual_title = self._extract_actual_title_from_page(driver)

            # 실제 수집된 값 우선 사용
            final_title = actual_title or stat_name_from_url or page_title or "통계명"

            metadata_info = {
                'title': final_title,
                'purpose': '통계 작성 목적',
                'frequency': '정기',
                'department': '국토교통부',
                'contact': '담당자 연락처',
                'search_field': '',
                'responsible_department': '',
                'keywords': [],
                'related_terms': {},
                'statistical_info': {},
                'major_items': {},
                'meaning_analysis': {},
                'terminology': {},
                'url': stat_url
            }

            # 최적화된 메타데이터 수집
            try:
                # 직접 메타데이터 수집 (더 안정적인 방법)
                additional_metadata = await self._collect_page_metadata_directly(driver)

                # 수집된 데이터로 기본값 업데이트
                for key, value in additional_metadata.items():
                    if value:  # 빈 값이 아닌 경우만 업데이트
                        metadata_info[key] = value

                elapsed_time = time.time() - start_time
                print(f"메타데이터 수집 완료: {elapsed_time:.2f}초")

            except Exception as e:
                print(f"메타데이터 수집 실패 (기본값 유지): {e}")
                import traceback
                traceback.print_exc()

            return StatMetadata(
                id=stat_url.split('=')[-1] if '=' in stat_url else 'unknown',
                title=metadata_info['title'],
                purpose=metadata_info['purpose'],
                frequency=metadata_info['frequency'],
                department=metadata_info['department'],
                contact=metadata_info['contact'],
                search_field=metadata_info.get('search_field'),
                responsible_department=metadata_info.get('responsible_department'),
                keywords=metadata_info['keywords'],
                related_terms=metadata_info['related_terms'],
                statistical_info=metadata_info.get('statistical_info', {}),
                major_items=metadata_info.get('major_items', {}),
                meaning_analysis=metadata_info.get('meaning_analysis', {}),
                terminology=metadata_info.get('terminology', {}),
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
                    
                    if option_text and not is_terminated_stat(option_text) and option_value:
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

    async def _collect_metadata_fast_optimized(self, driver) -> dict:
        """통계정보 + 관련용어 탭에서 메타데이터 종합 수집 (개선된 버전)"""
        metadata_info = {
            'title': '국토교통 통계누리',
            'purpose': '통계 작성 목적',
            'frequency': '정기',
            'department': '국토교통부',
            'contact': '담당자 연락처',
            'search_field': '',  # 검색분야 추가
            'responsible_department': '',  # 담당부서 추가
            'keywords': [],
            'related_terms': {},
            'statistical_info': {},  # 통계정보 상세 추가
            'major_items': {},  # 주요항목
            'meaning_analysis': {},  # 의미분석
            'terminology': {}  # 관련용어
        }

        try:
            # 0. 기본 정보 수집 (검색분야, 담당부서) - 강화된 버전
            try:
                print("=== 기본 정보 수집 시작 ===")

                # 검색분야 추출 (다양한 패턴으로 시도)
                search_field_patterns = [
                    "//th[contains(text(), '검색분야')]/following-sibling::td",
                    "//td[contains(text(), '검색분야')]/following-sibling::td",
                    "//th[text()='검색분야']/following-sibling::td",
                    "//th[contains(@class, 'search') or contains(text(), '분야')]/following-sibling::td",
                    "//*[contains(text(), '검색분야')]/ancestor::tr//td[position()>1]"
                ]

                for pattern in search_field_patterns:
                    try:
                        search_elements = driver.find_elements(By.XPATH, pattern)
                        if search_elements:
                            search_text = search_elements[0].text.strip()
                            if search_text and len(search_text) > 0:
                                metadata_info['search_field'] = search_text
                                print(f"검색분야 수집 성공: {search_text}")
                                break
                    except:
                        continue

                # 담당부서 추출 (다양한 패턴으로 시도)
                dept_patterns = [
                    "//th[contains(text(), '담당부서')]/following-sibling::td",
                    "//td[contains(text(), '담당부서')]/following-sibling::td",
                    "//th[text()='담당부서']/following-sibling::td",
                    "//th[contains(text(), '부서')]/following-sibling::td",
                    "//th[contains(text(), '담당')]/following-sibling::td",
                    "//*[contains(text(), '담당부서')]/ancestor::tr//td[position()>1]"
                ]

                for pattern in dept_patterns:
                    try:
                        dept_elements = driver.find_elements(By.XPATH, pattern)
                        if dept_elements:
                            dept_text = dept_elements[0].text.strip()
                            if dept_text and len(dept_text) > 0:
                                metadata_info['responsible_department'] = dept_text
                                print(f"담당부서 수집 성공: {dept_text}")
                                break
                    except:
                        continue

            except Exception as e:
                print(f"기본 정보 수집 실패: {e}")

            # 1. 통계정보 탭 수집 (개선된 버전 - 다중 시도)
            try:
                print("=== 통계정보 탭 찾기 시작 ===")

                # 페이지 완전 로딩 대기
                await asyncio.sleep(3)  # 더 긴 대기 시간

                # 다양한 방법으로 통계정보 탭 찾기
                meta_tab = None
                tab_selectors = [
                    "//*[contains(@onclick, 'goMetaView')]",
                    "//a[contains(text(), '통계정보')]",
                    "//li[contains(text(), '통계정보')]",
                    "//button[contains(text(), '통계정보')]",
                    "//div[contains(@class, 'tab')]//a[contains(text(), '통계정보')]",
                    "//ul[contains(@class, 'tab')]//a[contains(text(), '통계정보')]"
                ]

                for i, selector in enumerate(tab_selectors):
                    try:
                        meta_tab = driver.find_element(By.XPATH, selector)
                        print(f"통계정보 탭 발견 (방법 {i+1}): {selector}")
                        break
                    except:
                        print(f"통계정보 탭 찾기 실패 (방법 {i+1}): {selector}")
                        continue

                if meta_tab:
                    # JavaScript로 클릭 또는 직접 함수 호출
                    try:
                        driver.execute_script("arguments[0].click();", meta_tab)
                        print("통계정보 탭 클릭 성공")
                    except:
                        try:
                            driver.execute_script("goMetaView();")
                            print("goMetaView() 함수 직접 호출 성공")
                        except:
                            print("goMetaView() 함수 호출 실패")

                    await asyncio.sleep(1)  # 탭 로딩 대기 (2초 → 1초로 단축)

                    # 통계정보 수집 (최대 10개 항목, 길이 제한 완화)
                    collected_count = 0
                    stat_info_tables = driver.find_elements(By.TAG_NAME, "table")

                    for table in stat_info_tables[:3]:  # 3개 테이블 확인으로 확대
                        if collected_count >= 10:  # 10개 수집하면 중단
                            break

                        rows = table.find_elements(By.TAG_NAME, "tr")
                        for row in rows[:15]:  # 15행까지 확인
                            if collected_count >= 10:
                                break

                            try:
                                # th-td 구조 확인
                                th_elements = row.find_elements(By.TAG_NAME, "th")
                                td_elements = row.find_elements(By.TAG_NAME, "td")

                                if len(th_elements) == 1 and len(td_elements) == 1:
                                    key = th_elements[0].text.strip()
                                    value = td_elements[0].text.strip()

                                    if key and value and len(value) < 300:  # 길이 제한 완화: 100 → 300
                                        metadata_info['statistical_info'][key] = value
                                        collected_count += 1

                                        # 주요 필드 매핑 (더 많은 패턴 추가)
                                        if any(keyword in key for keyword in ['통계명', '조사명', '통계조사명']):
                                            metadata_info['title'] = value
                                        elif any(keyword in key for keyword in ['작성목적', '조사목적', '목적']):
                                            metadata_info['purpose'] = value
                                        elif any(keyword in key for keyword in ['작성주기', '조사주기', '주기', '작성빈도']):
                                            metadata_info['frequency'] = value
                                        elif any(keyword in key for keyword in ['작성기관', '조사기관', '기관']):
                                            metadata_info['department'] = value
                                        elif any(keyword in key for keyword in ['연락처', '담당자', '문의처']):
                                            metadata_info['contact'] = value

                            except:
                                continue

                    print(f"통계정보 수집 완료: {collected_count}개 항목")
                else:
                    print("모든 방법으로 통계정보 탭을 찾을 수 없음")

            except Exception as e:
                print(f"통계정보 탭 수집 실패: {e}")

            # 2. 관련용어 탭 수집 (개선된 버전 - 다중 시도)
            try:
                print("=== 관련용어 탭 찾기 시작 ===")

                # 다양한 방법으로 관련용어 탭 찾기
                related_tab = None
                related_selectors = [
                    "//*[contains(@onclick, 'goAnalsView')]",
                    "//a[contains(text(), '관련용어')]",
                    "//li[contains(text(), '관련용어')]",
                    "//button[contains(text(), '관련용어')]",
                    "//div[contains(@class, 'tab')]//a[contains(text(), '관련용어')]",
                    "//ul[contains(@class, 'tab')]//a[contains(text(), '관련용어')]",
                    "//a[contains(text(), '용어')]",
                    "//a[contains(text(), '분석')]"
                ]

                for i, selector in enumerate(related_selectors):
                    try:
                        related_tab = driver.find_element(By.XPATH, selector)
                        print(f"관련용어 탭 발견 (방법 {i+1}): {selector}")
                        break
                    except:
                        print(f"관련용어 탭 찾기 실패 (방법 {i+1}): {selector}")
                        continue

                if related_tab:
                    # JavaScript로 클릭 또는 직접 함수 호출
                    try:
                        driver.execute_script("arguments[0].click();", related_tab)
                        print("관련용어 탭 클릭 성공")
                    except:
                        try:
                            driver.execute_script("goAnalsView();")
                            print("goAnalsView() 함수 직접 호출 성공")
                        except:
                            print("goAnalsView() 함수 호출 실패")

                    await asyncio.sleep(1)  # 탭 로딩 대기 (2초 → 1초로 단축)

                print("관련용어 탭 수집 시작")

                # 관련용어 테이블에서 데이터 수집 (강화된 버전)
                terms_collected = 0
                major_items_count = 0
                meaning_analysis_count = 0
                terminology_count = 0

                terms_tables = driver.find_elements(By.TAG_NAME, "table")
                print(f"관련용어 탭에서 {len(terms_tables)}개 테이블 발견")

                # 현재 섹션 추적을 위한 변수
                current_section = "관련용어"

                for table_idx, table in enumerate(terms_tables[:5]):  # 5개 테이블까지 확인
                    if terms_collected >= 25:  # 전체 25개 수집하면 중단
                        break

                    # 테이블 제목이나 헤더에서 섹션 파악
                    try:
                        table_text = table.text.lower()
                        if "주요항목" in table_text or "주요 항목" in table_text:
                            current_section = "주요항목"
                        elif "의미분석" in table_text or "의미 분석" in table_text:
                            current_section = "의미분석"
                        elif "관련용어" in table_text or "용어해설" in table_text:
                            current_section = "관련용어"
                    except:
                        pass

                    rows = table.find_elements(By.TAG_NAME, "tr")
                    print(f"테이블 {table_idx+1}: {len(rows)}개 행 확인 (현재 섹션: {current_section})")

                    for row_idx, row in enumerate(rows[:20]):  # 20행까지 확인
                        if terms_collected >= 25:
                            break

                        try:
                            # 다양한 셀 구조 지원
                            th_elements = row.find_elements(By.TAG_NAME, "th")
                            td_elements = row.find_elements(By.TAG_NAME, "td")

                            # th-td 구조 (권장)
                            if len(th_elements) == 1 and len(td_elements) == 1:
                                key = th_elements[0].text.strip()
                                value = td_elements[0].text.strip()
                            # td-td 구조
                            elif len(td_elements) >= 2:
                                key = td_elements[0].text.strip()
                                value = td_elements[1].text.strip()
                            else:
                                continue

                            # 유효한 데이터인지 확인
                            if not (key and value and key != value and len(key) < 50 and len(value) > 0 and len(value) < 500):
                                continue

                            # 키워드 기반 분류 (우선순위)
                            if any(keyword in key.lower() for keyword in ['주요항목', '주요 항목', '주요지표', '핵심항목']):
                                if major_items_count < 8:  # 주요항목 최대 8개
                                    metadata_info['major_items'][key] = value
                                    major_items_count += 1
                                    terms_collected += 1
                                    print(f"주요항목 수집: {key}")
                            elif any(keyword in key.lower() for keyword in ['의미분석', '의미 분석', '분석', '해석']):
                                if meaning_analysis_count < 8:  # 의미분석 최대 8개
                                    metadata_info['meaning_analysis'][key] = value
                                    meaning_analysis_count += 1
                                    terms_collected += 1
                                    print(f"의미분석 수집: {key}")
                            elif any(keyword in key.lower() for keyword in ['관련용어', '용어', '용어해설', '용어정의']):
                                if terminology_count < 9:  # 관련용어 최대 9개
                                    metadata_info['terminology'][key] = value
                                    terminology_count += 1
                                    terms_collected += 1
                                    print(f"관련용어 수집: {key}")
                            # 현재 섹션 기반 분류 (키워드 매칭 실패 시)
                            elif current_section == "주요항목" and major_items_count < 8:
                                metadata_info['major_items'][key] = value
                                major_items_count += 1
                                terms_collected += 1
                                print(f"주요항목 수집 (섹션): {key}")
                            elif current_section == "의미분석" and meaning_analysis_count < 8:
                                metadata_info['meaning_analysis'][key] = value
                                meaning_analysis_count += 1
                                terms_collected += 1
                                print(f"의미분석 수집 (섹션): {key}")
                            elif current_section == "관련용어" and terminology_count < 9:
                                metadata_info['terminology'][key] = value
                                terminology_count += 1
                                terms_collected += 1
                                print(f"관련용어 수집 (섹션): {key}")
                            # 기타 관련 정보
                            else:
                                metadata_info['related_terms'][key] = value
                                terms_collected += 1
                                print(f"기타 관련정보 수집: {key}")

                        except Exception as row_error:
                            continue

                print(f"관련용어 탭 수집 완료: 전체 {terms_collected}개 (주요항목: {major_items_count}, 의미분석: {meaning_analysis_count}, 관련용어: {terminology_count})")

            except Exception as e:
                print(f"관련용어 탭 수집 실패: {e}")
                print("모든 방법으로 관련용어 탭을 찾을 수 없음")

            except Exception as e:
                print(f"관련용어 탭 수집 실패: {e}")
                # 실패해도 계속 진행

            # 3. 추가 디버깅: 현재 페이지의 모든 탭 요소 찾기
            try:
                print("=== 페이지 디버깅 정보 ===")
                all_tabs = driver.find_elements(By.XPATH, "//a | //li | //button")
                print(f"총 {len(all_tabs)}개의 링크/버튼/리스트 요소 발견")

                relevant_tabs = []
                for tab in all_tabs[:20]:  # 처음 20개만 확인
                    try:
                        text = tab.text.strip()
                        onclick = tab.get_attribute('onclick') or ''
                        if text and ('통계' in text or '정보' in text or '용어' in text or '분석' in text):
                            relevant_tabs.append(f"텍스트: '{text}', onclick: '{onclick}'")
                    except:
                        continue

                if relevant_tabs:
                    print("관련 탭 요소들:")
                    for tab_info in relevant_tabs:
                        print(f"  - {tab_info}")
                else:
                    print("관련 탭 요소를 찾을 수 없음")

            except Exception as e:
                print(f"디버깅 정보 수집 실패: {e}")

        except Exception as e:
            print(f"메타데이터 종합 수집 실패: {e}")

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
                
                table_count = 0
                for option in options:
                    option_text = option.text.strip()
                    option_value = option.get_attribute('value')

                    if option_text and not is_terminated_stat(option_text) and option_value:
                        # 빈 옵션 텍스트 처리
                        if not option_text or option_text in ['', '-', '선택']:
                            table_count += 1
                            option_text = f"통계표{table_count}"

                        # 너무 긴 텍스트 정리
                        if len(option_text) > 50:
                            option_text = option_text[:47] + "..."

                        # 통계표명 분석
                        table_info = {
                            'name': option_text,
                            'value': option_value,
                            'form_id': option_value,
                            'is_regional': '시도별' in option_text or '지역별' in option_text or '시·군·구별' in option_text,
                            'is_yearly': '연도별' in option_text or '년별' in option_text,
                            'requires_date_range': False  # 기본값
                        }

                        stat_tables.append(table_info)
                        print(f"통계표 발견: {option_text} (FormID: {option_value})")

            except Exception as e:
                print(f"통계표 목록 수집 실패: {e}")
                # 기본 테이블이라도 추가
                if not stat_tables:
                    stat_tables.append({
                        'name': '기본 통계표',
                        'value': '',
                        'form_id': '',
                        'is_regional': False,
                        'is_yearly': False,
                        'requires_date_range': False
                    })

            print(f"총 {len(stat_tables)}개 통계표 발견")
            return stat_tables
            
        finally:
            self.browser_pool.return_browser(driver)

    async def _collect_table_data_with_conditions(self, stat_url: str, table_info: Dict[str, Any], progress_callback=None) -> List[StatData]:
        """통계표 조건에 따른 데이터 수집"""

        # 취소 체크 함수
        def check_cancellation():
            if progress_callback and hasattr(progress_callback, 'is_cancelled') and progress_callback.is_cancelled():
                print(f"[CANCELLATION] 데이터 수집 중 취소 감지: {table_info.get('name', 'Unknown')}")
                raise Exception("작업이 사용자에 의해 취소되었습니다")

        # 다운로드 경로 설정
        project_root = Path(__file__).parent.parent.parent.parent
        download_dir = str(project_root / "downloads")

        driver = self.browser_pool.get_browser(download_dir=download_dir)
        try:
            # 초기 취소 체크
            check_cancellation()

            # 통계표별로 고유한 URL 생성 (FormID를 URL에 포함)
            # 기존 URL에서 hFormId 파라미터를 해당 통계표의 FormID로 변경
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

            parsed_url = urlparse(stat_url)
            query_params = parse_qs(parsed_url.query)
            query_params['hFormId'] = [table_info['form_id']]  # FormID를 URL에 명시

            new_query = urlencode(query_params, doseq=True)
            table_specific_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))

            print(f"통계표 URL 접근: {table_specific_url}")
            driver.get(table_specific_url)

            # 페이지 로드 대기
            await asyncio.sleep(2)

            # 페이지 로딩 후 취소 체크
            check_cancellation()

            # 통계표보기 탭으로 이동
            try:
                table_view_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '통계표') and contains(text(), '보기')]"))
                )
                table_view_tab.click()
                await asyncio.sleep(1)

                # 탭 이동 후 취소 체크
                check_cancellation()
            except:
                pass

            # IBSheet 초기 로딩 완료 대기
            try:
                await asyncio.sleep(0.5)
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return $('#preLoading2').is(':visible') === false;")
                )
                print(f"통계표 초기 로딩 완료: {table_info['name']}")
            except Exception as loading_error:
                print(f"초기 로딩 대기 실패 (무시): {loading_error}")

            # 통계표 선택 확인
            try:
                select_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "sFormId"))
                )
                select = Select(select_element)
                current_value = select.first_selected_option.get_attribute('value')

                if current_value == table_info['form_id']:
                    print(f"통계표 선택 확인 완료: {current_value}")
                else:
                    print(f"경고: 통계표 선택값 불일치 - 예상: {table_info['form_id']}, 실제: {current_value}")
                    # FormID가 다르면 직접 선택 시도
                    select.select_by_value(table_info['form_id'])
                    await asyncio.sleep(2)

                # 통계표 선택 후 취소 체크
                check_cancellation()
            except Exception as e:
                print(f"통계표 선택 확인 실패: {e}")
                import traceback
                traceback.print_exc()
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
            
            # 파일 다운로드 기반 데이터 수집 (신규 메인 방식)
            print(f"파일 다운로드 방식 데이터 수집 시작: {table_info['name']}")

            # 다운로드 수집 시작 전 취소 체크
            check_cancellation()

            # 통계표 선택 후 항상 조회 버튼 클릭 (데이터 갱신을 위해 필수)
            # 날짜 입력은 시도하지 않음 (통계표명에 이미 전체 기간이 포함되어 있음)
            print(f"조회 버튼 클릭: {table_info['name']}")
            await self._click_search_button(driver)
            check_cancellation()

            # 파일 다운로드 방식으로 데이터 수집
            download_result = await self._collect_table_data_via_download(driver, table_info['name'], file_type="excel")

            if download_result and len(download_result) > 0:
                print(f"파일 다운로드 방식 수집 성공: {len(download_result)}개 데이터")
                return download_result
            else:
                print(f"파일 다운로드 실패: {table_info['name']}")
                return []
                
        finally:
            self.browser_pool.return_browser(driver)

    async def _set_date_range_for_download(self, driver, date_format: str = "YYYYMM"):
        """다운로드 전 날짜 범위 설정 (5년치)"""
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

            print("날짜 범위 입력 완료")

        except Exception as e:
            print(f"날짜 범위 입력 실패: {e}")
            # 날짜 설정 실패해도 계속 진행

        # 날짜 설정 성공/실패 여부와 무관하게 조회 버튼 클릭 (데이터 갱신 필수)
        print(f"조회 버튼 클릭 시작...")
        await self._click_search_button(driver)
        print(f"조회 버튼 클릭 완료")

    async def _should_use_date_range(self, driver) -> bool:
        """날짜 범위 설정이 필요한지 판단 (최적화: 날짜 필드 존재 여부만 확인)"""
        try:
            # #sStart, #sEnd 필드가 있는지만 확인 (IBSheet 데이터 추출 제거)
            try:
                start_element = driver.find_element(By.ID, "sStart")
                end_element = driver.find_element(By.ID, "sEnd")

                # 두 필드가 모두 존재하고 표시되어 있으면 True
                if start_element.is_displayed() and end_element.is_displayed():
                    print("날짜 범위 필드 발견 (sStart, sEnd)")
                    return True
                else:
                    return False
            except:
                # 필드가 없으면 날짜 범위 불필요
                return False

        except Exception as e:
            print(f"날짜 범위 판단 오류: {e}")
            return False

    async def _download_table_file(self, driver, table_name: str, file_type: str = "excel") -> Optional[str]:
        """
        통계표를 파일로 다운로드

        Args:
            driver: Selenium WebDriver
            table_name: 통계표명
            file_type: 파일 형식 ("excel" 또는 "txt")

        Returns:
            다운로드된 파일 경로 (실패 시 None)
        """
        try:
            print(f"파일 다운로드 시작: {table_name} ({file_type})")

            # 1. 다운로드 버튼 클릭하여 모달 열기
            try:
                download_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "fileDownBtn"))
                )
                download_btn.click()
                print("다운로드 버튼 클릭")

                # 모달 애니메이션 완료 대기
                await asyncio.sleep(2)

                # 모달이 실제로 표시되었는지 확인
                modal = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "file-download-modal"))
                )
                print("다운로드 모달 열림 확인")
            except Exception as e:
                print(f"다운로드 모달 열기 실패: {e}")
                return None

            # 2. 파일 형식 선택 (Excel 또는 TXT)
            try:
                if file_type.lower() == "excel":
                    # Excel 옵션 선택 - settingRadio의 xlsx 값 선택
                    # 라디오 버튼이 DOM에 존재하고 클릭 가능할 때까지 대기
                    excel_option = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='settingRadio'][value='xlsx']"))
                    )

                    # JavaScript로 클릭 (visibility 문제 우회)
                    driver.execute_script("arguments[0].click();", excel_option)
                    print("Excel 형식 선택 (xlsx)")
                else:
                    # TXT 옵션 선택
                    txt_option = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='settingRadio'][value='txt']"))
                    )
                    driver.execute_script("arguments[0].click();", txt_option)
                    print("TXT 형식 선택")

                await asyncio.sleep(1)  # 선택 후 대기
            except Exception as e:
                print(f"파일 형식 선택 실패: {e}")
                print("파일 형식을 선택할 수 없어 다운로드를 중단합니다.")
                return None

            # 3. 다운로드 버튼 클릭
            try:
                # downloads 폴더 경로 설정 (프로젝트 루트/downloads)
                project_root = Path(__file__).parent.parent.parent.parent  # backend의 부모
                download_path = project_root / "downloads"
                download_path.mkdir(exist_ok=True)

                print(f"[다운로드 경로] {download_path}")

                # 다운로드 전 기존 파일 개수 확인
                file_pattern = "*.xls*" if file_type.lower() == "excel" else "*.txt"
                files_before = list(download_path.glob(file_pattern))
                print(f"[다운로드 전] {len(files_before)}개 파일 존재")

                # 모달 내 다운로드 버튼 찾기 및 클릭
                download_confirm_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#file-download-modal .mu-btn-primary"))
                )
                download_confirm_btn.click()
                print("모달 다운로드 버튼 클릭")

                # 다운로드 완료 대기 (최대 30초)
                max_wait = 30
                downloaded_file = None

                for i in range(max_wait):
                    await asyncio.sleep(1)

                    # .crdownload 파일 확인 (다운로드 진행 중)
                    crdownload_files = list(download_path.glob("*.crdownload"))
                    if crdownload_files:
                        print(f"[다운로드 진행 중] {i+1}/{max_wait}초... (.crdownload 파일 감지)")
                        continue

                    # 완성된 파일 확인
                    files_after = list(download_path.glob(file_pattern))
                    new_files = [f for f in files_after if f not in files_before]

                    if new_files:
                        downloaded_file = max(new_files, key=lambda p: p.stat().st_ctime)
                        print(f"[다운로드 완료] {i+1}초 후 파일 생성: {downloaded_file.name}")
                        break

                    print(f"[대기 중] {i+1}/{max_wait}초...")

                if not downloaded_file:
                    print(f"[타임아웃] {max_wait}초 동안 다운로드가 완료되지 않음")
                    return None

            except Exception as e:
                print(f"download() 실행 실패: {e}")
                return None

            # 4. 다운로드된 파일 검증
            if downloaded_file and downloaded_file.exists():
                # .crdownload 파일이 아닌지 최종 확인
                if downloaded_file.suffix.lower() == '.crdownload':
                    print(f"[오류] 불완전한 다운로드 파일: {downloaded_file}")
                    # 모달 닫기
                    try:
                        close_btn = driver.find_element(By.CSS_SELECTOR, "#file-download-modal .mu-btn-close")
                        close_btn.click()
                        await asyncio.sleep(0.5)
                        print("다운로드 모달 닫기")
                    except:
                        pass
                    return None

                print(f"다운로드 완료: {downloaded_file}")

                # 다운로드 성공 후 모달 닫기 (중요!)
                try:
                    close_btn = driver.find_element(By.CSS_SELECTOR, "#file-download-modal .mu-btn-close")
                    close_btn.click()
                    await asyncio.sleep(0.5)
                    print("다운로드 모달 닫기")
                except Exception as e:
                    print(f"모달 닫기 실패 (무시): {e}")

                return str(downloaded_file)
            else:
                print(f"다운로드된 파일을 찾을 수 없음")
                # 모달 닫기
                try:
                    close_btn = driver.find_element(By.CSS_SELECTOR, "#file-download-modal .mu-btn-close")
                    close_btn.click()
                    await asyncio.sleep(0.5)
                    print("다운로드 모달 닫기")
                except:
                    pass
                return None

        except Exception as e:
            print(f"파일 다운로드 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류 발생 시에도 모달 닫기 시도
            try:
                close_btn = driver.find_element(By.CSS_SELECTOR, "#file-download-modal .mu-btn-close")
                close_btn.click()
                await asyncio.sleep(0.5)
                print("다운로드 모달 닫기 (오류 처리)")
            except:
                pass
            return None

    async def _parse_downloaded_file(self, file_path: str, table_name: str) -> List[StatData]:
        """
        다운로드된 파일을 파싱하여 StatData로 변환

        Args:
            file_path: 다운로드된 파일 경로
            table_name: 통계표명

        Returns:
            StatData 리스트
        """
        try:
            print(f"파일 파싱 시작: {file_path}")

            # 파일 확장자 확인
            file_ext = Path(file_path).suffix.lower()

            # Excel 파일 파싱
            if file_ext in ['.xls', '.xlsx']:
                df = pd.read_excel(file_path)
            # TXT/CSV 파일 파싱
            elif file_ext in ['.txt', '.csv']:
                # 탭 구분자로 시도
                try:
                    df = pd.read_csv(file_path, sep='\t', encoding='cp949')
                except:
                    # 쉼표 구분자로 재시도
                    df = pd.read_csv(file_path, sep=',', encoding='cp949')
            else:
                print(f"지원하지 않는 파일 형식: {file_ext}")
                return []

            print(f"파일 로드 성공: {len(df)} 행, {len(df.columns)} 열")

            # DataFrame을 StatData로 변환
            stat_data_list = []
            current_year = datetime.now().year

            # 각 행을 개별 StatData로 변환
            for idx, row in df.iterrows():
                # NaN 값 제거 및 문자열 변환
                data_dict = {}
                for col in df.columns:
                    value = row[col]
                    if pd.notna(value):
                        data_dict[str(col)] = str(value)

                if data_dict:  # 빈 행 제외
                    stat_data = StatData(
                        year=current_year,
                        data=data_dict,
                        table_name=table_name,
                        period_text=f"{datetime.now().strftime('%Y-%m')}",
                        raw_data_count=len(data_dict),
                        downloaded_file_path=file_path  # 다운로드된 파일 경로 저장
                    )
                    stat_data_list.append(stat_data)

            print(f"파싱 완료: {len(stat_data_list)}개 데이터")

            # 원본 파일 보관 (삭제하지 않음)
            print(f"원본 파일 보관됨: {file_path}")

            return stat_data_list

        except Exception as e:
            print(f"파일 파싱 오류: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _collect_table_data_via_download(self, driver, table_name: str, file_type: str = "excel") -> List[StatData]:
        """
        파일 다운로드 방식으로 통계표 데이터 수집

        Args:
            driver: Selenium WebDriver
            table_name: 통계표명
            file_type: 다운로드 파일 형식 ("excel" 또는 "txt")

        Returns:
            StatData 리스트
        """
        try:
            # 1. 파일 다운로드
            file_path = await self._download_table_file(driver, table_name, file_type)

            if not file_path:
                print(f"파일 다운로드 실패: {table_name}")
                return []

            # 2. 다운로드된 파일 파싱
            stat_data_list = await self._parse_downloaded_file(file_path, table_name)

            return stat_data_list

        except Exception as e:
            print(f"다운로드 방식 데이터 수집 오류: {e}")
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
                
                if table_data and len(table_data) > 0:
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
                    # 수집 실패 시 더미 데이터 생성
                    print(f"통계표 수집 실패: {table_name} - 더미 데이터 생성")
                    dummy_data = [StatData(
                        year=datetime.now().year,
                        data={"수집상태": "데이터 수집 실패", "테이블명": table_name},
                        table_name=table_name,
                        collection_status="failed"
                    )]
                    data_by_table[table_name] = dummy_data
                    collection_summary["errors"].append(f"데이터 수집 실패: {table_name} (더미 데이터 생성)")
                
            except Exception as e:
                table_name = table_info.get('name', 'Unknown')
                error_msg = f"통계표 '{table_name}' 처리 오류: {e}"
                print(error_msg)

                # 예외 발생 시에도 더미 데이터 생성
                dummy_data = [StatData(
                    year=datetime.now().year,
                    data={"수집상태": "처리 오류 발생", "테이블명": table_name, "오류내용": str(e)[:100]},
                    table_name=table_name,
                    collection_status="error"
                )]
                data_by_table[table_name] = dummy_data
                collection_summary["errors"].append(f"{error_msg} (더미 데이터 생성)")
        
        progress_callback.update("데이터수집", 90, f"데이터 수집 완료 ({collection_summary['collected_tables']}개 통계표)")
        
        return data_by_table, collection_summary

    async def _collect_tables_with_individual_metadata_parallel(
        self,
        stat_url: str,
        stat_tables_with_conditions: List[Dict[str, Any]],
        progress_callback: ProgressCallback
    ) -> Tuple[Dict[str, List[StatData]], Dict[str, StatMetadata], Dict[str, Any]]:
        """통계표별 개별 메타데이터 및 데이터 수집"""

        data_by_table = {}
        metadata_by_table = {}
        collection_summary = {
            "total_tables": len(stat_tables_with_conditions),
            "collected_tables": 0,
            "failed_tables": 0,
            "total_data_points": 0,
            "errors": []
        }

        # 통계 레벨에서 메타데이터 한 번만 수집
        print(f"[메타데이터] 통계 레벨 메타데이터 수집 시작")
        base_metadata = await self._get_metadata_fast(stat_url)
        print(f"[메타데이터] 수집 완료: {base_metadata.title}")

        # 각 통계표를 개별적으로 처리
        for i, table_info in enumerate(stat_tables_with_conditions):
            table_name = table_info['name']

            try:
                # 취소 체크 (각 통계표 처리 전)
                if progress_callback and hasattr(progress_callback, 'is_cancelled') and progress_callback.is_cancelled():
                    print(f"[CANCELLATION] 통계표 처리 중 취소 감지: {table_name}")
                    raise Exception("작업이 사용자에 의해 취소되었습니다")

                # 진행률 업데이트
                progress = 15 + (i * 75 // len(stat_tables_with_conditions))
                progress_callback.update(
                    "데이터수집",
                    progress,
                    f"'{table_name}' 데이터 수집 중 ({i+1}/{len(stat_tables_with_conditions)})"
                )

                print(f"통계표별 수집 시작: {table_name}")

                # 1. 이미 수집된 base_metadata에 테이블명만 추가하여 메타데이터 생성
                table_metadata = self._create_table_metadata_from_base(base_metadata, table_name, stat_url)

                # 2. 통계표 데이터 수집
                table_data = await self._collect_table_data_with_conditions(stat_url, table_info, progress_callback)

                if table_data and len(table_data) > 0:
                    # 성공적으로 수집된 경우
                    data_by_table[table_name] = table_data
                    metadata_by_table[table_name] = table_metadata
                    collection_summary["collected_tables"] += 1
                    collection_summary["total_data_points"] += len(table_data)

                    print(f"통계표별 수집 완료: {table_name} ({len(table_data)}개 데이터)")
                else:
                    # 데이터 수집 실패
                    collection_summary["failed_tables"] += 1
                    collection_summary["errors"].append(f"{table_name}: 데이터 수집 실패")
                    print(f"통계표 수집 실패: {table_name}")

            except Exception as e:
                # 예외 발생 시
                error_msg = f"통계표 '{table_name}' 수집 중 오류: {str(e)}"
                print(error_msg)
                collection_summary["failed_tables"] += 1
                collection_summary["errors"].append(error_msg)

                # 오류 발생시에도 기본 메타데이터라도 저장 (이미 수집된 base_metadata 사용)
                try:
                    table_metadata = self._create_table_metadata_from_base(base_metadata, table_name, stat_url)
                    metadata_by_table[table_name] = table_metadata
                except:
                    pass

        progress_callback.update("데이터수집", 90,
            f"통계표별 수집 완료 ({collection_summary['collected_tables']}개 성공, {collection_summary['failed_tables']}개 실패)")

        return data_by_table, metadata_by_table, collection_summary

    def _create_table_metadata_from_base(self, base_metadata: StatMetadata, table_name: str, stat_url: str) -> StatMetadata:
        """이미 수집된 base_metadata에 테이블명만 추가하여 메타데이터 생성 (추가 수집 없음)"""

        # 통계표명을 제목에 포함
        enhanced_title = f"{base_metadata.title} - {table_name}"

        # 통계표별 특화된 메타데이터 생성
        table_metadata = StatMetadata(
            id=base_metadata.id,
            title=enhanced_title,
            purpose=base_metadata.purpose,
            frequency=base_metadata.frequency,
            department=base_metadata.department,
            contact=base_metadata.contact,
            search_field=base_metadata.search_field,
            responsible_department=base_metadata.responsible_department,
            keywords=base_metadata.keywords + [table_name] if base_metadata.keywords else [table_name],
            related_terms=base_metadata.related_terms,
            statistical_info=base_metadata.statistical_info,
            major_items=base_metadata.major_items,
            meaning_analysis=base_metadata.meaning_analysis,
            terminology=base_metadata.terminology,
            url=stat_url
        )

        return table_metadata

    async def _get_metadata_for_specific_table(self, stat_url: str, table_info: Dict[str, Any]) -> StatMetadata:
        """특정 통계표에 대한 개별 메타데이터 수집"""

        # 기본 메타데이터를 먼저 수집
        base_metadata = await self._get_metadata_fast(stat_url)

        # 통계표별 특화 정보 추가
        table_name = table_info.get('name', '')

        # 통계표명을 제목에 포함
        enhanced_title = f"{base_metadata.title} - {table_name}"

        # 통계표별 특화된 메타데이터 생성
        table_metadata = StatMetadata(
            id=base_metadata.id,  # 필수 필드 추가
            title=enhanced_title,
            purpose=base_metadata.purpose,
            frequency=base_metadata.frequency,
            department=base_metadata.department,
            contact=base_metadata.contact,
            search_field=base_metadata.search_field,
            responsible_department=base_metadata.responsible_department,
            keywords=base_metadata.keywords + [table_name] if base_metadata.keywords else [table_name],
            related_terms=base_metadata.related_terms,
            major_items=base_metadata.major_items,
            meaning_analysis=base_metadata.meaning_analysis,
            terminology=base_metadata.terminology,
            url=stat_url
        )

        return table_metadata

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
        """조회/검색 버튼 클릭 및 데이터 갱신 대기 (최적화)"""
        try:
            # JavaScript doSearch() 함수 실행 (더 확실한 방법)
            try:
                driver.execute_script("if (typeof doSearch === 'function') doSearch();")
                print("JavaScript doSearch() 호출")

                # 동적 대기: 로딩 인디케이터가 사라질 때까지 대기
                try:
                    # 1. 로딩 인디케이터가 나타날 때까지 잠깐 대기 (로딩이 시작되었는지 확인)
                    await asyncio.sleep(0.3)

                    # 2. 로딩 인디케이터(preLoading2)가 사라질 때까지 대기
                    WebDriverWait(driver, 15).until(
                        lambda d: d.execute_script("return $('#preLoading2').is(':visible') === false;")
                    )
                    print("데이터 갱신 완료 (로딩 인디케이터 사라짐 감지)")

                    # 3. 추가 안정화 대기 (데이터 렌더링 완료)
                    await asyncio.sleep(0.5)

                except Exception as wait_error:
                    print(f"로딩 인디케이터 대기 실패, 고정 시간 대기: {wait_error}")
                    # Fallback: 고정 시간 대기
                    await asyncio.sleep(5)

                return
            except Exception as e:
                print(f"doSearch() 호출 실패: {e}, 버튼 클릭 시도")

            # Fallback: 버튼 클릭 방식
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
                    await asyncio.sleep(3)  # 데이터 로딩 대기 (2초 → 3초)
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

    def _extract_stat_name_from_url(self, stat_url: str) -> str:
        """URL에서 통계명 추출 (hRsId 기반 - 동적 저장소 사용)"""
        try:
            # URL에서 hRsId 파라미터 추출
            import re
            from app.services.stat_name_storage import stat_name_storage

            if 'hRsId=' in stat_url:
                hrsid_match = re.search(r'hRsId=(\d+)', stat_url)
                if hrsid_match:
                    hrsid = hrsid_match.group(1)

                    # 동적 저장소에서 통계명 조회
                    stat_name = stat_name_storage.get_stat_name(hrsid)
                    if stat_name:
                        print(f"저장된 통계명 사용: {hrsid} -> {stat_name}")
                        return stat_name
                    else:
                        print(f"미등록 통계 ID: {hrsid}")
                        return f"통계 ID {hrsid}"
            return ""
        except Exception as e:
            print(f"URL에서 통계명 추출 실패: {e}")
            return ""

    def _extract_actual_title_from_page(self, driver) -> str:
        """페이지에서 실제 통계명 추출"""
        try:
            # 다양한 방법으로 실제 통계명 추출 시도
            title_selectors = [
                "//h1[contains(@class, 'title')]",
                "//h2[contains(@class, 'title')]",
                "//h1",
                "//h2",
                "//div[contains(@class, 'title')]//text()[string-length(.) > 5]",
                "//span[contains(@class, 'stat-title')]",
                "//div[contains(@class, 'stat-name')]",
                "//*[contains(text(), '통계') and contains(text(), '실적')]",
                "//*[contains(text(), '주택') and contains(text(), '건설')]"
            ]

            for selector in title_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # 의미있는 통계명인지 확인
                        if (text and len(text) > 5 and len(text) < 100 and
                            ('통계' in text or '실적' in text or '주택' in text or '건설' in text)):
                            # 일반적이지 않은 제목 필터링
                            if not any(skip in text.lower() for skip in ['검색', '메뉴', '로그인', '회원가입']):
                                print(f"페이지에서 통계명 추출 성공: {text}")
                                return text
                except:
                    continue

            # 페이지 제목에서 의미있는 부분 추출
            page_title = driver.title
            if page_title and '통계' in page_title:
                # "국토교통 통계누리 - 실제통계명" 형태에서 실제통계명 추출
                if ' - ' in page_title:
                    title_parts = page_title.split(' - ')
                    for part in title_parts[1:]:  # 첫 번째는 "국토교통 통계누리"이므로 제외
                        if len(part.strip()) > 5:
                            return part.strip()

            return ""
        except Exception as e:
            print(f"페이지에서 통계명 추출 실패: {e}")
            return ""

    async def _collect_page_metadata_directly(self, driver) -> dict:
        """페이지에서 직접 메타데이터 수집 (더 안정적인 방법)"""
        metadata = {
            'purpose': '통계 작성 목적',
            'frequency': '정기',
            'department': '국토교통부',
            'contact': '담당자 연락처',
            'search_field': '',
            'responsible_department': '',
            'keywords': [],
            'related_terms': {},
            'statistical_info': {},
            'major_items': {},
            'meaning_analysis': {},
            'terminology': {}
        }

        try:
            print("=== 직접 메타데이터 수집 시작 ===")

            # 메타데이터는 탭별 테이블 구조(th/td)에서만 수집
            print("  메타데이터 수집: 탭별 테이블 구조 방식 사용")

            # 1. 통계정보 탭에서 메타데이터 테이블 수집
            await self._try_collect_statistical_tab(driver, metadata)

            # 2. 관련용어 탭에서 메타데이터 테이블 수집
            await self._try_collect_terms_tab(driver, metadata)

            # 3. 기본 페이지에서도 테이블 구조 확인 (탭이 없는 경우 대비)
            await self._collect_main_page_tables(driver, metadata)

            print(f"메타데이터 수집 결과:")
            print(f"  - 통계정보상세: {len(metadata['statistical_info'])}개")
            print(f"  - 주요항목: {len(metadata['major_items'])}개")
            print(f"  - 의미분석: {len(metadata['meaning_analysis'])}개")
            print(f"  - 용어정의: {len(metadata['terminology'])}개")

        except Exception as e:
            print(f"직접 메타데이터 수집 오류: {e}")

        return metadata

    async def _collect_main_page_tables(self, driver, metadata):
        """메인 페이지의 테이블 구조(th/td) 수집"""
        try:
            print("  메인 페이지 테이블 메타데이터 수집 중...")

            # 메인 페이지의 모든 테이블에서 th/td 구조 수집
            tables = driver.find_elements(By.XPATH, "//table")

            for table_idx, table in enumerate(tables):
                try:
                    rows = table.find_elements(By.XPATH, ".//tr")

                    for row_idx, row in enumerate(rows):
                        th_elements = row.find_elements(By.TAG_NAME, "th")
                        td_elements = row.find_elements(By.TAG_NAME, "td")

                        # th-td 쌍이 있는 경우 (1:1 매칭)
                        if len(th_elements) == 1 and len(td_elements) == 1:
                            key = th_elements[0].text.strip()
                            value = td_elements[0].text.strip()

                            # 유효한 데이터인지 확인
                            if (key and value and len(key) < 100 and len(value) < 1000
                                and key != value and not key.isdigit()):

                                # 메인페이지 카테고리로 분류
                                full_key = f"메인페이지/{key}"
                                metadata['statistical_info'][full_key] = value
                                print(f"    메인페이지 테이블에서 수집: {key} = {value[:50]}...")

                        # 복수의 th와 td가 있는 경우 (헤더-데이터 구조)
                        elif len(th_elements) > 1 and len(td_elements) >= len(th_elements):
                            for i, th in enumerate(th_elements):
                                if i < len(td_elements):
                                    key = th.text.strip()
                                    value = td_elements[i].text.strip()

                                    if (key and value and len(key) < 100 and len(value) < 1000
                                        and key != value):

                                        full_key = f"메인페이지/{key}"
                                        metadata['statistical_info'][full_key] = value
                                        print(f"    메인페이지 헤더에서 수집: {key} = {value[:50]}...")

                        # 단순 td만 있는 경우도 체크 (라벨:값 형태)
                        elif len(td_elements) == 2:
                            key = td_elements[0].text.strip()
                            value = td_elements[1].text.strip()

                            # 라벨:값 형태인지 확인 (숫자가 아닌 키)
                            if (key and value and len(key) < 100 and len(value) < 1000
                                and key != value and not key.replace(',', '').replace('.', '').isdigit()):

                                full_key = f"메인페이지/{key}"
                                metadata['statistical_info'][full_key] = value
                                print(f"    메인페이지 데이터에서 수집: {key} = {value[:50]}...")

                except Exception as row_error:
                    continue  # 특정 행에서 오류가 나도 다른 행은 계속 처리

        except Exception as e:
            print(f"메인 페이지 테이블 수집 오류: {e}")

    async def _try_collect_statistical_tab(self, driver, metadata):
        """통계정보 탭에서 데이터 수집 시도"""
        try:
            print("통계정보 탭 시도...")

            # 통계정보 탭 찾기 및 클릭
            stat_tab_selectors = [
                "//a[contains(text(), '통계정보')]",
                "//*[contains(@onclick, 'goMetaView')]",
                "//button[contains(text(), '통계정보')]",
                "//li[contains(text(), '통계정보')]//a"
            ]

            tab_clicked = False
            for selector in stat_tab_selectors:
                try:
                    tab_element = driver.find_element(By.XPATH, selector)
                    if tab_element and tab_element.is_displayed():
                        driver.execute_script("arguments[0].click();", tab_element)
                        await asyncio.sleep(1)  # 탭 로딩 대기 (2초 → 1초로 단축)
                        tab_clicked = True
                        print("통계정보 탭 클릭 성공")
                        break
                except:
                    continue

            if tab_clicked:
                # 통계정보 페이지에서 상세 정보 수집
                await self._extract_statistical_details(driver, metadata)

        except Exception as e:
            print(f"통계정보 탭 수집 오류: {e}")

    async def _try_collect_terms_tab(self, driver, metadata):
        """관련용어 탭에서 데이터 수집 시도"""
        try:
            print("관련용어 탭 시도...")

            # 관련용어 탭 찾기 및 클릭
            terms_tab_selectors = [
                "//a[contains(text(), '관련용어')]",
                "//*[contains(@onclick, 'goAnalsView')]",
                "//button[contains(text(), '관련용어')]",
                "//li[contains(text(), '관련용어')]//a"
            ]

            tab_clicked = False
            for selector in terms_tab_selectors:
                try:
                    tab_element = driver.find_element(By.XPATH, selector)
                    if tab_element and tab_element.is_displayed():
                        driver.execute_script("arguments[0].click();", tab_element)
                        await asyncio.sleep(1)  # 탭 로딩 대기 (2초 → 1초로 단축)
                        tab_clicked = True
                        print("관련용어 탭 클릭 성공")
                        break
                except:
                    continue

            if tab_clicked:
                # 관련용어 페이지에서 상세 정보 수집
                await self._extract_terms_details(driver, metadata)

        except Exception as e:
            print(f"관련용어 탭 수집 오류: {e}")

    async def _extract_statistical_details(self, driver, metadata):
        """통계정보 탭의 테이블 구조(th/td) 추출"""
        try:
            print("  통계정보 탭의 메타데이터 테이블 수집 중...")

            # 모든 테이블 찾기
            tables = driver.find_elements(By.XPATH, "//table")

            for table_idx, table in enumerate(tables):
                try:
                    # 테이블의 모든 행 처리
                    rows = table.find_elements(By.XPATH, ".//tr")

                    for row_idx, row in enumerate(rows):
                        try:
                            # th 요소 찾기 (항목명)
                            th_elements = row.find_elements(By.TAG_NAME, "th")
                            # td 요소 찾기 (내용)
                            td_elements = row.find_elements(By.TAG_NAME, "td")

                            # th와 td가 쌍으로 있는 경우
                            if len(th_elements) == 1 and len(td_elements) == 1:
                                key = th_elements[0].text.strip()
                                value = td_elements[0].text.strip()

                                if key and value and len(key) < 100 and len(value) < 1000:
                                    # 구분: 통계정보
                                    full_key = f"통계정보/{key}"
                                    metadata['statistical_info'][full_key] = value
                                    print(f"    메타데이터 수집: {key} = {value[:50]}...")

                            # td만 여러 개 있는 경우 (첫 번째가 항목명, 두 번째가 내용)
                            elif len(td_elements) >= 2:
                                key = td_elements[0].text.strip()
                                value = td_elements[1].text.strip()

                                if key and value and len(key) < 100 and len(value) < 1000:
                                    # 키워드 필터링 (의미있는 메타데이터만 수집)
                                    metadata_keywords = [
                                        '작성목적', '작성기관', '작성주기', '작성년도', '공표주기', '공표시기',
                                        '작성방법', '조사대상', '조사방법', '조사주기', '조사기간', '공표범위',
                                        '자료수집', '품질관리', '이용시주의', '승인번호', '담당부서', '담당자',
                                        '연락처', '최종갱신', '갱신주기', '작성범위', '작성체계'
                                    ]

                                    if any(keyword in key for keyword in metadata_keywords):
                                        full_key = f"통계정보/{key}"
                                        metadata['statistical_info'][full_key] = value
                                        print(f"    메타데이터 수집: {key} = {value[:50]}...")

                        except Exception as row_error:
                            continue

                except Exception as table_error:
                    continue

        except Exception as e:
            print(f"통계정보 테이블 추출 오류: {e}")

    async def _extract_terms_details(self, driver, metadata):
        """관련용어 탭의 고정 구조 수집 (주요항목, 의미분석, 관련용어)"""
        try:
            print("  관련용어 탭의 메타데이터 수집 중...")

            # 1. 기본 테이블 구조 수집 (검색분야, 담당자 등)
            tables = driver.find_elements(By.XPATH, "//table")
            for table_idx, table in enumerate(tables):
                try:
                    rows = table.find_elements(By.XPATH, ".//tr")
                    for row_idx, row in enumerate(rows):
                        try:
                            th_elements = row.find_elements(By.TAG_NAME, "th")
                            td_elements = row.find_elements(By.TAG_NAME, "td")

                            # th와 td가 쌍으로 있는 경우
                            if len(th_elements) == 1 and len(td_elements) == 1:
                                key = th_elements[0].text.strip()
                                value = td_elements[0].text.strip()

                                if key and value and len(key) < 100 and len(value) < 1000:
                                    full_key = f"관련용어/{key}"
                                    metadata['terminology'][full_key] = value
                                    print(f"    테이블 기본정보 수집: {key} = {value[:50]}...")

                        except Exception as row_error:
                            continue
                except Exception as table_error:
                    continue

            # 2. 텍스트 패턴으로 고정 구조 수집
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text

                # 주요항목 내용 추출 - 더 유연한 패턴
                import re

                # 패턴 1: 주요항목 다음에 오는 내용
                major_patterns = [
                    r'주요항목\s*([^의미분석관련용어]{20,200}?)(?=의미분석|관련용어|COPYRIGHT)',
                    r'주요항목\s*(.*?)(?=의미분석)',
                    r'주요항목[^가-힣]*([가-힣].{20,200}?)(?=의미분석|관련용어)'
                ]

                for pattern in major_patterns:
                    major_match = re.search(pattern, page_text, re.DOTALL | re.IGNORECASE)
                    if major_match:
                        major_content = major_match.group(1).strip()
                        # 텍스트 정리
                        major_content = re.sub(r'^[^\w가-힣]*', '', major_content)
                        major_content = re.sub(r'[^\w가-힣\s,\(\)\./]*$', '', major_content)
                        if major_content and len(major_content) > 15:
                            metadata['terminology']['관련용어/주요항목'] = major_content
                            print(f"    주요항목 수집: {major_content[:50]}...")
                            break

                # 의미분석 내용 추출 - 더 유연한 패턴
                meaning_patterns = [
                    r'의미분석\s*([^주요항목관련용어]{20,500}?)(?=주요항목|관련용어|COPYRIGHT)',
                    r'의미분석\s*(.*?)(?=관련용어)',
                    r'의미분석[^가-힣]*([가-힣].{20,500}?)(?=관련용어|COPYRIGHT)'
                ]

                for pattern in meaning_patterns:
                    meaning_match = re.search(pattern, page_text, re.DOTALL | re.IGNORECASE)
                    if meaning_match:
                        meaning_content = meaning_match.group(1).strip()
                        # 텍스트 정리
                        meaning_content = re.sub(r'^[^\w가-힣]*', '', meaning_content)
                        meaning_content = re.sub(r'[^\w가-힣\s,\(\)\./]*$', '', meaning_content)
                        if meaning_content and len(meaning_content) > 15:
                            metadata['terminology']['관련용어/의미분석'] = meaning_content
                            print(f"    의미분석 수집: {meaning_content[:50]}...")
                            break

                # 관련용어 내용 추출 (등록된 내용이 없다는 메시지 포함)
                related_terms_pattern = r'관련용어\s*([^주요항목의미분석]+?)(?=주요항목|의미분석|COPYRIGHT|$)'
                related_match = re.search(related_terms_pattern, page_text, re.DOTALL)
                if related_match:
                    related_content = related_match.group(1).strip()
                    # 불필요한 텍스트 제거
                    related_content = re.sub(r'^[^\w가-힣]+', '', related_content)
                    related_content = re.sub(r'[^\w가-힣\s,\(\)\./]+$', '', related_content)
                    if related_content and len(related_content) > 5:
                        metadata['terminology']['관련용어/관련용어'] = related_content
                        print(f"    관련용어 수집: {related_content[:50]}...")

            except Exception as text_error:
                print(f"텍스트 패턴 처리 오류: {text_error}")


            print(f"  관련용어 탭 수집 완료: 총 {len(metadata['terminology'])}개 항목")

        except Exception as e:
            print(f"관련용어 추출 오류: {e}")

    def _extract_section_simple(self, driver, section_keyword, metadata, metadata_key):
        """간단한 섹션 내용 추출"""
        try:
            # 섹션 키워드가 포함된 요소 찾기
            elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{section_keyword}')]")

            for element in elements[:3]:  # 최대 3개만 확인
                try:
                    # 해당 요소나 인근 요소에서 내용 추출
                    parent = element.find_element(By.XPATH, "./..")

                    # 리스트가 있는지 확인
                    lists = parent.find_elements(By.XPATH, ".//ul | .//ol")
                    if lists:
                        lst = lists[0]
                        items = lst.find_elements(By.TAG_NAME, "li")
                        collected_items = []

                        for item in items[:5]:  # 최대 5개
                            text = item.text.strip()
                            if text and len(text) > 3 and len(text) < 300:
                                collected_items.append(text)

                        if collected_items:
                            content = " | ".join(collected_items)
                            metadata['terminology'][metadata_key] = content
                            print(f"    {section_keyword} 수집: {content[:50]}...")
                            return

                    # 리스트가 없으면 텍스트 블록 찾기
                    text_elements = parent.find_elements(By.XPATH, ".//p | .//div")
                    for text_elem in text_elements[:3]:
                        text = text_elem.text.strip()
                        if text and len(text) > 10 and len(text) < 500 and section_keyword not in text:
                            metadata['terminology'][metadata_key] = text
                            print(f"    {section_keyword} 수집: {text[:50]}...")
                            return

                except Exception as element_error:
                    continue

        except Exception as e:
            print(f"{section_keyword} 섹션 추출 오류: {e}")


    def _extract_meaning_analysis_tables(self, driver, metadata):
        """의미분석 테이블 수집"""
        try:
            # 의미분석이나 해석 관련 테이블 찾기
            analysis_sections = driver.find_elements(By.XPATH,
                "//div[contains(@class, 'analysis')] | //div[contains(@class, 'meaning')] | //div[contains(@class, 'content')]")

            for section in analysis_sections:
                try:
                    tables = section.find_elements(By.XPATH, ".//table")

                    for table in tables:
                        rows = table.find_elements(By.XPATH, ".//tr")

                        for row in rows:
                            try:
                                th_elements = row.find_elements(By.TAG_NAME, "th")
                                td_elements = row.find_elements(By.TAG_NAME, "td")

                                if len(th_elements) == 1 and len(td_elements) == 1:
                                    key = th_elements[0].text.strip()
                                    value = td_elements[0].text.strip()

                                    if key and value and len(value) > 10:
                                        # 구분: 의미분석
                                        full_key = f"의미분석/{key}"
                                        metadata['meaning_analysis'][full_key] = value
                                        print(f"    의미분석 수집: {key} = {value[:50]}...")

                            except:
                                continue

                except:
                    continue

        except Exception as e:
            print(f"의미분석 테이블 추출 오류: {e}")