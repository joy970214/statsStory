"""벡터 DB 컬렉션 목록 확인"""
import sys
sys.path.insert(0, 'C:/Users/jyj96/statsStory/backend')

from app.services.vector_db_service import vector_db_service

# 모든 컬렉션 확인
collections = vector_db_service.client.list_collections()

print('=' * 60)
print(f'=== 벡터 DB 컬렉션 목록 (총 {len(collections)}개) ===')
print('=' * 60)

for collection in collections:
    print(f'\n컬렉션 이름: {collection.name}')
    print(f'  메타데이터: {collection.metadata}')
    print(f'  문서 개수: {collection.count()}')

    # 샘플 데이터 확인
    if collection.count() > 0:
        samples = collection.get(limit=3, include=['metadatas'])
        if samples and samples.get('metadatas'):
            print(f'  샘플 메타데이터:')
            for i, meta in enumerate(samples['metadatas'][:2], 1):
                print(f'    {i}. {meta}')
