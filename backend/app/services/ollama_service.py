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

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.base_url = base_url
        self.model = model
        self.timeout = 180  # 3분 타임아웃 (10개 인사이트 생성)

    def is_available(self) -> bool:
        """Ollama 서버가 실행 중인지 확인"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

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
            # 프롬프트 구성
            prompt = self._build_descriptive_stats_prompt(
                metadata, data_summary, table_names, raw_data_sample
            )

            print(f"[Ollama] 기술통계 인사이트 생성 시작...")
            print(f"[Ollama] 모델: {self.model}")

            # Ollama API 호출
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # 낮은 temperature로 객관적 분석
                        "top_p": 0.9,
                        "num_predict": 2000  # 10개 인사이트를 위해 늘림
                    }
                },
                timeout=self.timeout
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API 오류: {response.status_code}")

            result = response.json()
            generated_text = result.get('response', '')

            print(f"[Ollama] 인사이트 생성 완료 (길이: {len(generated_text)}자)")

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
                        "top_p": 0.9
                    }
                },
                timeout=60
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

## 분석 요청사항
다음 **10개 카테고리**에 대해 **객관적 사실만** 기반으로 분석해주세요:

### 1. 기본 현황 (전체 규모/구성)
- 전체 데이터 규모, 총합, 평균 등 기본 현황
- 시각화 추천: 표 또는 텍스트

### 2. 분포 현황 (카테고리별 분포)
- 데이터가 어떻게 분포되어 있는지 (집중/분산)
- 시각화 추천: 막대그래프 또는 원그래프

### 3. 순위 현황 (상위/하위 순위)
- 최대값, 최소값 항목 및 상위/하위 순위
- 시각화 추천: 순위 막대그래프

### 4. 비교 현황 (그룹간 비교)
- 통계표 간, 카테고리 간 비교
- 시각화 추천: 비교 막대그래프

### 5. 지역 현황 (지역별 분포)
- 지역별 데이터 분포 (해당되는 경우)
- 시각화 추천: 지역별 막대그래프

### 6. 증감 현황 (전년 대비 변화)
- 시계열 변화, 증감률 (해당되는 경우)
- 시각화 추천: 추세선 그래프

### 7. 집중도 현황 (집중/분산 정도)
- 표준편차, 상위 몇 %가 전체의 몇 %를 차지하는지
- 시각화 추천: 파레토 차트

### 8. 특징 현황 (주요 특징)
- 이 데이터의 독특한 특징 (이상치, 패턴 등)
- 시각화 추천: 상황에 따라

### 9. 구성비 현황
- 전체 중 각 항목이 차지하는 비율
- 시각화 추천: 원그래프

### 10. 요약 및 시사점
- 전체 분석을 2-3문장으로 요약
- 시각화 추천: 종합 표

**중요 규칙:**
1. 제공된 데이터에 있는 **객관적 사실만** 작성
2. 추측, 예측, 인과관계 분석은 **절대 금지**
3. 복잡한 통계 검정이나 고급 기법은 사용하지 않음
4. 데이터에 해당 정보가 없으면 "데이터에 해당 정보 없음"으로 표시
5. 각 카테고리마다 **2-3문장**으로 간결하게 작성
6. 한국어로 명확하게 작성

답변 형식 (카테고리 번호와 제목을 명확히):
1. 기본 현황: ...
2. 분포 현황: ...
(이하 생략)
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

        # 10개 카테고리 인사이트 추가
        if insights:
            for i in range(1, 11):
                key = f'insight_{i}'
                if key in insights:
                    insight = insights[key]
                    prompt += f"\n{i}. {insight.get('category', '')}: {insight.get('content', '')}\n"

        # ChromaDB에서 검색된 관련 데이터 추가 (RAG)
        relevant_docs = relevant_data.get('documents', [])
        relevant_metas = relevant_data.get('metadatas', [])

        if relevant_docs:
            prompt += f"\n## 질문과 관련된 상세 데이터 ({len(relevant_docs)}개 발견)\n"
            for idx, (doc, meta) in enumerate(zip(relevant_docs[:10], relevant_metas[:10]), 1):
                # 메타데이터 정보
                year = meta.get('year', '')
                table_name = meta.get('table_name', '')

                # 문서 텍스트
                prompt += f"\n### 데이터 {idx}"
                if year:
                    prompt += f" ({year}년)"
                if table_name:
                    prompt += f" [{table_name}]"
                prompt += f"\n{doc}\n"

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
        """생성된 텍스트를 10개 카테고리 인사이트로 파싱"""

        insights = {
            'raw_text': generated_text,
            'insights_count': 0
        }

        # 카테고리 정의
        categories = [
            ('insight_1', '기본 현황', '표'),
            ('insight_2', '분포 현황', '막대그래프'),
            ('insight_3', '순위 현황', '순위 막대그래프'),
            ('insight_4', '비교 현황', '비교 막대그래프'),
            ('insight_5', '지역 현황', '지역별 막대그래프'),
            ('insight_6', '증감 현황', '추세선 그래프'),
            ('insight_7', '집중도 현황', '파레토 차트'),
            ('insight_8', '특징 현황', '상황별'),
            ('insight_9', '구성비 현황', '원그래프'),
            ('insight_10', '요약 및 시사점', '종합 표')
        ]

        try:
            lines = generated_text.split('\n')
            current_category = None
            current_content = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 카테고리 번호로 시작하는지 확인 (1., 2., ..., 10.)
                for i, (key, category_name, viz) in enumerate(categories, 1):
                    if line.startswith(f"{i}.") or f"{i}." in line[:5]:
                        # 이전 카테고리 저장
                        if current_category:
                            insights[current_category[0]] = {
                                'category': current_category[1],
                                'content': ' '.join(current_content).strip(),
                                'visualization': current_category[2]
                            }
                            insights['insights_count'] += 1

                        # 새 카테고리 시작
                        current_category = (key, category_name, viz)
                        current_content = [line.split('.', 1)[1].strip() if '.' in line else line]
                        break
                else:
                    # 카테고리 내용 추가
                    if current_category:
                        current_content.append(line)

            # 마지막 카테고리 저장
            if current_category:
                insights[current_category[0]] = {
                    'category': current_category[1],
                    'content': ' '.join(current_content).strip(),
                    'visualization': current_category[2]
                }
                insights['insights_count'] += 1

        except Exception as e:
            print(f"[Ollama] 인사이트 파싱 오류: {e}")

        return insights

    def _create_fallback_insights(
        self,
        metadata: Dict[str, Any],
        data_summary: Dict[str, Any],
        table_names: List[str]
    ) -> Dict[str, Any]:
        """Ollama 실패 시 기본 인사이트 생성"""

        stat_name = metadata.get('title', '통계')
        count = data_summary.get('count', 0)
        mean = data_summary.get('mean', 0)
        total = data_summary.get('total', 0)
        max_val = data_summary.get('max', 0)
        min_val = data_summary.get('min', 0)

        return {
            'stat_name': stat_name,
            'insights_count': 10,
            'insight_1': {
                'category': '기본 현황',
                'content': f'총 {count:,}개의 데이터가 수집되었으며, 전체 합계는 {total:,.2f}입니다. 평균값은 {mean:,.2f}입니다.',
                'visualization': '표'
            },
            'insight_2': {
                'category': '분포 현황',
                'content': f'데이터는 최솟값 {min_val:,.2f}에서 최댓값 {max_val:,.2f} 사이에 분포되어 있습니다.',
                'visualization': '막대그래프'
            },
            'insight_3': {
                'category': '순위 현황',
                'content': f'최댓값은 {max_val:,.2f}이고, 최솟값은 {min_val:,.2f}입니다.',
                'visualization': '순위 막대그래프'
            },
            'insight_4': {
                'category': '비교 현황',
                'content': f'{len(table_names)}개의 통계표가 수집되었습니다: {", ".join(table_names[:3])}',
                'visualization': '비교 막대그래프'
            },
            'insight_5': {
                'category': '지역 현황',
                'content': '지역별 데이터 분석을 위해서는 AI 분석이 필요합니다.',
                'visualization': '지역별 막대그래프'
            },
            'insight_6': {
                'category': '증감 현황',
                'content': '시계열 변화 분석을 위해서는 AI 분석이 필요합니다.',
                'visualization': '추세선 그래프'
            },
            'insight_7': {
                'category': '집중도 현황',
                'content': '데이터 집중도 분석을 위해서는 AI 분석이 필요합니다.',
                'visualization': '파레토 차트'
            },
            'insight_8': {
                'category': '특징 현황',
                'content': f'이 통계는 {stat_name}에 대한 기본 통계 분석입니다.',
                'visualization': '상황별'
            },
            'insight_9': {
                'category': '구성비 현황',
                'content': '구성비 분석을 위해서는 AI 분석이 필요합니다.',
                'visualization': '원그래프'
            },
            'insight_10': {
                'category': '요약 및 시사점',
                'content': f'{stat_name}에 대한 기본 통계 분석이 완료되었습니다. 상세 분석을 위해서는 AI 서비스가 필요합니다.',
                'visualization': '종합 표'
            },
            'generated_at': datetime.now().isoformat(),
            'model': 'fallback',
            'note': 'Ollama 서비스를 사용할 수 없어 기본 인사이트를 제공합니다.',
            'raw_text': ''
        }


# 싱글톤 인스턴스
ollama_service = OllamaService()
