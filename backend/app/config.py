"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Risk Control Platform"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/risk_control"
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Auth
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Lark (Feishu) OAuth
    LARK_APP_ID: str = ""
    LARK_APP_SECRET: str = ""
    LARK_REDIRECT_URI: str = "http://localhost:8000/api/auth/lark/callback"

    # AI Service
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.servetokens.com/v1"
    AI_MODEL: str = "gpt-4o"

    # ThinkingData (数数) API
    TA_API_URL: str = "https://your-ta-instance.thinkingdata.cn"
    TA_API_TOKEN: str = ""
    TA_APP_ID: str = ""

    # Risk Model Service
    RISK_MODEL_BASE_URL: str = "http://localhost:9000"
    RISK_MODEL_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"


settings = Settings()
