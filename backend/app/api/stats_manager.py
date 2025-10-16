from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pathlib import Path
from app.models.stat_models import (
    RecentStatsResponse,
    StatMetadata,
    StatData
)
from app.services.crawler_service import CrawlerService
from app.services.data_storage import DataStorageService
from datetime import datetime, timedelta
import json
import os
import numpy as np

router = APIRouter()
crawler_service = CrawlerService()
storage_service = DataStorageService()

# 캐시 저장소
_cache = {
    'recent_stats': None,
    'cache_time': None
}

# 캐시 TTL (5분)
CACHE_TTL_MINUTES = 5

@router.get("/recent-stats", response_model=RecentStatsResponse)
async def get_recent_stats():
    """최근 통계 목록 조회 - 캐시 및 fallback 지원"""
    try:
        now = datetime.now()

        # 캐시 확인
        if (_cache['recent_stats'] and _cache['cache_time'] and
            (now - _cache['cache_time']).seconds < CACHE_TTL_MINUTES * 60):
            print("캐시에서 최신 통계 데이터 반환")
            return _cache['recent_stats']

        print("새로운 통계 데이터 크롤링 시작")

        # 크롤링 시도
        stats = await crawler_service.get_recent_stats()

        # 크롤링 결과 검증
        if not stats or len(stats) == 0:
            print("크롤링 결과가 없습니다.")
            raise Exception("크롤링 결과가 없습니다.")

        # 실제 데이터인지 확인 (더미 데이터가 아닌지)
        if len(stats) > 0 and any(stat.id.startswith('dummy_') for stat in stats):
            print("더미 데이터가 감지되었습니다. 실제 크롤링을 다시 시도합니다.")
            raise Exception("더미 데이터가 감지되었습니다.")

        response = RecentStatsResponse(
            stats=stats,
            total_count=len(stats)
        )

        # 캐시 저장
        _cache['recent_stats'] = response
        _cache['cache_time'] = now

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{stat_id}/metadata", response_model=StatMetadata)
async def get_stat_metadata(stat_id: str):
    """특정 통계의 메타데이터 조회"""
    try:
        metadata = await crawler_service.get_stat_metadata(stat_id)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats-list", summary="수집된 통계표 목록 조회")
