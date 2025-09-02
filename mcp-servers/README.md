# MCP 서버 사용 가이드

AI API 없이도 통계 분석을 수행할 수 있는 MCP(Model Context Protocol) 서버들을 사용하는 방법입니다.

## 🚀 빠른 시작

### 1. MCP 서버들 시작
```bash
cd mcp-servers
python start_mcp_servers.py
```

### 2. 서버 상태 확인
- 메뉴에서 `1` 선택
- 실행 중인 서버들의 상태를 확인할 수 있습니다

### 3. 서버 모니터링
- 메뉴에서 `2` 선택
- 10초마다 자동으로 서버 상태를 확인합니다

## 📊 사용 가능한 MCP 서버들

| 서버명 | 설명 | 기능 |
|--------|------|------|
| `pandas-analysis` | pandas 기반 데이터 분석 | 통계 계산, 트렌드 분석 |
| `file-analysis` | 파일 구조 분석 | 데이터 프로파일링, 품질 평가 |
| `math-calculation` | 수학적 계산 | 통계 검정, 회귀 분석 |
| `visualization` | 데이터 시각화 | 차트 생성 (matplotlib, plotly) |

## 🔧 서버 관리

### 서버 시작
```bash
python start_mcp_servers.py
```
- 모든 MCP 서버가 자동으로 시작됩니다
- 각 서버는 1초 간격으로 순차적으로 시작됩니다

### 서버 중지
- **특정 서버 중지**: 메뉴에서 `3` 선택 후 서버 번호 입력
- **모든 서버 중지**: 메뉴에서 `4` 선택
- **프로그램 종료**: 메뉴에서 `5` 선택 또는 `Ctrl+C`

### 서버 모니터링
- 메뉴에서 `2` 선택
- 10초마다 자동으로 서버 상태 확인
- `Ctrl+C`로 모니터링 중지

## 📈 통계 분석 워크플로우

### 기본 분석
1. **데이터 준비**: 통계 데이터를 MCP 분석용 형식으로 변환
2. **기본 통계량**: Math Calculation MCP로 평균, 중앙값, 최대/최소값 계산
3. **트렌드 분석**: Pandas Analysis MCP로 증가/감소 추세 분석
4. **데이터 품질**: File Analysis MCP로 데이터 완성도 평가
5. **시각화**: Visualization MCP로 기본 차트 생성

### 종합 분석
- 기본 분석 + 고급 트렌드 분석
- 정책 시사점 도출
- 카드뉴스 생성

## 🛠️ 문제 해결

### 서버 시작 실패
- Python 경로 확인
- 필요한 패키지 설치: `pip install -r requirements.txt`
- 포트 충돌 확인

### 분석 실패
- MCP 서버가 실행 중인지 확인
- 로그 확인
- 로컬 계산으로 자동 대체됨

## 📝 예시

### 기본 분석 결과
```json
{
  "data_structure": {
    "description": "5년간의 자동차관리사업자업체현황분기 데이터",
    "total_years": 5,
    "data_fields": ["total", "value"]
  },
  "basic_statistics": {
    "mean": 45000.0,
    "median": 44000.0,
    "max": 52000.0,
    "min": 38000.0,
    "calculation_method": "MCP"
  },
  "trend_analysis": {
    "trend": "증가",
    "description": "평균 2500.00 증가",
    "confidence": "높음"
  },
  "analysis_method": "MCP 기반 분석"
}
```

## 🔄 폴백 메커니즘

MCP 서버 실패 시 자동으로 다음 순서로 대체됩니다:

1. **MCP 서버** (우선)
2. **AI 서비스** (Anthropic API)
3. **로컬 분석** (최종 대안)

## 💡 팁

- 서버 시작 후 잠시 기다려주세요 (초기화 시간 필요)
- 모니터링 모드를 사용하여 서버 상태를 지속적으로 확인하세요
- 문제 발생 시 모든 서버를 중지하고 다시 시작해보세요

## 📞 지원

문제가 발생하면:
1. 서버 상태 확인
2. 로그 메시지 확인
3. 서버 재시작 시도
4. 필요시 로컬 분석으로 대체

---

**MCP 서버를 사용하면 AI API 없이도 고품질의 통계 분석을 수행할 수 있습니다! 🎉**
