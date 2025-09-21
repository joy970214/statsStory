#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""메타데이터 수집 테스트"""

import sys
import os
import asyncio

# 백엔드 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.crawlers.optimized_molit_crawler import OptimizedMolitCrawler

async def test_metadata_collection():
    """메타데이터 수집 테스트"""
    print("=== 메타데이터 수집 테스트 ===")

    stat_url = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=471&hFormId=5386&hDivEng=&month_yn="

    crawler = OptimizedMolitCrawler()

    try:
        print(f"크롤링 시작: {stat_url}")

        # 크롤링 수행
        result = await crawler.crawl_comprehensive_statistics(
            stat_url=stat_url,
            stat_name="주택건설실적통계(착공) 메타데이터 테스트"
        )

        print(f"[SUCCESS] 크롤링 완료!")
        print(f"통계 제목: {result.stat_title}")
        print(f"수집된 테이블 수: {len(result.collected_tables)}")
        print(f"총 데이터 포인트: {result.total_data_points}")

        # 메타데이터 상세 확인
        metadata = result.metadata
        print(f"\n=== 메타데이터 상세 ===")
        print(f"제목: {metadata.title}")
        print(f"목적: {metadata.purpose}")
        print(f"주기: {metadata.frequency}")
        print(f"담당부서: {metadata.department}")
        print(f"키워드 수: {len(metadata.keywords)}")
        print(f"관련용어 수: {len(metadata.related_terms)}")
        print(f"통계정보 항목 수: {len(metadata.statistical_info)}")
        print(f"주요항목 수: {len(metadata.major_items)}")
        print(f"의미분석 수: {len(metadata.meaning_analysis)}")
        print(f"용어해설 수: {len(metadata.terminology)}")

        if metadata.keywords:
            print(f"키워드: {metadata.keywords}")

        if metadata.statistical_info:
            print(f"통계정보: {list(metadata.statistical_info.keys())[:5]}")

    except Exception as e:
        print(f"[ERROR] 메타데이터 수집 중 오류: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(test_metadata_collection())