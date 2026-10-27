from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.profile import CandidateProfile
from app.api.deps import get_current_user, get_current_user_optional
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobImportRequest,
    JobResponse,
    JobListResponse,
    JobSyncRequest,
    JobSyncResponse,
    JobSourcesStatusResponse
)
from app.schemas.matching import MatchBreakdownResponse, JobMatchRankingsResponse
from app.schemas.verification import JobVerificationResponse
from app.schemas.application import ApplicationResponse, TrackJobApplyRequest
from app.services import job_service, matching_service
from app.services.verification_service import VerificationService
from app.services.application_service import ApplicationService
from app.services.job_ingestion_service import JobIngestionService
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/jobs", tags=["Job Discovery & Records"])


@router.get("", response_model=JobListResponse)
def list_jobs(
    q: Optional[str] = Query(None, description="Search term for title, company, or description"),
    location: Optional[str] = Query(None, description="Filter by location"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode (Remote, Hybrid, On-site)"),
    skill: Optional[str] = Query(None, description="Filter by required technical skill"),
    source: Optional[str] = Query(None, description="Filter by source platform (e.g. RemoteOK, Jobicy, Manual)"),
    employment_type: Optional[str] = Query(None, description="Filter by employment type (e.g. Full-time, Contract, Internship)"),
    is_expired: Optional[bool] = Query(None, description="Filter by expired status (True/False)"),
    company_id: Optional[int] = Query(None, description="Filter by specific company ID"),
    sort_by: Optional[str] = Query("recent", description="Sort order: 'recent' (default) or 'match' (relevance)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Search and filter job postings with multi-parameter criteria, source filtering, and pagination.
    Supports sorting by 'recent' (default date order) or 'match' (relevance fit against authenticated profile).
    """
    jobs, total = job_service.list_jobs(
        db=db,
        q=q,
        location=location,
        work_mode=work_mode,
        skill=skill,
        source=source,
        employment_type=employment_type,
        is_expired=is_expired,
        company_id=company_id,
        sort_by=sort_by,
        user_id=current_user.id if current_user else None,
        skip=skip,
        limit=limit
    )
    return JobListResponse(
        total=total,
        skip=skip,
        limit=limit,
        jobs=jobs
    )


@router.post(
    "/sources/sync",
    response_model=JobSyncResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit("job-sources-sync", max_requests=10, window_seconds=60))]
)
def sync_job_sources(
    sync_in: Optional[JobSyncRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Triggers manual or background multi-source job ingestion across enabled source adapters
    (RemoteOK, Jobicy). Performs multi-tier deduplication, updates existing listings, and marks stale jobs.
    """
    sources_to_sync = sync_in.sources if sync_in else None
    limit_per_source = sync_in.limit_per_source if sync_in and sync_in.limit_per_source else 20
    return JobIngestionService.sync_sources(
        db=db,
        sources=sources_to_sync,
        limit_per_source=limit_per_source,
        user_id=current_user.id
    )


@router.get("/sources/status", response_model=JobSourcesStatusResponse)
def get_job_sources_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns real-time health, configuration, and sync telemetry for all supported external job sources.
    """
    return JobIngestionService.get_sources_status(db=db)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new job opportunity record manually.
    Associates or creates the corresponding Company and auto-extracts technical skills if needed.
    """
    return job_service.create_job(db=db, job_in=job_in, user_id=current_user.id)


@router.post(
    "/import-url",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("import-url", max_requests=15, window_seconds=60))]
)
def import_job_from_url(
    import_in: JobImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Imports job posting metadata (title, company, description, skills) directly from a user-provided job URL.
    """
    return job_service.import_job_from_url(db=db, url=import_in.url, user_id=current_user.id)


@router.get("/matches", response_model=JobMatchRankingsResponse)
def get_ranked_job_matches(
    q: Optional[str] = Query(None, description="Search term for title, company, or description"),
    location: Optional[str] = Query(None, description="Filter by location"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode (Remote, Hybrid, On-site)"),
    skill: Optional[str] = Query(None, description="Filter by technical skill"),
    source: Optional[str] = Query(None, description="Filter by source platform (e.g. RemoteOK, Jobicy, Manual)"),
    employment_type: Optional[str] = Query(None, description="Filter by employment type (e.g. Full-time, Contract, Internship)"),
    is_expired: Optional[bool] = Query(None, description="Filter by expired status (True/False)"),
    company_id: Optional[int] = Query(None, description="Filter by specific company ID"),
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ranks active jobs by explainable match score against the authenticated candidate profile,
    supporting multi-parameter search, source, and employment type filtering.
    """
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    return matching_service.rank_active_jobs_for_candidate(
        db=db,
        profile=profile,
        q=q,
        location=location,
        work_mode=work_mode,
        skill=skill,
        source=source,
        employment_type=employment_type,
        is_expired=is_expired,
        company_id=company_id,
        skip=skip,
        limit=limit
    )


@router.post("/{job_id}/match", response_model=MatchBreakdownResponse)
def match_job_with_candidate(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes and returns a transparent delta match breakdown between candidate profile and specified job.
    """
    job = job_service.get_job_by_id(db=db, job_id=job_id)
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    return matching_service.compute_job_match(profile=profile, job=job)


@router.post("/{job_id}/verify", response_model=JobVerificationResponse)
def verify_job_opportunity(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Triggers an evidence-based verification audit for a specific job posting
    and persists the audit findings to verification_logs.
    """
    job = job_service.get_job_by_id(db=db, job_id=job_id)
    return VerificationService.audit_job_legitimacy(db=db, job=job)


@router.get("/{job_id}/verification", response_model=JobVerificationResponse)
def get_job_verification(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the latest verification audit record, domain/DNS evidence,
    and scam heuristic signals for a specific job posting.
    """
    job = job_service.get_job_by_id(db=db, job_id=job_id)
    return VerificationService.get_latest_job_verification(db=db, job=job)


@router.post("/{job_id}/apply", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def apply_and_track_job(
    job_id: int,
    track_in: Optional[TrackJobApplyRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Instantly tracks a discovered job posting into the candidate's active Kanban pipeline.
    Auto-links Company, creates Application with status APPLIED (or custom status),
    and prevents duplicate applications.
    """
    return ApplicationService.track_from_job(
        db=db,
        user_id=current_user.id,
        job_id=job_id,
        track_in=track_in
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):

    """
    Retrieves full details for a specific job posting.
    """
    return job_service.get_job_by_id(db=db, job_id=job_id)


@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    job_in: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates details for a specific job posting.
    """
    return job_service.update_job(db=db, job_id=job_id, job_in=job_in, user_id=current_user.id)


@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deactivates a job posting record.
    """
    job_service.delete_job(db=db, job_id=job_id)
    return {"message": f"Job opportunity {job_id} deactivated successfully"}
