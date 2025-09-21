#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""URL 검증 시스템 테스트 스크립트"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.url_validator import URLValidator

def test_url_validation():
    """URL 검증 시스템 테스트"""
    validator = URLValidator()

    # 잘못된 URL 테스트 (도시형생활주택을 요청했는데 공동주택 분양 URL 사용)
    wrong_url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=488&hFormId=5557&hDivEng=&month_yn="

    # 실제로 수집될 것으로 예상되는 테이블명들 (공동주택 분양 관련)
    # 도시형생활주택을 요청했는데 공동주택 분양 데이터가 수집됨
    collected_table_names = [
        "공동주택 분양승인 실적(전국) (200801 ~ 202409)",
        "공동주택 분양승인 실적(시도별)",
        "주택건설분양실적통계표"
    ]

    print("=== URL 검증 테스트 ===")
    print(f"요청 URL: {wrong_url}")
    print(f"수집된 테이블명들: {collected_table_names}")
    print()

    # 사용자가 실제로 요청한 통계명
    requested_stat_name = "도시형생활주택인허가실적"

    # URL 검증 실행 (요청한 통계명 포함)
    result = validator.validate_url_and_suggest(wrong_url, collected_table_names, requested_stat_name)

    print("=== 검증 결과 ===")
    print(f"URL 유효성: {result['is_valid']}")
    print(f"URL 불일치: {result['url_mismatch']}")
    print(f"경고 메시지: {result['validation_warnings']}")
    print(f"올바른 URL: {result['correct_url']}")
    print(f"감지된 통계명: {result['detected_stat_name']}")
    print()

    # 올바른 URL이 제안되는지 확인
    if result['url_mismatch'] and result['correct_url']:
        print("✅ URL 불일치 감지됨!")
        print(f"올바른 URL: {result['correct_url']}")
        print(f"올바른 통계명: {result['detected_stat_name']}")
    else:
        print("❌ URL 불일치가 감지되지 않았습니다.")

    print()
    print("=== 사용 가능한 모든 통계 ===")
    all_stats = validator.get_all_available_stats()
    for stat in all_stats:
        print(f"- {stat.name} (rsid: {stat.rsid})")
        print(f"  URL: {stat.correct_url}")
        print()

if __name__ == "__main__":
    test_url_validation()