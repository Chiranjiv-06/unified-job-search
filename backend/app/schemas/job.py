from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

class JobBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, description="Job title, e.g. Full Stack Developer")
    company_name: str = Field(..., min_length=1, max_length=255, description="Company or employer name")
    description: Optional[str] = Field(None, description="Detailed job description or summary")
    required_skills: Optional[List[str]] = Field(default_factory=list, description="List of required technical skills")
    preferred_skills: Optional[List[str]] = Field(default_factory=list, description="List of preferred or bonus skills")
    experience_years_required: Optional[float] = Field(0.0, ge=0.0, description="Minimum years of experience")
    experience_level: Optional[str] = Field("Entry-Level", description="Entry-Level, Mid-Level, Senior, Intern")
    education_requirement: Optional[str] = Field(None, description="Degree or academic requirements")
    employment_type: Optional[str] = Field(None, max_length=50, description="Full-time, Part-time, Contract, Internship")
    location: Optional[str] = Field(None, description="Location, e.g. Bengaluru, Remote, Pune")
    work_mode: Optional[str] = Field("Any", description="Remote, Hybrid, On-site, Any")
    salary_min: Optional[float] = Field(None, ge=0.0)
    salary_max: Optional[float] = Field(None, ge=0.0)
    salary_currency: Optional[str] = Field("INR", max_length=10)
    salary_range: Optional[str] = Field(None, max_length=100)
    source_platform: Optional[str] = Field("Manual", max_length=100)
    source_url: Optional[str] = Field(None, max_length=1000)
    company_url: Optional[str] = Field(None, max_length=1000, description="Company careers page or website URL")
    external_id: Optional[str] = Field(None, max_length=255, description="External job ID from origin source")
    posting_date: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    is_expired: Optional[bool] = Field(False, description="Whether the job listing has expired or closed")
    import_status: Optional[str] = Field("active", max_length=50, description="active, updated, archived")
    raw_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw source metadata")

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_years_required: Optional[float] = Field(None, ge=0.0)
    experience_level: Optional[str] = None
    education_requirement: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_range: Optional[str] = None
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    company_url: Optional[str] = None
    external_id: Optional[str] = None
    posting_date: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_expired: Optional[bool] = None
    import_status: Optional[str] = None
    raw_metadata: Optional[Dict[str, Any]] = None

class JobImportRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=1000, description="Valid HTTP/HTTPS job posting URL")
    source_platform: Optional[str] = Field(None, description="Optional override for source platform (e.g. Careers, LinkedIn)")

class JobResponse(JobBase):
    id: int
    company_id: Optional[int] = None
    is_active: bool
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    match_score: Optional[float] = Field(None, description="Relevance match score if evaluated against candidate profile")
    match_summary: Optional[str] = Field(None, description="Concise match explanation if evaluated")

    model_config = ConfigDict(from_attributes=True)

class JobListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    jobs: List[JobResponse]

class JobSourceStatus(BaseModel):
    name: str
    enabled: bool
    status: str  # "ready", "syncing", "success", "error", "disabled", "partial_failure"
    last_sync_at: Optional[datetime] = None
    last_sync_fetched: Optional[int] = 0
    last_sync_imported: Optional[int] = 0
    last_sync_updated: Optional[int] = 0
    last_sync_skipped: Optional[int] = 0
    total_fetched: int = 0
    total_imported: int = 0
    total_updated: int = 0
    total_skipped: int = 0
    last_error: Optional[str] = None

class JobSourcesStatusResponse(BaseModel):
    sources: List[JobSourceStatus]
    total_jobs: int
    active_sources_count: int

class JobSyncRequest(BaseModel):
    sources: Optional[List[str]] = Field(None, description="List of source names to sync, e.g. ['remoteok', 'jobicy']")
    limit_per_source: Optional[int] = Field(20, ge=1, le=100)

class JobSyncResponse(BaseModel):
    status: str
    total_fetched: int
    total_imported: int
    total_updated: int
    total_skipped: int
    source_results: Dict[str, Any]
    message: str
