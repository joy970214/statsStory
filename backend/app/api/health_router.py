from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }

@router.post("/test-simple")
async def test_simple():
    """가장 간단한 테스트 엔드포인트"""
    return {"message": "success"}