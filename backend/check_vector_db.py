"""벡터 DB 데이터 확인 스크립트"""
import sys
sys.path.insert(0, 'C:/Users/jyj96/statsStory/backend')

from app.services.vector_db_service import vector_db_service

# 송변전설비 현황 컬렉션 확인
stat_name = '송변전설비 현황'
stats = vector_db_service.get_collection_stats(stat_name)

print('=' * 60)
print('=== 벡터 DB 통계 ===')
print('=' * 60)
print(f'통계명: {stats["stat_name"]}')
print(f'문서 개수: {stats["document_count"]}')
print(f'존재 여부: {stats["exists"]}')
print()

# 실제 데이터 샘플 확인
if stats['exists'] and stats['document_count'] > 0:
    samples = vector_db_service.get_all_data_for_analysis(stat_name, limit=5)
    print('=' * 60)
    print(f'=== 데이터 샘플 (최대 5개) ===')
    print('=' * 60)
    for i, sample in enumerate(samples, 1):
        print(f'\n샘플 {i}:')
        print(f'  Year: {sample.get("year")}')
        print(f'  Table: {sample.get("table_name")}')
        doc = sample.get("document", "")
        print(f'  Document 길이: {len(doc)}자')
        print(f'  Document 내용: {doc[:300]}...')
        print(f'  Metadata: {sample.get("metadata")}')
else:
    print('⚠️ 벡터 DB에 데이터가 없습니다!')

# 메타데이터 확인
print('\n' + '=' * 60)
print('=== 메타데이터 파일 확인 ===')
print('=' * 60)

import json
from pathlib import Path

metadata_dir = Path('data/metadata')
for file in metadata_dir.glob('*_metadata.json'):
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        title = data.get('metadata', {}).get('title', '')
        if '송변전설비' in title:
            print(f'\n파일: {file.name}')
            print(f'제목: {title}')

            # AI 인사이트 확인
            ai_insights = data.get('metadata', {}).get('ai_insights')
            if ai_insights:
                print(f'AI 인사이트 존재: ✅')
                print(f'  - insights_count: {ai_insights.get("insights_count", 0)}')
                print(f'  - model: {ai_insights.get("model", "Unknown")}')
                print(f'  - raw_text 길이: {len(ai_insights.get("raw_text", ""))}자')

                # 인사이트 내용 확인
                for key in ['insight_1', 'insight_2', 'insight_10']:
                    if key in ai_insights:
                        insight = ai_insights[key]
                        print(f'\n  {key}:')
                        print(f'    - category: {insight.get("category")}')
                        print(f'    - content: {insight.get("content", "")[:150]}...')
            else:
                print(f'AI 인사이트 존재: ❌')
