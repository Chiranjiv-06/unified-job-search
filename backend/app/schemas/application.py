from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.core.enums import ApplicationStatus

class CompanyBriefResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    careers_url: Optional[str] = None
    is_verified: bool = False
    fraud_score: float = 0.0

    model_config = ConfigDict(from_attributes=True)

class ApplicationBase(BaseModel):
    job_title: str = Field(..., min_length=1, max_length=255, description="Position or job title")
    job_description: Optional[str] = None
    source_platform: Optional[str] = Field(None, max_length=100, description="Platform source (e.g. LinkedIn, Indeed)")
    source_url: Optional[str] = Field(None, max_length=1000, description="Link to the original job posting")
    status: ApplicationStatus = Field(default=ApplicationStatus.DRAFT, description="Current pipeline stage")
    applied_at: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    notes: Optional[str] = None
    recruiter_contact: Optional[str] = None
    interview_details: Optional[str] = None
    resume_version: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    company_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Company name to create or link")
    company_id: Optional[int] = Field(None, description="Existing Company ID if known")
    job_id: Optional[int] = Field(None, description="Linked Job ID if tracked from discovery")

class ApplicationUpdate(BaseModel):
    job_title: Optional[str] = Field(None, min_length=1, max_length=255)
    job_description: Optional[str] = None
    source_platform: Optional[str] = Field(None, max_length=100)
    source_url: Optional[str] = Field(None, max_length=1000)
    status: Optional[ApplicationStatus] = None
    applied_at: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    notes: Optional[str] = None
    recruiter_contact: Optional[str] = None
    interview_details: Optional[str] = None
    resume_version: Optional[str] = None

class ApplicationStageUpdate(BaseModel):
    status: ApplicationStatus = Field(..., description="Target pipeline stage")
    notes: Optional[str] = Field(None, description="Optional transition note or rationale")

class ApplicationResponse(ApplicationBase):
    id: int
    user_id: int
    company_id: Optional[int] = None
    job_id: Optional[int] = None
    company: Optional[CompanyBriefResponse] = None
    timeline_events: Optional[List[Dict[str, Any]]] = []
    days_since_activity: int = 0
    last_activity_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def compute_days_since_activity(self) -> "ApplicationResponse":
        if self.last_activity_at:
            last = self.last_activity_at
            now = datetime.now(timezone.utc)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            delta = now - last
            self.days_since_activity = max(0, delta.days)
        return self

class ApplicationListResponse(BaseModel):
    items: List[ApplicationResponse]
    total: int
    skip: int
    limit: int

class PipelineMetricsResponse(BaseModel):
    total_applications: int = 0
    applied_count: int = 0
    assessment_count: int = 0
    interview_count: int = 0
    offer_count: int = 0
    rejected_count: int = 0
    stale_count: int = 0
    draft_count: int = 0
    active_interviews: int = 0
    tests_due: int = 0

class TrackJobApplyRequest(BaseModel):
    notes: Optional[str] = None
    status: Optional[ApplicationStatus] = ApplicationStatus.APPLIED
    recruiter_contact: Optional[str] = None
    interview_details: Optional[str] = None
    resume_version: Optional[str] = None
