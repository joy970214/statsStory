# 📊 StatsStory 인터랙티브 분석 시스템 설계서

## 🎯 개요

지시사항.md에 명시된 요구사항을 바탕으로 한 완전 자동화된 통계 분석 시스템입니다.

### 핵심 기능
- 수집된 통계 데이터 자동 탐색 및 주제 제안
- 사용자 선택 기반 인터랙티브 분석
- LLM을 활용한 8개 현황 인사이트 자동 생성
- 완전한 분석 보고서 자동 생성 (10개 페이지)

## 🏗️ 시스템 아키텍처

```
📁 statsStory/
├── 🗄️ backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── analysis.py          # 새로운 분석 API
│   │   ├── services/
│   │   │   ├── analysis_engine.py   # 핵심 분석 엔진
│   │   │   ├── llm_service.py       # LLM 연동 서비스
│   │   │   ├── report_generator.py  # 보고서 생성
│   │   │   └── data_explorer.py     # 데이터 탐색
│   │   └── models/
│   │       └── analysis_models.py   # 분석 데이터 모델
│   └── reports/                     # 생성된 보고서 저장
├── 🎨 frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnalysisWizard.tsx   # 단계별 분석 마법사
│   │   │   ├── TopicSelector.tsx    # 주제 선택 컴포넌트
│   │   │   ├── ProgressTracker.tsx  # 진행 상황 추적
│   │   │   └── ReportViewer.tsx     # 보고서 뷰어
│   │   └── pages/
│   │       └── AnalysisPage.tsx     # 메인 분석 페이지
└── 📊 ollama/                       # LLM 모델 (로컬)
```

## 🔄 워크플로우

### Phase 1: 데이터 탐색 (자동)
1. **파일 스캔**: `backend/data/statistics/` 디렉토리 전체 스캔
2. **메타데이터 수집**: 파일명, 크기, 수정일, 데이터 구조 분석
3. **통계 분류**: 통계 유형별 자동 분류 (교통, 부동산, 인구 등)
4. **주제 제안**: LLM이 3개 분석 주제 자동 생성

### Phase 2: 주제 선택 (인터랙티브)
1. **주제 제시**: 사용자에게 3개 주제 카드 형태로 제시
2. **상세 계획**: 선택된 주제의 8개 현황 분석 계획 제시
3. **사용자 승인**: "진행/수정요청" 선택지 제공

### Phase 3: 분석 실행 (자동)
1. **8개 현황 분석**: 병렬로 각 현황별 전문 분석 실행
2. **LLM 인사이트**: 각 현황별 의미있는 인사이트 생성
3. **시각화 생성**: 차트 데이터 및 디자인 가이드 자동 생성

### Phase 4: 보고서 생성 (자동)
1. **10개 페이지 생성**: 메인 보고서 + 8개 현황 + 메타데이터
2. **디자인 가이드**: 각 페이지별 색상, 차트, 레이아웃 가이드
3. **로컬 백업**: 생성된 모든 파일 자동 저장

## 🧠 LLM 통합 설계

### Ollama 연동
```python
class LLMService:
    def __init__(self):
        self.model = "llama3.1"  # 또는 사용 가능한 모델

    def analyze_data_structure(self, data_summary):
        """데이터 구조 및 특성 자동 파악"""

    def generate_topic_suggestions(self, statistics_list):
        """분석 가능한 3개 주제 제안"""

    def create_status_insights(self, status_type, data):
        """현황별 전문 인사이트 생성"""

    def generate_design_guide(self, data_type, analysis_result):
        """시각화 디자인 가이드 자동 생성"""
```

### 프롬프트 설계
```python
TOPIC_GENERATION_PROMPT = """
다음 통계 데이터를 분석하여 3개의 흥미로운 분석 주제를 제안해주세요:

데이터 목록:
{statistics_summary}

각 주제는 다음 형식으로 제안해주세요:
"주제 1: [제목] - [간단한 설명] (관련 파일: X개)"
"주제 2: [제목] - [간단한 설명] (관련 파일: X개)"
"주제 3: [제목] - [간단한 설명] (관련 파일: X개)"
"""

STATUS_ANALYSIS_PROMPT = """
다음 데이터의 {status_type} 현황을 분석해주세요:

데이터: {data}

다음 요소들을 포함하여 분석해주세요:
1. 핵심 통계 지표 (평균, 중위수, 최대/최소값 등)
2. 주요 패턴 및 특징
3. 중요한 발견사항
4. 객관적 현황 요약

분석 결과는 명확하고 이해하기 쉽게 작성해주세요.
"""
```

## 🎯 API 설계

### 엔드포인트 구조
```python
# 1단계: 데이터 탐색
GET /api/analysis/explore
Response: {
    "total_files": 50,
    "categories": ["교통", "부동산", "인구"],
    "suggested_topics": [
        {
            "id": "topic_1",
            "title": "지역별 자동차 산업 현황 분석",
            "description": "17개 시도별 자동차관리사업 분포와 특성",
            "related_files": 5
        }
    ]
}

# 1-A단계: 분석 계획
POST /api/analysis/plan
Request: { "topic_id": "topic_1" }
Response: {
    "analysis_plan": {
        "topic": "지역별 자동차 산업 현황 분석",
        "data_files": ["432ade6bad5a_stats.json"],
        "status_insights": [
            "현황 1: 전국 자동차관리사업 전체 규모",
            "현황 2: 업종별 분포 현황",
            ...
        ],
        "estimated_duration": "5-10분"
    }
}

# 2단계: 분석 실행
POST /api/analysis/execute
Request: { "topic_id": "topic_1", "approved": true }
Response: { "analysis_id": "analysis_123" }

# 진행 상황 확인
GET /api/analysis/progress/{analysis_id}
Response: {
    "status": "running",
    "progress": 60,
    "current_step": "현황 5 분석 중",
    "completed_reports": 4
}

# 보고서 다운로드
GET /api/analysis/download/{analysis_id}
Response: ZIP 파일 (10개 마크다운 파일)
```

