#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""관련용어 탭의 실제 HTML 구조 확인 테스트"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.optimized_molit_crawler import OptimizedMolitCrawler
import time
from selenium.webdriver.common.by import By

async def test_related_terms_structure():
    """관련용어 탭의 HTML 구조 분석"""

    # 자동차관리사업자업체현황분기 통계 URL
    stat_url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=437&hFormId=4392&hDivEng=&month_yn="

    print("=== 관련용어 탭 HTML 구조 분석 ===")
    print(f"URL: {stat_url}")
    print()

    try:
        crawler = OptimizedMolitCrawler(pool_size=1, max_concurrent_tables=1)
        driver = crawler.browser_pool.get_browser()

        print("1. 페이지 로딩 중...")
        driver.get(stat_url)
        time.sleep(3)

        print("2. 관련용어 탭 찾기...")
        # 관련용어 탭 찾기
        tab_patterns = [
            "//a[contains(text(), '관련용어')]",
            "//li[contains(text(), '관련용어')]//a",
            "//span[contains(text(), '관련용어')]//parent::a",
            "//*[contains(@class, 'tab') and contains(text(), '관련용어')]",
            "//a[@href='#tab4']"  # 일반적인 4번째 탭
        ]

        related_terms_tab = None
        for pattern in tab_patterns:
            try:
                elements = driver.find_elements(By.XPATH, pattern)
                if elements:
                    related_terms_tab = elements[0]
                    print(f"  관련용어 탭 발견: {pattern}")
                    break
            except:
                continue

        if not related_terms_tab:
            print("  ❌ 관련용어 탭을 찾을 수 없습니다.")

            # 사용 가능한 모든 탭 출력
            print("\n사용 가능한 탭들:")
            all_tabs = driver.find_elements(By.XPATH, "//a[contains(@href, '#tab') or contains(@class, 'tab')]")
            for i, tab in enumerate(all_tabs):
                try:
                    print(f"  {i+1}. {tab.text.strip()} - href: {tab.get_attribute('href')}")
                except:
                    continue

            # 모든 링크 텍스트 확인
            print("\n모든 링크 텍스트:")
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for i, link in enumerate(all_links):
                try:
                    text = link.text.strip()
                    if text and ('용어' in text or '관련' in text):
                        print(f"  관련용어 후보 {i+1}: '{text}' - href: {link.get_attribute('href')}")
                except:
                    continue

            return

        print("3. 관련용어 탭 클릭...")
        driver.execute_script("arguments[0].click();", related_terms_tab)
        time.sleep(2)

        print("4. 관련용어 탭 내용 구조 분석...")

        # 활성화된 탭 컨텐츠 찾기
        content_selectors = [
            "#tab4",  # 일반적인 4번째 탭 내용
            ".tab-content.active",
            "[id*='tab'][class*='active']",
            ".tab-pane.active"
        ]

        tab_content = None
        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and elements[0].is_displayed():
                    tab_content = elements[0]
                    print(f"  활성 탭 내용 발견: {selector}")
                    break
            except:
                continue

        if not tab_content:
            print("  활성 탭 내용을 특정할 수 없어 전체 페이지에서 분석...")
            tab_content = driver.find_element(By.TAG_NAME, "body")

        # 관련용어 영역의 구조 분석
        print("\n=== 관련용어 영역 구조 분석 ===")

        # 1. 테이블 구조 확인
        print("\n1. 테이블 구조:")
        tables = tab_content.find_elements(By.TAG_NAME, "table")
        print(f"  테이블 개수: {len(tables)}")

        for i, table in enumerate(tables):
            print(f"\n  테이블 {i+1}:")
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"    행 개수: {len(rows)}")

            for j, row in enumerate(rows[:3]):  # 처음 3개 행만
                try:
                    ths = row.find_elements(By.TAG_NAME, "th")
                    tds = row.find_elements(By.TAG_NAME, "td")
                    print(f"    행 {j+1}: th={len(ths)}개, td={len(tds)}개")

                    if ths:
                        th_texts = [th.text.strip() for th in ths]
                        print(f"      th 내용: {th_texts}")
                    if tds:
                        td_texts = [td.text.strip()[:50] for td in tds]
                        print(f"      td 내용: {td_texts}")
                except Exception as e:
                    print(f"    행 {j+1}: 분석 실패 - {e}")

        # 2. 리스트 구조 확인
        print("\n2. 리스트 구조:")
        lists = tab_content.find_elements(By.XPATH, ".//ul | .//ol | .//dl")
        print(f"  리스트 개수: {len(lists)}")

        for i, lst in enumerate(lists):
            try:
                items = lst.find_elements(By.XPATH, ".//li | .//dt | .//dd")
                print(f"  리스트 {i+1}: {lst.tag_name}, 항목 {len(items)}개")

                for j, item in enumerate(items[:3]):  # 처음 3개만
                    text = item.text.strip()
                    print(f"    항목 {j+1}: {item.tag_name} - {text[:50]}...")
            except Exception as e:
                print(f"  리스트 {i+1}: 분석 실패 - {e}")

        # 3. 일반 텍스트 블록 확인
        print("\n3. 텍스트 블록:")
        text_elements = tab_content.find_elements(By.XPATH, ".//p | .//div[text()]")
        print(f"  텍스트 블록 개수: {len(text_elements)}")

        for i, elem in enumerate(text_elements[:5]):  # 처음 5개만
            try:
                text = elem.text.strip()
                if text and len(text) > 10:  # 의미있는 텍스트만
                    print(f"  블록 {i+1}: {elem.tag_name} - {text[:100]}...")
            except:
                continue

        # 4. 전체 HTML 구조 샘플
        print("\n4. 관련용어 영역 HTML 샘플:")
        try:
            html_sample = tab_content.get_attribute('innerHTML')
            # HTML을 줄바꿈과 함께 정리해서 출력
            import re
            html_sample = re.sub(r'>\s*<', '>\n<', html_sample)
            lines = html_sample.split('\n')
            for i, line in enumerate(lines[:20]):  # 처음 20줄만
                if line.strip():
                    print(f"    {i+1:2d}: {line.strip()[:100]}...")
        except Exception as e:
            print(f"  HTML 샘플 추출 실패: {e}")

        crawler.browser_pool.return_browser(driver)

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_related_terms_structure())