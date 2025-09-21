#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""관련용어 탭의 상세 구조 재분석"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.optimized_molit_crawler import OptimizedMolitCrawler
import time
from selenium.webdriver.common.by import By

async def detailed_terms_analysis():
    """관련용어 탭의 모든 요소 상세 분석"""

    stat_url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=437&hFormId=4392&hDivEng=&month_yn="

    print("=== 자동차관리사업자업체현황분기 관련용어 탭 상세 분석 ===")
    print(f"URL: {stat_url}")
    print()

    try:
        crawler = OptimizedMolitCrawler(pool_size=1, max_concurrent_tables=1)
        driver = crawler.browser_pool.get_browser()

        print("1. 페이지 로딩 중...")
        driver.get(stat_url)
        time.sleep(3)

        print("2. 관련용어 탭 클릭...")
        # 관련용어 탭 찾기 및 클릭
        tab_patterns = [
            "//a[contains(text(), '관련용어')]",
            "//li[contains(text(), '관련용어')]//a",
            "//span[contains(text(), '관련용어')]//parent::a",
            "//*[contains(@class, 'tab') and contains(text(), '관련용어')]"
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

        if related_terms_tab:
            driver.execute_script("arguments[0].click();", related_terms_tab)
            time.sleep(2)
            print("  관련용어 탭 클릭 완료")
        else:
            print("  ❌ 관련용어 탭을 찾을 수 없습니다.")
            return

        print("\n3. 전체 텍스트 내용 확인...")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print("=== 페이지 전체 텍스트에서 키워드 검색 ===")

            keywords = ["주요항목", "의미분석", "관련용어", "등록된", "없습니다"]
            for keyword in keywords:
                if keyword in body_text:
                    print(f"✅ '{keyword}' 발견")
                    # 해당 키워드 주변 텍스트 출력
                    keyword_index = body_text.find(keyword)
                    if keyword_index != -1:
                        start = max(0, keyword_index - 50)
                        end = min(len(body_text), keyword_index + 100)
                        context = body_text[start:end].replace('\n', ' ').strip()
                        print(f"   주변 텍스트: ...{context}...")
                else:
                    print(f"❌ '{keyword}' 없음")
            print()
        except Exception as e:
            print(f"텍스트 분석 오류: {e}")

        print("4. 모든 요소 구조 분석...")

        # 활성 탭 컨텐츠 찾기
        print("\n=== 활성 탭 컨텐츠 찾기 ===")
        active_content = None
        content_selectors = [
            "#tab4",
            ".tab-content.active",
            "[id*='tab'][style*='block']",
            ".tab-pane.active"
        ]

        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        active_content = elem
                        print(f"✅ 활성 컨텐츠 발견: {selector}")
                        break
                if active_content:
                    break
            except:
                continue

        if not active_content:
            print("❌ 활성 탭 컨텐츠를 찾을 수 없어 전체 body에서 분석")
            active_content = driver.find_element(By.TAG_NAME, "body")

        # 헤딩 요소들 찾기
        print("\n=== 헤딩 요소 분석 ===")
        heading_tags = ["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"]
        for tag in heading_tags:
            try:
                elements = active_content.find_elements(By.TAG_NAME, tag)
                for i, elem in enumerate(elements):
                    text = elem.text.strip()
                    if text and any(keyword in text for keyword in ["주요항목", "의미분석", "관련용어"]):
                        print(f"  {tag.upper()} {i+1}: {text}")
            except:
                continue

        # 모든 텍스트 요소에서 키워드 찾기
        print("\n=== 텍스트 요소에서 키워드 찾기 ===")
        all_elements = active_content.find_elements(By.XPATH, "//*[text()]")

        for elem in all_elements:
            try:
                text = elem.text.strip()
                if text and any(keyword in text for keyword in ["주요항목", "의미분석", "관련용어"]):
                    tag_name = elem.tag_name
                    element_class = elem.get_attribute("class") or "no-class"
                    element_id = elem.get_attribute("id") or "no-id"
                    print(f"  {tag_name} (class: {element_class}, id: {element_id}): {text[:100]}...")
            except:
                continue

        # 특정 패턴으로 섹션 헤더 찾기
        print("\n=== 섹션 헤더 패턴 검색 ===")
        section_patterns = [
            "//div[contains(@class, 'section')]",
            "//div[contains(@class, 'content')]",
            "//div[contains(@class, 'info')]",
            "//*[contains(@class, 'title')]",
            "//*[contains(@class, 'header')]"
        ]

        for pattern in section_patterns:
            try:
                elements = driver.find_elements(By.XPATH, pattern)
                for elem in elements:
                    text = elem.text.strip()
                    if text and any(keyword in text for keyword in ["주요항목", "의미분석", "관련용어"]):
                        print(f"  패턴 {pattern}: {text[:100]}...")
            except:
                continue

        # 리스트와 테이블 구조 재확인
        print("\n=== 리스트 및 테이블 구조 재확인 ===")

        # 모든 리스트
        lists = active_content.find_elements(By.XPATH, ".//ul | .//ol | .//dl")
        for i, lst in enumerate(lists):
            try:
                list_text = lst.text.strip()
                if list_text:
                    print(f"  리스트 {i+1} ({lst.tag_name}): {list_text[:100]}...")

                    # 리스트 항목들
                    items = lst.find_elements(By.XPATH, ".//li | .//dt | .//dd")
                    for j, item in enumerate(items[:5]):
                        item_text = item.text.strip()
                        if item_text:
                            print(f"    항목 {j+1}: {item_text[:50]}...")
            except:
                continue

        # 모든 테이블
        tables = active_content.find_elements(By.TAG_NAME, "table")
        for i, table in enumerate(tables):
            try:
                print(f"  테이블 {i+1}:")
                rows = table.find_elements(By.TAG_NAME, "tr")
                for j, row in enumerate(rows[:3]):
                    row_text = row.text.strip()
                    if row_text:
                        print(f"    행 {j+1}: {row_text[:100]}...")
            except:
                continue

        crawler.browser_pool.return_browser(driver)

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(detailed_terms_analysis())