async def get_collected_stats_list():
    """수집된 모든 통계표의 실제 통계표명 목록 반환"""
    try:
        storage_service = DataStorageService()
        stats_list = []

        # 모든 메타데이터 파일 확인
        if not os.path.exists(storage_service.metadata_dir):
            return {"message": "수집된 통계표가 없습니다", "stats": []}

        for filename in os.listdir(storage_service.metadata_dir):
            if not filename.endswith('_metadata.json'):
                continue

            file_path = os.path.join(storage_service.metadata_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                metadata_dict = data['metadata']
                cache_key = data['cache_key']

                # 통계 데이터 로드하여 기본 정보 확인
                stat_url = data['stat_url']
                stat_data = storage_service.load_statistics(stat_url)

                # 데이터 필드 분석
                total_fields = 0
                numeric_fields = 0
                text_fields = 0
                table_names = set()

                if stat_data:
                    for item in stat_data:
                        if hasattr(item, 'table_name') and item.table_name:
                            table_names.add(item.table_name)
                        if item.data:
                            total_fields += len(item.data)
                            for key, value in item.data.items():
                                try:
                                    if isinstance(value, (int, float)):
                                        numeric_fields += 1
                                    elif isinstance(value, str):
                                        try:
                                            float(value.replace(',', '').replace('%', ''))
                                            numeric_fields += 1
                                        except ValueError:
                                            text_fields += 1
                                    else:
                                        text_fields += 1
                                except:
                                    text_fields += 1

                # title에서 통계명만 추출 (최신목록 형식과 동일하게)
                full_title = metadata_dict.get('title', 'Unknown')
                stat_name_display = full_title

                # "-" 앞부분만 사용 (테이블명 제거)
                if '-' in full_title:
                    stat_name_display = full_title.split('-')[0].strip()

                # 괄호 안의 영문, 숫자만 제거 (한글은 유지 - 준공, 착공 등 구분용)
                import re
                # 영문, 숫자, 공백, 특수문자만 포함된 괄호를 반복적으로 제거
                # 예: "(1999 ~ 2024)" 제거, 하지만 "(준공)", "(인허가)" 유지
                prev_display = ''
                while prev_display != stat_name_display:
                    prev_display = stat_name_display
                    stat_name_display = re.sub(r'\([A-Za-z0-9\s.,\-/~]+\)', '', stat_name_display).strip()

                stat_info = {
                    "stat_name": stat_name_display,
                    "full_title": full_title,  # 원본 title도 저장 (필요시 사용)
                    "cache_key": cache_key,
                    "stat_url": stat_url,
                    "department": metadata_dict.get('department', ''),
                    "keywords": metadata_dict.get('keywords', []),
                    "total_data_points": len(stat_data) if stat_data else 0,
                    "data_fields_info": {
                        "total_fields": total_fields,
                        "numeric_fields": numeric_fields,
                        "text_fields": text_fields
                    },
                    "table_names": list(table_names),
                    "saved_at": data.get('saved_at', '')
                }

                stats_list.append(stat_info)

            except Exception as e:
                print(f"메타데이터 파일 처리 오류: {filename} -> {e}")
                continue

        # 저장 시간 기준 내림차순 정렬
        stats_list.sort(key=lambda x: x['saved_at'], reverse=True)

        return {
            "total_collected_stats": len(stats_list),
            "stats": stats_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계표 목록 조회 오류: {str(e)}")

@router.get("/stats-detail/{stat_name}", summary="통계표명별 상세 정보")
async def get_stat_detail_by_name(stat_name: str):
    """실제 통계표명으로 상세 정보 조회 - 총 데이터 필드, 숫자/텍스트 데이터 구분, 샘플 데이터"""
    try:
        storage_service = DataStorageService()
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)

        if not metadata or not stat_data:
            raise HTTPException(status_code=404, detail="해당 통계표 데이터를 찾을 수 없습니다")

        # 통계표별로 데이터 그룹화
        table_groups = {}
        table_counter = 1
        for data_item in stat_data:
            table_name = getattr(data_item, 'table_name', None)

            # 테이블명이 없거나 기본값인 경우 개선된 이름 사용
            if not table_name or table_name in ['', '기본 통계표']:
                # 메타데이터에서 키워드 사용하여 의미있는 이름 생성
                if metadata and metadata.keywords:
                    table_name = f"{metadata.keywords[0]} 통계표 {table_counter}"
                else:
                    table_name = f"통계표 {table_counter}"
                table_counter += 1
            elif table_name.startswith('테이블') and table_name[2:].isdigit():
                # "테이블1", "테이블2" 같은 기본값 개선
                if metadata and metadata.keywords:
                    table_name = f"{metadata.keywords[0]} {table_name}"
                else:
                    table_name = f"수집된 {table_name}"

            if table_name not in table_groups:
                table_groups[table_name] = []
            table_groups[table_name].append(data_item)

        # 각 통계표별 상세 분석
        tables_detail = {}
        for table_name, table_data in table_groups.items():
            # 데이터 필드 분석
            all_fields = set()
            numeric_fields = set()
            text_fields = set()

            for item in table_data:
                if item.data:
                    all_fields.update(item.data.keys())
                    for key, value in item.data.items():
                        try:
                            if isinstance(value, (int, float)):
                                numeric_fields.add(key)
                            elif isinstance(value, str):
                                try:
                                    float(value.replace(',', '').replace('%', ''))
                                    numeric_fields.add(key)
                                except ValueError:
                                    text_fields.add(key)
                            else:
                                text_fields.add(key)
                        except:
                            text_fields.add(key)

            # 샘플 데이터 (처음 3개)
            sample_data = []
            for i, item in enumerate(table_data[:3]):
                sample = {
                    "sample_index": i + 1,
                    "year": item.year,
                    "data_preview": {}
                }

                if item.data:
                    # 중요한 필드 우선 (숫자 데이터 먼저)
                    sorted_fields = sorted(item.data.items(),
                                         key=lambda x: (x[0] not in numeric_fields, x[0]))

                    for key, value in sorted_fields[:5]:  # 최대 5개 필드
                        sample["data_preview"][key] = {
                            "value": value,
                            "type": "numeric" if key in numeric_fields else "text"
                        }

                sample_data.append(sample)

            tables_detail[table_name] = {
                "total_records": len(table_data),
                "year_range": {
                    "min_year": min([item.year for item in table_data]) if table_data else None,
                    "max_year": max([item.year for item in table_data]) if table_data else None
                },
                "data_fields": {
                    "total_fields": len(all_fields),
                    "numeric_fields": list(numeric_fields),
                    "text_fields": list(text_fields),
                    "numeric_count": len(numeric_fields),
                    "text_count": len(text_fields)
                },
                "sample_data": sample_data
            }

        return {
            "stat_name": stat_name,
            "stat_url": stat_url,
            "metadata": {
                "title": metadata.title,
                "department": metadata.department,
                "keywords": metadata.keywords,
                "purpose": getattr(metadata, 'purpose', None),
                "frequency": getattr(metadata, 'frequency', None),
                "contact": getattr(metadata, 'contact', None),
                "search_field": getattr(metadata, 'search_field', None),
                "responsible_department": getattr(metadata, 'responsible_department', None),
                "statistical_info": getattr(metadata, 'statistical_info', None),
                "major_items": getattr(metadata, 'major_items', None),
                "meaning_analysis": getattr(metadata, 'meaning_analysis', None),
                "terminology": getattr(metadata, 'terminology', None),
                "related_terms": getattr(metadata, 'related_terms', None)
            },
            "total_tables": len(tables_detail),
            "total_data_points": len(stat_data),
            "tables_detail": tables_detail
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계표 상세 정보 조회 오류: {str(e)}")

@router.get("/stats-distribution/{stat_name}", summary="통계표별 데이터 분포 특성 분석")
async def get_stat_distribution_analysis(stat_name: str):
    """통계표명별 데이터 분포 특성 및 통계적 특성 분석"""
    try:
        storage_service = DataStorageService()
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)

        if not metadata or not stat_data:
            raise HTTPException(status_code=404, detail="해당 통계표 데이터를 찾을 수 없습니다")

        # 통계표별 분포 분석
        table_groups = {}
        table_counter = 1
        for data_item in stat_data:
            table_name = getattr(data_item, 'table_name', None)

            # 실제 수집된 테이블명 사용 - 키워드 추가하지 않음
            if not table_name or table_name.strip() in ['', '기본 통계표']:
                # 테이블명이 완전히 없는 경우만 기본명 사용
                table_name = f"통계표 {table_counter}"
                table_counter += 1
            # 실제 수집된 테이블명이 있으면 그대로 사용 (키워드 추가 제거)

            if table_name not in table_groups:
                table_groups[table_name] = []
            table_groups[table_name].append(data_item)

        distribution_analysis = {}

        for table_name, table_data in table_groups.items():
            # 숫자 데이터 수집
            numeric_values = []
            field_distributions = {}

            for item in table_data:
                if item.data:
                    for key, value in item.data.items():
                        if key not in field_distributions:
                            field_distributions[key] = {"values": [], "type": "unknown"}

                        try:
                            if isinstance(value, (int, float)):
                                numeric_val = float(value)
                                numeric_values.append(numeric_val)
                                field_distributions[key]["values"].append(numeric_val)
                                field_distributions[key]["type"] = "numeric"
                            elif isinstance(value, str):
                                try:
                                    numeric_val = float(value.replace(',', '').replace('%', ''))
                                    numeric_values.append(numeric_val)
                                    field_distributions[key]["values"].append(numeric_val)
                                    field_distributions[key]["type"] = "numeric"
                                except ValueError:
                                    field_distributions[key]["values"].append(value)
                                    field_distributions[key]["type"] = "text"
                            else:
                                field_distributions[key]["values"].append(str(value))
                                field_distributions[key]["type"] = "text"
                        except:
                            field_distributions[key]["values"].append(str(value))
                            field_distributions[key]["type"] = "text"

            # 기초 통계 계산
            basic_stats = {}
            if numeric_values:
                basic_stats = {
                    "count": len(numeric_values),
                    "mean": float(np.mean(numeric_values)),
                    "median": float(np.median(numeric_values)),
                    "std": float(np.std(numeric_values)),
                    "min": float(np.min(numeric_values)),
                    "max": float(np.max(numeric_values)),
                    "quartiles": {
                        "q1": float(np.percentile(numeric_values, 25)),
                        "q2": float(np.percentile(numeric_values, 50)),
                        "q3": float(np.percentile(numeric_values, 75))
                    },
                    "skewness": float(np.mean(((np.array(numeric_values) - np.mean(numeric_values)) / np.std(numeric_values)) ** 3)) if len(numeric_values) > 2 else 0
                }

            # 필드별 상세 분포
            field_stats = {}
            for field_name, field_info in field_distributions.items():
                if field_info["type"] == "numeric" and len(field_info["values"]) > 0:
                    values = field_info["values"]
                    field_stats[field_name] = {
                        "type": "numeric",
                        "count": len(values),
                        "mean": float(np.mean(values)),
                        "std": float(np.std(values)),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "range": float(np.max(values) - np.min(values)),
                        "coefficient_of_variation": float(np.std(values) / np.mean(values)) if np.mean(values) != 0 else 0
                    }
                elif field_info["type"] == "text":
                    values = field_info["values"]
                    unique_values = list(set(values))
                    field_stats[field_name] = {
                        "type": "text",
                        "count": len(values),
                        "unique_count": len(unique_values),
                        "most_common": max(set(values), key=values.count) if values else None,
                        "sample_values": unique_values[:5]
                    }

            # 데이터 품질 평가
            data_quality = {
                "completeness": len([item for item in table_data if item.data]) / len(table_data) * 100 if table_data else 0,
                "consistency": len([f for f, info in field_distributions.items() if info["type"] != "unknown"]) / len(field_distributions) * 100 if field_distributions else 0,
                "numeric_ratio": len([f for f, info in field_distributions.items() if info["type"] == "numeric"]) / len(field_distributions) * 100 if field_distributions else 0
            }

            distribution_analysis[table_name] = {
                "basic_statistics": basic_stats,
                "field_statistics": field_stats,
                "data_quality": data_quality,
                "distribution_characteristics": {
                    "total_numeric_values": len(numeric_values),
                    "data_variability": "높음" if basic_stats.get("std", 0) / basic_stats.get("mean", 1) > 0.5 else "낮음" if basic_stats.get("std", 0) / basic_stats.get("mean", 1) < 0.2 else "보통",
                    "distribution_type": "정규분포 유사" if abs(basic_stats.get("skewness", 0)) < 0.5 else "치우침 분포"
                }
            }

        return {
            "stat_name": stat_name,
            "analysis_type": "데이터 분포 특성 분석",
            "total_tables": len(distribution_analysis),
            "analysis_date": datetime.now().isoformat(),
            "distribution_analysis": distribution_analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분포 특성 분석 오류: {str(e)}")

@router.get("/stats-summary/{stat_name}", summary="통계표별 객관적 현황 요약")
async def get_stat_objective_summary(stat_name: str):
    """통계표명별 객관적이고 구체적인 현황 요약 제공"""
    try:
        storage_service = DataStorageService()
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)

        if not metadata or not stat_data:
            raise HTTPException(status_code=404, detail="해당 통계표 데이터를 찾을 수 없습니다")

        # 통계표별 객관적 요약 생성
        table_groups = {}
        table_counter = 1
        for data_item in stat_data:
            table_name = getattr(data_item, 'table_name', None)

            # 실제 수집된 테이블명 사용 - 키워드 추가하지 않음
            if not table_name or table_name.strip() in ['', '기본 통계표']:
                # 테이블명이 완전히 없는 경우만 기본명 사용
                table_name = f"통계표 {table_counter}"
                table_counter += 1
            # 실제 수집된 테이블명이 있으면 그대로 사용 (키워드 추가 제거)

            if table_name not in table_groups:
                table_groups[table_name] = []
            table_groups[table_name].append(data_item)

        table_summaries = {}

        for table_name, table_data in table_groups.items():
            # 기본 정보 수집
            years = [item.year for item in table_data if item.year]
            total_records = len(table_data)

            # 데이터 필드 분석
            all_fields = set()
            numeric_values = []
            field_analysis = {}

            for item in table_data:
                if item.data:
                    all_fields.update(item.data.keys())
                    for key, value in item.data.items():
                        if key not in field_analysis:
                            field_analysis[key] = {"numeric_values": [], "text_values": [], "type": "unknown"}

                        try:
                            if isinstance(value, (int, float)):
                                numeric_val = float(value)
                                numeric_values.append(numeric_val)
                                field_analysis[key]["numeric_values"].append(numeric_val)
                                field_analysis[key]["type"] = "numeric"
                            elif isinstance(value, str):
                                try:
                                    numeric_val = float(value.replace(',', '').replace('%', ''))
                                    numeric_values.append(numeric_val)
                                    field_analysis[key]["numeric_values"].append(numeric_val)
                                    field_analysis[key]["type"] = "numeric"
                                except ValueError:
                                    field_analysis[key]["text_values"].append(value)
                                    field_analysis[key]["type"] = "text"
                        except:
                            field_analysis[key]["text_values"].append(str(value))
                            field_analysis[key]["type"] = "text"

            # 객관적 현황 요약 생성
            summary_parts = []

            # 1. 기본 현황
            summary_parts.append(f"'{table_name}' 통계표는 총 {total_records}개의 데이터 레코드를 포함합니다.")

            if years:
                if min(years) == max(years):
                    summary_parts.append(f"{min(years)}년 기준 데이터입니다.")
                else:
                    summary_parts.append(f"{min(years)}년부터 {max(years)}년까지 {max(years) - min(years) + 1}년간의 시계열 데이터입니다.")

            # 2. 데이터 구성
            numeric_fields = [k for k, v in field_analysis.items() if v["type"] == "numeric"]
            text_fields = [k for k, v in field_analysis.items() if v["type"] == "text"]

            summary_parts.append(f"총 {len(all_fields)}개 데이터 필드 중 {len(numeric_fields)}개는 수치형, {len(text_fields)}개는 텍스트형 데이터입니다.")

            # 3. 수치 데이터 특성
            if numeric_values:
                mean_val = np.mean(numeric_values)
                median_val = np.median(numeric_values)
                max_val = np.max(numeric_values)
                min_val = np.min(numeric_values)
                std_val = np.std(numeric_values)

                summary_parts.append(f"수치 데이터의 평균은 {mean_val:,.1f}, 중앙값은 {median_val:,.1f}이며, {min_val:,.1f}에서 {max_val:,.1f}까지의 범위를 가집니다.")

                # 변동성 평가
                cv = std_val / mean_val if mean_val != 0 else 0
                if cv < 0.1:
                    variability = "매우 안정적"
                elif cv < 0.3:
                    variability = "안정적"
                elif cv < 0.7:
                    variability = "변동성이 있는"
                else:
                    variability = "변동성이 매우 큰"

                summary_parts.append(f"데이터 변동성은 {variability} 특성을 보입니다 (변동계수: {cv:.3f}).")

            # 4. 핵심 필드 식별
            if numeric_fields:
                # 가장 변동이 큰 필드와 안정적인 필드 찾기
                field_variations = {}
                for field in numeric_fields:
                    values = field_analysis[field]["numeric_values"]
                    if len(values) > 1:
                        cv = np.std(values) / np.mean(values) if np.mean(values) != 0 else 0
                        field_variations[field] = cv

                if field_variations:
                    most_variable = max(field_variations, key=field_variations.get)
                    most_stable = min(field_variations, key=field_variations.get)
                    summary_parts.append(f"'{most_variable}' 필드가 가장 변동성이 크며, '{most_stable}' 필드가 가장 안정적입니다.")

            # 5. 데이터 품질 평가
            completeness = len([item for item in table_data if item.data and any(item.data.values())]) / len(table_data) * 100
            summary_parts.append(f"데이터 완성도는 {completeness:.1f}%입니다.")

            # 6. 주요 통계 지표 (상위 3개 필드)
            key_insights = []
            for field in numeric_fields[:3]:
                values = field_analysis[field]["numeric_values"]
                if len(values) > 1:
                    total = sum(values)
                    avg = np.mean(values)
                    growth = ((values[-1] - values[0]) / values[0] * 100) if len(values) > 1 and values[0] != 0 else 0
                    key_insights.append(f"'{field}': 총합 {total:,.0f}, 평균 {avg:,.1f}, 증감률 {growth:+.1f}%")

            if key_insights:
                summary_parts.append("주요 지표별 현황: " + ", ".join(key_insights[:2]))

            objective_summary = " ".join(summary_parts)

            table_summaries[table_name] = {
                "objective_summary": objective_summary,
                "key_metrics": {
                    "total_records": total_records,
                    "year_span": max(years) - min(years) + 1 if years else 0,
                    "field_count": len(all_fields),
                    "numeric_field_count": len(numeric_fields),
                    "data_completeness": completeness,
                    "key_numeric_fields": numeric_fields[:5]
                },
                "data_insights": key_insights
            }

        return {
            "stat_name": stat_name,
            "analysis_type": "객관적 현황 요약",
            "metadata": {
                "title": metadata.title,
                "department": metadata.department,
                "keywords": metadata.keywords,
                "purpose": getattr(metadata, 'purpose', None),
                "frequency": getattr(metadata, 'frequency', None),
                "contact": getattr(metadata, 'contact', None),
                "search_field": getattr(metadata, 'search_field', None),
                "responsible_department": getattr(metadata, 'responsible_department', None),
                "statistical_info": getattr(metadata, 'statistical_info', None),
                "major_items": getattr(metadata, 'major_items', None),
                "meaning_analysis": getattr(metadata, 'meaning_analysis', None),
                "terminology": getattr(metadata, 'terminology', None),
                "related_terms": getattr(metadata, 'related_terms', None)
            },
            "total_tables": len(table_summaries),
            "analysis_date": datetime.now().isoformat(),
            "table_summaries": table_summaries
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"객관적 현황 요약 생성 오류: {str(e)}")

@router.get("/stats/suggest-urls", summary="통계명으로 URL 제안")
async def suggest_urls_by_name(stat_name: str):
    """통계명을 기반으로 올바른 URL들을 제안"""
    try:
        from app.services.url_validator import URLValidator

        url_validator = URLValidator()
        suggestions = url_validator.suggest_urls_by_name(stat_name)

        return {
            "stat_name": stat_name,
            "suggestions": [
                {
                    "rsid": stat.rsid,
                    "name": stat.name,
                    "category": stat.category,
                    "description": stat.description,
                    "keywords": stat.keywords,
                    "url": stat.correct_url
                }
                for stat in suggestions
            ],
            "total_suggestions": len(suggestions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL 제안 생성 오류: {str(e)}")

@router.get("/stats/available", summary="사용 가능한 모든 통계 목록")
async def get_available_stats():
    """사용 가능한 모든 국토교통부 통계 목록"""
    try:
        from app.services.url_validator import URLValidator

        url_validator = URLValidator()
        all_stats = url_validator.get_all_available_stats()

        return {
            "available_stats": [
                {
                    "rsid": stat.rsid,
                    "name": stat.name,
                    "category": stat.category,
                    "description": stat.description,
                    "keywords": stat.keywords,
                    "url": stat.correct_url
                }
                for stat in all_stats
            ],
            "total_count": len(all_stats)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용 가능한 통계 목록 조회 오류: {str(e)}")

@router.delete("/stats/{cache_key}", summary="수집된 통계표 삭제")
async def delete_collected_stat(cache_key: str):
    """수집된 통계표 삭제 - 메타데이터, 통계 데이터, Excel 파일, 다운로드된 원본 파일, 벡터 DB 모두 삭제"""
    try:
        print(f"통계표 삭제 시작: {cache_key}")

        # 벡터 DB 삭제 (cache_key 기반)
        try:
            from app.services.vector_db_service import vector_db_service
            vector_db_service.delete_collection(cache_key)
            print(f"벡터 DB 컬렉션 삭제 완료: cache_{cache_key}")
        except Exception as e:
            print(f"벡터 DB 삭제 중 오류 (무시하고 계속): {e}")

        # 기본 파일들 목록
        files_to_delete = [
            Path(f"data/metadata/{cache_key}_metadata.json"),
            Path(f"data/statistics/{cache_key}_stats.json"),
            Path(f"data/excel/{cache_key}_data.xlsx")
        ]

        # stat_data에서 downloaded_file_path 정보 확인하여 원본 파일도 삭제 목록에 추가
        download_files_set = set()  # 중복 제거를 위한 set
        try:
            stats_file = Path(f"data/statistics/{cache_key}_stats.json")
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats_data = json.load(f)

                # 통계 데이터에서 downloaded_file_path 추출
                if 'statistics' in stats_data:
                    for stat_item in stats_data['statistics']:
                        downloaded_path = stat_item.get('downloaded_file_path')
                        if downloaded_path:
                            # 상대 경로를 절대 경로로 변환
                            full_path = Path(downloaded_path)
                            if full_path.exists() and str(full_path) not in download_files_set:
                                download_files_set.add(str(full_path))
                                files_to_delete.append(full_path)
                                print(f"다운로드 파일 삭제 대상 추가: {full_path}")
        except Exception as e:
            print(f"다운로드 파일 경로 확인 중 오류 (무시하고 계속): {e}")

        deleted_files = []
        errors = []

        # 각 파일 삭제 시도
        for file_path in files_to_delete:
            try:
                if file_path.exists():
                    file_path.unlink()  # 파일 삭제
                    deleted_files.append(str(file_path))
                    print(f"파일 삭제 완료: {file_path}")
                else:
                    print(f"파일이 존재하지 않음: {file_path}")
            except Exception as delete_error:
                error_msg = f"파일 삭제 실패 ({file_path}): {delete_error}"
                errors.append(error_msg)
                print(error_msg)

        # 결과 생성
        if deleted_files and not errors:
            result = {
                "success": True,
                "message": f"통계표 '{cache_key}'가 성공적으로 삭제되었습니다 (원본 파일 및 벡터 DB 포함).",
                "deleted_files": deleted_files,
                "cache_key": cache_key,
                "vector_db_deleted": True
            }
            print(f"통계표 삭제 완료: {cache_key}")
        elif deleted_files and errors:
            result = {
                "success": True,
                "message": f"통계표 '{cache_key}'가 부분적으로 삭제되었습니다.",
                "deleted_files": deleted_files,
                "errors": errors,
                "cache_key": cache_key,
                "vector_db_deleted": True
            }
            print(f"통계표 부분 삭제: {cache_key}")
        else:
            result = {
                "success": False,
                "message": f"통계표 '{cache_key}'를 삭제할 파일을 찾을 수 없습니다.",
                "errors": errors if errors else ["삭제할 파일이 없습니다."],
                "cache_key": cache_key,
                "vector_db_deleted": True
            }
            print(f"통계표 삭제 실패: {cache_key}")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계표 삭제 오류: {str(e)}")