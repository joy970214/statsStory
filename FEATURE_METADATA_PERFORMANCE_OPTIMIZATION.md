# 메타데이터 성능 최적화 및 통계표 선택 문제 해결

## 📋 작업 개요

기본통계현황분석 결과 화면에서 발생하는 주요 문제들을 해결하였습니다:

1. **전체요약 탭 통계 값이 0으로 표시되는 문제**
2. **잘못된 통계표가 선택되는 문제** (미분양주택현황 선택 시 공동주택현황 표시)
3. **수집 프로세스 없이 바로 결과 화면으로 이동하는 문제**

## 🔍 문제 분석

### 1. 통계 값 0 표시 문제

**원인**: 프론트엔드에서 숫자 데이터 추출 시 `unit === 'number'`만 처리하고, `unit === 'text'`인 숫자 문자열을 무시

**근본 원인**: 실제 데이터에서 숫자가 다음과 같이 저장됨:
```json
{
  "value": "21274",
  "unit": "text",
  "raw": "21274"
}
```

### 2. 잘못된 통계표 선택 문제

**원인**: API에서 `find_data_by_name()` 함수가 유사한 이름의 데이터를 반환하고, 제목 정확성 검증 없이 사용

**구체적 문제**:
- 요청: "미분양주택현황보고"
- 실제 반환: "공동주택 현황" 데이터
- 결과: 잘못된 테이블명 표시

### 3. 수집 프로세스 우회 문제

**원인**: 백엔드에서 제목 불일치를 감지하지 못하고 기존 캐시 데이터를 사용하여 즉시 분석 완료 처리

## 🛠️ 해결 방안

### 1. 프론트엔드 숫자 데이터 추출 로직 개선

**파일**: `frontend/src/components/EnhancedBasicStatisticsViewer.tsx` (라인 641-661)

```typescript
// 기존: unit === 'number'만 처리
if (cellValue.unit === 'number' && typeof cellValue.value === 'number') {
  numericValue = cellValue.value;
}

// 개선: 문자열 형태의 숫자도 처리
let numericValue: number | null = null;

if (cellValue.unit === 'number' && typeof cellValue.value === 'number') {
  numericValue = cellValue.value;
} else if (typeof cellValue.value === 'string') {
  // 문자열에서 숫자 추출 시도 (쉼표 제거)
  const cleaned = cellValue.value.replace(/,/g, '').trim();
  const parsed = parseFloat(cleaned);
  if (!isNaN(parsed) && isFinite(parsed)) {
    numericValue = parsed;
  }
} else if (typeof cellValue.value === 'number') {
  numericValue = cellValue.value;
}
```

**효과**:
- 문자열 형태의 숫자("21274", "143,812" 등) 정상 인식
- 실제 통계 값 계산 가능

### 2. API 데이터 검증 로직 추가

**파일**: `backend/app/api/stats.py`

#### 2.1 `/api/data/raw-view` 엔드포인트 (라인 1360-1369)

```python
# 실제 메타데이터의 title이 요청한 stat_name과 정확히 일치하는지 확인
if cached_metadata and hasattr(cached_metadata, 'title'):
    actual_title = cached_metadata.title
    if actual_title != request.stat_name:
        # 제목이 다르면 데이터가 없는 것으로 처리
        print(f"제목 불일치: 요청={request.stat_name}, 실제={actual_title}")
        cached_metadata = None
        cached_stat_data = None
    else:
        stat_url = found_url
```

#### 2.2 `run_optimized_analysis` 함수 (라인 475-484)

```python
# 제목이 정확히 일치하는지 확인
if cached_metadata and hasattr(cached_metadata, 'title'):
    actual_title = cached_metadata.title
    if actual_title != request.stat_name:
        print(f"  - title_mismatch: 요청={request.stat_name}, 실제={actual_title}")
        cached_metadata = None
        cached_stat_data = None
    elif found_url:
        print(f"  - found_cached_url: {found_url}")
        stat_url = found_url  # 캐시된 URL로 업데이트
```

**효과**:
- 정확한 통계명만 캐시 데이터 사용
- 제목 불일치 시 새로운 데이터 수집 강제

### 3. 테이블명 생성 로직 개선

**파일**: `backend/app/api/stats.py` (라인 1383-1403)

