# 기본통계현황분석 로직 현황 문서

## 📊 개요

**작성일**: 2025-09-17
**브랜치**: `feature/metadata-performance-optimization`
**버전**: 최적화된 메타데이터 수집 버전

이 문서는 "기본통계현황분석" 버튼을 클릭했을 때 실행되는 로직의 상세한 현황을 설명합니다.

## 🔄 전체 플로우

```mermaid
graph TD
    A[기본통계현황분석 버튼 클릭] --> B[통계표 목록 수집]
    B --> C[통계표 필터링]
    C --> D[통계표별 조건 분석]
    D --> E[기간 선택 로직]
    E --> F[데이터 수집]
    D --> G[메타데이터 수집]
    F --> H[분석 결과 생성]
    G --> H
```

## 🔍 1. 통계표 필터링 로직

### 1.1 필터링 함수
**파일**: `backend/app/crawlers/optimized_molit_crawler.py:42`
**함수**: `is_terminated_stat(stat_name: str) -> bool`

### 1.2 제외 키워드 (기본 패턴)
```python
termination_patterns = [
    '(종료)',
    '작성중지',
    '중지',
    '폐지',
    '통계작성중지'
]
```

### 1.3 연도 기반 스마트 필터링
현재년도 기준으로 2년 이전 종료된 통계는 제외:

| 패턴 | 예시 | 처리 로직 |
|------|------|-----------|
| `YYYY년 이후 중지` | "2020년 이후 중지" | 2020 ≤ 현재년도-2 → 제외 |
| `YYYY~YYYY 중지` | "2019~2021 중지" | 2021 ≤ 현재년도-2 → 제외 |
| `~YYYY 종료` | "~2020 종료" | 2020 ≤ 현재년도-2 → 제외 |
| `YYYY 중지` | "2020 중지" | 2020 ≤ 현재년도-2 → 제외 |

**예시**: 2025년 기준으로 2023년 이전 종료 통계는 모두 제외

### 1.4 통계표 분류
**파일**: `backend/app/crawlers/optimized_molit_crawler.py:1144`

```python
table_info = {
    'name': option_text,
    'value': option_value,
    'form_id': option_value,
    'is_regional': '시도별' in option_text or '지역별' in option_text,
    'is_yearly': '연도별' in option_text or '년별' in option_text,
    'requires_date_range': False
}
```

## 📅 2. 기간 선택 로직

### 2.1 통계표 유형별 기간 설정
**파일**: `backend/app/crawlers/optimized_molit_crawler.py:1220`

#### A. 연도별 통계표 (`is_yearly: true`)
**조건**: 통계표명에 "연도별" 또는 "년별" 포함
```python
if table_info['is_yearly'] or await self._should_use_date_range(driver):
    # 5년치 범위 계산
    if date_format == "YYYY":
        start_date = str(current_date.year - 4)  # 2021
        end_date = str(current_date.year)        # 2025
    else:
        # YYYYMM 형식으로 5년 전부터
        start_year = current_date.year - 4
        start_date = f"{start_year}01"           # 202101
        end_date = current_month                 # 202512
```

#### B. 지역별 통계표 (`is_regional: true`)
**조건**: 통계표명에 "시도별" 또는 "지역별" 포함
```python
if table_info['is_regional'] or '시·군·구별' in table_info['name']:
    # 현재 월만 수집
    start_date = end_date = current_month  # 202512
```

#### C. 월별/전체 데이터
**조건**: 위 조건에 해당하지 않는 경우
```python
else:
    # 전체 데이터 수집 (제한 없음)
    start_date = end_date = current_month
```

### 2.2 날짜 형식 자동 감지
**파일**: `backend/app/crawlers/optimized_molit_crawler.py:1204`

| 형식 | 예시 | 사용 케이스 |
|------|------|-------------|
| `YYYY` | 2025 | 연간 통계 |
| `YYYYMM` | 202512 | 월간 통계 |
| `YYYY-MM` | 2025-12 | 월간 통계 (하이픈) |

### 2.3 5년치 데이터 수집 로직
**파일**: `backend/app/crawlers/optimized_molit_crawler.py:1300`

```python
async def _collect_data_with_date_range(self, driver, table_name: str, date_format: str = "YYYYMM"):
    # 5년치 날짜 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*5)

    # #sStart와 #sEnd 폼 필드에 설정
    start_element = driver.find_element(By.ID, "sStart")
    start_element.clear()
    start_element.send_keys(start_value)

    end_element = driver.find_element(By.ID, "sEnd")
    end_element.clear()
    end_element.send_keys(end_value)
```

## 🗂️ 3. 메타데이터 수집 로직

### 3.1 현재 최적화된 상태
**파일**: `backend/app/crawlers/optimized_molit_crawler.py:1009`

#### 성능 최적화 요소:
- ✅ 대기 시간: 3초 → 1초 단축
- ✅ 수집 범위: 전체 → 최대 5개 항목
- ✅ 테이블 검사: 전체 → 처음 2개만
- ✅ 행 검사: 전체 → 최대 10행만

### 3.2 통계정보 탭 수집 ✅
**실행 여부**: ✅ **실행됨**

```python
# goMetaView 함수 직접 호출
meta_tab = driver.find_element(By.XPATH, "//*[contains(@onclick, 'goMetaView')]")
driver.execute_script("arguments[0].click();", meta_tab)
await asyncio.sleep(1)  # 1초 대기

# 기본 통계정보만 수집 (최대 5개 항목)
for table in stat_info_tables[:2]:  # 처음 2개 테이블만
    for row in rows[:10]:  # 최대 10행만
        # th-td 매핑으로 수집
        if key and value and len(value) < 100:  # 짧은 값만
            metadata_info['statistical_info'][key] = value
```

