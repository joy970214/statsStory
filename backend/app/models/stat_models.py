from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class StatItem(BaseModel):
    id: str
    title: str
    publish_date: str
    category: Optional[str] = None
    department: Optional[str] = None
    url: Optional[str] = None
    stat_field: Optional[str] = None

class RecentStatsResponse(BaseModel):
    stats: List[StatItem]
    total_count: int

class StatMetadata(BaseModel):
    id: str
    title: str
    purpose: Optional[str] = None
    frequency: Optional[str] = None
    department: Optional[str] = None
    contact: Optional[str] = None
    keywords: List[str] = []
    related_terms: Dict[str, str] = {}
    url: Optional[str] = None

class StatData(BaseModel):
    year: int
    data: Dict[str, Any]
    table_name: Optional[str] = None
    period_text: Optional[str] = None
    period_type: Optional[str] = None  # 년간, 월간, 분기 등
    raw_data_count: Optional[int] = None  # 수집된 데이터 항목 수
    collection_status: Optional[str] = "success"  # success, partial, failed
    data_quality_score: Optional[float] = None  # 데이터 품질 점수 (0-1)

class ComprehensiveStatAnalysis(BaseModel):
    """종합 통계 분석 결과"""
    stat_url: str
    stat_title: str
    metadata: StatMetadata
    collected_tables: List[str] = []  # 수집된 통계표명 목록
    data_by_table: Dict[str, List[StatData]] = {}  # 통계표별 데이터
    total_data_points: int = 0
    collection_summary: Dict[str, Any] = {}  # 수집 요약 정보
    analysis_insights: List[str] = []  # 분석 인사이트
    created_at: datetime

class GenerateStoryRequest(BaseModel):
    stat_name: str
    stat_url: Optional[str] = None
    period: str = "5years"

class CardNewsSection(BaseModel):
    title: str
    content: str
    chart_data: Optional[Dict[str, Any]] = None

class StoryResponse(BaseModel):
    title: str
    summary: str
    sections: List[CardNewsSection]
    metadata: StatMetadata
    generated_at: datetime

class TableColumn(BaseModel):
    """테이블 컬럼 정보"""
    id: str
    name: str
    data_type: Optional[str] = "text"  # text, number, date
    level: Optional[int] = 1  # 헤더 레벨
    parent_id: Optional[str] = None  # 상위 컬럼 ID

class TableRow(BaseModel):
    """테이블 행 데이터"""
    row_id: str
    cells: Dict[str, Any]  # column_id -> value
    
class StatTable(BaseModel):
    """IBSheet 스타일 통계 테이블"""
    table_name: str
    form_id: str
    period: str  # "2025-07" or "2020~2025" 등
    columns: List[TableColumn]
    rows: List[TableRow]
    total_rows: int
    summary: Dict[str, Any] = {}
    collection_method: str = "api"  # api, selenium, hybrid

class InspectionResult(BaseModel):
    """데이터 검사 결과"""
    stat_name: str
    stat_url: str
    tables: List[StatTable] = []
    metadata: Optional[StatMetadata] = None
    total_tables: int = 0
    total_data_points: int = 0
    collection_success: bool = True
    errors: List[str] = []
    inspected_at: datetime