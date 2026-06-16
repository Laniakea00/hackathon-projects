from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smartbot_db"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/smartbot_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # App
    DEBUG: bool = True
    # Strict production frontend origin (Vercel)
    ALLOWED_ORIGINS: str = "https://mylink-rouge.vercel.app"
    # No regex wildcard; only exact origin above is allowed
    ALLOWED_ORIGIN_REGEX: str | None = None

    # AI / OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4.1"

    # AI policy
    AI_APPROVAL_THRESHOLD: int = 70
    AI_MAX_QUESTIONS: int = 3
    AI_TONE: str = "neutral"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

