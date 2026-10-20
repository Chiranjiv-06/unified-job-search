import os
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Unified Job Search & Application Management System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost"
    ]
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:6314/unified_job_search"
    
    # Security / JWT
    SECRET_KEY: str = "temporary_secret_key_change_in_production_min_32_characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # File Uploads
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    MAX_FILE_SIZE_MB: int = 5

    @model_validator(mode="after")
    def validate_production_security(self):
        insecure_keys = {
            "temporary_secret_key_change_in_production_min_32_characters",
            "secret",
            "changeme",
            "password",
            "your-secret-key-here"
        }
        if self.ENVIRONMENT.lower() == "production":
            if not self.SECRET_KEY or self.SECRET_KEY in insecure_keys or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: In production mode, SECRET_KEY must be set to a cryptographically secure string of at least 32 characters and cannot be a default placeholder."
                )
            if self.DEBUG:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: DEBUG must be set to False in production mode."
                )
        return self
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
