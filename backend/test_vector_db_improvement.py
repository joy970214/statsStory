"""
개선된 벡터 DB 테스트 스크립트
- 1개 통계 데이터로 테스트
- 구조 분석 및 자연어 생성 확인
"""
import json
from pathlib import Path
from app.services.vector_db_service import VectorDBService

def load_test_data(cache_key: str):
    """테스트 데이터 로드"""
    stats_file = Path(__file__).parent / "data" / "statistics" / f"{cache_key}_stats.json"

    with open(stats_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data

def test_improved_vector_db():
    """개선된 벡터 DB 테스트"""
    # 테스트할 cache_key (국토지표의 진전)
    test_cache_key = "1a6ff8ca7437"

    print("=" * 80)
    print("개선된 벡터 DB 테스트 시작")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n[1단계] 데이터 로드")
    test_data = load_test_data(test_cache_key)
    print(f"- 통계명: {test_data.get('statistics', [{}])[0].get('table_name', '')}")
    print(f"- 전체 행 수: {len(test_data.get('statistics', []))}")

    # 2. VectorDB 서비스 초기화
    print("\n[2단계] VectorDB 서비스 초기화")
    vector_db = VectorDBService()

    # 3. StatData 형태로 변환 (간단한 객체)
    print("\n[3단계] 데이터 변환")
    class StatDataMock:
        def __init__(self, row_data):
            self.year = row_data.get('year')
            self.data = row_data.get('data', {})
            self.table_name = row_data.get('table_name', '')
            self.period_text = row_data.get('period_text', '')

    stat_data_list = [StatDataMock(row) for row in test_data.get('statistics', [])]
    print(f"- 변환 완료: {len(stat_data_list)}개 행")

    # 4. 벡터 DB에 저장
    print("\n[4단계] 벡터 DB에 저장")
    print("-" * 80)

    chunk_count = vector_db.store_stat_data(
        cache_key=test_cache_key,
        stat_name="국토지표의 진전",
        stat_data=stat_data_list,
        metadata=None
    )

    print("-" * 80)
    print(f"[OK] 저장 완료: {chunk_count}개 청크 생성됨")

    # 5. 검색 테스트
    print("\n[5단계] 검색 테스트")
    print("-" * 80)

    test_queries = [
        "2020년 국토면적",
        "교통 인프라",
        "주택 보급률"
    ]

    for query in test_queries:
        print(f"\n[SEARCH] 검색어: '{query}'")
        results = vector_db.search_relevant_data(
            cache_key=test_cache_key,
            query=query,
            n_results=3
        )

        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])

        if documents:
            for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
                print(f"\n  [{i}] {doc[:150]}...")
                print(f"      Meta: year={meta.get('year')}, category={meta.get('category')}")
        else:
            print("  [NO RESULT]")

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)

if __name__ == "__main__":
    test_improved_vector_db()
