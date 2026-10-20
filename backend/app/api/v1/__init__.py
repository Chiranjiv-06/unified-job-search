from fastapi import APIRouter
from app.api.v1.applications import router as applications_router
from app.api.v1.verify import router as verify_router
from app.api.v1.emails import router as emails_router
from app.api.v1.reminders import router as reminders_router

api_v1_router = APIRouter()

api_v1_router.include_router(applications_router)
api_v1_router.include_router(verify_router)
api_v1_router.include_router(emails_router)
api_v1_router.include_router(reminders_router)
