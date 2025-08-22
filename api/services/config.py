import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://credtech:credtech_pass@postgres:5432/credtech"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # MLflow
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    
    # Security
    SECRET_KEY: str = "blackswan-credit-intelligence-secret-key-2024"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # External APIs (placeholders)
    YAHOO_FINANCE_API_KEY: Optional[str] = None
    SEC_EDGAR_API_KEY: Optional[str] = None
    FRED_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"


settings = Settings()
