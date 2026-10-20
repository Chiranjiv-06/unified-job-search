from datetime import datetime
from typing import Optional, List, Any
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
    location: Optional[str] = Field(None, description="Location, e.g. Bengaluru, Remote, Pune")
    work_mode: Optional[str] = Field("Any", description="Remote, Hybrid, On-site, Any")
    salary_min: Optional[float] = Field(None, ge=0.0)
    salary_max: Optional[float] = Field(None, ge=0.0)
    salary_currency: Optional[str] = Field("INR", max_length=10)
    salary_range: Optional[str] = Field(None, max_length=100)
    source_platform: Optional[str] = Field("Manual", max_length=100)
    source_url: Optional[str] = Field(None, max_length=1000)
    posting_date: Optional[datetime] = None

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
    location: Optional[str] = None
    work_mode: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_range: Optional[str] = None
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    posting_date: Optional[datetime] = None
    is_active: Optional[bool] = None

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

    model_config = ConfigDict(from_attributes=True)

class JobListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    jobs: List[JobResponse]
