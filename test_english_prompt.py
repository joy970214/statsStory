"""영어 프롬프트 테스트"""
import sys
import json
import time
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

print("=" * 80)
print("영어 프롬프트 테스트")
print("=" * 80)

# 통계량 계산
table_summary = ollama_service._calculate_table_statistics(test_table_data)
print(f"\n기본 통계량:")
print(f"  평균: {table_summary.get('mean', 0):.2f}")
print(f"  최대: {table_summary.get('max', 0):.2f}")
print(f"  최소: {table_summary.get('min', 0):.2f}")

# 프롬프트 생성
print("\n프롬프트 생성 중...")
prompt = ollama_service._build_single_table_prompt(
    table_name="테스트 통계표",
    table_data=test_table_data,
    table_summary=table_summary,
    metadata=test_metadata
)

print(f"프롬프트 길이: {len(prompt)}자")
print(f"프롬프트 미리보기 (첫 300자):")
print("=" * 80)
print(prompt[:300])
print("=" * 80)

# Ollama 호출
print("\nOllama API 호출 중... (최대 60초 대기)")
start_time = time.time()

try:
    insight = ollama_service.generate_single_table_insight(
        table_name="테스트 통계표",
        table_data=test_table_data,
        table_summary=table_summary,
        metadata=test_metadata
    )

    elapsed = time.time() - start_time

    print(f"\n소요 시간: {elapsed:.2f}초")
    print(f"인사이트 길이: {len(insight)}자")
    print("\n생성된 인사이트:")
    print("=" * 80)
    print(insight)
    print("=" * 80)

    if "분석 실패" in insight:
        print("\nERROR: 인사이트 생성 실패!")
    elif len(insight) < 20:
        print("\nWARNING: 인사이트가 너무 짧습니다!")
    else:
        print(f"\nOK: 인사이트 생성 성공! ({elapsed:.2f}초 소요)")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"\nERROR ({elapsed:.2f}초 후): {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)
