from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.job import JobResponse

class MatchBreakdownResponse(BaseModel):
    job_id: int
    job_title: Optional[str] = Field(default="Untitled Role", description="Job posting title")
    company_name: Optional[str] = Field(default="Unknown Company", description="Employer company name")
    match_score: float = Field(..., ge=0.0, le=100.0, description="Overall match score from 0 to 100%")
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both candidate profile and job")
    missing_critical_skills: List[str] = Field(default_factory=list, description="Missing skills from job required_skills")
    missing_secondary_skills: List[str] = Field(default_factory=list, description="Missing skills from job preferred_skills")
    meets_experience: bool
    candidate_experience_years: float
    required_experience_years: float
    experience_gap: float
    experience_warning: Optional[str] = None
    explanation: str
    resume_advice: List[str]
    positive_reasons: List[str] = Field(default_factory=list, description="Explicit compatibility factors")
    negative_reasons: List[str] = Field(default_factory=list, description="Key mismatches, gaps, or penalties")
    core_skills_score: Optional[float] = Field(default=0.0, description="Core skills score percentage")
    preferred_skills_score: Optional[float] = Field(default=0.0, description="Preferred skills score percentage")
    experience_score: Optional[float] = Field(default=0.0, description="Experience alignment score percentage")
    role_score: Optional[float] = Field(default=0.0, description="Role alignment score percentage")
    experience_status: Optional[str] = Field(default="ELIGIBLE", description="ELIGIBLE, GAP_WARNING, or NEUTRAL")
    experience_gap_years: Optional[float] = Field(default=0.0, description="Tenure gap in years")

    model_config = ConfigDict(from_attributes=True)

class JobMatchRankingItem(BaseModel):
    job: JobResponse
    match_score: float
    matched_skills_count: int
    missing_critical_skills_count: int
    meets_experience: bool
    quick_summary: str
    positive_reasons: List[str] = Field(default_factory=list, description="Positive match reasons")
    negative_reasons: List[str] = Field(default_factory=list, description="Negative mismatch reasons")

class JobMatchRankingsResponse(BaseModel):
    total_jobs_evaluated: int
    rankings: List[JobMatchRankingItem]
    has_profile_skills: bool = Field(default=True, description="Indicates if candidate has technical skills configured")
    profile_summary: Optional[str] = Field(default=None, description="Summary of evaluated profile skills and target roles")
