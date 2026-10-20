from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.application import Application
from app.models.company import Company
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStageUpdate
)
from app.core.enums import ApplicationStatus

class ApplicationService:
    @staticmethod
    def resolve_or_create_company(
        db: Session,
        company_id: Optional[int] = None,
        company_name: Optional[str] = None
    ) -> Optional[Company]:
        if company_id:
            company = db.get(Company, company_id)
            if company:
                return company

        if company_name and company_name.strip():
            normalized_name = company_name.strip()
            # Lookup case-insensitive
            existing = db.execute(
                select(Company).where(func.lower(Company.name) == normalized_name.lower())
            ).scalar_one_or_none()

            if existing:
                return existing

            new_company = Company(
                name=normalized_name,
                is_verified=False,
                fraud_score=0.0
            )
            db.add(new_company)
            db.flush()
            return new_company

        return None

    @classmethod
    def create_application(
        cls,
        db: Session,
        user_id: int,
        application_in: ApplicationCreate
    ) -> Application:
        company = cls.resolve_or_create_company(
            db,
            company_id=application_in.company_id,
            company_name=application_in.company_name
        )

        company_id = company.id if company else None

        # Duplicate check: prevent duplicate application for same user, company, and job title
        if company_id:
            duplicate = db.execute(
                select(Application).where(
                    Application.user_id == user_id,
                    Application.company_id == company_id,
                    func.lower(Application.job_title) == application_in.job_title.strip().lower()
                )
            ).scalar_one_or_none()
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"An application for '{application_in.job_title}' at this company already exists in your pipeline."
                )

        application = Application(
            user_id=user_id,
            company_id=company_id,
            job_title=application_in.job_title.strip(),
            job_description=application_in.job_description,
            source_platform=application_in.source_platform,
            source_url=application_in.source_url,
            status=application_in.status,
            applied_at=application_in.applied_at or (datetime.now(timezone.utc) if application_in.status != ApplicationStatus.DRAFT else None),
            response_deadline=application_in.response_deadline
        )
        db.add(application)
        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def get_applications(
        db: Session,
        user_id: int,
        status_filter: Optional[ApplicationStatus] = None,
        platform_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Application], int]:
        query = select(Application).where(Application.user_id == user_id)

        if status_filter:
            query = query.where(Application.status == status_filter)
        if platform_filter:
            query = query.where(func.lower(Application.source_platform) == platform_filter.strip().lower())

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total = db.execute(count_query).scalar_one()

        # Order by last_activity_at descending with pagination
        stmt = (
            query.options(selectinload(Application.company))
            .order_by(Application.last_activity_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).scalars().all())
        return items, total

    @staticmethod
    def get_application_by_id(
        db: Session,
        user_id: int,
        application_id: int
    ) -> Application:
        stmt = (
            select(Application)
            .where(Application.id == application_id, Application.user_id == user_id)
            .options(selectinload(Application.company))
        )
        application = db.execute(stmt).scalar_one_or_none()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or unauthorized access."
            )
        return application

    @classmethod
    def update_application(
        cls,
        db: Session,
        user_id: int,
        application_id: int,
        update_in: ApplicationUpdate
    ) -> Application:
        application = cls.get_application_by_id(db, user_id, application_id)

        if update_in.job_title is not None:
            application.job_title = update_in.job_title.strip()
        if update_in.job_description is not None:
            application.job_description = update_in.job_description
        if update_in.source_platform is not None:
            application.source_platform = update_in.source_platform
        if update_in.source_url is not None:
            application.source_url = update_in.source_url
        if update_in.status is not None:
            application.status = update_in.status
        if update_in.applied_at is not None:
            application.applied_at = update_in.applied_at
        if update_in.response_deadline is not None:
            application.response_deadline = update_in.response_deadline

        application.last_activity_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(application)
        return application

    @classmethod
    def update_stage(
        cls,
        db: Session,
        user_id: int,
        application_id: int,
        stage_in: ApplicationStageUpdate
    ) -> Application:
        application = cls.get_application_by_id(db, user_id, application_id)
        application.status = stage_in.status
        application.last_activity_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(application)
        return application

    @classmethod
    def delete_application(
        cls,
        db: Session,
        user_id: int,
        application_id: int
    ) -> None:
        application = cls.get_application_by_id(db, user_id, application_id)
        db.delete(application)
        db.commit()
