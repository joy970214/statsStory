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

class StatData(BaseModel):
    year: str
    data: Dict[str, Any]

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