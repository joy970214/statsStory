# 통계이야기 - 국토교통부 통계 카드뉴스 생성 서비스

국토교통부 통계누리 데이터를 활용한 자동 통계 카드뉴스 생성 웹서비스

## 📋 프로젝트 구조

```
statsStory/
├── backend/                    # FastAPI 백엔드 서버
│   ├── app/
│   │   ├── api/               # API 라우터
│   │   ├── core/              # 설정 파일
│   │   ├── crawlers/          # 웹 크롤링 모듈
│   │   ├── services/          # 비즈니스 로직
│   │   └── models/            # 데이터 모델
│   ├── data/                  # 수집된 데이터 저장소
│   │   ├── metadata/          # 통계 메타데이터
│   │   ├── statistics/        # 통계 데이터
│   │   └── excel/            # 엑셀 파일
│   ├── requirements.txt
│   └── main.py
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── components/        # React 컴포넌트
│   │   ├── pages/            # 페이지 컴포넌트
│   │   ├── services/         # API 서비스
│   │   └── utils/            # 유틸리티
│   ├── package.json
│   └── public/
├── docs/                      # 프로젝트 문서화
│   ├── 2025-09-08_*.md       # 개발 과정 문서 (일자순 정렬)
│   ├── 2025-09-09_*.md
│   ├── 2025-09-16_*.md
│   └── 2025-09-17_*.md
└── README.md
```

## 🛠 기술 스택

### 백엔드
- **Python FastAPI**: 고성능 비동기 웹 프레임워크
- **Playwright**: 동적 웹 크롤링 (JavaScript 렌더링 지원)
- **BeautifulSoup4**: HTML 파싱
- **Anthropic Claude**: AI 보고서 생성
- **Pydantic**: 데이터 검증 및 모델링

### 프론트엔드
- **React 18**: 사용자 인터페이스 구축
- **TypeScript**: 타입 안전성
- **Tailwind CSS**: 유틸리티 퍼스트 CSS 프레임워크
- **Axios**: HTTP 클라이언트

### 개발 도구
- **Git**: 버전 관리
- **ESLint/Prettier**: 코드 포맷팅

## 🚀 주요 기능

### 📊 데이터 수집 시스템
1. **최신 통계 목록 조회**: 국토교통부 통계누리에서 최근 1달 통계 데이터 크롤링
2. **고급 데이터 수집**: IBSheet 기반 동적 테이블 데이터 수집
3. **구조화된 메타데이터**: 통계정보, 주요항목, 의미분석, 관련용어 분리 수집
4. **원본 테이블 구조 보존**: 실제 웹사이트와 동일한 테이블 레이아웃 재현

### 🎯 분석 및 시각화
5. **기본통계현황분석**: 수집된 데이터의 통계표별 상세 분석
6. **원본 테이블 형태 보기**: IBSheet 데이터를 원본 형태로 재구성하여 표시
7. **데이터 품질 검증**: 수집 품질 점수 및 상세 검사 기능
8. **다양한 내보내기**: Excel, PDF, 마크다운 형태로 분석 결과 다운로드

### 🤖 AI 기능
9. **AI 카드뉴스 생성**: Claude를 활용한 마크다운 형태의 7장 분량 카드뉴스 생성
10. **반응형 웹 인터페이스**: 데스크톱/모바일 친화적인 UI

## 📡 API 엔드포인트

### 통계 데이터 API
- `GET /api/recent-stats`: 최근 통계 목록 조회
- `GET /api/stats/{id}/metadata`: 통계 메타데이터 조회
- `POST /api/data/comprehensive-analysis`: 기본통계현황분석 실행
- `POST /api/data/inspect`: 수집된 데이터 검사

### AI 생성 API
- `POST /api/generate-story`: 카드뉴스 보고서 생성
- `POST /api/generate-basic-statistics-story`: 기본통계 분석 보고서 생성

### 유틸리티 API
- `GET /health`: 서버 상태 확인
- `POST /api/export/excel`: Excel 파일 생성
- `POST /api/export/pdf`: PDF 파일 생성

## 🔧 개발 환경 설정

### 백엔드 실행
```bash
cd backend
# .env 파일에 Anthropic API 키 설정
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
pip install -r requirements.txt
python main.py
# 서버: http://localhost:8000
```

### 프론트엔드 실행
```bash
cd frontend
npm install
npm start
```

## 📚 문서화

### 개발 과정 문서
프로젝트의 모든 개발 과정과 문제 해결 과정이 `docs/` 폴더에 일자순으로 정리되어 있습니다.

#### 최근 문서들
- **[2025-09-17_데이터-수집-시스템-개선-IBSheet-테이블구조-메타데이터.md](./docs/2025-09-17_데이터-수집-시스템-개선-IBSheet-테이블구조-메타데이터.md)**
  - IBSheet 데이터 수집 방식 개선
  - 원본 테이블 구조 보존 기능 구현
  - 메타데이터 수집 로직 강화

- **[2025-09-16_프로젝트-문제해결-총정리.md](./docs/2025-09-16_프로젝트-문제해결-총정리.md)**
  - SSE 연결 문제 해결
  - 통계표별 분석 기능 구현
  - UI 개선 및 사용자 경험 향상

- **[2025-09-09_StatData-모델-validation-완전해결-및-데이터-저장-검증.md](./docs/2025-09-09_StatData-모델-validation-완전해결-및-데이터-저장-검증.md)**
  - 데이터 모델 검증 문제 해결
  - 데이터 저장 안정성 확보

#### 전체 문서 목록
```bash
docs/
├── 2025-09-08_AJAX-API-기반-데이터-수집-시스템-구현.md
├── 2025-09-08_크롤링-시스템-개선.md
├── 2025-09-09_StatData-모델-validation-에러-해결.md
├── 2025-09-09_StatData-모델-validation-완전해결-및-데이터-저장-검증.md
├── 2025-09-10_troubleshooting.md
├── 2025-09-16_SSE-연결-문제-해결-가이드.md
├── 2025-09-16_통계표명개선및UI탭구성.md
├── 2025-09-16_통계표별-데이터-분석-기능-구현.md
├── 2025-09-16_통계표별-상세-분석-기능-구현-완료.md
├── 2025-09-16_프로젝트-문제해결-총정리.md
└── 2025-09-17_데이터-수집-시스템-개선-IBSheet-테이블구조-메타데이터.md
```

## ⚡ 최신 개선사항 (2025-09-17)

### 🔧 데이터 수집 시스템 대폭 개선
- **IBSheet 구조화**: 원본 테이블 형태 완전 보존
- **메타데이터 강화**: 통계정보, 주요항목, 의미분석, 관련용어 분리 수집
- **테이블 재현**: 실제 웹사이트와 동일한 레이아웃으로 데이터 표시

### 📊 사용자 경험 향상
- **직관적 데이터 보기**: `ibsheet_cell_` 대신 의미있는 테이블 형태
- **상세 메타정보**: 검색분야, 담당부서 등 추가 정보 제공
- **데이터 품질 표시**: 수집 품질 점수 및 검증 정보