from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.core.enums import ApplicationStatus
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStageUpdate,
    ApplicationResponse,
    ApplicationListResponse
)
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    application_in: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new job application in the candidate pipeline.
    Resolves or registers the company and prevents accidental duplicate submissions.
    """
    return ApplicationService.create_application(
        db=db,
        user_id=current_user.id,
        application_in=application_in
    )

@router.get("", response_model=ApplicationListResponse)
def list_applications(
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status", description="Filter by pipeline stage"),
    platform_filter: Optional[str] = Query(None, alias="platform", description="Filter by source platform"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the candidate's active job pipeline with stage and platform filters.
    """
    items, total = ApplicationService.get_applications(
        db=db,
        user_id=current_user.id,
        status_filter=status_filter,
        platform_filter=platform_filter,
        skip=skip,
        limit=limit
    )
    return ApplicationListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves a single application by ID with company details.
    """
    return ApplicationService.get_application_by_id(
        db=db,
        user_id=current_user.id,
        application_id=application_id
    )

@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    update_in: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates application details such as job description, source URL, or response deadline.
    """
    return ApplicationService.update_application(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        update_in=update_in
    )

@router.patch("/{application_id}/stage", response_model=ApplicationResponse)
def update_application_stage(
    application_id: int,
    stage_in: ApplicationStageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Transitions the application to a new pipeline stage (e.g. APPLIED -> INTERVIEW).
    """
    return ApplicationService.update_stage(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        stage_in=stage_in
    )

@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Removes an application from the candidate's workspace.
    """
    ApplicationService.delete_application(
        db=db,
        user_id=current_user.id,
        application_id=application_id
    )
