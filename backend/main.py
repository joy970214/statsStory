import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import stats

app = FastAPI(
    title="통계이야기 API",
    description="국토교통부 통계 카드뉴스 생성 서비스",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3005", "http://localhost:3006", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stats.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "통계이야기 API 서버"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)