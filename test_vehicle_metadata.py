#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""자동차관리사업자업체현황분기 통계 메타데이터 수집 테스트"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.optimized_molit_crawler import OptimizedMolitCrawler

async def test_vehicle_metadata_collection():
    """자동차관리사업자업체현황분기 통계 메타데이터 수집 테스트"""

    # 자동차관리사업자업체현황분기 통계 URL
    stat_url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=437&hFormId=4392&hDivEng=&month_yn="

    print("=== 자동차관리사업자업체현황분기 메타데이터 수집 테스트 ===")
    print(f"URL: {stat_url}")
    print()

    try:
        crawler = OptimizedMolitCrawler(pool_size=1, max_concurrent_tables=1)

        # 메타데이터만 수집
        print("1. 웹 드라이버 초기화 중...")
        driver = crawler.browser_pool.get_browser()

        print("2. 페이지 로딩 중...")
        driver.get(stat_url)
        import time
        time.sleep(3)  # 페이지 로딩 대기

        print("3. 메타데이터 수집 중...")
        metadata = await crawler._collect_page_metadata_directly(driver)

        print("4. 수집 결과:")
        print(f"  - 부서: {metadata.get('department', 'N/A')}")
        print(f"  - 담당자: {metadata.get('contact', 'N/A')}")
        print(f"  - 키워드: {metadata.get('keywords', [])}")
        print(f"  - 통계정보: {len(metadata.get('statistical_info', {}))}개")
        print(f"  - 주요항목: {len(metadata.get('major_items', {}))}개")
        print(f"  - 의미분석: {len(metadata.get('meaning_analysis', {}))}개")
        print(f"  - 관련용어: {len(metadata.get('related_terms', {}))}개")

        print("\n=== 상세 메타데이터 ===")

        if metadata.get('statistical_info'):
            print("\n📊 통계정보:")
            for key, value in metadata['statistical_info'].items():
                print(f"  - {key}: {value}")

        if metadata.get('major_items'):
            print("\n📋 주요항목:")
            for key, value in list(metadata['major_items'].items())[:5]:  # 처음 5개만
                print(f"  - {key}: {value}")
            if len(metadata['major_items']) > 5:
                print(f"  ... 총 {len(metadata['major_items'])}개 항목")

        if metadata.get('meaning_analysis'):
            print("\n🔍 의미분석:")
            for key, value in metadata['meaning_analysis'].items():
                print(f"  - {key}: {value[:100]}..." if len(value) > 100 else f"  - {key}: {value}")

        if metadata.get('related_terms'):
            print("\n📖 관련용어:")
            for key, value in metadata['related_terms'].items():
                print(f"  - {key}: {value}")

        crawler.browser_pool.return_browser(driver)

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_vehicle_metadata_collection())