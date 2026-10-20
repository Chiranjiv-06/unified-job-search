from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class SkillBase(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100)
    proficiency_level: Optional[str] = Field("Intermediate", max_length=50)

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class CandidateProfileBase(BaseModel):
    education: Optional[str] = None
    experience_level: Optional[str] = "Entry-Level"
    experience_years: Optional[float] = 0.0
    raw_resume_text: Optional[str] = None
    parsed_skills: Optional[Union[List[Any], Dict[str, Any], Any]] = None
    preferred_roles: Optional[Union[str, List[Any], Any]] = None
    preferred_locations: Optional[str] = None
    preferred_work_mode: Optional[str] = "Any"
    salary_expectation: Optional[str] = None

class CandidateProfileUpdate(CandidateProfileBase):
    skills: Optional[List[SkillCreate]] = None

class CandidateProfileResponse(CandidateProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    skills: List[SkillResponse] = []

    model_config = ConfigDict(from_attributes=True)
