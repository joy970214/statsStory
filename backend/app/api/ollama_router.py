from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

from app.services.ollama_service import ollama_service


class SetModelRequest(BaseModel):
    model_name: str


@router.get("/ollama/models")
async def get_ollama_models():
    """vLLM 서버의 모델 목록 조회"""
    models = ollama_service.get_available_models()
    return {
        "models": models,
        "current_model": ollama_service.get_current_model()
    }


@router.post("/ollama/model")
async def set_ollama_model(request: SetModelRequest):
    """사용할 모델 변경 (vLLM 서버 내 모델)"""
    ollama_service.set_model(request.model_name)
    return {
        "success": True,
        "current_model": ollama_service.get_current_model()
    }


@router.get("/ollama/model")
async def get_current_model():
    """현재 사용 중인 모델 및 서버 상태 조회"""
    return {
        "current_model": ollama_service.get_current_model(),
        "ollama_available": ollama_service.is_available(),
        "server_url": ollama_service.base_url
    }
