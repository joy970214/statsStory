#!/usr/bin/env python3
"""
메타데이터 저장 기능 통합 테스트
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime

# 백엔드 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.ultra_fast_metadata_collector import UltraFastMetadataCollector
from app.services.data_storage import DataStorageService
from app.models.stat_models import StatMetadata, StatData
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 테스트용 통계 정보
test_stat = {
    "name": "도로현황",
    "url": "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=59&hFormId=5676&hDivEng=&month_yn="
}

async def test_metadata_storage():
    """메타데이터 수집 및 저장 통합 테스트"""

    print("="*60)
    print("[TEST] 메타데이터 저장 기능 통합 테스트")
    print("="*60)

    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    driver = None
    storage_service = None

    try:
        # 1단계: 웹드라이버 시작
        print("\n[STEP 1] Chrome 웹드라이버 시작...")
        driver = webdriver.Chrome(options=chrome_options)

        # 2단계: 페이지 로드
        print(f"\n[STEP 2] 페이지 로드: {test_stat['url']}")
        driver.get(test_stat['url'])
        await asyncio.sleep(3)

        # 3단계: 메타데이터 수집
        print("\n[STEP 3] 메타데이터 수집 중...")
        collector = UltraFastMetadataCollector(driver)
        start_time = time.time()
        metadata_dict = await collector.collect_all_metadata_once()
        collection_time = time.time() - start_time

        print(f"[SUCCESS] 메타데이터 수집 완료 - 소요시간: {collection_time:.2f}초")

        # 수집된 데이터 확인
        print(f"\n[COLLECTED DATA]")
        print(f"  - 제목: '{metadata_dict['title']}'")
        print(f"  - 작성기관: '{metadata_dict['department']}'")
        print(f"  - 통계정보상세: {len(metadata_dict['statistical_info'])}개")
        print(f"  - 관련용어: {len(metadata_dict['terminology'])}개")

        # 4단계: 메타데이터 모델 생성
        print("\n[STEP 4] 메타데이터 모델 생성...")
        metadata_obj = StatMetadata(
            id=f"test_{int(time.time())}",
            title=metadata_dict['title'] or test_stat['name'],
            purpose=metadata_dict['purpose'] or "테스트 목적",
            frequency=metadata_dict['frequency'] or "정기",
            department=metadata_dict['department'] or "국토교통부",
            contact=metadata_dict['contact'] or "담당자 연락처",
            search_field=metadata_dict['search_field'],
            responsible_department=metadata_dict['responsible_department'],
            keywords=metadata_dict['keywords'],
            related_terms=metadata_dict['related_terms'],
            statistical_info=metadata_dict['statistical_info'],
            major_items=metadata_dict['major_items'],
            meaning_analysis=metadata_dict['meaning_analysis'],
            terminology=metadata_dict['terminology'],
            url=test_stat['url']
        )

        print(f"[SUCCESS] 메타데이터 모델 생성 완료")
        print(f"  - ID: {metadata_obj.id}")
        print(f"  - 제목: {metadata_obj.title}")

        # 5단계: 데이터 저장 서비스 초기화
        print("\n[STEP 5] 데이터 저장 서비스 초기화...")
        storage_service = DataStorageService()

        # 6단계: 메타데이터 저장
        print("\n[STEP 6] 메타데이터 저장 중...")

        try:
            cache_key = storage_service.save_metadata(test_stat['url'], metadata_obj)
            print(f"[SUCCESS] 메타데이터 저장 완료")
            print(f"  - 캐시키: {cache_key}")

            # 저장 파일 확인
            metadata_file = f"backend/data/metadata/{cache_key}_metadata.json"
            if os.path.exists(metadata_file):
                print(f"  - 메타데이터 파일 생성: {metadata_file}")

                # 파일 내용 확인
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)

                print(f"  - 저장된 통계명: {saved_data['metadata']['title']}")
                print(f"  - 저장된 작성기관: {saved_data['metadata']['department']}")
                print(f"  - 저장된 통계정보상세 항목수: {len(saved_data['metadata']['statistical_info'])}")
            else:
                print(f"  - [WARNING] 메타데이터 파일이 생성되지 않음")

        except Exception as storage_error:
            print(f"[ERROR] 메타데이터 저장 실패: {storage_error}")
            return False

        # 7단계: 통계 데이터 저장 (가상 데이터)
        print("\n[STEP 7] 통계 데이터 저장 테스트...")
        test_stats_data = [
            StatData(year=2023, data={"총연장": "110,717", "포장률": "82.9"}),
            StatData(year=2022, data={"총연장": "110,356", "포장률": "82.5"}),
            StatData(year=2021, data={"총연장": "109,971", "포장률": "82.1"})
        ]

        try:
            stats_result = storage_service.save_statistics(test_stat['url'], test_stats_data)
            print(f"[SUCCESS] 통계 데이터 저장 완료")
            print(f"  - 저장 결과: {stats_result}")

            # 통계 데이터 파일 확인
            stats_file = f"backend/data/statistics/{cache_key}_stats.json"
            if os.path.exists(stats_file):
                print(f"  - 통계 데이터 파일 생성: {stats_file}")

                with open(stats_file, 'r', encoding='utf-8') as f:
                    saved_stats = json.load(f)

                print(f"  - 저장된 데이터 행수: {len(saved_stats['data'])}개")
            else:
                print(f"  - [WARNING] 통계 데이터 파일이 생성되지 않음")

        except Exception as stats_error:
            print(f"[ERROR] 통계 데이터 저장 실패: {stats_error}")

        # 8단계: Excel 파일 생성 테스트
        print("\n[STEP 8] Excel 파일 생성 테스트...")
        try:
            excel_result = storage_service.save_to_excel(test_stat['url'], metadata_obj, test_stats_data)
            print(f"[SUCCESS] Excel 파일 생성 완료")
            print(f"  - 생성 결과: {excel_result}")

            # Excel 파일 확인
            if excel_result and os.path.exists(excel_result):
                print(f"  - Excel 파일 생성: {excel_result}")
                file_size = os.path.getsize(excel_result)
                print(f"  - 파일 크기: {file_size:,} bytes")
            else:
                print(f"  - [WARNING] Excel 파일이 생성되지 않음")

        except Exception as excel_error:
            print(f"[ERROR] Excel 파일 생성 실패: {excel_error}")

        # 9단계: 최종 검증
        print("\n[STEP 9] 최종 검증...")

        # 생성된 파일들 확인
        files_created = []
        expected_files = [
            f"backend/data/metadata/{cache_key}_metadata.json",
            f"backend/data/statistics/{cache_key}_stats.json"
        ]

        # Excel 파일은 실제 생성된 경로 사용
        if excel_result and os.path.exists(excel_result):
            expected_files.append(excel_result)

        for file_path in expected_files:
            if os.path.exists(file_path):
                files_created.append(file_path)

        print(f"[RESULT] 생성된 파일 수: {len(files_created)}/3개")
        for file_path in files_created:
            print(f"  ✓ {file_path}")

        success_rate = (len(files_created) / 3) * 100
        print(f"[SCORE] 저장 성공률: {success_rate:.1f}%")

        return success_rate >= 66.7  # 3개 중 2개 이상 성공

    except Exception as e:
        print(f"[ERROR] 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if driver:
            driver.quit()
            print("\n[CLOSE] 웹드라이버 종료")

if __name__ == "__main__":
    result = asyncio.run(test_metadata_storage())

    if result:
        print("\n[COMPLETE] 메타데이터 저장 기능이 정상 작동합니다!")
    else:
        print("\n[FAILED] 메타데이터 저장 기능에 문제가 있습니다!")