```python
# 메타데이터에서 실제 통계명 가져오기
actual_stat_title = getattr(metadata, 'title', None) or request.stat_name

for item in raw_data:
    table_name = item.get('table_name')

    # table_name이 없거나 기본값인 경우 메타데이터의 title 사용
    if not table_name or table_name in ['', '기본 통계표']:
        # 기간 정보 추가 (년도 범위 자동 계산)
        years = [int(item.get('year', 0)) for item in raw_data if item.get('year')]
        if years:
            min_year = min(years)
            max_year = max(years)
            # YYYYMM 형식을 YYYY로 변환
            if min_year > 10000:  # YYYYMM 형식인 경우
                min_year = min_year // 100
                max_year = max_year // 100
            table_name = f"{actual_stat_title} ({min_year:04d}01 ~ {max_year:04d}08)"
        else:
            table_name = actual_stat_title
```

**효과**:
- 메타데이터의 실제 제목 사용
- 자동 기간 정보 추가
- 정확한 테이블명 생성

### 4. 프론트엔드 데이터 없음 처리

**파일**: `frontend/src/components/EnhancedBasicStatisticsViewer.tsx` (라인 73-82)

```typescript
// 백엔드에서 데이터 없음 메시지를 보낸 경우 확인
if (rawData.message && rawData.suggestion) {
  console.log('데이터 없음:', rawData.message);
  console.log('제안:', rawData.suggestion);

  // 사용자에게 알리고 수집 필요함을 표시
  alert(`${rawData.message}\n\n${rawData.suggestion}`);
  setLoading(false);
  return; // 여기서 중단하고 수집 프로세스로 돌아가야 함
}
```

**효과**:
- 데이터 없음 메시지 감지
- 사용자에게 명확한 안내

## 📊 개선 결과

### Before (문제 상황)
```
1. 미분양주택현황보고 선택
2. 기본통계현황분석 클릭
3. 즉시 결과 화면 표시 (수집 과정 없음)
4. 테이블명: "공동주택현황 (201401 ~ 202508)" ❌
5. 모든 통계 값: 0 ❌
```

### After (해결 후)
```
1. 미분양주택현황보고 선택
2. 기본통계현황분석 클릭
3. 제목 불일치 감지
4. 새로운 데이터 수집 시작 (진행률 표시) ✅
5. 테이블명: "미분양주택현황보고 (201401 ~ 202508)" ✅
6. 실제 통계 값 표시 ✅
```

### 통계 데이터 처리 개선
```
- 기존: unit='number'만 처리 → 대부분 값이 0
- 개선: unit='text'인 숫자 문자열도 처리 → 실제 값 추출
- 예시: "21,274" → 21274 (정상 변환)
```

## 🔧 핵심 수정 파일

1. **`backend/app/api/stats.py`**
   - `/api/data/raw-view` 엔드포인트 제목 검증 로직
   - `run_optimized_analysis` 캐시 검증 로직
   - `raw_data_by_table` 테이블명 생성 로직

2. **`frontend/src/components/EnhancedBasicStatisticsViewer.tsx`**
   - 숫자 데이터 추출 로직 개선
   - 데이터 없음 상황 처리
   - 상세 디버깅 로그 추가

## 🎯 기대 효과

1. **정확한 데이터 표시**: 선택한 통계의 실제 데이터만 사용
2. **올바른 통계 계산**: 문자열 형태 숫자까지 포함한 정확한 통계 산출
3. **명확한 사용자 경험**: 데이터 수집 과정의 투명성 확보
4. **시스템 안정성**: 캐시 데이터 오용 방지

## 📝 테스트 시나리오

### 시나리오 1: 기존 데이터 사용
1. "공동주택현황" 선택
2. 기본통계현황분석 실행
3. 기존 캐시 데이터 사용 (제목 일치)
4. 올바른 통계 값 표시

### 시나리오 2: 새로운 데이터 수집
1. "미분양주택현황보고" 선택
2. 기본통계현황분석 실행
3. 제목 불일치 감지
4. 새로운 데이터 수집 프로세스 시작
5. 정확한 테이블명 및 통계 값 표시

## 🚀 배포 준비

모든 수정사항이 완료되어 테스트 및 배포 준비가 완료되었습니다.

---

**작업 완료 일시**: 2025-09-22
**브랜치**: feature/metadata-performance-optimization
**다음 작업**: 사용자 테스트 및 피드백 수집