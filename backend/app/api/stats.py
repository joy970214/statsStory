from fastapi import APIRouter

# 분리된 라우터 모듈들 import
from app.api.health_router import router as health_router
from app.api.stats_manager import router as stats_router
from app.api.analysis_router import router as analysis_router
from app.api.data_router import router as data_router

# 메인 라우터 생성
router = APIRouter()

# 각 하위 라우터들을 포함 (prefix 없이 기존 경로 유지)
router.include_router(health_router, tags=["health"])
router.include_router(stats_router, tags=["stats"])
router.include_router(analysis_router, tags=["analysis"])
router.include_router(data_router, tags=["data"])