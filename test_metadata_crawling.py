#!/usr/bin/env python3
"""
도로현황 메타데이터 크롤링 테스트
"""

import asyncio
import sys
import os

# 백엔드 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.ultra_fast_metadata_collector import UltraFastMetadataCollector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

async def test_metadata_collection():
    """도로현황 URL에서 메타데이터 수집 테스트"""

    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 헤드리스 모드
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    driver = None
    try:
        # 웹드라이버 초기화
        print("[START] Chrome 웹드라이버 시작...")
        driver = webdriver.Chrome(options=chrome_options)

        # 도로현황 페이지 이동
        url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=59&hFormId=5676&hDivEng=&month_yn="
        print(f"[LOAD] 페이지 로드: {url}")
        driver.get(url)

        # 페이지 로딩 대기
        await asyncio.sleep(3)
        print(f"[OK] 페이지 제목: {driver.title}")

        # 현재 페이지 탭 확인
        print("\n=== 페이지 탭 확인 ===")
        tabs = driver.find_elements(By.XPATH, "//a | //button | //*[@onclick]")

        stat_info_found = False
        related_terms_found = False

        print("발견된 탭/링크:")
        for i, tab in enumerate(tabs[:20]):  # 처음 20개만
            try:
                text = tab.text.strip()
                onclick = tab.get_attribute('onclick') or ''

                if text and ('통계' in text or '정보' in text or '용어' in text or '분석' in text):
                    print(f"  {i+1}. '{text}' | onclick: '{onclick}'")

                    if '통계정보' in text or 'goMetaView' in onclick:
                        stat_info_found = True
                    if '관련용어' in text or 'goAnalsView' in onclick:
                        related_terms_found = True

            except:
                continue

        print(f"\n통계정보 탭 존재: {'YES' if stat_info_found else 'NO'}")
        print(f"관련용어 탭 존재: {'YES' if related_terms_found else 'NO'}")

        # 메타데이터 수집기 테스트
        print("\n=== 메타데이터 수집 테스트 ===")
        collector = UltraFastMetadataCollector(driver)
        metadata = await collector.collect_all_metadata_once()

        print("\n=== 수집 결과 ===")
        print(f"제목: {metadata['title']}")
        print(f"목적: {metadata['purpose']}")
        print(f"주기: {metadata['frequency']}")
        print(f"작성기관: {metadata['department']}")
        print(f"담당자: {metadata['contact']}")
        print(f"검색분야: {metadata['search_field']}")
        print(f"담당부서: {metadata['responsible_department']}")
        print(f"통계정보상세: {len(metadata['statistical_info'])}개")
        print(f"주요항목: {len(metadata['major_items'])}개")
        print(f"의미분석: {len(metadata['meaning_analysis'])}개")
        print(f"용어정의: {len(metadata['terminology'])}개")

        if metadata['statistical_info']:
            print("\n통계정보상세 내용:")
            for key, value in list(metadata['statistical_info'].items())[:5]:
                print(f"  - {key}: {value}")

        if metadata['major_items']:
            print("\n주요항목 내용:")
            for key, value in list(metadata['major_items'].items())[:3]:
                print(f"  - {key}: {value}")

        return metadata

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        if driver:
            driver.quit()
            print("[CLOSE] 웹드라이버 종료")

if __name__ == "__main__":
    print("=" * 50)
    print("도로현황 메타데이터 크롤링 테스트")
    print("=" * 50)

    result = asyncio.run(test_metadata_collection())

    if result:
        print("\n[SUCCESS] 테스트 완료!")
    else:
        print("\n[FAIL] 테스트 실패!")