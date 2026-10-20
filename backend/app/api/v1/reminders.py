import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.reminder import (
    AlertsListResponse,
    DraftFollowUpRequest,
    FollowUpDraftResponse,
    LogFollowUpRequest
)
from app.schemas.application import ApplicationResponse
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reminders", tags=["Reminders & Follow-Ups"])

@router.get("/alerts", response_model=AlertsListResponse)
def get_action_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves prioritized action items for candidate:
    - Urgent test deadlines
    - Upcoming interview rounds
    - Stalled applications where follow-up is recommended
    """
    return ReminderService.get_alerts_for_user(
        db=db,
        user_id=current_user.id
    )

@router.post("/draft-followup/{application_id}", response_model=FollowUpDraftResponse)
def draft_followup_email(
    application_id: int,
    request: DraftFollowUpRequest = DraftFollowUpRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a personalized, stage-aware follow-up email draft.
    Safety Rule: STRICT NO AUTO-SEND. Draft is returned solely for candidate review and manual copying.
    """
    try:
        draft = ReminderService.generate_followup_draft(
            db=db,
            user_id=current_user.id,
            application_id=application_id,
            tone=request.tone or "professional",
            custom_notes=request.custom_notes
        )
        return draft
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )

@router.post("/log-followup/{application_id}", response_model=ApplicationResponse)
def log_followup_action(
    application_id: int,
    request: LogFollowUpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records a follow-up action in the application's timeline events
    and updates the last_activity_at timestamp.
    """
    try:
        app = ReminderService.log_followup_activity(
            db=db,
            user_id=current_user.id,
            application_id=application_id,
            notes=request.notes or "Follow-up email sent to recruiter"
        )
        return app
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
