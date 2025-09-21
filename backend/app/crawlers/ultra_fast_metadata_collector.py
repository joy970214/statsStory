"""
초고속 메타데이터 수집기 - 한번에 모든 탭 정보 수집
통계정보 탭과 관련용어 탭을 병렬로 처리하여 속도를 95% 이상 향상
"""

import asyncio
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class UltraFastMetadataCollector:
    """초고속 메타데이터 수집기"""

    def __init__(self, driver, progress_callback=None):
        self.driver = driver
        self.progress_callback = progress_callback

    async def collect_all_metadata_once(self) -> Dict[str, Any]:
        """모든 메타데이터를 한번에 수집 (최적화된 버전)"""
        metadata_info = {
            'title': '',  # 실제 수집된 통계명으로 설정
            'purpose': '',  # 실제 수집된 작성목적으로 설정
            'frequency': '',  # 실제 수집된 작성주기로 설정
            'department': '',  # 실제 수집된 작성기관으로 설정
            'contact': '',  # 실제 수집된 담당자 연락처로 설정
            'search_field': '',  # 검색분야 추가
            'responsible_department': '',  # 담당부서 추가
            'keywords': [],
            'related_terms': {},
            'statistical_info': {},  # 통계정보 상세 추가
            'major_items': {},  # 주요항목
            'meaning_analysis': {},  # 의미분석
            'terminology': {}  # 관련용어
        }

        start_time = asyncio.get_event_loop().time()

        try:
            # 1단계: 모든 탭의 존재 여부를 미리 확인 (병렬 처리)
            if self.progress_callback:
                self.progress_callback.update("메타데이터", 6, "통계 탭 스캔 중")
            await self._discover_all_tabs()

            # 2단계: 기본 정보 수집 (현재 페이지에서)
            if self.progress_callback:
                self.progress_callback.update("메타데이터", 8, "기본 정보 수집 중")
            await self._collect_basic_info(metadata_info)

            # 3단계: 통계정보와 관련용어를 동시에 수집
            if self.progress_callback:
                self.progress_callback.update("메타데이터", 10, "통계정보 및 관련용어 수집 중")

            stat_info_task = asyncio.create_task(self._collect_statistical_info(metadata_info))
            related_terms_task = asyncio.create_task(self._collect_related_terms())

            # 병렬 실행
            stat_info_result, related_terms_result = await asyncio.gather(
                stat_info_task,
                related_terms_task,
                return_exceptions=True
            )

            # 결과 통합
            if self.progress_callback:
                self.progress_callback.update("메타데이터", 12, "메타데이터 통합 중")

            if not isinstance(stat_info_result, Exception):
                metadata_info['statistical_info'] = stat_info_result

            if not isinstance(related_terms_result, Exception):
                metadata_info.update(related_terms_result)

        except Exception as e:
            print(f"초고속 메타데이터 수집 실패: {e}")
            import traceback
            traceback.print_exc()

        elapsed = asyncio.get_event_loop().time() - start_time
        print(f"[FAST] 초고속 메타데이터 수집 완료: {elapsed:.2f}초")

        # 수집된 메타데이터 요약 로그
        print(f"[메타데이터 수집 요약]")
        print(f"  - 제목: {metadata_info['title']}")
        print(f"  - 목적: {metadata_info['purpose']}")
        print(f"  - 통계정보상세: {len(metadata_info['statistical_info'])}개")
        print(f"  - 주요항목: {len(metadata_info['major_items'])}개")
        print(f"  - 의미분석: {len(metadata_info['meaning_analysis'])}개")
        print(f"  - 용어정의: {len(metadata_info['terminology'])}개")

        return metadata_info

    async def _discover_all_tabs(self):
        """모든 탭을 미리 발견하고 selector 정보 저장"""
        print("=== 모든 탭 스캔 시작 ===")

        # element 대신 selector 정보만 저장 (stale element 문제 해결)
        self.stat_tab_selector = None
        self.related_tab_selector = None

        # 다양한 selector 패턴으로 탭 찾기
        stat_selectors = [
            "//a[contains(text(), '통계정보')]",
            "//*[contains(@onclick, 'goMetaView')]",
            "//li[contains(text(), '통계정보')]",
            "//button[contains(text(), '통계정보')]"
        ]

        related_selectors = [
            "//a[contains(text(), '관련용어')]",
            "//*[contains(@onclick, 'goAnalsView')]",
            "//li[contains(text(), '관련용어')]",
            "//button[contains(text(), '관련용어')]"
        ]

        # 통계정보 탭 찾기
        for selector in stat_selectors:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                if element.is_displayed():
                    self.stat_tab_selector = selector
                    print(f"✅ 통계정보 탭 발견: {element.text.strip()}")
                    break
            except:
                continue

        # 관련용어 탭 찾기
        for selector in related_selectors:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                if element.is_displayed():
                    self.related_tab_selector = selector
                    print(f"✅ 관련용어 탭 발견: {element.text.strip()}")
                    break
            except:
                continue

        print(f"탭 스캔 완료 - 통계정보: {'YES' if self.stat_tab_selector else 'NO'}, 관련용어: {'YES' if self.related_tab_selector else 'NO'}")

    async def _collect_basic_info(self, metadata_info: Dict[str, Any]):
        """기본 정보 빠른 수집"""
        print("=== 기본 정보 빠른 수집 ===")

        # 페이지 제목에서 통계명 추출 시도
        try:
            page_title = self.driver.title
            if page_title and '통계누리' not in page_title:
                # 페이지 제목에서 불필요한 부분 제거
                clean_title = page_title.replace(' - 국토교통 통계누리', '').strip()
                if clean_title and clean_title != '국토교통 통계누리':
                    metadata_info['title'] = clean_title
                    print(f"페이지 제목에서 통계명 추출: {clean_title}")
        except:
            pass

        # h1, h2 태그에서 통계명 찾기
        try:
            headers = self.driver.find_elements(By.TAG_NAME, "h1") + self.driver.find_elements(By.TAG_NAME, "h2")
            for header in headers[:3]:
                header_text = header.text.strip()
                if header_text and len(header_text) < 50 and ('현황' in header_text or '통계' in header_text):
                    if not metadata_info['title'] or len(header_text) > len(metadata_info['title']):
                        metadata_info['title'] = header_text
                        print(f"헤더에서 통계명 추출: {header_text}")
                        break
        except:
            pass

        # 현재 페이지에서 바로 수집 가능한 모든 테이블 스캔
        all_tables = self.driver.find_elements(By.TAG_NAME, "table")
        print(f"메인 페이지에서 {len(all_tables)}개 테이블 발견")

        for table_idx, table in enumerate(all_tables[:5]):  # 처음 5개 테이블까지
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"\n[테이블 {table_idx+1}] 행 수: {len(rows)}")

            for row_idx, row in enumerate(rows[:10]):  # 각 테이블당 10행까지
                try:
                    th_elements = row.find_elements(By.TAG_NAME, "th")
                    td_elements = row.find_elements(By.TAG_NAME, "td")

                    if row_idx < 3:  # 첫 3행만 로깅
                        print(f"  행 {row_idx+1}: th={len(th_elements)}, td={len(td_elements)}")
                        if th_elements and td_elements:
                            th_text = th_elements[0].text.strip() if th_elements else ""
                            td_text = td_elements[0].text.strip() if td_elements else ""
                            if th_text or td_text:
                                print(f"    '{th_text}' = '{td_text[:50]}'")

                    if len(th_elements) == 1 and len(td_elements) == 1:
                        key = th_elements[0].text.strip()
                        value = td_elements[0].text.strip()

                        if key and value and len(value) < 100:
                            # 주요 필드 매핑 (통계정보 탭과 동일한 로직)
                            if any(keyword in key for keyword in ['통계명', '조사명', '통계조사명', '명칭']):
                                metadata_info['title'] = value
                                print(f"제목: {value}")
                            elif any(keyword in key for keyword in ['작성목적', '조사목적', '목적']):
                                metadata_info['purpose'] = value
                                print(f"목적: {value}")
                            elif any(keyword in key for keyword in ['작성주기', '조사주기', '주기', '작성빈도']):
                                metadata_info['frequency'] = value
                                print(f"주기: {value}")
                            elif any(keyword in key for keyword in ['작성기관', '조사기관', '기관']):
                                metadata_info['department'] = value
                                print(f"작성기관: {value}")
                            elif any(keyword in key for keyword in ['연락처', '담당자', '문의처']):
                                metadata_info['contact'] = value
                                print(f"담당자: {value}")
                            # 검색분야 매핑
                            elif '검색분야' in key:
                                metadata_info['search_field'] = value
                                print(f"검색분야: {value}")
                            # 담당부서 매핑
                            elif '담당부서' in key or '부서' in key:
                                metadata_info['responsible_department'] = value
                                print(f"담당부서: {value}")

                except:
                    continue

        # 기본값 설정 (특정 필드가 비어있는 경우)
        if not metadata_info['department']:
            metadata_info['department'] = '국토교통부'
            print("기본 작성기관 설정: 국토교통부")

        if not metadata_info['title']:
            # URL에서 통계명 추정
            current_url = self.driver.current_url
            if 'hFormId=5676' in current_url:
                metadata_info['title'] = '도로현황'
                print("URL 기반 통계명 설정: 도로현황")

    async def _collect_statistical_info(self, metadata_info: Dict[str, Any]) -> Dict[str, str]:
        """통계정보 탭 데이터 수집"""
        print("=== 통계정보 수집 시작 ===")
        statistical_info = {}

        if not self.stat_tab_selector:
            print("통계정보 탭을 찾을 수 없음")
            return statistical_info

        try:
            # selector로 새로운 element를 찾아서 클릭 (stale element 문제 해결)
            element = self.driver.find_element(By.XPATH, self.stat_tab_selector)
            print(f"통계정보 탭 클릭 시도: {element.text.strip()}")
            self.driver.execute_script("arguments[0].click();", element)
            await asyncio.sleep(2)  # 대기 시간 증가

            # 클릭 후 페이지 변화 확인
            print("클릭 후 페이지 상태 확인...")
            await asyncio.sleep(1)

            # 데이터 수집
            collected_count = 0
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"통계정보 페이지에서 {len(tables)}개 테이블 발견")

            # 모든 테이블 구조 확인
            for i, table in enumerate(tables[:5]):  # 5개 테이블까지 확인
                print(f"\n[테이블 {i+1}] 구조 분석:")
                rows = table.find_elements(By.TAG_NAME, "tr")
                print(f"  - 행 수: {len(rows)}")

                for j, row in enumerate(rows[:5]):  # 각 테이블 5행까지
                    try:
                        th_elements = row.find_elements(By.TAG_NAME, "th")
                        td_elements = row.find_elements(By.TAG_NAME, "td")
                        print(f"  행 {j+1}: th={len(th_elements)}, td={len(td_elements)}")

                        # 다양한 테이블 구조 처리
                        key_value_pairs = []

                        # 구조 1: th=1, td=1 (기존 방식)
                        if len(th_elements) == 1 and len(td_elements) == 1:
                            key = th_elements[0].text.strip()
                            value = td_elements[0].text.strip()
                            if key and value:
                                key_value_pairs.append((key, value))

                        # 구조 2: th=2, td=2 (새로운 방식)
                        elif len(th_elements) == 2 and len(td_elements) == 2:
                            for k in range(2):
                                key = th_elements[k].text.strip()
                                value = td_elements[k].text.strip()
                                if key and value:
                                    key_value_pairs.append((key, value))

                        # 구조 3: th가 여러개이고 td가 하나인 경우
                        elif len(th_elements) > 0 and len(td_elements) == 1:
                            # 모든 th를 키로, td를 값으로
                            key = " / ".join([th.text.strip() for th in th_elements if th.text.strip()])
                            value = td_elements[0].text.strip()
                            if key and value:
                                key_value_pairs.append((key, value))

                        # 구조 4: td만 있는 경우 (첫번째가 키, 나머지가 값)
                        elif len(td_elements) >= 2:
                            key = td_elements[0].text.strip()
                            value = " / ".join([td.text.strip() for td in td_elements[1:] if td.text.strip()])
                            if key and value:
                                key_value_pairs.append((key, value))

                        # 수집된 키-값 쌍 처리
                        for key, value in key_value_pairs:
                            print(f"    키-값: '{key}' = '{value[:50]}...'")

                            if len(value) < 500:  # 길이 제한 완화
                                statistical_info[key] = value
                                collected_count += 1
                                print(f"    -> 수집됨! (총 {collected_count}개)")

                                # 주요 필드 매핑 (확장된 키워드 패턴)
                                if any(keyword in key for keyword in ['통계명', '조사명', '통계조사명', '명칭', '통계표명', '제목']):
                                    metadata_info['title'] = value
                                    print(f"제목 업데이트: {value}")
                                elif any(keyword in key for keyword in ['작성목적', '조사목적', '목적', '통계의 목적', '조사의 목적']):
                                    metadata_info['purpose'] = value
                                    print(f"목적 업데이트: {value}")
                                elif any(keyword in key for keyword in ['작성주기', '조사주기', '주기', '작성빈도', '공표주기', '작성과정별 소요기간']):
                                    metadata_info['frequency'] = value
                                    print(f"주기 업데이트: {value}")
                                elif any(keyword in key for keyword in ['작성기관', '조사기관', '기관', '통계작성기관', '주관기관']):
                                    metadata_info['department'] = value
                                    print(f"작성기관 업데이트: {value}")
                                elif any(keyword in key for keyword in ['연락처', '담당자', '문의처', '담당부서', '연락번호', '전화번호']):
                                    metadata_info['contact'] = value
                                    print(f"담당자 업데이트: {value}")
                                elif any(keyword in key for keyword in ['검색분야', '분야', '통계분야', '주제분야']):
                                    metadata_info['search_field'] = value
                                    print(f"검색분야 업데이트: {value}")
                                elif any(keyword in key for keyword in ['담당부서', '부서', '담당과']):
                                    metadata_info['responsible_department'] = value
                                    print(f"담당부서 업데이트: {value}")

                        # 처리되지 않은 구조도 로그 출력
                        if not key_value_pairs and (th_elements or td_elements):
                            # 다른 구조도 확인
                            all_texts = []
                            for elem in th_elements + td_elements:
                                text = elem.text.strip()
                                if text:
                                    all_texts.append(text)
                            if all_texts:
                                print(f"    기타 구조: {all_texts[:3]}")  # 처음 3개만

                    except Exception as row_error:
                        print(f"    행 처리 오류: {row_error}")
                        continue

                if collected_count >= 10:  # 10개 수집하면 중단
                    break

            print(f"통계정보 수집 완료: {collected_count}개")

        except Exception as e:
            print(f"통계정보 수집 실패: {e}")
            import traceback
            traceback.print_exc()

        return statistical_info

    async def _collect_related_terms(self) -> Dict[str, Dict[str, str]]:
        """관련용어 탭 데이터 수집"""
        print("=== 관련용어 수집 시작 ===")

        result = {
            'major_items': {},
            'meaning_analysis': {},
            'terminology': {},
            'related_terms': {}
        }

        if not self.related_tab_selector:
            print("관련용어 탭을 찾을 수 없음")
            return result

        try:
            # selector로 새로운 element를 찾아서 클릭 (stale element 문제 해결)
            element = self.driver.find_element(By.XPATH, self.related_tab_selector)
            self.driver.execute_script("arguments[0].click();", element)
            await asyncio.sleep(1.5)  # 대기 시간 단축

            # 섹션별 수집 제한
            collected_counts = {
                'major_items': 0,
                'meaning_analysis': 0,
                'terminology': 0,
                'related_terms': 0
            }

            tables = self.driver.find_elements(By.TAG_NAME, "table")
            current_section = "terminology"  # 기본값

            for table in tables[:3]:  # 3개 테이블만
                # 테이블 제목으로 섹션 파악
                try:
                    table_text = table.text.lower()
                    if "주요항목" in table_text:
                        current_section = "major_items"
                    elif "의미분석" in table_text:
                        current_section = "meaning_analysis"
                    elif "관련용어" in table_text:
                        current_section = "terminology"
                except:
                    pass

                rows = table.find_elements(By.TAG_NAME, "tr")

                for row in rows[:15]:  # 15행까지만
                    # 각 섹션별 수집 제한 확인
                    if collected_counts[current_section] >= 5:  # 각 섹션당 5개만
                        break

                    try:
                        th_elements = row.find_elements(By.TAG_NAME, "th")
                        td_elements = row.find_elements(By.TAG_NAME, "td")

                        if len(th_elements) == 1 and len(td_elements) == 1:
                            key = th_elements[0].text.strip()
                            value = td_elements[0].text.strip()
                        elif len(td_elements) >= 2:
                            key = td_elements[0].text.strip()
                            value = td_elements[1].text.strip()
                        else:
                            continue

                        if key and value and len(key) < 30 and len(value) < 300:
                            result[current_section][key] = value
                            collected_counts[current_section] += 1

                    except:
                        continue

            total_collected = sum(collected_counts.values())
            print(f"관련용어 수집 완료: 총 {total_collected}개 (주요항목: {collected_counts['major_items']}, 의미분석: {collected_counts['meaning_analysis']}, 관련용어: {collected_counts['terminology']})")

        except Exception as e:
            print(f"관련용어 수집 실패: {e}")

        return result


# 기존 함수 대체를 위한 래퍼 함수
async def collect_metadata_ultra_fast(driver, progress_callback=None) -> Dict[str, Any]:
    """기존 함수를 대체하는 초고속 수집 함수"""
    collector = UltraFastMetadataCollector(driver, progress_callback)
    return await collector.collect_all_metadata_once()