import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Unified Job Search & Application Management System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Configuration
origins = list(set([settings.FRONTEND_URL] + settings.ALLOWED_ORIGINS))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "docs": "/api/docs"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }

@app.get("/api/health/db")
def health_check_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as exc:
        logger.error("Database health check error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )

# Include API Routers
from app.api.routes.auth import router as auth_router
from app.api.routes.profile import router as profile_router
from app.api.v1 import api_v1_router

app.include_router(auth_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(api_v1_router, prefix=settings.API_V1_STR)



