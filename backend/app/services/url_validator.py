#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""국토교통부 통계 URL 검증 및 제안 서비스"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class StatInfo:
    """통계 정보"""
    rsid: str
    name: str
    category: str
    description: str
    keywords: List[str]
    correct_url: str

class URLValidator:
    """국토교통부 통계 URL 검증 및 제안 서비스"""

    def __init__(self):
        # 알려진 국토교통부 통계 정보 데이터베이스
        self.stat_database = {
            "31": StatInfo(
                rsid="31",
                name="주택건설실적통계(인허가)",
                category="주택건설",
                description="주택 허가·신고·사업계획 승인 호수",
                keywords=["주택건설", "인허가", "허가", "신고", "사업계획"],
                correct_url="https://stat.molit.go.kr/portal/cate/statView.do?hRsId=31&hFormId=2086&hDivEng=&month_yn="
            ),
            "471": StatInfo(
                rsid="471",
                name="주택건설실적통계(착공)",
                category="주택건설",
                description="주택건설 착공실적 통계",
                keywords=["주택건설", "착공", "착공실적"],
                correct_url="https://stat.molit.go.kr/portal/cate/statView.do?hRsId=471&hFormId=5386&hDivEng=&month_yn="
            ),
            "468": StatInfo(
                rsid="468",
                name="주택건설실적통계(준공)",
                category="주택건설",
                description="주택건설 준공실적 통계",
                keywords=["주택건설", "준공", "준공실적"],
                correct_url="https://stat.molit.go.kr/portal/cate/statView.do?hRsId=468&hFormId=&hDivEng=&month_yn="
            ),
            "488": StatInfo(
                rsid="488",
                name="공동주택 분양승인 실적",
                category="주택분양",
                description="공동주택 분양승인 실적 통계",
                keywords=["공동주택", "분양", "분양승인", "아파트"],
                correct_url="https://stat.molit.go.kr/portal/cate/statView.do?hRsId=488&hFormId=5387&hDivEng=&month_yn="
            ),
            "489": StatInfo(
                rsid="489",
                name="도시형생활주택 인허가 실적",
                category="도시형생활주택",
                description="도시형생활주택 인허가 실적 통계",
                keywords=["도시형생활주택", "인허가", "도시형", "생활주택"],
                correct_url="https://stat.molit.go.kr/portal/cate/statView.do?hRsId=489&hFormId=&hDivEng=&month_yn="
            ),
            "32": StatInfo(
                rsid="32",
                name="미분양주택현황보고",
                category="미분양",
                description="미분양주택 현황 통계",
                keywords=["미분양", "미분양주택", "재고"],
                correct_url="https://stat.molit.go.kr/portal/cate/statView.do?hRsId=32&hFormId=2086&hDivEng=&month_yn="
            ),
            "37": StatInfo(
                rsid="37",
                name="임대주택통계",
                category="임대주택",
                description="임대주택 건설 및 전환 실적",
                keywords=["임대주택", "임대", "공공임대"],
                correct_url="https://stat.molit.go.kr/portal/cate/statView.do?hRsId=37&hFormId=&hDivEng=&month_yn="
            )
        }

    def extract_rsid_from_url(self, url: str) -> Optional[str]:
        """URL에서 hRsId 파라미터 추출"""
        try:
            match = re.search(r'hRsId=(\d+)', url)
            return match.group(1) if match else None
        except:
            return None

    def validate_url_and_suggest(self, url: str, collected_table_names: List[str], requested_stat_name: str = None) -> Dict:
        """URL을 검증하고 올바른 URL 제안"""
        result = {
            "is_valid": True,
            "validation_warnings": [],
            "suggested_urls": [],
            "url_mismatch": False,
            "correct_url": None,
            "detected_stat_name": None
        }

        # URL에서 rsid 추출
        current_rsid = self.extract_rsid_from_url(url)
        if not current_rsid:
            result["is_valid"] = False
            result["validation_warnings"].append("URL에서 hRsId 파라미터를 찾을 수 없습니다")
            return result

        # 현재 URL의 통계 정보 확인
        current_stat = self.stat_database.get(current_rsid)
        if not current_stat:
            result["validation_warnings"].append(f"알 수 없는 통계 ID (hRsId={current_rsid})")

        # 요청한 통계명과 URL의 일치성 검사
        if requested_stat_name and current_stat:
            # 요청한 통계명에서 핵심 키워드 추출
            requested_name_lower = requested_stat_name.lower().replace(" ", "")
            current_stat_name_lower = current_stat.name.lower().replace(" ", "")

            # 요청한 통계명과 URL이 일치하지 않는지 확인
            if requested_name_lower not in current_stat_name_lower and current_stat_name_lower not in requested_name_lower:
                # 키워드별 매칭도 확인
                requested_keywords = self._extract_keywords_from_name(requested_stat_name)
                stat_keywords = current_stat.keywords

                keyword_overlap = len(set(requested_keywords) & set(stat_keywords))

                if keyword_overlap == 0:
                    result["url_mismatch"] = True
                    result["validation_warnings"].append(
                        f"요청한 통계명('{requested_stat_name}')과 URL의 통계({current_stat.name})가 일치하지 않습니다"
                    )

                    # 요청한 통계명에 맞는 올바른 URL 찾기
                    suggested_stat = self._find_matching_stat_by_name(requested_stat_name)
                    if suggested_stat:
                        result["correct_url"] = suggested_stat.correct_url
                        result["detected_stat_name"] = suggested_stat.name
                        result["validation_warnings"].append(
                            f"'{requested_stat_name}'에 해당하는 올바른 URL: {suggested_stat.correct_url}"
                        )

        # 수집된 테이블명과 예상 통계명 비교
        if collected_table_names and current_stat and not result["url_mismatch"]:
            expected_keywords = current_stat.keywords
            table_text = " ".join(collected_table_names).lower()

            # 키워드 매칭 검사
            keyword_matches = sum(1 for keyword in expected_keywords if keyword in table_text)

            if keyword_matches == 0:
                # 수집된 데이터와 URL이 일치하지 않음
                result["url_mismatch"] = True
                result["validation_warnings"].append(
                    f"요청한 URL({current_stat.name})과 실제 수집된 데이터가 일치하지 않습니다"
                )

                # 수집된 데이터를 기반으로 올바른 통계 찾기
                suggested_stat = self._find_matching_stat_by_table_names(collected_table_names)
                if suggested_stat:
                    result["correct_url"] = suggested_stat.correct_url
                    result["detected_stat_name"] = suggested_stat.name
                    result["validation_warnings"].append(
                        f"수집된 데이터는 '{suggested_stat.name}' 통계에 해당합니다"
                    )

        return result

    def _find_matching_stat_by_table_names(self, table_names: List[str]) -> Optional[StatInfo]:
        """테이블명을 기반으로 해당하는 통계 찾기"""
        table_text = " ".join(table_names).lower()

        best_match = None
        best_score = 0

        for stat in self.stat_database.values():
            score = 0
            for keyword in stat.keywords:
                if keyword in table_text:
                    score += 1

            # 통계명 직접 매칭도 확인
            if stat.name.replace(" ", "") in table_text.replace(" ", ""):
                score += 3

            if score > best_score:
                best_score = score
                best_match = stat

        return best_match if best_score > 0 else None

    def _extract_keywords_from_name(self, name: str) -> List[str]:
        """통계명에서 핵심 키워드 추출"""
        # 일반적인 통계 관련 키워드들
        common_keywords = [
            "도시형생활주택", "도시형", "생활주택", "인허가",
            "공동주택", "분양", "분양승인", "아파트",
            "주택건설", "착공", "준공", "실적",
            "미분양", "임대주택", "임대"
        ]

        found_keywords = []
        name_lower = name.lower()

        for keyword in common_keywords:
            if keyword in name_lower:
                found_keywords.append(keyword)

        return found_keywords

    def _find_matching_stat_by_name(self, stat_name: str) -> Optional[StatInfo]:
        """통계명으로 가장 적합한 통계 찾기"""
        best_match = None
        best_score = 0

        name_keywords = self._extract_keywords_from_name(stat_name)

        for stat in self.stat_database.values():
            score = 0

            # 키워드 매칭 점수
            keyword_matches = len(set(name_keywords) & set(stat.keywords))
            score += keyword_matches * 2

            # 통계명 직접 매칭 점수
            if stat.name.replace(" ", "").lower() in stat_name.replace(" ", "").lower():
                score += 5
            elif stat_name.replace(" ", "").lower() in stat.name.replace(" ", "").lower():
                score += 5

            if score > best_score:
                best_score = score
                best_match = stat

        return best_match if best_score > 0 else None

    def suggest_urls_by_name(self, stat_name: str) -> List[StatInfo]:
        """통계명으로 URL 제안"""
        suggestions = []
        name_lower = stat_name.lower().replace(" ", "")

        for stat in self.stat_database.values():
            stat_name_lower = stat.name.lower().replace(" ", "")

            # 통계명 포함 검사
            if name_lower in stat_name_lower or stat_name_lower in name_lower:
                suggestions.append(stat)
                continue

            # 키워드 매칭 검사
            keyword_matches = sum(1 for keyword in stat.keywords if keyword in stat_name)
            if keyword_matches >= 1:
                suggestions.append(stat)

        return suggestions

    def get_all_available_stats(self) -> List[StatInfo]:
        """사용 가능한 모든 통계 목록"""
        return list(self.stat_database.values())

    def format_validation_message(self, validation_result: Dict) -> str:
        """검증 결과를 사용자 친화적 메시지로 포맷"""
        if validation_result["is_valid"] and not validation_result["url_mismatch"]:
            return "URL이 올바르게 설정되었습니다."

        messages = []

        if validation_result["validation_warnings"]:
            messages.extend(validation_result["validation_warnings"])

        if validation_result["correct_url"]:
            messages.append(f"올바른 URL: {validation_result['correct_url']}")

        return " | ".join(messages)