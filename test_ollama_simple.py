"""간단한 Ollama 테스트"""
import sys
import json
sys.path.insert(0, 'backend')

from app.services.ollama_service import ollama_service

# 실제 데이터 로드
print("실제 통계 데이터 로드 중...")
with open('backend/data/statistics/a23adaca0683_stats.json', 'r', encoding='utf-8') as f:
    stats_json = json.load(f)

with open('backend/data/metadata/a23adaca0683_metadata.json', 'r', encoding='utf-8') as f:
    metadata_json = json.load(f)

# 데이터 구조 확인
all_data = stats_json.get('statistics', [])
print(f"전체 데이터 개수: {len(all_data)}개")

# 통계표별로 그룹화
tables_data = {}
for item in all_data:
    table_name = item.get('table_name', '기본 통계표')
    if table_name not in tables_data:
        tables_data[table_name] = []
    tables_data[table_name].append(item)

print(f"통계표 개수: {len(tables_data)}개")
for table_name, data in tables_data.items():
    print(f"  - {table_name}: {len(data)}개 데이터")

# 첫 번째 통계표만 테스트
first_table_name = list(tables_data.keys())[0]
first_table_data = tables_data[first_table_name]

print(f"\n'{first_table_name}' 분석 시작...")
print(f"데이터 샘플 (첫 3개):")
for i, item in enumerate(first_table_data[:3], 1):
    print(f"  {i}. year={item.get('year')}, data keys={list(item.get('data', {}).keys())[:3]}")

# 통계량 계산
table_summary = ollama_service._calculate_table_statistics(first_table_data)
print(f"\n기본 통계량:")
print(f"  평균: {table_summary.get('mean', 0):.2f}")
print(f"  최대: {table_summary.get('max', 0):.2f}")
print(f"  최소: {table_summary.get('min', 0):.2f}")
print(f"  개수: {table_summary.get('count', 0)}")

# 프롬프트 생성 (실제로 보내기 전에 확인)
print("\n프롬프트 생성 중...")
prompt = ollama_service._build_single_table_prompt(
    table_name=first_table_name,
    table_data=first_table_data,
    table_summary=table_summary,
    metadata=metadata_json.get('metadata', {})
)

print(f"프롬프트 길이: {len(prompt)}자")
print(f"프롬프트 미리보기 (첫 500자):")
print("=" * 80)
print(prompt[:500])
print("=" * 80)

# 실제 Ollama 호출
print("\nOllama API 호출 중... (최대 60초 대기)")
try:
    insight = ollama_service.generate_single_table_insight(
        table_name=first_table_name,
        table_data=first_table_data,
        table_summary=table_summary,
        metadata=metadata_json.get('metadata', {})
    )

    print(f"\n인사이트 생성 결과:")
    print(f"길이: {len(insight)}자")
    print("=" * 80)
    print(insight)
    print("=" * 80)

    if "분석 실패" in insight:
        print("\nERROR: 인사이트 생성 실패!")
    elif len(insight) < 20:
        print("\nWARNING: 인사이트가 너무 짧습니다!")
    else:
        print("\nOK: 인사이트 생성 성공!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
