#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""수집된 관련용어 탭 정보 상세 확인"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.optimized_molit_crawler import OptimizedMolitCrawler
import time
import json

async def show_collected_terms():
    """수집된 관련용어 정보 상세 출력"""

    stat_url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=437&hFormId=4392&hDivEng=&month_yn="

    print("=== 관련용어 탭 수집 정보 상세 확인 ===")
    print(f"URL: {stat_url}")
    print()

    try:
        crawler = OptimizedMolitCrawler(pool_size=1, max_concurrent_tables=1)
        driver = crawler.browser_pool.get_browser()

        print("1. 페이지 로딩 중...")
        driver.get(stat_url)
        time.sleep(3)

        print("2. 메타데이터 수집 중...")
        metadata = await crawler._collect_page_metadata_directly(driver)

        print("\n=== 수집된 관련용어 정보 ===")

        # terminology 섹션만 추출
        if 'terminology' in metadata:
            terminology = metadata['terminology']
            print(f"총 관련용어 항목 수: {len(terminology)}개")
            print()

            for i, (key, value) in enumerate(terminology.items(), 1):
                print(f"{i}. 키: {key}")
                print(f"   값: {value}")
                print()
        else:
            print("❌ terminology 섹션이 없습니다.")

        # 전체 메타데이터 구조 확인
        print("\n=== 전체 메타데이터 구조 ===")
        for section_name, section_data in metadata.items():
            if isinstance(section_data, dict):
                print(f"{section_name}: {len(section_data)}개 항목")
            elif isinstance(section_data, list):
                print(f"{section_name}: {len(section_data)}개 항목 (리스트)")
            else:
                print(f"{section_name}: {type(section_data).__name__}")

        # JSON 형태로도 출력
        print("\n=== JSON 형태 출력 ===")
        if 'terminology' in metadata:
            print(json.dumps(metadata['terminology'], ensure_ascii=False, indent=2))

        crawler.browser_pool.return_browser(driver)

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(show_collected_terms())