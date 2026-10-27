import os
from typing import List, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Unified Job Search & Application Management System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Server & Reverse Proxy
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    TRUSTED_PROXIES: List[str] = [
        "127.0.0.1",
        "::1",
        "testclient",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16"
    ]
    
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

    # Email Webhook Integration Secret
    WEBHOOK_SECRET: Optional[str] = "ujs_dev_webhook_secret_key_change_in_prod"

    # Multi-Source Job Discovery
    REMOTEOK_ENABLED: bool = True
    REMOTEOK_API_URL: str = "https://remoteok.com/api"
    JOBICY_ENABLED: bool = True
    JOBICY_API_URL: str = "https://jobicy.com/api/v2/remote-jobs"
    JOB_INGESTION_RATE_LIMIT_SECONDS: float = 1.0
    JOB_INGESTION_MAX_JOBS_PER_SOURCE: int = 25

    @model_validator(mode="after")
    def validate_production_security(self):
        insecure_keys = {
            "temporary_secret_key_change_in_production_min_32_characters",
            "generate_a_cryptographically_secure_random_key_min_32_characters",
            "replace_with_a_secure_random_secret_key_at_least_32_chars",
            "ujs_dev_webhook_secret_key_change_in_prod",
            "replace_with_a_secure_webhook_secret_key_for_external_ingest",
            "secret",
            "changeme",
            "password",
            "your-secret-key-here",
            "admin",
            "default"
        }
        if self.ENVIRONMENT.lower() == "production":
            sec_lower = (self.SECRET_KEY or "").lower()
            if (
                not self.SECRET_KEY
                or self.SECRET_KEY in insecure_keys
                or len(self.SECRET_KEY) < 32
                or any(p in sec_lower for p in ["change_in_production", "replace_with", "random_key_min_32", "your-secret", "placeholder"])
            ):
                raise ValueError(
                    "CRITICAL SECURITY ERROR: In production mode, SECRET_KEY must be set to an explicitly configured, cryptographically secure string of at least 32 characters and cannot be a default or placeholder value."
                )
            if self.DEBUG:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: DEBUG must be set to False in production mode."
                )

            webhook_lower = (self.WEBHOOK_SECRET or "").lower()
            if (
                not self.WEBHOOK_SECRET
                or self.WEBHOOK_SECRET in insecure_keys
                or len(self.WEBHOOK_SECRET) < 32
                or any(p in webhook_lower for p in ["change_in_prod", "change_in_production", "replace_with", "placeholder", "dev_webhook"])
            ):
                raise ValueError(
                    "CRITICAL SECURITY ERROR: In production mode, WEBHOOK_SECRET must be set to an explicitly configured, cryptographically secure string of at least 32 characters and cannot be a default or placeholder value."
                )

            db_url_lower = (self.DATABASE_URL or "").lower()
            if any(default_cred in db_url_lower for default_cred in [":postgres@", ":password@", ":root@", ":123456@", "://postgres:postgres@"]):
                raise ValueError(
                    "CRITICAL SECURITY ERROR: In production mode, DATABASE_URL must not use default or placeholder database credentials ('postgres:postgres'). Please provide dedicated production database credentials."
                )
        return self
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
