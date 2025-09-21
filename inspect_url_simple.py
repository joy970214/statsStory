#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""실제 URL 구조 간단 검토"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.optimized_molit_crawler import OptimizedMolitCrawler
import time
from selenium.webdriver.common.by import By

async def inspect_url_simple():
    """실제 URL 구조 간단 검토"""

    stat_url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=437&hFormId=4392&hDivEng=&month_yn="

    print("=== 자동차관리사업자업체현황분기 URL 검토 ===")
    print(f"URL: {stat_url}")
    print()

    try:
        crawler = OptimizedMolitCrawler(pool_size=1, max_concurrent_tables=1)
        driver = crawler.browser_pool.get_browser()

        print("1. 페이지 로딩...")
        driver.get(stat_url)
        time.sleep(3)

        print("2. 관련용어 탭 클릭...")
        # 관련용어 탭 클릭
        related_terms_tab = driver.find_element(By.XPATH, "//a[contains(text(), '관련용어')]")
        driver.execute_script("arguments[0].click();", related_terms_tab)
        time.sleep(2)

        print("3. 페이지 전체 텍스트에서 키워드 확인...")
        body_text = driver.find_element(By.TAG_NAME, "body").text

        keywords = ["주요항목", "의미분석", "관련용어", "등록된", "없습니다"]
        for keyword in keywords:
            if keyword in body_text:
                print(f"[발견] '{keyword}'")
                # 키워드 주변 텍스트
                keyword_index = body_text.find(keyword)
                if keyword_index != -1:
                    start = max(0, keyword_index - 30)
                    end = min(len(body_text), keyword_index + 70)
                    context = body_text[start:end].replace('\n', ' ').strip()
                    print(f"  주변: ...{context}...")
            else:
                print(f"[없음] '{keyword}'")
        print()

        print("4. HTML 구조 확인...")

        # 관련용어 탭의 실제 HTML 내용
        try:
            # 현재 활성화된 탭 컨텐츠 찾기
            tab_content = driver.find_element(By.CSS_SELECTOR, "#tab4")
            if tab_content.is_displayed():
                print("관련용어 탭 컨텐츠 HTML:")
                html_content = tab_content.get_attribute('innerHTML')

                # HTML을 줄바꿈으로 정리
                import re
                html_lines = re.split(r'>\s*<', html_content)

                for i, line in enumerate(html_lines[:30]):  # 처음 30줄만
                    clean_line = line.strip()
                    if clean_line and len(clean_line) > 5:
                        print(f"  {i+1:2d}: {clean_line[:100]}...")

        except Exception as html_error:
            print(f"HTML 분석 오류: {html_error}")

        print("\n5. 모든 텍스트 요소 스캔...")

        # 활성 탭에서 모든 텍스트 요소 찾기
        try:
            tab_content = driver.find_element(By.CSS_SELECTOR, "#tab4")
            all_elements = tab_content.find_elements(By.XPATH, ".//*")

            for elem in all_elements:
                try:
                    text = elem.text.strip()
                    tag_name = elem.tag_name

                    # 주요 키워드가 포함된 요소만 출력
                    if text and any(keyword in text for keyword in ["주요항목", "의미분석", "관련용어", "등록된"]):
                        element_class = elem.get_attribute("class") or ""
                        element_id = elem.get_attribute("id") or ""
                        print(f"  {tag_name} [class:{element_class}] [id:{element_id}]: {text[:80]}...")

                except:
                    continue

        except Exception as scan_error:
            print(f"요소 스캔 오류: {scan_error}")

        crawler.browser_pool.return_browser(driver)

    except Exception as e:
        print(f"전체 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(inspect_url_simple())