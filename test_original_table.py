#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""원본 테이블 형태 표시 기능 테스트"""

import sys
import os
import json

# 백엔드 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.api.stats import _generate_original_table_format, _calculate_basic_statistics_from_comprehensive
from app.services.data_storage import DataStorageService

def test_original_table_format():
    """원본 테이블 형태 표시 기능 테스트"""
    print("=== 원본 테이블 형태 표시 기능 테스트 ===")

    storage_service = DataStorageService()

    # 캐시된 데이터 로드
    stat_url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=471&hFormId=5386&hDivEng=&month_yn="
    cached_metadata, cached_stat_data = storage_service.get_cached_data(stat_url)

    if not cached_stat_data:
        print("[ERROR] 캐시된 데이터가 없습니다.")
        return

    print(f"[SUCCESS] 캐시된 데이터 로드 성공: {len(cached_stat_data)}개 테이블")

    # 첫 번째 테이블의 _table_data 확인
    first_table = cached_stat_data[0]
    if hasattr(first_table, 'data') and first_table.data and '_table_data' in first_table.data:
        print(f"[SUCCESS] _table_data 필드 발견: {first_table.table_name}")

        # 원본 테이블 형태 생성 테스트
        try:
            table_data_str = first_table.data['_table_data']
            print(f"_table_data 길이: {len(table_data_str)} 문자")

            original_format = _generate_original_table_format(table_data_str)

            if original_format:
                print(f"[SUCCESS] 원본 테이블 형태 생성 성공!")
                print(f"헤더 개수: {len(original_format.get('headers', []))}")
                print(f"데이터 행 개수: {original_format.get('total_rows', 0)}")
                print(f"첫 5개 헤더: {original_format.get('headers', [])[:5]}")

                # 첫 번째 데이터 행 출력
                if original_format.get('data_rows'):
                    first_row = original_format['data_rows'][0]
                    print(f"첫 번째 행 필드 개수: {len(first_row)}")
                    for i, (key, value) in enumerate(list(first_row.items())[:3]):
                        print(f"  {key}: {value.get('value', '')} ({value.get('unit', 'text')})")

            else:
                print("[ERROR] 원본 테이블 형태 생성 실패")

        except Exception as e:
            print(f"[ERROR] 원본 테이블 형태 생성 중 오류: {e}")

    # 전체 기본통계분석 함수 테스트
    print("\n=== 전체 기본통계분석 테스트 ===")
    try:
        result = _calculate_basic_statistics_from_comprehensive(cached_stat_data)

        print(f"[SUCCESS] 기본통계분석 완료!")
        print(f"테이블명: {result.get('table_name', '')}")
        print(f"총 레코드 수: {result.get('data_overview', {}).get('total_records', 0)}")
        print(f"기본통계 평균: {result.get('basic_statistics', {}).get('mean', 0)}")

        # 원본 테이블 형태 확인
        if 'original_table_format' in result:
            print(f"[SUCCESS] 원본 테이블 형태 포함됨!")
            original = result['original_table_format']
            print(f"  헤더: {len(original.get('headers', []))}개")
            print(f"  데이터 행: {original.get('total_rows', 0)}개")
        else:
            print("[ERROR] 원본 테이블 형태가 결과에 포함되지 않음")

    except Exception as e:
        print(f"[ERROR] 기본통계분석 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_original_table_format()