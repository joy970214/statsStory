from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.data_storage import DataStorageService
from app.services.ollama_service import ollama_service
from app.services.vector_db_service import vector_db_service

router = APIRouter()
storage_service = DataStorageService()

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    stat_name: str
    message: str
    chat_history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    response: str
    stat_name: str
    context_used: bool
    insights_available: bool
    relevant_data_count: int = 0

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    통계 데이터 기반 AI 채팅 (RAG 방식)
    - AI 인사이트 + ChromaDB 벡터 검색 활용
    - 사용자 질문과 관련된 데이터만 Ollama에게 전달
    """
    try:
        # 1. 통계 데이터 찾기
        metadata, stat_data, stat_url = storage_service.find_data_by_name(request.stat_name)

        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"'{request.stat_name}' 통계 데이터를 찾을 수 없습니다. 먼저 분석을 실행해주세요."
            )

        # 2. Ollama 서버 확인
        if not ollama_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="AI 서비스를 사용할 수 없습니다. Ollama 서버가 실행 중인지 확인해주세요."
            )

        # 3. AI 인사이트 확인
        ai_insights = getattr(metadata, 'ai_insights', None)
        insights_available = ai_insights is not None and ai_insights.get('insights_count', 0) > 0

        # 4. ChromaDB에서 관련 데이터 검색 (RAG)
        cache_key = getattr(metadata, 'cache_key', None)
        if not cache_key:
            raise HTTPException(
                status_code=500,
                detail="통계 데이터에 cache_key가 없습니다."
            )

        relevant_data = vector_db_service.search_relevant_data(
            cache_key=cache_key,
            query=request.message,
            n_results=8  # 상위 8개 관련 데이터 (타임아웃 방지)
        )

        relevant_docs = relevant_data.get('documents', [])
        relevant_metadatas = relevant_data.get('metadatas', [])

        print(f"[CHAT] ChromaDB 검색: '{request.message[:50]}...' → {len(relevant_docs)}개 데이터 발견")

        # 5. 컨텍스트 준비
        context = {
            "stat_name": request.stat_name,
            "metadata": {
                "title": metadata.title,
                "department": getattr(metadata, 'department', ''),
                "purpose": getattr(metadata, 'purpose', ''),
                "frequency": getattr(metadata, 'frequency', ''),
                "statistical_info": getattr(metadata, 'statistical_info', {}),
                "terminology": getattr(metadata, 'terminology', {})
            },
            "ai_insights": ai_insights if insights_available else None,
            "relevant_data": {
                "count": len(relevant_docs),
                "documents": relevant_docs,
                "metadatas": relevant_metadatas
            }
        }

        # 6. 채팅 히스토리 변환
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.chat_history
        ]

        # 7. Ollama로 응답 생성
        try:
            ai_response = ollama_service.chat(
                message=request.message,
                context=context,
                chat_history=chat_history
            )

            return ChatResponse(
                response=ai_response,
                stat_name=request.stat_name,
                context_used=True,
                insights_available=insights_available,
                relevant_data_count=len(relevant_docs)
            )

        except Exception as ollama_error:
            print(f"[CHAT] Ollama 응답 생성 오류: {ollama_error}")

            # 폴백 응답
            if not insights_available:
                fallback_response = (
                    f"'{request.stat_name}'에 대한 AI 인사이트가 아직 생성되지 않았습니다. "
                    "먼저 '분석하기'를 실행하여 AI 인사이트를 생성해주세요.\n\n"
                    "현재 사용 가능한 정보:\n"
                    f"- 통계명: {metadata.title}\n"
                    f"- 담당부서: {getattr(metadata, 'department', '정보 없음')}\n"
                    f"- 작성목적: {getattr(metadata, 'purpose', '정보 없음')}\n"
                    f"- 검색된 관련 데이터: {len(relevant_docs)}개"
                )
            else:
                fallback_response = (
                    "죄송합니다. 일시적인 오류로 응답을 생성할 수 없습니다. "
                    f"잠시 후 다시 시도해주세요.\n\n"
                    f"검색된 관련 데이터: {len(relevant_docs)}개"
                )

            return ChatResponse(
                response=fallback_response,
                stat_name=request.stat_name,
                context_used=False,
                insights_available=insights_available,
                relevant_data_count=len(relevant_docs)
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[CHAT] 채팅 처리 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/chat/check/{stat_name}")
async def check_chat_availability(stat_name: str):
    """
    채팅 가능 여부 확인
    - AI 인사이트 생성 여부
    - ChromaDB 데이터 저장 여부
    - Ollama 서버 상태
    """
    try:
        # 통계 데이터 찾기
        metadata, stat_data, stat_url = storage_service.find_data_by_name(stat_name)

        if not metadata:
            return {
                "available": False,
                "reason": "통계 데이터를 찾을 수 없습니다",
                "ollama_available": ollama_service.is_available(),
                "insights_available": False,
                "vector_db_available": False
            }

        # AI 인사이트 확인
        ai_insights = getattr(metadata, 'ai_insights', None)
        insights_available = ai_insights is not None and ai_insights.get('insights_count', 0) > 0

        # ChromaDB 데이터 확인
        cache_key = getattr(metadata, 'cache_key', None)
        vector_db_available = False
        vector_db_count = 0

        if cache_key:
            vector_stats = vector_db_service.get_collection_stats(cache_key)
            vector_db_available = vector_stats['exists'] and vector_stats['document_count'] > 0
            vector_db_count = vector_stats.get('document_count', 0)

        # Ollama 서버 확인
        ollama_available = ollama_service.is_available()

        # 모든 조건 확인
        all_available = ollama_available and insights_available and vector_db_available

        # 상태별 메시지
        if all_available:
            reason = "사용 가능"
        elif not ollama_available:
            reason = "Ollama 서버를 사용할 수 없습니다"
        elif not insights_available:
            reason = "AI 인사이트가 없습니다. 먼저 분석을 실행해주세요."
        elif not vector_db_available:
            reason = "벡터 DB 데이터가 없습니다. 먼저 분석을 실행해주세요."
        else:
            reason = "알 수 없는 오류"

        return {
            "available": all_available,
            "reason": reason,
            "ollama_available": ollama_available,
            "insights_available": insights_available,
            "insights_count": ai_insights.get('insights_count', 0) if ai_insights else 0,
            "vector_db_available": vector_db_available,
            "vector_db_count": vector_db_count,
            "stat_title": metadata.title
        }

    except Exception as e:
        print(f"[CHAT] 가용성 확인 오류: {e}")
        return {
            "available": False,
            "reason": f"오류 발생: {str(e)}",
            "ollama_available": False,
            "insights_available": False,
            "vector_db_available": False
        }
