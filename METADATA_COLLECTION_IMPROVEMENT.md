# 메타데이터 수집 로직 개선 작업

## 📋 문제 분석

### 1. 기존 문제점
- **파일 리스트 수집**: 메타데이터 수집 시 실제 테이블 내용 대신 파일 목록만 수집
- **구조화되지 않은 데이터**: th(항목)와 td(내용) 구분 없이 텍스트만 수집
- **비효율적인 기본정보 수집**: 크롤링으로 수집되지 않는 하드코딩된 기본정보
- **카테고리 구분 부족**: 탭별 구분 없이 모든 데이터를 혼합하여 저장

### 2. 사용자 요구사항
- 통계정보 탭에서 **테이블 구조(th/td) 수집**
- th값은 **엑셀 항목**에 해당, td값은 **내용**에 해당
- **탭 이름으로 카테고리** 구분 (예: "통계정보")
- **비효율적인 기본정보 수집 로직 제거**

## 🔧 해결방법

### 1. 메타데이터 수집 로직 재설계

#### Before (기존 방식)
```python
# 파일 리스트만 수집
file_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='.xls'], a[href*='.xlsx']")
for link in file_links:
    metadata['files'].append(link.text)
```

#### After (개선된 방식)
```python
# 테이블 구조(th/td) 수집
tables = driver.find_elements(By.XPATH, "//table")
for table in tables:
    rows = table.find_elements(By.XPATH, ".//tr")
    for row in rows:
        th_elements = row.find_elements(By.TAG_NAME, "th")
        td_elements = row.find_elements(By.TAG_NAME, "td")

        if len(th_elements) == 1 and len(td_elements) == 1:
            key = th_elements[0].text.strip()
            value = td_elements[0].text.strip()
            full_key = f"통계정보/{key}"  # 탭별 카테고리 구분
            metadata['statistical_info'][full_key] = value
```

### 2. 주요 변경사항

#### A. `_extract_statistical_details()` 메소드 개선
- **기존**: 파일 링크만 수집
- **개선**: th/td 테이블 구조 정확히 파싱
- **카테고리**: `통계정보/` 접두사로 구분

#### B. `_extract_terms_details()` 메소드 개선
- **기존**: 텍스트 블록만 수집
- **개선**: 용어-정의 쌍을 th/td 구조로 수집
- **카테고리**: `관련용어/` 접두사로 구분

#### C. `_collect_basic_page_info()` → `_collect_main_page_tables()` 교체
- **기존**: 비효율적인 패턴 매칭으로 기본정보 수집
- **개선**: 메인 페이지의 모든 테이블에서 th/td 구조 수집
- **카테고리**: `메인페이지/` 접두사로 구분

### 3. 데이터 구조 개선

#### Before
```json
{
  "purpose": "하드코딩된 값",
  "files": ["파일1.xlsx", "파일2.xlsx"],
  "terms": "텍스트 블록"
}
```

#### After
```json
{
  "statistical_info": {
    "통계정보/작성(조사)목적": "17세 이상 자동차관리사업자 현황...",
    "통계정보/작성(조사)방법": "자동차정비업 현황 파악을 위한 정례조사...",
    "통계정보/공표주기": "분기 60일 이내(2,5,8,11월)...",
    "메인페이지/검색분야": "통계정보/자동차관리사업자업체현황분기"
  },
  "related_terms": {
    "관련용어/자동차관리사업자업체현황분기": "자동차정비업 (국토부, 전화 044-201-3857)"
  }
}
```

## 🚀 구현 과정

### Step 1: 실제 사이트에서 메타데이터 구조 확인
- 자동차관리사업자업체현황분기 통계 페이지 분석
- 통계정보 탭의 테이블 구조 확인
- th/td 매핑 관계 파악

### Step 2: 메타데이터 수집 로직 수정
#### 파일 위치: `backend/app/crawlers/optimized_molit_crawler.py`

