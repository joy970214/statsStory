#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""직접 JSON 파일에서 원본 테이블 형태 표시 기능 테스트"""

import sys
import os
import json

# 백엔드 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.api.stats import _generate_original_table_format

def test_with_json_file():
    """JSON 파일에서 직접 테스트"""
    print("=== 직접 JSON 파일 테스트 ===")

    # JSON 파일 경로
    json_file = "backend/data/statistics/3d336983f675_stats.json"

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"[SUCCESS] JSON 파일 로드 성공")
        print(f"데이터 구조: {list(data.keys())}")

        # statistics 배열에서 _table_data 찾기
        found_table_data = False
        statistics = data.get('statistics', [])
        print(f"통계 테이블 개수: {len(statistics)}")

        for i, table in enumerate(statistics):
            print(f"테이블 {i}: {list(table.keys())[:10]}")

            # data 필드 안에 _table_data가 있는지 확인
            table_data_field = table.get('data', {})
            if isinstance(table_data_field, dict) and '_table_data' in table_data_field:
                print(f"[SUCCESS] _table_data 발견: {table.get('table_name', 'Unknown')}")
                found_table_data = True

                # 원본 테이블 형태 생성 테스트
                table_data_str = table_data_field['_table_data']
                print(f"_table_data 길이: {len(table_data_str)} 문자")
                print(f"_table_data 타입: {type(table_data_str)}")
                print(f"_table_data 시작 100자: {table_data_str[:100]}")

                try:
                    original_format = _generate_original_table_format(table_data_str)

                    if original_format:
                        print("[SUCCESS] 원본 테이블 형태 생성 성공!")
                        print(f"헤더 개수: {len(original_format.get('headers', []))}")
                        print(f"데이터 행 개수: {original_format.get('total_rows', 0)}")

                        # 헤더 출력
                        headers = original_format.get('headers', [])
                        if headers:
                            print(f"헤더 (처음 5개): {headers[:5]}")

                        # 첫 번째 데이터 행 출력
                        data_rows = original_format.get('data_rows', [])
                        if data_rows:
                            first_row = data_rows[0]
                            print(f"첫 번째 행 필드 개수: {len(first_row)}")
                            for i, (key, value) in enumerate(list(first_row.items())[:3]):
                                print(f"  {key}: {value.get('value', '')} ({value.get('unit', 'text')})")

                        # JSON으로 저장해서 확인
                        with open('test_original_table_result.json', 'w', encoding='utf-8') as f:
                            json.dump(original_format, f, ensure_ascii=False, indent=2)
                        print("[INFO] 결과를 test_original_table_result.json에 저장했습니다.")

                    else:
                        print("[ERROR] 원본 테이블 형태 생성 실패")

                except Exception as e:
                    print(f"[ERROR] 원본 테이블 형태 생성 중 오류: {e}")
                    import traceback
                    traceback.print_exc()

                break

        if not found_table_data:
            print("[ERROR] _table_data 필드를 찾을 수 없습니다.")

    except Exception as e:
        print(f"[ERROR] JSON 파일 처리 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_json_file()