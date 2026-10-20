from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.application import Application
from app.models.company import Company
from app.models.job import Job
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStageUpdate,
    PipelineMetricsResponse,
    TrackJobApplyRequest
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

        now = datetime.now(timezone.utc)
        applied_time = application_in.applied_at or (now if application_in.status != ApplicationStatus.DRAFT else None)
        initial_events = [
            {
                "stage": application_in.status.value,
                "timestamp": now.isoformat(),
                "notes": application_in.notes or "Application tracked in pipeline"
            }
        ]

        application = Application(
            user_id=user_id,
            company_id=company_id,
            job_id=application_in.job_id,
            job_title=application_in.job_title.strip(),
            job_description=application_in.job_description,
            source_platform=application_in.source_platform,
            source_url=application_in.source_url,
            status=application_in.status,
            applied_at=applied_time,
            last_activity_at=now,
            response_deadline=application_in.response_deadline,
            notes=application_in.notes,
            recruiter_contact=application_in.recruiter_contact,
            interview_details=application_in.interview_details,
            resume_version=application_in.resume_version,
            timeline_events=initial_events
        )
        db.add(application)
        db.commit()
        db.refresh(application)
        return application

    @classmethod
    def track_from_job(
        cls,
        db: Session,
        user_id: int,
        job_id: int,
        track_in: Optional[TrackJobApplyRequest] = None
    ) -> Application:
        """
        Instantly tracks a discovered job posting into the candidate's active pipeline.
        Resolves/creates Company, detects duplicates, logs initial timeline event, and sets applied_at.
        """
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job opportunity with ID {job_id} not found."
            )

        company = cls.resolve_or_create_company(
            db,
            company_id=job.company_id,
            company_name=job.company_name
        )
        company_id = company.id if company else None

        # Duplicate check: check if candidate already applied to this specific job or same role at company
        existing_app_stmt = select(Application).where(
            Application.user_id == user_id,
            (Application.job_id == job.id) |
            (
                (Application.company_id == company_id) &
                (func.lower(Application.job_title) == job.title.strip().lower())
            )
        )
        existing_app = db.execute(existing_app_stmt).scalar_one_or_none()
        if existing_app:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have an active application for '{job.title}' at '{job.company_name}' in your pipeline (Application ID: {existing_app.id}, Status: {existing_app.status.value})."
            )

        target_status = track_in.status if track_in and track_in.status else ApplicationStatus.APPLIED
        now = datetime.now(timezone.utc)
        note_text = track_in.notes if track_in and track_in.notes else "Tracked directly from Job Discovery"

        application = Application(
            user_id=user_id,
            company_id=company_id,
            job_id=job.id,
            job_title=job.title.strip(),
            job_description=job.description,
            source_platform=job.source_platform or "Job Discovery",
            source_url=job.source_url,
            status=target_status,
            applied_at=now,
            last_activity_at=now,
            notes=note_text,
            recruiter_contact=track_in.recruiter_contact if track_in else None,
            interview_details=track_in.interview_details if track_in else None,
            resume_version=track_in.resume_version if track_in else None,
            timeline_events=[
                {
                    "stage": target_status.value,
                    "timestamp": now.isoformat(),
                    "notes": note_text
                }
            ]
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
        now = datetime.now(timezone.utc)

        if update_in.job_title is not None:
            application.job_title = update_in.job_title.strip()
        if update_in.job_description is not None:
            application.job_description = update_in.job_description
        if update_in.source_platform is not None:
            application.source_platform = update_in.source_platform
        if update_in.source_url is not None:
            application.source_url = update_in.source_url
        if update_in.applied_at is not None:
            application.applied_at = update_in.applied_at
        if update_in.response_deadline is not None:
            application.response_deadline = update_in.response_deadline
        if update_in.notes is not None:
            application.notes = update_in.notes
        if update_in.recruiter_contact is not None:
            application.recruiter_contact = update_in.recruiter_contact
        if update_in.interview_details is not None:
            application.interview_details = update_in.interview_details
        if update_in.resume_version is not None:
            application.resume_version = update_in.resume_version

        # If stage/status updated, log timeline event
        if update_in.status is not None and update_in.status != application.status:
            old_status = application.status.value
            application.status = update_in.status
            timeline = list(application.timeline_events or [])
            timeline.append({
                "stage": update_in.status.value,
                "timestamp": now.isoformat(),
                "notes": f"Status updated from {old_status} to {update_in.status.value}"
            })
            application.timeline_events = timeline

        application.last_activity_at = now
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
        now = datetime.now(timezone.utc)
        old_status = application.status.value
        application.status = stage_in.status

        # Timeline event logging
        timeline = list(application.timeline_events or [])
        event_note = stage_in.notes or f"Stage transitioned from {old_status} to {stage_in.status.value}"
        timeline.append({
            "stage": stage_in.status.value,
            "timestamp": now.isoformat(),
            "notes": event_note
        })
        application.timeline_events = timeline

        if stage_in.notes:
            note_entry = f"[{stage_in.status.value} - {now.strftime('%b %d, %Y')}]: {stage_in.notes}"
            application.notes = f"{application.notes}\n{note_entry}" if application.notes else note_entry

        application.last_activity_at = now
        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def get_pipeline_metrics(db: Session, user_id: int) -> PipelineMetricsResponse:
        """
        Aggregates application counts per stage for the authenticated candidate.
        """
        stmt = (
            select(Application.status, func.count(Application.id))
            .where(Application.user_id == user_id)
            .group_by(Application.status)
        )
        rows = db.execute(stmt).all()
        stage_counts = {row[0]: row[1] for row in rows}

        applied = stage_counts.get(ApplicationStatus.APPLIED, 0)
        assessment = stage_counts.get(ApplicationStatus.ASSESSMENT, 0)
        interview = stage_counts.get(ApplicationStatus.INTERVIEW, 0)
        offer = stage_counts.get(ApplicationStatus.OFFER, 0)
        rejected = stage_counts.get(ApplicationStatus.REJECTED, 0)
        stale = stage_counts.get(ApplicationStatus.STALE, 0)
        draft = stage_counts.get(ApplicationStatus.DRAFT, 0)
        total = sum(stage_counts.values())

        return PipelineMetricsResponse(
            total_applications=total,
            applied_count=applied,
            assessment_count=assessment,
            interview_count=interview,
            offer_count=offer,
            rejected_count=rejected,
            stale_count=stale,
            draft_count=draft,
            active_interviews=interview,
            tests_due=assessment
        )

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
