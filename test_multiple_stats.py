#!/usr/bin/env python3
"""
다양한 통계 URL로 메타데이터 수집 테스트
"""

import asyncio
import sys
import os

# 백엔드 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.ultra_fast_metadata_collector import UltraFastMetadataCollector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# 테스트할 통계 목록
test_stats = [
    {
        "name": "도로현황",
        "url": "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=59&hFormId=5676&hDivEng=&month_yn="
    },
    {
        "name": "국내외 여객 개황",
        "url": "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=54&hFormId=1050&hDivEng=&month_yn="
    },
    {
        "name": "교통장비 현황",
        "url": "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=54&hFormId=1068&hDivEng=&month_yn="
    },
    {
        "name": "상용차 운송 개황",
        "url": "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=54&hFormId=1066&hDivEng=&month_yn="
    }
]

async def test_single_stat(stat_info, driver):
    """단일 통계 메타데이터 수집 테스트"""
    print(f"\n{'='*60}")
    print(f"통계명: {stat_info['name']}")
    print(f"URL: {stat_info['url']}")
    print('='*60)

    try:
        # 페이지 로드
        print(f"[LOAD] 페이지 로딩 중...")
        driver.get(stat_info['url'])
        await asyncio.sleep(3)

        print(f"[OK] 페이지 제목: {driver.title}")

        # 메타데이터 수집
        collector = UltraFastMetadataCollector(driver)
        start_time = time.time()
        metadata = await collector.collect_all_metadata_once()
        end_time = time.time()

        # 결과 분석
        print(f"\n[RESULT] 수집 완료 - 소요시간: {end_time - start_time:.2f}초")

        # 기본 정보 출력
        print(f"\n[기본 정보]")
        print(f"  - 제목: '{metadata['title']}'")
        print(f"  - 목적: '{metadata['purpose']}'")
        print(f"  - 주기: '{metadata['frequency']}'")
        print(f"  - 작성기관: '{metadata['department']}'")
        print(f"  - 담당자: '{metadata['contact']}'")
        print(f"  - 검색분야: '{metadata['search_field']}'")
        print(f"  - 담당부서: '{metadata['responsible_department']}'")

        # 상세 정보 카운트
        counts = {
            'statistical_info': len(metadata['statistical_info']),
            'major_items': len(metadata['major_items']),
            'meaning_analysis': len(metadata['meaning_analysis']),
            'terminology': len(metadata['terminology'])
        }

        print(f"\n[상세 정보]")
        print(f"  - 통계정보상세: {counts['statistical_info']}개")
        print(f"  - 주요항목: {counts['major_items']}개")
        print(f"  - 의미분석: {counts['meaning_analysis']}개")
        print(f"  - 용어정의: {counts['terminology']}개")

        # 상세 내용 일부 출력 (통계정보상세)
        if metadata['statistical_info']:
            print(f"\n[통계정보상세 샘플]")
            for i, (key, value) in enumerate(list(metadata['statistical_info'].items())[:3]):
                print(f"  {i+1}. {key}: {value}")

        # 성공도 평가
        filled_basic_fields = sum(1 for field in ['title', 'department', 'search_field', 'responsible_department']
                                if metadata.get(field))
        total_items = sum(counts.values())

        print(f"\n[수집 성공도]")
        print(f"  - 기본 필드: {filled_basic_fields}/4개")
        print(f"  - 상세 항목: {total_items}개")

        success_score = (filled_basic_fields / 4) * 50 + min(total_items / 10, 1) * 50
        print(f"  - 종합 점수: {success_score:.1f}%")

        return {
            'name': stat_info['name'],
            'url': stat_info['url'],
            'success': True,
            'metadata': metadata,
            'counts': counts,
            'basic_fields': filled_basic_fields,
            'total_items': total_items,
            'score': success_score,
            'duration': end_time - start_time
        }

    except Exception as e:
        print(f"[ERROR] 수집 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            'name': stat_info['name'],
            'url': stat_info['url'],
            'success': False,
            'error': str(e),
            'score': 0
        }

async def test_all_stats():
    """모든 통계에 대해 메타데이터 수집 테스트"""

    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    driver = None
    results = []

    try:
        print("[START] Chrome 웹드라이버 시작...")
        driver = webdriver.Chrome(options=chrome_options)

        # 각 통계별 테스트
        for stat_info in test_stats:
            result = await test_single_stat(stat_info, driver)
            results.append(result)

            # 테스트 간 대기
            await asyncio.sleep(2)

        # 전체 결과 요약
        print(f"\n{'='*60}")
        print("[SUMMARY] 전체 테스트 결과 요약")
        print('='*60)

        successful_tests = [r for r in results if r['success']]
        failed_tests = [r for r in results if not r['success']]

        print(f"[SUCCESS] 성공: {len(successful_tests)}/{len(results)}개")
        print(f"[FAILED] 실패: {len(failed_tests)}개")

        if successful_tests:
            avg_score = sum(r['score'] for r in successful_tests) / len(successful_tests)
            avg_duration = sum(r['duration'] for r in successful_tests) / len(successful_tests)
            total_items = sum(r['total_items'] for r in successful_tests)

            print(f"\n[STATS] 성공한 테스트 통계:")
            print(f"  - 평균 점수: {avg_score:.1f}%")
            print(f"  - 평균 소요시간: {avg_duration:.2f}초")
            print(f"  - 총 수집 항목: {total_items}개")

            print(f"\n[DETAILS] 개별 결과:")
            for result in successful_tests:
                print(f"  - {result['name']}: {result['score']:.1f}% ({result['total_items']}개 항목)")

        if failed_tests:
            print(f"\n[ERRORS] 실패한 테스트:")
            for result in failed_tests:
                print(f"  - {result['name']}: {result.get('error', 'Unknown error')}")

        return results

    except Exception as e:
        print(f"[ERROR] 전체 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        if driver:
            driver.quit()
            print("\n[CLOSE] 웹드라이버 종료")

if __name__ == "__main__":
    print("[TEST] 다양한 통계 URL 메타데이터 수집 테스트")
    print("="*60)

    results = asyncio.run(test_all_stats())

    if results and any(r['success'] for r in results):
        print("\n[COMPLETE] 테스트 완료! 메타데이터 수집기가 정상 작동합니다.")
    else:
        print("\n[FAILED] 테스트 실패! 메타데이터 수집기에 문제가 있습니다.")