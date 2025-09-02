import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    MOLIT_BASE_URL: str = "https://stat.molit.go.kr"
    RECENT_STATS_URL: str = f"{MOLIT_BASE_URL}/portal/cate/recentStatView.do"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3005"]
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = 30

settings = Settings()