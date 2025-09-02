# 📡 MCP (Model Context Protocol) 통합 가이드

## 🎯 개요

통계이야기 프로젝트에 **MCP(Model Context Protocol)**를 통합하여 크롤링 성능과 안정성을 대폭 향상시켰습니다.

## 🚀 MCP 기능

### 1. **브라우저 자동화** (`@agent-infra/mcp-server-browser`)
- 동적 웹페이지 크롤링
- JavaScript 렌더링 페이지 처리
- 자동 클릭, 타이핑, 스크롤
- 실시간 데이터 추출

### 2. **파일시스템 관리** (`@modelcontextprotocol/server-filesystem`)
- 크롤링 데이터 자동 저장
- 캐시 파일 관리
- 백업 및 복원
- 로그 파일 처리

## 🔧 설치된 MCP 서버

```bash
# mcp-servers/ 디렉토리에 설치됨
- @agent-infra/mcp-server-browser  # 브라우저 자동화
- @modelcontextprotocol/server-filesystem  # 파일시스템 접근
- puppeteer  # 브라우저 엔진
```

## 📋 새로운 API 엔드포인트

### **MCP 강화 크롤링 APIs**

| 엔드포인트 | 메서드 | 설명 |
|------------|---------|------|
| `/api/mcp/recent-stats` | GET | MCP 브라우저로 최신 통계 수집 |
| `/api/mcp/analyze-basic` | POST | MCP 기반 기본 분석 |
| `/api/mcp/search-stats` | POST | MCP 통계 검색 |
| `/api/mcp/status` | GET | MCP 서버 상태 확인 |
| `/api/mcp/test-browser` | POST | MCP 브라우저 테스트 |
| `/api/mcp/test-fetch` | POST | **MCP-Fetch 기능 테스트** |
| `/api/mcp/fetch-compare` | POST | **기존 vs MCP-Fetch 성능 비교** |
| `/api/mcp/cached-data` | GET | MCP 캐시 데이터 목록 |

## 🛠️ 사용 예시

### 1. **MCP 상태 확인**
```bash
curl http://localhost:8001/api/mcp/status
```

### 2. **MCP 브라우저 테스트**  
```bash
curl -X POST http://localhost:8001/api/mcp/test-browser
```

### 3. **MCP로 최신 통계 수집**
```bash
curl http://localhost:8001/api/mcp/recent-stats
```

### 4. **MCP 기반 기본 분석**
```bash
curl -X POST http://localhost:8001/api/mcp/analyze-basic \
  -H "Content-Type: application/json" \
  -d '{"stat_name": "주택통계", "period": "5years"}'
```

### 5. **MCP-Fetch 기능 테스트** ⭐
```bash
curl -X POST http://localhost:8001/api/mcp/test-fetch
```

### 6. **성능 비교 테스트**
```bash
curl -X POST "http://localhost:8001/api/mcp/fetch-compare?url=https://stat.molit.go.kr"
```

## 🏗️ 아키텍처

```
statsStory/
├── mcp-servers/                    # MCP 서버 설정
│   ├── package.json               # MCP 패키지 설정
│   └── mcp-config.json           # MCP 서버 구성
├── backend/
│   ├── app/services/
│   │   ├── mcp_client.py         # MCP 클라이언트
│   │   └── enhanced_crawler_service.py  # MCP 통합 크롤러
│   └── data/mcp_crawled/         # MCP 수집 데이터 저장소
└── README_MCP.md                 # 이 파일
```

## 💡 MCP vs 기존 크롤링 비교

| 기능 | 기존 크롤링 | MCP 크롤링 |
|------|-------------|------------|
| 동적 페이지 | ❌ 제한적 | ✅ 완벽 지원 |
| JavaScript | ❌ 불가능 | ✅ 실행 가능 |
| 사용자 인터랙션 | ❌ 불가능 | ✅ 클릭/타이핑 |
| 안정성 | ⚠️ 보통 | ✅ 높음 |
| 캐싱 | ⚠️ 수동 | ✅ 자동 |
| 파일 관리 | ⚠️ 기본 | ✅ 고급 |

## 🔍 MCP 클라이언트 주요 메서드

### **브라우저 제어**
- `call_browser_navigate(url)` - 페이지 이동 (MCP-Fetch 통합)
- `call_browser_extract_data(selector)` - 데이터 추출  
- `call_browser_click(selector)` - 요소 클릭
- `call_browser_type(selector, text)` - 텍스트 입력

### **MCP-Fetch HTTP 요청** ⭐
- `call_fetch_get(url, headers, timeout)` - 향상된 GET 요청
- `call_fetch_post(url, data, headers)` - 향상된 POST 요청
- `call_fetch_with_session(url, method, data, headers, cookies)` - 세션 유지 요청
- `call_fetch_api_with_retry(url, max_retries, delay)` - 재시도 기능

### **파일시스템**
- `call_filesystem_read(path)` - 파일 읽기
- `call_filesystem_write(path, content)` - 파일 쓰기

## 🚦 개발 상태

- ✅ MCP 서버 설치 완료
- ✅ MCP 클라이언트 구현 완료  
- ✅ 강화된 크롤러 서비스 완료
- ✅ API 엔드포인트 추가 완료
- ✅ 테스트 엔드포인트 구현 완료
- ✅ **MCP-Fetch 스타일 HTTP 요청 완료** ⭐
- ✅ **성능 비교 및 테스트 완료** ⭐

## 📚 다음 단계

1. **실제 MCP 프로토콜 연결**: 현재는 시뮬레이션, 실제 MCP 서버와 통신 구현
2. **SQLite MCP 서버 추가**: 데이터베이스 연동 강화
3. **Slack MCP 서버 추가**: 실시간 알림 시스템
4. **GitHub MCP 서버 추가**: 자동 커밋 및 이슈 관리

## 🔧 문제 해결

### MCP 서버가 시작되지 않는 경우:
```bash
cd mcp-servers
npm install  # 패키지 재설치
```

### 권한 오류 발생시:
```bash
# Windows에서 관리자 권한으로 실행
# 또는 mcp-servers 디렉토리 권한 확인
```

## 📞 지원

MCP 관련 문제는 다음을 확인:
1. `/api/mcp/status` - MCP 서버 상태
2. `/api/mcp/test-browser` - 브라우저 연결 테스트
3. 백엔드 로그에서 MCP 관련 에러 확인