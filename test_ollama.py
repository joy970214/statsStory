"""Ollama 분석 테스트 스크립트"""
import sys
import json
sys.path.insert(0, 'backend')

from app.services.ollama_service import ollama_service

# 테스트 데이터
test_table_data = [
    {
        "year": 2025,
        "data": {
            "계": "1,908",
            "소형": "1,500",
            "중형": "300",
            "대형": "108"
        }
    },
    {
        "year": 2024,
        "data": {
            "계": "2,100",
            "소형": "1,600",
            "중형": "350",
            "대형": "150"
        }
    }
]

test_metadata = {
    "title": "도시형생활주택 인허가 실적 테스트",
    "department": "국토교통부"
}

test_tables_data = {
    "테스트 통계표": test_table_data
}

print("=" * 80)
print("Ollama 서비스 테스트")
print("=" * 80)

# 1. Ollama 사용 가능 여부 확인
print("\n1. Ollama 서버 상태 확인...")
is_available = ollama_service.is_available()
print(f"   결과: {'OK 사용 가능' if is_available else 'ERROR 사용 불가'}")

if not is_available:
    print("\n오류: Ollama 서버가 실행되지 않았습니다.")
    print("다음 명령으로 Ollama를 실행하세요: ollama serve")
    sys.exit(1)

# 2. 단일 통계표 인사이트 생성 테스트
print("\n2. 단일 통계표 인사이트 생성 테스트...")
try:
    table_summary = ollama_service._calculate_table_statistics(test_table_data)
    print(f"   통계량: mean={table_summary['mean']:.2f}, max={table_summary['max']:.2f}")

    insight = ollama_service.generate_single_table_insight(
        table_name="테스트 통계표",
        table_data=test_table_data,
        table_summary=table_summary,
        metadata=test_metadata
    )

    print(f"   결과 (길이: {len(insight)}자):")
    print(f"   {insight[:200]}...")

    if "분석 실패" in insight or len(insight) < 10:
        print("   ERROR 인사이트 생성 실패")
    else:
        print("   OK 인사이트 생성 성공")

except Exception as e:
    print(f"   ERROR 오류 발생: {e}")
    import traceback
    traceback.print_exc()

# 3. 통계표별 인사이트 생성 테스트
print("\n3. 통계표별 인사이트 종합 생성 테스트...")
try:
    combined_insights = ollama_service.generate_statistical_insights_by_tables(
        metadata=test_metadata,
        tables_data=test_tables_data
    )

    print(f"   생성된 인사이트 개수: {combined_insights.get('insights_count', 0)}")
    print(f"   분석 제목: {combined_insights.get('analysis_title', 'N/A')}")

    insight_1 = combined_insights.get('insight_1', {})
    print(f"   인사이트 1 내용: {insight_1.get('content', 'N/A')[:100]}...")

    if combined_insights.get('insights_count', 0) > 0:
        print("   OK 종합 인사이트 생성 성공")
    else:
        print("   ERROR 종합 인사이트 생성 실패")

except Exception as e:
    print(f"   ERROR 오류 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)
