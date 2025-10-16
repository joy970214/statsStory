# 디자인 시스템 가이드

## 폰트

### Paperlogy (타이틀 전용)
모든 제목(H1~H6)에 Paperlogy 폰트를 사용합니다.

**특징:**
- 세련되고 현대적인 디자인
- 100~900 weight 지원
- 타이틀에 적합한 가독성
- 무료 사용 가능

**사용:**
```css
/* CSS에서 */
font-family: 'Paperlogy', 'Pretendard Variable', sans-serif;

/* Tailwind에서 */
className="font-paperlogy"
```

### Pretendard Variable (본문)
본문 텍스트에 [Pretendard](https://github.com/orioncactus/pretendard) 폰트를 사용합니다.

**특징:**
- 한글 최적화 가독성
- 가변 폰트 (100~900 weight)
- 다이나믹 서브셋 (빠른 로딩)
- 크로스 플랫폼 일관성
- SIL 오픈 폰트 라이선스

**사용:**
```css
/* CSS에서 */
font-family: "Pretendard Variable", Pretendard, sans-serif;

/* Tailwind에서 */
className="font-pretendard"
```

## 색상 팔레트

### Primary (Blue)
- 주요 액션 버튼, 링크, 강조 요소
- `primary-50` ~ `primary-900`
- 예: 분석하기, 상세보기 버튼

### Secondary (Gray)
- 중립적 UI 요소, 텍스트
- `secondary-50` ~ `secondary-900`

### Success (Green)
- 성공 상태, 긍정적 정보
- `success-50`, `success-100`, `success-500`, `success-600`, `success-700`

### Danger (Red)
- 경고, 삭제, 오류
- `danger-50`, `danger-100`, `danger-500`, `danger-600`, `danger-700`

### Warning (Amber)
- 주의, 경고 정보
- `warning-50`, `warning-100`, `warning-500`, `warning-600`, `warning-700`

### Info (Blue)
- 정보 표시
- `info-50`, `info-100`, `info-500`, `info-600`, `info-700`

## 타이포그래피

### 페이지 제목 (H1)
```tsx
<h1 className="text-2xl font-bold text-gray-900 mb-2">
  {/* Paperlogy 폰트 자동 적용 */}
</h1>
```

### 섹션 제목 (H2)
```tsx
<h2 className="text-xl font-bold text-gray-900 mb-4">
  {/* Paperlogy 폰트 자동 적용 */}
</h2>
```

### 서브섹션 제목 (H3)
```tsx
<h3 className="text-lg font-semibold text-gray-900 mb-3">
  {/* Paperlogy 폰트 자동 적용 */}
</h3>
```

**참고:** 모든 제목(h1~h6)은 자동으로 Paperlogy 폰트가 적용됩니다.  
필요시 `font-pretendard` 클래스로 Pretendard를 명시적으로 사용할 수 있습니다.

### 본문 텍스트
```tsx
<p className="text-gray-600">
```

### 작은 텍스트
```tsx
<p className="text-sm text-gray-500">
```

## 버튼

### Primary 버튼 (주요 액션)
```tsx
<button className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors text-sm font-medium">
  분석하기
</button>
```

### Secondary 버튼 (보조 액션)
```tsx
<button className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors text-sm font-medium">
  뒤로 가기
</button>
```

### Success 버튼 (긍정적 액션)
```tsx
<button className="bg-success-600 text-white px-4 py-2 rounded-md hover:bg-success-700 transition-colors text-sm font-medium">
  저장
</button>
```

### Danger 버튼 (위험한 액션)
```tsx
<button className="bg-danger-600 text-white px-4 py-2 rounded-md hover:bg-danger-700 transition-colors text-sm font-medium">
  삭제
</button>
```

## 카드

### 기본 카드
```tsx
<div className="bg-white rounded-lg shadow border border-gray-200 p-6">
```

### 정보 카드 (색상별)
```tsx
<!-- Primary -->
<div className="bg-primary-50 border border-primary-200 rounded-lg p-6">

<!-- Success -->
<div className="bg-success-50 border border-success-200 rounded-lg p-6">

<!-- Warning -->
<div className="bg-warning-50 border border-warning-200 rounded-lg p-6">

<!-- Danger -->
<div className="bg-danger-50 border border-danger-200 rounded-lg p-6">
```

## 간격 (Spacing)

- 페이지 섹션 간: `mb-8`
- 카드 내부: `p-6`
- 요소 간 작은 간격: `gap-2` 또는 `mb-2`
- 요소 간 중간 간격: `gap-4` 또는 `mb-4`
- 요소 간 큰 간격: `gap-6` 또는 `mb-6`

## 모서리 (Border Radius)

- 카드, 박스: `rounded-lg`
- 버튼: `rounded-md`
- 작은 요소, 뱃지: `rounded-full`

## 그림자 (Shadow)

- 카드: `shadow`
- Hover 시: `hover:shadow-md`
- **사용 금지**: `shadow-lg`, `shadow-xl`, `shadow-2xl`

## 애니메이션

- 버튼, 링크 hover: `transition-colors`
- 카드 hover: `transition-shadow`
- **사용 금지**: `transform`, `scale`, `translate`, 복잡한 framer-motion

## 금지 사항

❌ **사용하지 말 것:**
- Gradient 배경 (`bg-gradient-to-*`)
- Gradient 텍스트 (`bg-clip-text text-transparent`)
- 이모지 (아이콘 사용)
- 과도한 애니메이션 (scale, translate, rotate)
- 큰 그림자 (`shadow-lg` 이상)
- `rounded-xl`, `rounded-2xl` (rounded-lg 사용)

## 사용 예시

### 페이지 헤더
```tsx
<div className="mb-8">
  <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-3">
    <IconComponent className="w-7 h-7 text-primary-600" />
    페이지 제목
  </h1>
  <p className="text-gray-600">
    페이지 설명
  </p>
</div>
```

### 액션 버튼 그룹
```tsx
<div className="flex gap-2">
  <button className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors text-sm font-medium">
    주요 액션
  </button>
  <button className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors text-sm font-medium">
    보조 액션
  </button>
</div>
```

