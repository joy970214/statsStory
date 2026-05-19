"""
외부 vLLM 서버 기반 LLM 서비스
기술통계 중심의 통계 데이터 분석 인사이트 생성
OpenAI 호환 API (/v1/chat/completions) 사용
"""
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# 외부 vLLM 서버 설정
VLLM_BASE_URL = "http://192.168.100.53:8000"
VLLM_MODEL = "google/gemma-4-31B-it"


class OllamaService:
    """외부 vLLM 서버 기반 LLM 서비스 - 기술통계 분석 특화"""

    def __init__(self, base_url: str = VLLM_BASE_URL, model: str = VLLM_MODEL):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = 600
        self.chat_timeout = 120

    def _chat_completions(self, messages: List[Dict], max_tokens: int = 1000, temperature: float = 0.3) -> str:
        """OpenAI 호환 /v1/chat/completions API 호출"""
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
            },
            timeout=self.timeout
        )
        if response.status_code != 200:
            raise Exception(f"vLLM API 오류: {response.status_code} - {response.text[:200]}")
        result = response.json()
        return result['choices'][0]['message']['content'].strip()

    def is_available(self) -> bool:
        """vLLM 서버가 실행 중인지 확인"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_available_models(self) -> List[Dict[str, Any]]:
        """vLLM 서버의 모델 목록 반환"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code != 200:
                return []
            data = response.json()
            models = []
            for m in data.get('data', []):
                models.append({
                    'name': m.get('id', ''),
                    'size_gb': 0,
                    'modified_at': '',
                    'is_current': m.get('id', '') == self.model
                })
            return models
        except Exception as e:
            print(f"[vLLM] 모델 목록 조회 실패: {e}")
            return []

    def set_model(self, model_name: str) -> bool:
        """사용할 모델 변경"""
        self.model = model_name
        print(f"[vLLM] 모델 변경: {model_name}")
        return True

    def get_current_model(self) -> str:
        """현재 사용 중인 모델명 반환"""
        return self.model

    def generate_statistical_insights_by_tables(
        self,
        metadata: Dict[str, Any],
        tables_data: Dict[str, List[Dict]],  # {table_name: [data1, data2, ...]}
        cancellation_checker: Optional[callable] = None  # 취소 체크 콜백
    ) -> Dict[str, Any]:
        """
        통계표별로 나눠서 AI 인사이트 생성 (16K 컨텍스트 제한 대응)

        Args:
            metadata: 통계 메타데이터
            tables_data: {통계표명: 데이터리스트} 딕셔너리
            cancellation_checker: 취소 여부를 확인하는 콜백 함수

        Returns:
            종합된 인사이트
        """
        try:
            print(f"[Ollama] 통계표별 인사이트 생성 시작... (총 {len(tables_data)}개 통계표)")

            table_insights = []

            # 각 통계표별로 개별 인사이트 생성
            for idx, (table_name, table_data) in enumerate(tables_data.items(), 1):
                # 취소 체크
                if cancellation_checker and cancellation_checker():
                    print(f"[Ollama] AI 인사이트 생성이 사용자에 의해 취소되었습니다 (진행: {idx-1}/{len(tables_data)})")
                    raise Exception("AI 인사이트 생성이 취소되었습니다")

                print(f"[Ollama] [{idx}/{len(tables_data)}] '{table_name}' 분석 중... ({len(table_data)}개 데이터)")

                # 통계표별 기본 통계량 계산
                table_summary = self._calculate_table_statistics(table_data)

                # 단일 통계표 인사이트 생성
                insight = self.generate_single_table_insight(
                    table_name=table_name,
                    table_data=table_data,
                    table_summary=table_summary,
                    metadata=metadata
                )

                table_insights.append({
                    'table_name': table_name,
                    'insight': insight,
                    'data_count': len(table_data)
                })

                print(f"[Ollama] [{idx}/{len(tables_data)}] '{table_name}' 분석 완료")

            # 통계표별 인사이트를 종합
            combined_insights = self._combine_table_insights(metadata, table_insights)

            print(f"[Ollama] 통계표별 인사이트 생성 완료: 총 {len(table_insights)}개 통계표")

            return combined_insights

        except Exception as e:
            # 취소 예외는 그대로 전파
            if "취소" in str(e):
                raise
            print(f"[Ollama] 통계표별 인사이트 생성 실패: {e}")
            return self._create_fallback_insights(metadata, {}, list(tables_data.keys()))

    def generate_single_table_insight(
        self,
        table_name: str,
        table_data: List[Dict],
        table_summary: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """단일 통계표에 대한 인사이트 생성.
        CSV raw 텍스트(_raw_csv)가 있으면 그대로 AI에 전달, 없으면 구조화 데이터 사용.
        """
        try:
            # CSV 파일 우선 사용 (AI 분석용)
            # 1순위: csv_file_path 에서 직접 읽기
            # 2순위: data 딕셔너리의 _raw_csv 키 (이전 방식 호환)
            raw_csv = None
            if table_data:
                # csv_file_path 가 있으면 파일에서 직접 읽기
                csv_file_path = table_data[0].get('csv_file_path')
                if csv_file_path:
                    import os
                    if os.path.exists(csv_file_path):
                        encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']
                        for enc in encodings:
                            try:
                                with open(csv_file_path, 'r', encoding=enc) as f:
                                    raw_csv = f.read()
                                print(f"[vLLM] CSV 파일 읽기 성공 ({enc}): {csv_file_path}")
                                break
                            except Exception:
                                continue
                    else:
                        print(f"[vLLM] CSV 파일 없음: {csv_file_path}")

                # csv_file_path 실패 시 _raw_csv 키 확인 (fallback)
                if not raw_csv:
                    first_data = table_data[0].get('data', {})
                    raw_csv = first_data.get('_raw_csv')

            if raw_csv:
                system_msg, user_msg = self._build_csv_raw_prompt(table_name, raw_csv, metadata)
            else:
                system_msg, user_msg = self._build_single_table_prompt(
                    table_name, table_data, table_summary, metadata
                )

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ]
            return self._chat_completions(messages, max_tokens=1200, temperature=0.3)
        except Exception as e:
            print(f"[vLLM] 통계표 '{table_name}' 인사이트 생성 실패: {e}")
            return f"{table_name}: 분석 실패"

    def _build_csv_raw_prompt(self, table_name: str, raw_csv: str, metadata: Dict[str, Any]):
        """CSV 원본 텍스트를 그대로 AI에게 전달하는 프롬프트"""
        stat_name = metadata.get('title', table_name)

        system_msg = (
            "당신은 국토교통부 통계 데이터를 분석하는 데이터 분석가입니다.\n"
            "규칙:\n"
            "1. 제공된 CSV 데이터의 실제 수치만 사용하세요. 데이터에 없는 수치는 절대 작성하지 마세요.\n"
            "2. 추측·원인 분석·정책적 해석·시사점은 작성하지 마세요.\n"
            "3. 기술통계(빈도, 평균, 비율, 증감률, 순위) 수준의 객관적 사실만 기술하세요.\n"
            "4. 지정된 섹션 형식을 반드시 지키세요. 섹션을 임의로 추가하거나 생략하지 마세요.\n"
            "5. 마크다운 형식으로 작성하세요."
        )

        # CSV 토큰 제한: 최대 3000자
        csv_preview = raw_csv[:3000] + ("\n...(이하 생략)" if len(raw_csv) > 3000 else "")

        user_msg = f"""다음은 '{stat_name}' 통계의 '{table_name}' CSV 원본 데이터입니다.

## CSV 원본 데이터
```
{csv_preview}
```

---

## 작성 요청

위 데이터를 분석하여 아래 5개 섹션을 순서대로 작성하세요. 실제 수치만 인용하세요.

### 📊 현황 1: 전체 규모 및 기본 현황
- 가장 최근 기간 기준 전체 규모 수치 기술
- 전체 합계, 평균, 데이터 수 등 기본 통계량 나열

### 📋 현황 2: 주요 항목별 구성 현황
데이터의 주요 항목을 표로 나열:
| 항목 | 수치 | 비율(%) |
|------|------|---------|

### 📈 현황 3: 기간별 증감 현황
- 시작~최근 기간의 증감량, 증감률
- 연도/기간별 수치를 표로 정리:

| 기간 | 주요수치 | 전기대비 증감 |
|------|---------|------------|

### 🏆 현황 4: 순위 현황
수치 기준 상위 3개, 하위 3개 항목 나열

### 📉 현황 5: 분포 및 집중도 현황
- 상위 항목 집중도(비율)
- 수치 범위(최대-최소) 및 분포 특징
"""
        return system_msg, user_msg

    def _build_single_table_prompt(
        self,
        table_name: str,
        table_data: List[Dict],
        table_summary: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        """단일 통계표 분석용 프롬프트 (system, user 튜플 반환)"""

        sample_data = table_data[-50:] if len(table_data) > 50 else table_data

        # 데이터 전처리: 변화율 계산
        trend_info = self._calculate_trend(table_data)

        system_msg = (
            "당신은 국토교통부 통계 데이터를 분석하는 데이터 분석가입니다.\n"
            "규칙:\n"
            "1. 제공된 실제 수치만 사용하세요. 데이터에 없는 수치는 절대 작성하지 마세요.\n"
            "2. 추측·원인 분석·정책적 해석·시사점은 작성하지 마세요.\n"
            "3. 기술통계(빈도, 평균, 비율, 증감률, 순위) 수준의 객관적 사실만 기술하세요.\n"
            "4. 지정된 섹션 형식을 반드시 지키세요. 섹션을 임의로 추가하거나 생략하지 마세요.\n"
            "5. 마크다운 형식으로 작성하세요."
        )

        # 전체 데이터에서 연도별 주요 수치 추출
        yearly_summary = {}
        for item in table_data:
            year = item.get('year', '')
            if not year:
                continue
            values = item.get('data', {})
            nums = {k: v for k, v in values.items() if not k.startswith('_') and v}
            if nums:
                yearly_summary[str(year)] = nums

        sorted_years = sorted(yearly_summary.keys())
        full_data_text = ""
        for year in sorted_years:
            vals = yearly_summary[year]
            val_str = ", ".join([f"{k}: {v}" for k, v in list(vals.items())[:8]])
            full_data_text += f"- {year}년: {val_str}\n"

        # 항목 목록 추출 (첫 번째 데이터 기준)
        field_names = []
        if table_data:
            sample = table_data[0].get('data', {})
            field_names = [k for k in sample.keys() if not k.startswith('_')]

        period_str = f"{sorted_years[0]}~{sorted_years[-1]}년" if len(sorted_years) >= 2 else (sorted_years[0] + "년" if sorted_years else "")

        user_msg = f"""다음 통계표를 분석해주세요.

## 통계표명
{table_name}

## 데이터 구조
- 수집 기간: {period_str}
- 전체 데이터 수: {len(table_data):,}개
- 주요 항목: {', '.join(field_names[:10]) if field_names else '없음'}

## 기본 통계량
- 수치 평균: {table_summary.get('mean', 0):,.2f}
- 최댓값: {table_summary.get('max', 0):,.2f}
- 최솟값: {table_summary.get('min', 0):,.2f}
{trend_info}

## 전체 연도별 데이터
{full_data_text if full_data_text else "데이터 없음"}

---

## 작성 요청

아래 5개 섹션을 순서대로 작성하세요. 각 섹션은 반드시 포함하고, 실제 수치만 인용하세요.

### 📊 현황 1: 전체 규모 및 기본 현황
- 가장 최근 연도 기준 전체 규모 수치 기술
- 전체 합계, 평균, 데이터 수 등 기본 통계량 나열
- 수치는 단위와 함께 표기

### 📋 현황 2: 주요 항목별 구성 현황
데이터의 주요 항목을 구성비(%) 또는 수치로 나열:
| 항목 | 수치 | 비율(%) |
|------|------|---------|
| (항목명) | (수치) | (비율) |

### 📈 현황 3: 기간별 증감 현황 ({period_str})
- 시작 연도 수치 → 최근 연도 수치: 증감량, 증감률
- 최고값: (연도) (수치)
- 최저값: (연도) (수치)
- 연도별 수치를 표로 정리:

| 연도 | 주요수치 | 전년대비 증감 |
|------|---------|------------|
(데이터에서 추출하여 작성)

### 🏆 현황 4: 순위 현황
항목 중 수치 기준 상위 3개와 하위 3개를 순위별로 나열:
- 1위: (항목명) (수치)
- 2위: (항목명) (수치)
- 3위: (항목명) (수치)

### 📉 현황 5: 분포 및 집중도 현황
- 상위 항목이 전체에서 차지하는 비율
- 수치 범위(최댓값 - 최솟값) 및 평균 대비 분포 기술
- 데이터가 특정 항목/구간에 집중되어 있는지 수치로 기술
"""
        return system_msg, user_msg

    def _calculate_trend(self, table_data: List[Dict]) -> str:
        """연도별 트렌드 정보 계산"""
        try:
            yearly = {}
            for item in table_data:
                year = item.get('year', '')
                if not year:
                    continue
                values = item.get('data', {})
                nums = []
                for k, v in values.items():
                    if k.startswith('_'):
                        continue
                    try:
                        nums.append(float(str(v).replace(',', '').replace('%', '')))
                    except:
                        pass
                if nums:
                    yearly[str(year)] = sum(nums) / len(nums)

            if len(yearly) < 2:
                return ""

            sorted_years = sorted(yearly.keys())
            first_val = yearly[sorted_years[0]]
            last_val = yearly[sorted_years[-1]]
            if first_val != 0:
                change_rate = (last_val - first_val) / abs(first_val) * 100
                direction = "증가" if change_rate > 0 else "감소"
                return f"- 기간 변화율: {sorted_years[0]}→{sorted_years[-1]} {abs(change_rate):.1f}% {direction}"
            return ""
        except:
            return ""

    def _calculate_table_statistics(self, table_data: List[Dict]) -> Dict[str, Any]:
        """통계표별 기본 통계량 계산"""
        numeric_values = []

        for item in table_data:
            data = item.get('data', {})
            for key, value in data.items():
                if key.startswith('_'):
                    continue
                try:
                    if isinstance(value, (int, float)):
                        numeric_values.append(float(value))
                    elif isinstance(value, str):
                        cleaned = value.replace(',', '').replace('%', '').strip()
                        numeric_values.append(float(cleaned))
                except (ValueError, TypeError):
                    continue

        if not numeric_values:
            return {'mean': 0, 'max': 0, 'min': 0, 'count': 0}

        import numpy as np
        return {
            'mean': float(np.mean(numeric_values)),
            'max': float(np.max(numeric_values)),
            'min': float(np.min(numeric_values)),
            'count': len(numeric_values)
        }

    def _combine_table_insights(
        self,
        metadata: Dict[str, Any],
        table_insights: List[Dict]
    ) -> Dict[str, Any]:
        """통계표별 인사이트를 종합"""

        stat_name = metadata.get('title', '통계')
        table_names = [t['table_name'] for t in table_insights]

        # 종합 인사이트 구조 생성
        combined = {
            'stat_name': stat_name,
            'raw_text': '',
            'insights_count': len(table_insights),
            'generated_at': datetime.now().isoformat(),
            'model': self.model,

            # 필수 항목
            'analysis_title': f'{stat_name} 통계표별 현황 분석',
            'analysis_overview': f'{stat_name}의 {len(table_names)}개 통계표를 개별 분석하여 종합한 결과입니다.',
            'analysis_purpose': f'- {stat_name}의 통계표별 현황 파악\n- 각 통계표의 주요 특징 분석',
            'data_sources': '\n'.join([f'- {name}' for name in table_names])
        }

        # 통계표별 인사이트를 insight_1, insight_2, ... 형태로 저장
        for idx, table_insight in enumerate(table_insights, 1):
            combined[f'insight_{idx}'] = {
                'title': table_insight['table_name'],
                'method': '기본 통계량 산출',
                'items': table_insight['table_name'],
                'content': table_insight['insight'],
                'features': f"데이터 수: {table_insight['data_count']:,}개",
                'visualization': '막대그래프'
            }

        return combined

    def generate_statistical_insights(
        self,
        metadata: Dict[str, Any],
        data_summary: Dict[str, Any],
        table_names: List[str],
        raw_data_sample: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        기술통계 중심의 AI 인사이트 생성 (10개 카테고리)

        Args:
            metadata: 통계 메타데이터
            data_summary: 기본 통계량 (평균, 최대, 최소, 총합 등)
            table_names: 수집된 통계표 목록
            raw_data_sample: 원본 데이터 샘플 (선택)

        Returns:
            구조화된 10개 카테고리 인사이트
        """
        try:
            import time
            system_msg, user_msg = self._build_descriptive_stats_prompt(
                metadata, data_summary, table_names, raw_data_sample
            )
            print(f"[vLLM] 기술통계 인사이트 생성 시작... 모델: {self.model}")
            start_api = time.time()
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ]
            generated_text = self._chat_completions(messages, max_tokens=1500, temperature=0.3)
            print(f"[vLLM] 응답 수신 완료: {time.time() - start_api:.2f}초, {len(generated_text)}자")

            insights = self._parse_descriptive_insights(generated_text)
            insights['generated_at'] = datetime.now().isoformat()
            insights['model'] = self.model
            insights['stat_name'] = metadata.get('title', '알 수 없음')
            return insights

        except Exception as e:
            print(f"[vLLM] 인사이트 생성 실패: {e}")
            return self._create_fallback_insights(metadata, data_summary, table_names)

    def chat(
        self,
        message: str,
        context: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """통계 데이터 기반 채팅"""
        try:
            system_msg, user_msg = self._build_chat_prompt(message, context, chat_history)
            print(f"[vLLM Chat] 사용자: {message[:50]}...")

            messages = []
            messages.append({"role": "system", "content": system_msg})

            # 대화 히스토리 포함
            if chat_history:
                for chat in chat_history[-4:]:
                    role = chat.get('role', '')
                    content = chat.get('content', '')
                    if role in ('user', 'assistant') and content:
                        messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": user_msg})

            ai_response = self._chat_completions(messages, max_tokens=500, temperature=0.3)
            print(f"[vLLM Chat] AI: {ai_response[:50]}...")
            return ai_response

        except Exception as e:
            print(f"[vLLM Chat] 오류: {e}")
            return "죄송합니다. 현재 응답을 생성할 수 없습니다. 잠시 후 다시 시도해주세요."

    def _build_descriptive_stats_prompt(
        self,
        metadata: Dict[str, Any],
        data_summary: Dict[str, Any],
        table_names: List[str],
        raw_data_sample: Optional[List[Dict]] = None
    ):
        """기술통계 분석용 프롬프트 작성 (system, user 튜플 반환)"""

        stat_name = metadata.get('title', '알 수 없는 통계')
        stat_info = metadata.get('statistical_info', {})

        system_msg = "당신은 국토교통부 통계 데이터 분석 전문가입니다. 기술통계 중심의 현황 분석을 수행하고 지정된 형식으로 한국어 인사이트를 작성하세요."

        prompt = f"""## 통계 기본 정보
- 통계명: {stat_name}
- 담당 부서: {metadata.get('department', '정보 없음')}
- 수집 통계표: {len(table_names)}개 ({', '.join(table_names[:3])}{' 외' if len(table_names) > 3 else ''})

## 통계 상세 정보
"""

        # 통계정보 추가 (주요 항목만)
        if stat_info:
            for key, value in list(stat_info.items())[:5]:
                prompt += f"- {key}: {str(value)[:200]}\n"

        prompt += f"""
## 기본 통계량
- 평균: {data_summary.get('mean', 0):,.2f}
- 중위수: {data_summary.get('median', 0):,.2f}
- 최댓값: {data_summary.get('max', 0):,.2f}
- 최솟값: {data_summary.get('min', 0):,.2f}
- 총합: {data_summary.get('total', 0):,.2f}
- 표준편차: {data_summary.get('std_dev', 0):,.2f}
- 데이터 수: {data_summary.get('count', 0):,}개
"""

        # JSON 데이터 샘플 추가
        if raw_data_sample and len(raw_data_sample) > 0:
            prompt += f"""
## 실제 데이터 샘플 ({len(raw_data_sample)}개)
**아래는 실제 수집된 통계 데이터입니다. 이 데이터를 기반으로 분석해주세요:**

"""
            # JSON 데이터를 프롬프트에 포함
            for idx, sample in enumerate(raw_data_sample, 1):
                year = sample.get('year', '')
                table_name = sample.get('table_name', '')
                data = sample.get('data', {})

                # 데이터 구조를 읽기 쉬운 형태로 변환
                sample_text = f"{idx}. "
                if year:
                    sample_text += f"[{year}년] "
                if table_name:
                    sample_text += f"({table_name}) "

                # data 딕셔너리를 key: value 형태로 변환
                if data:
                    data_parts = []
                    for key, value in data.items():
                        # 특수 키나 너무 긴 키는 건너뛰기
                        if key.startswith('_') or len(str(key)) > 100:
                            continue
                        # 의미있는 데이터만 포함
                        if value and str(value).strip() and str(value) != ' ':
                            data_parts.append(f"{key}={value}")

                    if data_parts:
                        sample_text += ", ".join(data_parts[:10])  # 최대 10개 항목만

                prompt += f"{sample_text}\n"

        prompt += """
## 분석 요청사항
제공된 데이터를 분석하여 **의미있는 인사이트만** 생성해주세요. 아래는 참고할 수 있는 카테고리 예시입니다:

**필수 항목:**
1-1. 분석주제명
1-2. 주제 개요 및 의의(배경)
1-3. 분석 목적

2-1. 분석에 사용 데이터 통계표명

**분석 인사이트 예시** (해당되는 것만 선택):
3-1. 기본 현황: 전체 데이터 규모, 총합, 평균 등
3-2. 분포 현황: 데이터 분산/집중 정도
3-3. 순위 현황: 최대/최소값, 상위/하위 순위
3-4. 비교 현황: 통계표 간, 카테고리 간 비교
3-5. 지역 현황: 지역별 데이터 분포
3-6. 증감 현황: 시계열 변화, 증감률
3-7. 집중도 현황: 표준편차, 상위 집중도
3-8. 특징 현황: 데이터의 독특한 특징, 이상치, 패턴
3-9. 구성비 현황: 각 항목이 차지하는 비율
3-10. 요약 및 시사점: 전체 분석 요약

**중요 규칙:**
1. 제공된 데이터로 **분석 가능한 인사이트만** 생성하세요
2. 데이터가 부족하거나 의미없는 카테고리는 **생략**하세요
3. 분석주제와 목적, 의의(배경)과 분석에 사용된 통계표명은 필수로 생성하세요
4. 기초통계현황 인사이트는 최소 1개 ~ 최대 10개 인사이트를 생성하세요
5. 객관적 사실만 작성하고, 추측이나 예측은 금지합니다
6. 각 인사이트는 2-3문장으로 간결하게 작성하세요
7. 복잡한 통계 검정이나 고급 기법은 사용하지 마세요
8. 한국어로 명확하게 작성하세요
9. 인사이트에 어울리는 시각화를 추천하세요 (예시: 표, 막대그래프, 순위 막대그래프, 원그래프, 비교 막대그래프, 누적 막대그래프, 파레토 그래프 등)

**답변 형식** (반드시 아래 형식 준수):
1-1. 분석주제명
[분석주제명 작성]

1-2. 주제 개요 및 의의(배경)
[주제 개요 및 배경 작성]

1-3. 분석 목적
[분석 목적을 항목별로 작성]

2-1. 분석에 사용 데이터 통계표명
[사용된 통계표 목록]

3-1. [인사이트명]
기초통계 방법: [사용된 통계 방법]
분석 항목: [분석한 항목]
분석 내용: [상세 분석 내용]
주요특징: [주요 특징 항목별로]
추천 차트 유형: [차트 형태, 축 정보 등 상세하게]

3-2. [인사이트명]
기초통계 방법: [사용된 통계 방법]
분석 항목: [분석한 항목]
분석 내용: [상세 분석 내용]
주요특징: [주요 특징 항목별로]
추천 차트 유형: [차트 형태, 축 정보 등 상세하게]

(이하 생략)

**예시:**
1-1. 분석주제명
개인 토지소유 현황 분석 (연령별 및 규모별 토지소유 구조 변화)

1-2. 주제 개요 및 의의(배경)
개인 토지소유자들의 연령별, 규모별 특성과 소유 집중도를 기초통계 중심으로 분석하여 우리나라 개인 토지소유의 구조적 현황을 파악

1-3. 분석 목적
- 연령대별 개인 토지소유 현황의 기초통계 파악
- 면적규모별/가액규모별 소유자수 및 세대수 분포 현황 분석
- 2020-2024년 5개년간 개인 토지소유 변화 추이 분석

2-1. 분석에 사용 데이터 통계표명
- 개인_토지의_연령별_소유현황
- 개인_토지의_성별_연령별_소유현황
- 개인_토지의_면적규모별_소유자수_현황

3-1. 개인(민유지) 토지소유의 전체 규모 및 구성
기초통계 방법: 평균, 합계, 비율 계산을 통한 기본 현황 파악
분석 항목: 개인(민유지) 토지소유의 전체 규모 및 구성
분석 내용: 전체 개인 토지소유 규모는 총 면적 572.2km², 총 지번수 285.0만 필지, 총 가액 5,498.8조원, 소유자 수 약 1,903만 명입니다. 세대별로는 청년층(20-39세) 54.2km² (9.5%), 중장년층(40-64세) 275.2km² (48.1%), 고령층(65세+) 240.8km² (42.1%)로 확인됩니다.
주요특징: 지속적 증가 추세 (5년간 27.8% 증가), 중장년층 중심 (48.1%), 고령화 심화 (42.1%), 청년층 저조 (9.5%)
추천 차트 유형: 수평 막대그래프 + 파이차트 조합 (Y축: 연령대, X축: 면적(km²))
"""

        return system_msg, prompt

    def _build_chat_prompt(
        self,
        message: str,
        context: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ):
        """채팅용 프롬프트 (system, user 튜플 반환)"""

        metadata = context.get('metadata', {})
        insights = context.get('ai_insights', {})
        relevant_data = context.get('relevant_data', {})

        system_msg = (
            f"당신은 '{metadata.get('title', '통계')}' 데이터를 전문적으로 분석하는 통계 분석가입니다. "
            "제공된 데이터와 인사이트만 활용하여 정확하고 간결하게 한국어로 답변하세요. "
            "데이터에 없는 내용은 추측하지 말고 '제공된 데이터에는 해당 정보가 없습니다'라고 하세요."
        )

        user_msg = f"## 통계 기본 정보\n- 통계명: {metadata.get('title', '')}\n- 담당부서: {metadata.get('department', '')}\n"

        # AI 인사이트 요약
        if insights and insights.get('insights_count', 0) > 0:
            user_msg += "\n## 분석 인사이트\n"
            for i in range(1, min(insights.get('insights_count', 0) + 1, 6)):
                key = f'insight_{i}'
                if key in insights:
                    insight = insights[key]
                    title = insight.get('title', '')
                    content = insight.get('content', '')[:200]
                    user_msg += f"- {title}: {content}\n"

        # 관련 데이터 (RAG)
        relevant_docs = relevant_data.get('documents', [])
        relevant_metas = relevant_data.get('metadatas', [])
        if relevant_docs:
            user_msg += f"\n## 관련 데이터 ({len(relevant_docs)}건)\n"
            for idx, (doc, meta) in enumerate(zip(relevant_docs[:5], relevant_metas[:5]), 1):
                year = meta.get('year', '')
                table_name = meta.get('table_name', '')
                user_msg += f"{idx}. [{year}년] {table_name}: {doc[:200]}\n"

        user_msg += f"\n## 질문\n{message}"

        return system_msg, user_msg

    def _parse_descriptive_insights(self, generated_text: str) -> Dict[str, Any]:
        """
        새로운 구조의 인사이트 파싱
        1-1, 1-2, 1-3: 분석주제, 개요, 목적
        2-1: 사용 데이터
        3-1 ~ 3-10: 기초통계 인사이트 (가변)
        """

        insights = {
            'raw_text': generated_text,
            'insights_count': 0,
            # 필수 항목
            'analysis_title': '',           # 1-1
            'analysis_overview': '',        # 1-2
            'analysis_purpose': '',         # 1-3
            'data_sources': ''              # 2-1
        }

        try:
            lines = generated_text.split('\n')
            current_section = None
            current_content = []
            current_subsection = None  # 기초통계 방법, 분석 항목 등

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                if not line:
                    i += 1
                    continue

                # 1-1. 분석주제명
                if line.startswith('1-1.'):
                    if current_section:
                        self._save_section(insights, current_section, current_content, current_subsection)
                    current_section = 'analysis_title'
                    current_content = [line.replace('1-1.', '').strip()]
                    current_subsection = None

                # 1-2. 주제 개요 및 의의(배경)
                elif line.startswith('1-2.'):
                    if current_section:
                        self._save_section(insights, current_section, current_content, current_subsection)
                    current_section = 'analysis_overview'
                    current_content = [line.replace('1-2.', '').strip()]
                    current_subsection = None

                # 1-3. 분석 목적
                elif line.startswith('1-3.'):
                    if current_section:
                        self._save_section(insights, current_section, current_content, current_subsection)
                    current_section = 'analysis_purpose'
                    current_content = [line.replace('1-3.', '').strip()]
                    current_subsection = None

                # 2-1. 분석에 사용 데이터 통계표명
                elif line.startswith('2-1.'):
                    if current_section:
                        self._save_section(insights, current_section, current_content, current_subsection)
                    current_section = 'data_sources'
                    current_content = [line.replace('2-1.', '').strip()]
                    current_subsection = None

                # 3-1 ~ 3-10. 기초통계 인사이트
                elif line.startswith('3-'):
                    # 3-1. 형식 체크
                    parts = line.split('.', 1)
                    if len(parts) == 2 and parts[0].startswith('3-'):
                        # 이전 섹션 저장
                        if current_section:
                            self._save_section(insights, current_section, current_content, current_subsection)

                        # 인사이트 번호 추출 (3-1 -> 1, 3-10 -> 10)
                        try:
                            insight_num = int(parts[0].replace('3-', ''))
                            current_section = f'insight_{insight_num}'
                            insights['insights_count'] += 1

                            # 인사이트명 (제목)
                            insight_title = parts[1].strip()
                            current_content = {
                                'title': insight_title,
                                'method': '',
                                'items': '',
                                'content': '',
                                'features': '',
                                'visualization': ''
                            }
                            current_subsection = None
                        except ValueError:
                            current_content.append(line)

                # 인사이트 내부의 하위 섹션
                elif current_section and current_section.startswith('insight_'):
                    if line.startswith('기초통계 방법:'):
                        current_subsection = 'method'
                        current_content['method'] = line.replace('기초통계 방법:', '').strip()
                    elif line.startswith('분석 항목:'):
                        current_subsection = 'items'
                        current_content['items'] = line.replace('분석 항목:', '').strip()
                    elif line.startswith('분석 내용:') or line.startswith('분석내용:'):
                        current_subsection = 'content'
                        current_content['content'] = line.replace('분석 내용:', '').replace('분석내용:', '').strip()
                    elif line.startswith('주요특징:'):
                        current_subsection = 'features'
                        current_content['features'] = line.replace('주요특징:', '').strip()
                    elif line.startswith('추천 차트 유형:'):
                        current_subsection = 'visualization'
                        current_content['visualization'] = line.replace('추천 차트 유형:', '').strip()
                    else:
                        # 현재 하위섹션에 내용 추가
                        if current_subsection and isinstance(current_content, dict):
                            if current_content[current_subsection]:
                                current_content[current_subsection] += ' ' + line
                            else:
                                current_content[current_subsection] = line
                        elif isinstance(current_content, list):
                            current_content.append(line)

                # 기타 내용 추가
                else:
                    if current_section:
                        if isinstance(current_content, list):
                            current_content.append(line)
                        elif isinstance(current_content, dict) and current_subsection:
                            if current_content[current_subsection]:
                                current_content[current_subsection] += ' ' + line
                            else:
                                current_content[current_subsection] = line

                i += 1

            # 마지막 섹션 저장
            if current_section:
                self._save_section(insights, current_section, current_content, current_subsection)

        except Exception as e:
            print(f"[Ollama] 인사이트 파싱 오류: {e}")
            import traceback
            traceback.print_exc()

        return insights

    def _save_section(self, insights: Dict, section: str, content, subsection):
        """섹션 내용을 insights에 저장"""
        if section in ['analysis_title', 'analysis_overview', 'analysis_purpose', 'data_sources']:
            # 필수 항목은 문자열로 저장
            insights[section] = '\n'.join(content).strip() if isinstance(content, list) else str(content)
        elif section.startswith('insight_'):
            # 인사이트는 딕셔너리로 저장
            if isinstance(content, dict):
                insights[section] = content
            else:
                insights[section] = {'content': '\n'.join(content).strip() if isinstance(content, list) else str(content)}

    def _create_fallback_insights(
        self,
        metadata: Dict[str, Any],
        data_summary: Dict[str, Any],
        table_names: List[str]
    ) -> Dict[str, Any]:
        """Ollama 실패 시 기본 인사이트 생성 (새 구조)"""

        stat_name = metadata.get('title', '통계')
        count = data_summary.get('count', 0)
        mean = data_summary.get('mean', 0)
        total = data_summary.get('total', 0)
        max_val = data_summary.get('max', 0)
        min_val = data_summary.get('min', 0)

        return {
            'stat_name': stat_name,
            'raw_text': '',
            'insights_count': 3,

            # 필수 항목
            'analysis_title': f'{stat_name} 기본 통계 분석',
            'analysis_overview': f'{stat_name}에 대한 기초 통계량 중심의 현황 분석입니다.',
            'analysis_purpose': f'- {stat_name}의 전체 규모 및 기본 통계량 파악\n- 데이터 분포 현황 분석\n- 주요 특징 도출',
            'data_sources': '\n'.join([f'- {name}' for name in table_names[:5]]),

            # 기초통계 인사이트
            'insight_1': {
                'title': '기본 현황',
                'method': '평균, 합계, 개수 등 기본 통계량 산출',
                'items': '전체 데이터 규모 및 기본 통계량',
                'content': f'총 {count:,}개의 데이터가 수집되었습니다. 전체 합계는 {total:,.2f}이며, 평균값은 {mean:,.2f}입니다.',
                'features': f'데이터 수: {count:,}개, 평균: {mean:,.2f}, 합계: {total:,.2f}',
                'visualization': '표 또는 텍스트'
            },
            'insight_2': {
                'title': '분포 현황',
                'method': '최댓값, 최솟값 확인을 통한 분포 범위 파악',
                'items': '데이터 분포 범위 및 변동성',
                'content': f'데이터는 최솟값 {min_val:,.2f}에서 최댓값 {max_val:,.2f} 사이에 분포되어 있습니다.',
                'features': f'최솟값: {min_val:,.2f}, 최댓값: {max_val:,.2f}, 범위: {max_val - min_val:,.2f}',
                'visualization': '막대그래프 (X축: 항목, Y축: 값)'
            },
            'insight_3': {
                'title': '요약 및 시사점',
                'method': '전체 분석 결과 종합',
                'items': '분석 결과 요약',
                'content': f'{stat_name}에 대한 기본 통계 분석이 완료되었습니다. 총 {len(table_names)}개의 통계표를 분석하였으며, 상세 분석을 위해서는 AI 서비스가 필요합니다.',
                'features': f'수집 통계표 수: {len(table_names)}개, 분석 완료',
                'visualization': '종합 표'
            },

            'generated_at': datetime.now().isoformat(),
            'model': 'fallback',
            'note': 'Ollama 서비스를 사용할 수 없어 기본 인사이트를 제공합니다.'
        }


# 싱글톤 인스턴스
ollama_service = OllamaService()