## 🎨 프론트엔드 설계

### 컴포넌트 구조
```typescript
// 메인 분석 페이지
interface AnalysisPageProps {
  step: 'explore' | 'select' | 'execute' | 'complete'
}

// 주제 선택 컴포넌트
interface TopicSelectorProps {
  topics: Topic[]
  onSelect: (topic: Topic) => void
  onPlanApprove: (approved: boolean) => void
}

// 진행 상황 추적
interface ProgressTrackerProps {
  analysisId: string
  onComplete: (reportId: string) => void
}

// 보고서 뷰어
interface ReportViewerProps {
  reportId: string
  reports: Report[]
}
```

### UI/UX 설계
- **단계별 진행**: 명확한 진행 단계 표시
- **실시간 피드백**: WebSocket 기반 실시간 진행 상황
- **인터랙티브 선택**: 직관적인 주제 선택 인터페이스
- **미리보기**: 생성된 보고서 즉시 확인 가능

## 📊 데이터 모델

### 분석 요청
```python
class AnalysisRequest(BaseModel):
    topic_id: str
    data_files: List[str]
    user_preferences: Optional[dict] = None

class Topic(BaseModel):
    id: str
    title: str
    description: str
    category: str
    related_files: List[str]
    estimated_insights: List[str]
```

### 분석 결과
```python
class AnalysisResult(BaseModel):
    analysis_id: str
    topic: Topic
    status: Literal["pending", "running", "completed", "failed"]
    progress: int
    reports: List[GeneratedReport]
    created_at: datetime
    completed_at: Optional[datetime]

class GeneratedReport(BaseModel):
    report_type: Literal["main", "status_1", "status_2", ..., "metadata"]
    title: str
    content: str
    design_guide: DesignGuide
    file_path: str
```

### 디자인 가이드
```python
class DesignGuide(BaseModel):
    color_palette: ColorPalette
    chart_config: ChartConfig
    icon_suggestions: List[str]
    layout_suggestion: LayoutConfig

class ColorPalette(BaseModel):
    primary: str
    secondary: str
    accent: str
    background: str

class ChartConfig(BaseModel):
    chart_type: str
    x_axis: str
    y_axis: str
    recommended_library: str
```

## 🔧 핵심 알고리즘

### 지능형 데이터 분석
```python
class SmartAnalysisEngine:
    def detect_data_type(self, data):
        """데이터 유형 자동 감지"""
        if self.has_geographic_data(data):
            return "regional"
        elif self.has_time_series(data):
            return "temporal"
        elif self.has_categories(data):
            return "categorical"
        return "general"

    def generate_adaptive_insights(self, data_type, data):
        """데이터 유형별 적응적 인사이트 생성"""
        analyzers = {
            "regional": RegionalAnalyzer(),
            "temporal": TimeSeriesAnalyzer(),
            "categorical": CategoricalAnalyzer(),
            "general": GeneralAnalyzer()
        }
        return analyzers[data_type].analyze(data)
```

### 8개 현황 분석 매트릭스
```python
STATUS_MATRIX = {
    1: ("기본현황", "전체 규모 및 구성"),
    2: ("분포현황", "카테고리별 분포 패턴"),
    3: ("순위현황", "상위/하위 순위 분석"),
    4: ("비교현황", "그룹간 비교 분석"),
    5: ("지역현황", "지역별 분포 특성"),
    6: ("증감현황", "시계열 변화 추이"),
    7: ("집중도현황", "집중/분산 정도"),
    8: ("특징현황", "주요 특징 및 이상치")
}
```

## 📋 구현 계획

### Phase 1: 백엔드 코어 (1일)
1. `DataExplorer` - 파일 스캔 및 메타데이터 수집
2. `LLMService` - Ollama 연동 및 기본 프롬프트
3. `AnalysisEngine` - 8개 현황 분석 엔진

### Phase 2: API 레이어 (1일)
1. 분석 API 엔드포인트 구현
2. WebSocket 실시간 진행 상황
3. 파일 업로드/다운로드 처리

### Phase 3: 프론트엔드 (1일)
1. 분석 마법사 UI 구현
2. 실시간 진행 상황 표시
3. 보고서 미리보기 기능

### Phase 4: 보고서 생성 (1일)
1. 마크다운 템플릿 시스템
2. 디자인 가이드 자동 생성
3. ZIP 파일 패키징

## ✅ 성공 기준

1. **완전 자동화**: 사용자 개입 최소화 (주제 선택만)
2. **품질 보장**: 각 페이지 완전한 내용으로 생성
3. **실시간 피드백**: 분석 진행 상황 실시간 표시
4. **확장성**: 새로운 통계 유형 자동 처리
5. **사용성**: 직관적이고 간단한 UI/UX

## 🚀 확장 계획

- **다국어 지원**: 영어, 일본어 보고서 생성
- **고급 분석**: 예측 분석, 상관관계 분석
- **시각화 강화**: D3.js 기반 인터랙티브 차트
- **협업 기능**: 팀 단위 분석 결과 공유
- **API 통합**: 외부 데이터 소스 연동

---

*이 설계서는 지시사항.md의 모든 요구사항을 충족하며, 확장 가능하고 유지보수하기 쉬운 아키텍처를 제공합니다.*