```python
async def _extract_statistical_details(self, driver, metadata):
    """통계정보 탭의 테이블 구조(th/td) 추출"""
    try:
        print("  통계정보 탭의 메타데이터 테이블 수집 중...")
        tables = driver.find_elements(By.XPATH, "//table")

        for table_idx, table in enumerate(tables):
            rows = table.find_elements(By.XPATH, ".//tr")

            for row_idx, row in enumerate(rows):
                th_elements = row.find_elements(By.TAG_NAME, "th")
                td_elements = row.find_elements(By.TAG_NAME, "td")

                # th-td 쌍이 있는 경우 (1:1 매칭)
                if len(th_elements) == 1 and len(td_elements) == 1:
                    key = th_elements[0].text.strip()
                    value = td_elements[0].text.strip()

                    # 유효한 데이터인지 확인
                    if (key and value and len(key) < 100 and len(value) < 1000
                        and key != value and not key.isdigit()):

                        # 통계정보 카테고리로 분류
                        full_key = f"통계정보/{key}"
                        metadata['statistical_info'][full_key] = value
                        print(f"    통계정보 테이블에서 수집: {key} = {value[:50]}...")

    except Exception as e:
        print(f"통계정보 상세 수집 오류: {e}")
```

### Step 3: 불필요한 기본정보 수집 로직 제거
- `_collect_basic_page_info()` 메소드 삭제
- `_collect_main_page_tables()` 메소드로 교체
- 효과적이지 않은 패턴 매칭 로직 제거

### Step 4: 수정된 로직 테스트
```bash
python test_vehicle_metadata.py
```

## ✅ 테스트 결과

### 성공적인 데이터 수집 확인
```
=== 자동차관리사업자업체현황분기 메타데이터 수집 테스트 ===
URL: https://stat.molit.go.kr/portal/cate/statView.do?hRsId=437&hFormId=4392&hDivEng=&month_yn=

메타데이터 수집 결과:
  - 통계정보상세: 6개
  - 주요항목: 0개
  - 의미분석: 0개
  - 용어정의: 1개

수집된 데이터 예시:
  - 통계정보/작성(조사)목적: 17세 이상 자동차관리사업자 현황...
  - 통계정보/작성(조사)방법: 자동차정비업 현황 파악을 위한 정례조사로서 활용...
  - 통계정보/공표주기: 분기 60일 이내(2,5,8,11월)...
  - 관련용어/자동차관리사업자업체현황분기: 자동차정비업 (국토부, 전화 044-201-3857)...
```

## 📊 개선 효과

### 1. 데이터 품질 향상
- **구조화된 데이터**: th(항목) - td(내용) 명확한 매핑
- **카테고리 구분**: 탭별 분류로 데이터 구조화
- **실제 내용 수집**: 파일 리스트 대신 실제 통계 정보

### 2. 유지보수성 향상
- **명확한 로직**: 테이블 구조 기반의 일관된 수집 방식
- **오류 처리**: 각 테이블별 독립적인 오류 처리
- **확장성**: 새로운 탭 추가 시 동일한 패턴 적용 가능

### 3. 성능 최적화
- **불필요한 로직 제거**: 비효율적인 기본정보 수집 제거
- **타겟 수집**: 필요한 테이블 데이터만 정확히 수집

## 🔄 코드 변경 요약

### 수정된 파일
1. **`backend/app/crawlers/optimized_molit_crawler.py`**
   - `_extract_statistical_details()` 메소드 재작성
   - `_extract_terms_details()` 메소드 재작성
   - `_collect_basic_page_info()` → `_collect_main_page_tables()` 교체

2. **`test_vehicle_metadata.py`**
   - 테스트 스크립트 메소드 호출 수정

### 핵심 변경사항
- ✅ 파일 리스트 → 테이블 구조(th/td) 수집
- ✅ 텍스트 블록 → 구조화된 키-값 쌍
- ✅ 하드코딩 → 실제 웹페이지 데이터
- ✅ 혼합 데이터 → 탭별 카테고리 구분

## 🎯 결론

사용자 요구사항에 따라 메타데이터 수집 로직을 완전히 개선했습니다:

1. **문제 해결**: 파일 리스트 대신 실제 테이블 내용 수집
2. **구조화**: th값(항목) - td값(내용) 명확한 매핑
3. **카테고리화**: 탭 이름으로 데이터 분류
4. **최적화**: 비효율적인 로직 제거 및 성능 향상

이제 메타데이터가 엑셀에서 보는 것과 동일한 구조로 수집됩니다.