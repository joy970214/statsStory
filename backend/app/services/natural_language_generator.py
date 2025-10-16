"""
자연어 텍스트 생성기
- 구조화된 데이터를 검색 가능한 자연어로 변환
- 다양한 패턴 템플릿 지원
"""
from typing import List, Dict, Any, Optional
import re


class NaturalLanguageGenerator:
    """통계 데이터를 자연어 텍스트로 변환하는 클래스"""

    def __init__(self):
        pass

    def generate(
        self,
        year: str,
        category: str,
        rows: List[Dict],
        structure: Dict[str, Any],
        table_name: str
    ) -> str:
        """
        데이터 행들을 자연어로 변환

        Args:
            year: 연도
            category: 카테고리 (대분류)
            rows: 해당 카테고리의 데이터 행들
            structure: 테이블 구조 정보
            table_name: 테이블 이름

        Returns:
            자연어 텍스트
        """
        if not rows:
            return ""

        # 구조에 따라 다른 생성 전략 선택
        if structure.get('has_hierarchy'):
            return self._generate_hierarchical(year, category, rows, structure, table_name)
        elif structure.get('is_geographic'):
            return self._generate_geographic(year, category, rows, structure, table_name)
        elif structure.get('is_timeseries'):
            return self._generate_timeseries(year, category, rows, structure, table_name)
        else:
            return self._generate_simple(year, category, rows, structure, table_name)

    def _generate_simple(
        self,
        year: str,
        category: str,
        rows: List[Dict],
        structure: Dict[str, Any],
        table_name: str
    ) -> str:
        """
        단순 형태: "{year}년 {category}: {metric1} {value1}{unit1}, {metric2} {value2}{unit2}, ..."
        """
        parts = []

        # 연도-카테고리 헤더
        header = f"{year}년 {category}"

        # 각 행에서 지표-값-단위 추출
        metrics = []
        for row in rows[:5]:  # 최대 5개까지
            metric_text = self._extract_metric_text(row, structure)
            if metric_text:
                metrics.append(metric_text)

        if metrics:
            parts.append(f"{header}: {', '.join(metrics)}")
        else:
            parts.append(header)

        # 테이블 출처 추가
        parts.append(f"(출처: {table_name})")

        return ". ".join(parts) + "."

    def _generate_hierarchical(
        self,
        year: str,
        category: str,
        rows: List[Dict],
        structure: Dict[str, Any],
        table_name: str
    ) -> str:
        """
        계층 구조: "{year}년 {category} 합계 {total_value}{unit} (세부: {detail1} {value1}, {detail2} {value2})"
        """
        # 합계 행 찾기
        total_row = None
        detail_rows = []

        for row in rows:
            data = row.get('data', {})
            data_str = str(data.values()).lower()

            if any(keyword in data_str for keyword in ['합계', '계', '총계']):
                total_row = row
            else:
                detail_rows.append(row)

        parts = []

        # 헤더
        header = f"{year}년 {category}"

        # 합계가 있으면 합계 먼저
        if total_row:
            total_text = self._extract_metric_text(total_row, structure)
            if total_text:
                parts.append(f"{header} 합계: {total_text}")
            else:
                parts.append(f"{header}")
        else:
            parts.append(f"{header}")

        # 세부 항목 (최대 3개)
        if detail_rows:
            details = []
            for row in detail_rows[:3]:
                detail_text = self._extract_metric_text(row, structure, include_subcategory=True)
                if detail_text:
                    details.append(detail_text)

            if details:
                parts.append(f"세부: {', '.join(details)}")

        # 테이블 출처
        parts.append(f"(출처: {table_name})")

        return ". ".join(parts) + "."

    def _generate_timeseries(
        self,
        year: str,
        category: str,
        rows: List[Dict],
        structure: Dict[str, Any],
        table_name: str
    ) -> str:
        """
        시계열 추세: "{year}년 {category} {metric}: {value}{unit} (전년대비 {change_rate}%)"
        """
        parts = []

        header = f"{year}년 {category}"

        # 각 행 처리
        for row in rows[:5]:  # 최대 5개
            metric_text = self._extract_metric_text(row, structure, include_subcategory=True)
            if metric_text:
                parts.append(metric_text)

        # 조합
        if parts:
            text = f"{header}. " + ", ".join(parts)
        else:
            text = header

        # 테이블 출처
        text += f". (출처: {table_name})"

        return text + "."

    def _generate_geographic(
        self,
        year: str,
        category: str,
        rows: List[Dict],
        structure: Dict[str, Any],
        table_name: str
    ) -> str:
        """
        지역 비교: "{year}년 {metric} 지역별: {region1} {value1}{unit}, {region2} {value2}{unit}, ..."
        """
        parts = []

        header = f"{year}년 {category} 지역별 현황"

        # 지역별 데이터 추출 (최대 5개)
        regional_data = []
        for row in rows[:5]:
            metric_text = self._extract_metric_text(row, structure, include_subcategory=True)
            if metric_text:
                regional_data.append(metric_text)

        if regional_data:
            parts.append(f"{header}: {', '.join(regional_data)}")
        else:
            parts.append(header)

        # 테이블 출처
        parts.append(f"(출처: {table_name})")

        return ". ".join(parts) + "."

    def _extract_metric_text(
        self,
        row: Dict,
        structure: Dict[str, Any],
        include_subcategory: bool = False
    ) -> str:
        """
        한 행에서 "지표명: 값단위" 형태의 텍스트 추출

        Args:
            row: 데이터 행
            structure: 테이블 구조
            include_subcategory: 소분류 포함 여부

        Returns:
            "{subcategory} {value}{unit}" 또는 "{value}{unit}"
        """
        data = row.get('data', {})

        # 컬럼 정보
        columns_info = structure.get('data_structure', {}).get('columns_info', {})

        # 값 찾기
        value_col = structure.get('data_structure', {}).get('value_column')
        if value_col and value_col in data:
            value = data[value_col]
        else:
            # value_column이 명시되지 않았으면 마지막 컬럼을 값으로 간주
            value = list(data.values())[-1] if data else None

        # 단위 찾기
        unit_col = structure.get('data_structure', {}).get('unit_column')
        if unit_col and unit_col in data:
            unit = data[unit_col]
        else:
            # 단위 컬럼이 없으면 값 컬럼 바로 앞 것을 단위로 간주
            unit = ""

        # 소분류 찾기 (선택적)
        subcategory = ""
        if include_subcategory:
            # 'Unnamed: 2' 같은 컬럼에서 소분류 추출
            for col_name, col_val in data.items():
                if col_name.startswith('Unnamed:') and col_val not in ['nan', '', ' ']:
                    col_info = columns_info.get(col_name, {})
                    if col_info.get('semantic', '').lower() in ['소분류', 'sub', '항목']:
                        subcategory = str(col_val)
                        break

            # 소분류 못 찾으면 두 번째 컬럼 사용
            if not subcategory:
                col_list = list(data.keys())
                if len(col_list) >= 2:
                    second_col = col_list[1]
                    subcategory = str(data.get(second_col, ''))

        # 값 정제
        value_clean = self._clean_value(value)
        unit_clean = self._clean_unit(unit)

        if not value_clean:
            return ""

        # 텍스트 조합
        if subcategory and subcategory not in ['nan', '', ' ']:
            return f"{subcategory} {value_clean}{unit_clean}"
        else:
            return f"{value_clean}{unit_clean}"

    def _clean_value(self, value: Any) -> str:
        """값 정제"""
        if value is None or str(value).strip() in ['', ' ', 'nan']:
            return ""

        value_str = str(value).strip()

        # 쉼표 제거하지 않음 (가독성을 위해 유지)
        return value_str

    def _clean_unit(self, unit: Any) -> str:
        """단위 정제"""
        if unit is None or str(unit).strip() in ['', ' ', 'nan']:
            return ""

        unit_str = str(unit).strip()

        # 단위 앞에 공백 추가하지 않음 (한글 단위는 붙여쓰기)
        return unit_str

    def generate_chunk_with_context(
        self,
        year: str,
        category: str,
        rows: List[Dict],
        structure: Dict[str, Any],
        table_name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        컨텍스트가 풍부한 청크 생성
        검색 정확도를 높이기 위해 추가 정보 포함

        Args:
            year: 연도
            category: 카테고리
            rows: 데이터 행들
            structure: 테이블 구조
            table_name: 테이블 이름
            metadata: 추가 메타데이터

        Returns:
            컨텍스트가 풍부한 자연어 텍스트
        """
        # 기본 텍스트 생성
        base_text = self.generate(year, category, rows, structure, table_name)

        # 추가 컨텍스트
        enrichments = []

        # 카테고리 컨텍스트
        if category and category not in ['nan', '', ' ']:
            enrichments.append(f"분류: {category}")

        # 데이터 개수
        if rows:
            enrichments.append(f"{len(rows)}개 항목")

        # 메타데이터에서 부서 정보 추가
        if metadata:
            department = metadata.get('department')
            if department:
                enrichments.append(f"담당: {department}")

        # 조합
        if enrichments:
            return f"{base_text} [{', '.join(enrichments)}]"
        else:
            return base_text
