from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.job import JobResponse

class MatchBreakdownResponse(BaseModel):
    job_id: int
    job_title: str
    company_name: str
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

    model_config = ConfigDict(from_attributes=True)

class JobMatchRankingItem(BaseModel):
    job: JobResponse
    match_score: float
    matched_skills_count: int
    missing_critical_skills_count: int
    meets_experience: bool
    quick_summary: str

class JobMatchRankingsResponse(BaseModel):
    total_jobs_evaluated: int
    rankings: List[JobMatchRankingItem]
