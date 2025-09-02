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

1. **최신 통계 목록 조회**: 국토교통부 통계누리에서 최근 1달 통계 데이터 크롤링
2. **통계 데이터 수집**: 선택된 통계의 5년치 시계열 데이터 및 메타정보 수집
3. **AI 카드뉴스 생성**: Claude를 활용한 마크다운 형태의 7장 분량 카드뉴스 생성
4. **반응형 웹 인터페이스**: 데스크톱/모바일 친화적인 UI

## 📡 API 엔드포인트

- `GET /api/recent-stats`: 최근 통계 목록 조회
- `POST /api/generate-story`: 카드뉴스 보고서 생성
- `GET /api/stats/{id}/metadata`: 통계 메타데이터 조회

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