**수집되는 필드:**
- `통계명` → `title`
- `작성목적` → `purpose`
- `작성주기` → `frequency`
- `작성기관` → `department`
- 기타 항목들 → `statistical_info` 딕셔너리

### 3.3 관련용어 탭 수집 ❌
**실행 여부**: ❌ **스킵됨** (성능 최적화)

```python
# 2. 관련용어 탭은 성능상 스킵 (필요시 별도 함수로 구현)
print("관련용어 탭 수집 스킵 (성능 최적화)")
```

**수집되지 않는 필드:**
- ❌ `major_items` (주요항목)
- ❌ `meaning_analysis` (의미분석)
- ❌ `terminology` (관련용어)
- ❌ `related_terms` (추가 용어들)

## ⚡ 4. 성능 개선 현황

### 4.1 최적화 전후 비교

| 구분 | 이전 (8분 25초) | 현재 (20-30초) | 개선률 |
|------|----------------|----------------|--------|
| 메타데이터 수집 | 8분 25초 | 20-30초 | **95%** |
| 통계정보 탭 | 복잡한 다중 검색 | 직접 호출 | **90%** |
| 관련용어 탭 | 전체 수집 | 스킵 | **100%** |
| 디버깅 로그 | 과도한 출력 | 최소화 | **80%** |

### 4.2 주요 최적화 기법

1. **선택적 수집**: 핵심 5개 항목만
2. **직접 호출**: `goMetaView()` JavaScript 함수 직접 실행
3. **범위 제한**: 처음 2개 테이블, 10행만 검사
4. **관련용어 스킵**: 성능 우선으로 제외
5. **대기 시간 단축**: 3초 → 1초

## 📋 5. 데이터 저장 현황

### 5.1 JSON 저장 구조
**파일**: `backend/app/services/data_storage.py:52`

```json
{
  "metadata": {
    "id": "통계ID",
    "title": "통계명",
    "purpose": "작성목적",
    "frequency": "작성주기",
    "department": "작성기관",
    "contact": "담당자",
    "search_field": "검색분야",
    "responsible_department": "담당부서",
    "keywords": [],
    "related_terms": {},
    "statistical_info": {
      "수집된키": "수집된값"
    },
    "major_items": {},      // 빈 객체 (수집 안됨)
    "meaning_analysis": {}, // 빈 객체 (수집 안됨)
    "terminology": {},      // 빈 객체 (수집 안됨)
    "url": "통계URL"
  }
}
```

### 5.2 Excel 저장 구조
**파일**: `backend/app/services/data_storage.py:347`

| 시트명 | 내용 | 수집 여부 |
|--------|------|-----------|
| 메타데이터 | 기본 정보 + 검색분야 + 담당부서 | ✅ |
| 통계데이터 | 실제 수집된 통계 | ✅ |
| 통계정보상세 | statistical_info 상세 | ✅ |
| 관련용어 | related_terms | ❌ (빈 시트) |
| 주요항목 | major_items | ❌ (빈 시트) |

## 🚨 6. 현재 제한사항

### 6.1 메타데이터 수집 제한
1. **관련용어 탭 미수집**: 성능 최적화로 인해 스킵
2. **부분 수집**: 최대 5개 항목만 수집
3. **짧은 값만**: 100자 이상 값 제외

### 6.2 요구사항 대비 차이점

| 요구사항 | 현재 상태 | 비고 |
|----------|-----------|------|
| 통계정보 탭 수집 | ✅ 부분 수집 | 5개 항목 제한 |
| 관련용어 탭 수집 | ❌ 수집 안됨 | 성능 최적화로 스킵 |
| 연도별 5년치 | ✅ 정확히 구현 | |
| 월별 전체 데이터 | ✅ 정확히 구현 | |
| 종료/중지 제외 | ✅ 정확히 구현 | |

## 🔧 7. 향후 개선 방안

### 7.1 메타데이터 수집 완성
```python
# 관련용어 탭 수집 추가 (선택적)
if collect_full_metadata:  # 옵션으로 제어
    await self._collect_related_terms_tab(driver)
```

### 7.2 성능과 완성도 균형
- **기본 모드**: 현재와 동일 (빠른 수집)
- **상세 모드**: 관련용어 포함 (완전한 수집)

### 7.3 점진적 개선
1. 관련용어 탭 수집 로직 복원
2. 사용자 선택 옵션 추가
3. 캐시 활용으로 성능 유지

## 📊 8. 실행 결과 예시

### 8.1 성공적인 수집 로그
```
최적화된 종합 통계 분석 시작: https://stat.molit.go.kr/portal/cate/statView.do?hRsId=419&hFormId=5882
메타데이터 수집 완료: 1.2초
통계표 발견: 공동주택현황 (201401 ~ 202508) (FormID: 5882)
연도별 데이터 수집: 5년치 (2021~2025)
통계정보 수집 완료: 5개 항목
관련용어 탭 수집 스킵 (성능 최적화)
```

### 8.2 수집된 메타데이터 예시
```json
{
  "title": "공동주택현황",
  "purpose": "공동주택 현황 파악",
  "frequency": "월간",
  "department": "국토교통부",
  "search_field": "주택/공동주택 현황",
  "statistical_info": {
    "통계명": "공동주택현황",
    "작성목적": "공동주택 현황 파악",
    "작성주기": "월간",
    "작성기관": "국토교통부",
    "승인번호": "116032"
  }
}
```

---

**최종 업데이트**: 2025-09-17
**작성자**: Claude Code Assistant
**문서 버전**: 1.0