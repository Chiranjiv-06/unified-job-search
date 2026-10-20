from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
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

class ApplicationCreate(ApplicationBase):
    company_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Company name to create or link")
    company_id: Optional[int] = Field(None, description="Existing Company ID if known")

class ApplicationUpdate(BaseModel):
    job_title: Optional[str] = Field(None, min_length=1, max_length=255)
    job_description: Optional[str] = None
    source_platform: Optional[str] = Field(None, max_length=100)
    source_url: Optional[str] = Field(None, max_length=1000)
    status: Optional[ApplicationStatus] = None
    applied_at: Optional[datetime] = None
    response_deadline: Optional[datetime] = None

class ApplicationStageUpdate(BaseModel):
    status: ApplicationStatus = Field(..., description="Target pipeline stage")
    notes: Optional[str] = Field(None, description="Optional transition note or rationale")

class ApplicationResponse(ApplicationBase):
    id: int
    user_id: int
    company_id: Optional[int] = None
    company: Optional[CompanyBriefResponse] = None
    last_activity_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ApplicationListResponse(BaseModel):
    items: List[ApplicationResponse]
    total: int
    skip: int
    limit: int
