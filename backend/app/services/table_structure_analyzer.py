"""
테이블 구조 동적 분석기
- 다양한 통계 데이터의 구조를 자동으로 파악
- Unnamed 컬럼을 의미있는 이름으로 매핑
- 헤더, 메타데이터, 실제 데이터 구분
"""
from typing import List, Dict, Any, Optional, Tuple
import re


class TableStructureAnalyzer:
    """통계 테이블 구조를 동적으로 분석하는 클래스"""

    def __init__(self):
        self.header_keywords = ['단위 :', '검색기간', '다운로드 시간', '검색분야', '작성주기']
        self.meta_column_keywords = ['년(Annual)', '대분류', '소분류', '단위', '측정값', '구분', '지역']

    def analyze(self, statistics: List[Dict]) -> Dict[str, Any]:
        """
        통계 데이터의 전체 구조를 분석

        Args:
            statistics: StatData 리스트 (JSON 형태)

        Returns:
            구조 분석 결과
        """
        if not statistics:
            return self._empty_structure()

        # 1단계: 메타데이터/헤더/데이터 행 분리
        metadata_rows, header_rows, data_rows = self._classify_rows(statistics)

        # 2단계: 컬럼 매핑 구조 파악
        column_mapping = self._build_column_mapping(header_rows, data_rows)

        # 3단계: 데이터 타입 및 구조 감지
        data_structure = self._detect_data_structure(data_rows, column_mapping)

        return {
            'column_mapping': column_mapping,
            'data_structure': data_structure,
            'metadata_rows': metadata_rows,
            'header_rows': header_rows,
            'data_rows': data_rows,
            'table_name': statistics[0].get('table_name', '') if statistics else ''
        }

    def _classify_rows(self, statistics: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        행을 메타데이터, 헤더, 실제 데이터로 분류
        """
        metadata_rows = []
        header_rows = []
        data_rows = []

        for row in statistics:
            data = row.get('data', {})

            # 메타데이터 행 (다운로드 시간, 검색기간 등)
            if self._is_metadata_row(data):
                metadata_rows.append(row)
                continue

            # 헤더 행 (년(Annual), 대분류, 소분류 등)
            if self._is_header_row(data):
                header_rows.append(row)
                continue

            # 실제 데이터 행
            if self._is_data_row(data):
                data_rows.append(row)

        return metadata_rows, header_rows, data_rows

    def _is_metadata_row(self, data: Dict) -> bool:
        """메타데이터 행인지 확인"""
        data_str = str(data.values())
        return any(keyword in data_str for keyword in self.header_keywords)

    def _is_header_row(self, data: Dict) -> bool:
        """헤더 행인지 확인"""
        data_str = str(data.values())
        # 메타 컬럼 키워드가 있으면 헤더
        return any(keyword in data_str for keyword in self.meta_column_keywords)

    def _is_data_row(self, data: Dict) -> bool:
        """실제 데이터 행인지 확인"""
        # 메타데이터도 아니고 헤더도 아니면 데이터
        if self._is_metadata_row(data) or self._is_header_row(data):
            return False

        # 최소한 하나의 값이 있어야 함
        values = [v for v in data.values() if v and str(v).strip() not in ['', ' ', 'nan']]
        return len(values) > 0

    def _build_column_mapping(self, header_rows: List[Dict], data_rows: List[Dict]) -> Dict[str, Dict]:
        """
        컬럼 매핑 구조 생성
        Unnamed: N → 의미 있는 이름
        """
        if not header_rows and not data_rows:
            return {}

        # 샘플 행에서 모든 컬럼 추출
        sample_row = header_rows[0] if header_rows else data_rows[0]
        all_columns = list(sample_row.get('data', {}).keys())

        column_mapping = {}

        # 헤더 행이 있으면 헤더에서 의미 추출
        if header_rows and len(header_rows) > 0:
            header_data = header_rows[0].get('data', {})

            for col_name in all_columns:
                semantic_name = header_data.get(col_name, col_name)

                # 'Unnamed: N' 형태면 의미 있는 이름 추출
                if col_name.startswith('Unnamed:'):
                    column_mapping[col_name] = {
                        'original': col_name,
                        'semantic': semantic_name if semantic_name not in ['nan', '', ' '] else col_name,
                        'index': int(col_name.split(':')[1]) if ':' in col_name else 0
                    }
                else:
                    column_mapping[col_name] = {
                        'original': col_name,
                        'semantic': semantic_name,
                        'index': 0
                    }
        else:
            # 헤더 없으면 원래 이름 사용
            for i, col_name in enumerate(all_columns):
                column_mapping[col_name] = {
                    'original': col_name,
                    'semantic': col_name,
                    'index': i
                }

        return column_mapping

    def _detect_data_structure(self, data_rows: List[Dict], column_mapping: Dict) -> Dict[str, Any]:
        """
        데이터 구조 및 타입 감지
        """
        if not data_rows:
            return self._default_structure()

        # 컬럼별 의미 파악
        columns_info = {}

        for col_name, col_info in column_mapping.items():
            semantic = col_info['semantic'].lower()

            # 시간 관련 컬럼
            if any(keyword in semantic for keyword in ['년', 'year', 'annual', '월']):
                col_type = 'temporal'
            # 카테고리 컬럼
            elif any(keyword in semantic for keyword in ['대분류', '소분류', '구분', '지역', '분류']):
                col_type = 'category'
            # 단위 컬럼
            elif '단위' in semantic:
                col_type = 'unit'
            # 값 컬럼
            elif any(keyword in semantic for keyword in ['측정값', 'value', '값']):
                col_type = 'value'
            else:
                col_type = 'unknown'

            columns_info[col_name] = {
                **col_info,
                'type': col_type
            }

        # 계층 구조 감지 (합계, 소계 등)
        has_hierarchy = self._detect_hierarchy(data_rows)

        # 시계열 데이터 여부
        is_timeseries = any(col['type'] == 'temporal' for col in columns_info.values())

        # 지역 데이터 여부
        is_geographic = self._detect_geographic(data_rows)

        # 카테고리 추출
        categories = self._extract_categories(data_rows, columns_info)

        return {
            'columns_info': columns_info,
            'has_hierarchy': has_hierarchy,
            'is_timeseries': is_timeseries,
            'is_geographic': is_geographic,
            'categories': categories,
            'temporal_column': self._find_column_by_type(columns_info, 'temporal'),
            'category_column': self._find_column_by_type(columns_info, 'category'),
            'unit_column': self._find_column_by_type(columns_info, 'unit'),
            'value_column': self._find_column_by_type(columns_info, 'value')
        }

    def _detect_hierarchy(self, data_rows: List[Dict]) -> bool:
        """계층 구조 감지 (합계, 소계 등)"""
        hierarchy_keywords = ['합계', '계', '소계', '총계', '전체']

        for row in data_rows[:10]:  # 처음 10개 행만 확인
            data = row.get('data', {})
            data_str = str(data.values()).lower()
            if any(keyword in data_str for keyword in hierarchy_keywords):
                return True
        return False

    def _detect_geographic(self, data_rows: List[Dict]) -> bool:
        """지역 데이터 감지"""
        regions = [
            '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
            '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'
        ]

        for row in data_rows[:20]:  # 처음 20개 행만 확인
            data = row.get('data', {})
            data_str = str(data.values())
            if any(region in data_str for region in regions):
                return True
        return False

    def _extract_categories(self, data_rows: List[Dict], columns_info: Dict) -> List[str]:
        """카테고리 추출"""
        categories = set()

        # 카테고리 컬럼 찾기
        category_cols = [col for col, info in columns_info.items() if info['type'] == 'category']

        if not category_cols:
            return []

        # 첫 번째 카테고리 컬럼에서 고유 값 추출
        first_cat_col = category_cols[0]

        for row in data_rows:
            data = row.get('data', {})
            cat_value = data.get(first_cat_col, '')
            if cat_value and str(cat_value).strip() not in ['', ' ', 'nan']:
                categories.add(str(cat_value).strip())

        return sorted(list(categories))

    def _find_column_by_type(self, columns_info: Dict, col_type: str) -> Optional[str]:
        """특정 타입의 첫 번째 컬럼 찾기"""
        for col_name, info in columns_info.items():
            if info['type'] == col_type:
                return col_name
        return None

    def _empty_structure(self) -> Dict[str, Any]:
        """빈 구조 반환"""
        return {
            'column_mapping': {},
            'data_structure': self._default_structure(),
            'metadata_rows': [],
            'header_rows': [],
            'data_rows': [],
            'table_name': ''
        }

    def _default_structure(self) -> Dict[str, Any]:
        """기본 구조 반환"""
        return {
            'columns_info': {},
            'has_hierarchy': False,
            'is_timeseries': False,
            'is_geographic': False,
            'categories': [],
            'temporal_column': None,
            'category_column': None,
            'unit_column': None,
            'value_column': None
        }
