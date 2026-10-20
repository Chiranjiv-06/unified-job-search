from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.profile import CandidateProfile
from app.api.deps import get_current_user
from app.schemas.job import JobCreate, JobUpdate, JobImportRequest, JobResponse, JobListResponse
from app.schemas.matching import MatchBreakdownResponse, JobMatchRankingsResponse
from app.schemas.verification import JobVerificationResponse
from app.schemas.application import ApplicationResponse, TrackJobApplyRequest
from app.services import job_service, matching_service
from app.services.verification_service import VerificationService
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/jobs", tags=["Job Discovery & Records"])




@router.get("", response_model=JobListResponse)
def list_jobs(
    q: Optional[str] = Query(None, description="Search term for title, company, or description"),
    location: Optional[str] = Query(None, description="Filter by location"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode (Remote, Hybrid, On-site)"),
    skill: Optional[str] = Query(None, description="Filter by required technical skill"),
    company_id: Optional[int] = Query(None, description="Filter by specific company ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Search and filter job postings with multi-parameter criteria and pagination.
    """
    jobs, total = job_service.list_jobs(
        db=db,
        q=q,
        location=location,
        work_mode=work_mode,
        skill=skill,
        company_id=company_id,
        skip=skip,
        limit=limit
    )
    return JobListResponse(
        total=total,
        skip=skip,
        limit=limit,
        jobs=jobs
    )


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


@router.post("/import-url", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ranks all active jobs by match score against the authenticated candidate profile.
    """
    profile = db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    return matching_service.rank_active_jobs_for_candidate(db=db, profile=profile)


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
