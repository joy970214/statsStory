"""
Ollama 오프라인 LLM 서비스
기술통계 중심의 통계 데이터 분석 인사이트 생성
"""
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class OllamaService:
    """Ollama LLM 서비스 - 기술통계 분석 특화"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:8b-instruct-q4_K_M"):
        self.base_url = base_url
        self.model = model
        self.timeout = 600  # 10분 타임아웃 (통계표별 분석)
        self.chat_timeout = 120  # 2분 타임아웃 (채팅용)

    def is_available(self) -> bool:
        """Ollama 서버가 실행 중인지 확인"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def generate_statistical_insights_by_tables(
        self,
        metadata: Dict[str, Any],
        tables_data: Dict[str, List[Dict]]  # {table_name: [data1, data2, ...]}
    ) -> Dict[str, Any]:
        """
        통계표별로 나눠서 AI 인사이트 생성 (16K 컨텍스트 제한 대응)

        Args:
            metadata: 통계 메타데이터
            tables_data: {통계표명: 데이터리스트} 딕셔너리

        Returns:
            종합된 인사이트
        """
        try:
            print(f"[Ollama] 통계표별 인사이트 생성 시작... (총 {len(tables_data)}개 통계표)")

            table_insights = []

            # 각 통계표별로 개별 인사이트 생성
            for idx, (table_name, table_data) in enumerate(tables_data.items(), 1):
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
            print(f"[Ollama] 통계표별 인사이트 생성 실패: {e}")
            return self._create_fallback_insights(metadata, {}, list(tables_data.keys()))

    def generate_single_table_insight(
        self,
        table_name: str,
        table_data: List[Dict],
        table_summary: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """단일 통계표에 대한 인사이트 생성 (간단 버전)"""
        try:
            # 프롬프트 구성 (간결한 버전)
            prompt = self._build_single_table_prompt(
                table_name, table_data, table_summary, metadata
            )

            # Ollama API 호출
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 500,  # 통계표당 500 토큰
                        "num_ctx": 16384
                    }
                },
                timeout=self.timeout
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API 오류: {response.status_code}")

            result = response.json()
            return result.get('response', '').strip()

        except Exception as e:
            print(f"[Ollama] 통계표 '{table_name}' 인사이트 생성 실패: {e}")
            return f"{table_name}: 분석 실패"

    def _build_single_table_prompt(
        self,
        table_name: str,
        table_data: List[Dict],
        table_summary: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """단일 통계표 분석용 프롬프트 (간결 버전)"""

        # 최신 데이터 50개만 사용 (16K 컨텍스트 제한)
        sample_data = table_data[-50:] if len(table_data) > 50 else table_data

        prompt = f"""당신은 통계 데이터 분석 전문가입니다. '{table_name}' 통계표를 분석해주세요.

## 통계표 정보
- 통계표명: {table_name}
- 데이터 수: {len(table_data):,}개
- 평균: {table_summary.get('mean', 0):,.2f}
- 최댓값: {table_summary.get('max', 0):,.2f}
- 최솟값: {table_summary.get('min', 0):,.2f}

## 데이터 샘플 (최신 {len(sample_data)}개)
"""

        # 샘플 데이터 추가
        for idx, data in enumerate(sample_data[:30], 1):  # 최대 30개만
            year = data.get('year', '')
            values = data.get('data', {})

            # 주요 값만 추출 (최대 5개)
            main_values = []
            for k, v in list(values.items())[:5]:
                if not k.startswith('_'):
                    main_values.append(f"{k}={v}")

            if main_values:
                prompt += f"{idx}. [{year}년] {', '.join(main_values)}\n"

        prompt += """
## 분석 요청
이 통계표의 주요 특징을 2-3문장으로 간결하게 분석해주세요:
- 전체 규모 및 추세
- 주요 특징 (최댓값/최솟값, 증감 패턴 등)
- 한줄 요약

답변:"""

        return prompt

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

            # 프롬프트 구성
            start_prompt = time.time()
            prompt = self._build_descriptive_stats_prompt(
                metadata, data_summary, table_names, raw_data_sample
            )
            prompt_time = time.time() - start_prompt

            print(f"[Ollama] 기술통계 인사이트 생성 시작...")
            print(f"[Ollama] 모델: {self.model}")
            print(f"[Ollama] 프롬프트 생성 시간: {prompt_time:.2f}초")
            print(f"[Ollama] 프롬프트 길이: {len(prompt):,}자 ({len(prompt.encode('utf-8')):,} bytes)")
            print(f"[Ollama] 데이터 샘플 개수: {len(raw_data_sample) if raw_data_sample else 0}개")

            # Ollama API 호출
            print(f"[Ollama] API 요청 전송 중...")
            start_api = time.time()

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # 낮은 temperature로 객관적 분석
                        "top_p": 0.9,
                        "num_predict": 1000,  # 10개 인사이트를 위해 늘림
                        "num_ctx": 16384  # 16K 토큰 컨텍스트 (기본 8K → 16K)
                    }
                },
                timeout=self.timeout
            )

            api_time = time.time() - start_api
            print(f"[Ollama] API 응답 수신 완료: {api_time:.2f}초 소요")

            if response.status_code != 200:
                raise Exception(f"Ollama API 오류: {response.status_code}")

            result = response.json()
            generated_text = result.get('response', '')

            print(f"[Ollama] 인사이트 생성 완료 (응답 길이: {len(generated_text)}자)")
            print(f"[Ollama] 총 소요 시간: {prompt_time + api_time:.2f}초")

            # 생성된 텍스트를 10개 카테고리로 구조화
            insights = self._parse_descriptive_insights(generated_text)
            insights['generated_at'] = datetime.now().isoformat()
            insights['model'] = self.model
            insights['stat_name'] = metadata.get('title', '알 수 없음')

            return insights

        except Exception as e:
            print(f"[Ollama] 인사이트 생성 실패: {e}")
            return self._create_fallback_insights(metadata, data_summary, table_names)

    def chat(
        self,
        message: str,
        context: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        통계 데이터 기반 채팅

        Args:
            message: 사용자 메시지
            context: 통계 데이터 컨텍스트 (메타데이터 + 인사이트)
            chat_history: 이전 대화 히스토리

        Returns:
            AI 응답 텍스트
        """
        try:
            # 채팅 프롬프트 구성
            prompt = self._build_chat_prompt(message, context, chat_history)

            print(f"[Ollama Chat] 사용자: {message[:50]}...")

            # Ollama API 호출
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 500,  # 짧은 답변 유도
                        "num_ctx": 16384  # 16K 토큰 컨텍스트 (채팅용)
                    }
                },
                timeout=self.chat_timeout
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API 오류: {response.status_code}")

            result = response.json()
            ai_response = result.get('response', '')

            print(f"[Ollama Chat] AI: {ai_response[:50]}...")

            return ai_response.strip()

        except Exception as e:
            print(f"[Ollama Chat] 오류: {e}")
            return "죄송합니다. 현재 응답을 생성할 수 없습니다. 잠시 후 다시 시도해주세요."

    def _build_descriptive_stats_prompt(
        self,
        metadata: Dict[str, Any],
        data_summary: Dict[str, Any],
        table_names: List[str],
        raw_data_sample: Optional[List[Dict]] = None
    ) -> str:
        """기술통계 분석용 프롬프트 작성 (10개 카테고리)"""

        stat_name = metadata.get('title', '알 수 없는 통계')
        stat_info = metadata.get('statistical_info', {})

        prompt = f"""당신은 통계 데이터 분석 전문가입니다. 아래 통계 데이터에 대해 **기술통계 중심의 현황 분석**을 수행해주세요.

## 통계 기본 정보
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

        return prompt

    def _build_chat_prompt(
        self,
        message: str,
        context: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """채팅용 프롬프트 작성 (RAG 방식 - ChromaDB 검색 결과 활용)"""

        metadata = context.get('metadata', {})
        insights = context.get('ai_insights', {})
        relevant_data = context.get('relevant_data', {})

        prompt = f"""당신은 통계 데이터 분석 전문가입니다. 사용자의 질문에 답변할 때 반드시 아래의 데이터만을 참고하세요.

## 통계 정보
- 통계명: {metadata.get('title', '알 수 없음')}
- 담당 부서: {metadata.get('department', '정보 없음')}

## 분석 인사이트 (종합 분석)
"""

        # AI 인사이트 요약 (간결하게)
        if insights and insights.get('insights_count', 0) > 0:
            prompt += "\n"
            # 주요 인사이트만 3개 포함 (타임아웃 방지)
            for i in [1, 3, 10]:  # 기본현황, 순위현황, 요약
                key = f'insight_{i}'
                if key in insights:
                    insight = insights[key]
                    content = insight.get('content', '')[:150]  # 150자로 제한
                    prompt += f"- {insight.get('category', '')}: {content}\n"

        # ChromaDB에서 검색된 관련 데이터 추가 (RAG)
        relevant_docs = relevant_data.get('documents', [])
        relevant_metas = relevant_data.get('metadatas', [])

        if relevant_docs:
            prompt += f"\n## 질문과 관련된 상세 데이터 ({len(relevant_docs)}개)\n"
            # 최대 5개만 포함 (타임아웃 방지)
            for idx, (doc, meta) in enumerate(zip(relevant_docs[:5], relevant_metas[:5]), 1):
                year = meta.get('year', '')
                table_name = meta.get('table_name', '')

                prompt += f"\n{idx}. "
                if year:
                    prompt += f"[{year}년] "
                if table_name:
                    prompt += f"{table_name}: "
                # 문서 길이 제한 (200자)
                prompt += f"{doc[:200]}\n"

        # 대화 히스토리 추가
        if chat_history:
            prompt += "\n## 이전 대화\n"
            for chat in chat_history[-3:]:  # 최근 3개만
                prompt += f"사용자: {chat.get('user', '')}\n"
                prompt += f"AI: {chat.get('ai', '')}\n"

        prompt += f"""
## 사용자 질문
{message}

**중요 규칙:**
1. 위에 제공된 "분석 인사이트"와 "질문과 관련된 상세 데이터"를 모두 활용하여 답변하세요
2. 구체적인 수치가 필요한 질문이라면 "질문과 관련된 상세 데이터"를 우선 참고하세요
3. 전반적인 추세나 요약이 필요한 질문이라면 "분석 인사이트"를 우선 참고하세요
4. 데이터에 없는 내용은 "제공된 데이터에는 해당 정보가 없습니다"라고 답변하세요
5. 추측하거나 외부 지식을 사용하지 마세요
6. 객관적이고 간결하게 답변하세요 (2-4문장)
7. 한국어로 답변하세요

답변:"""

        return prompt

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
