import json
from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

class SkillBase(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100)
    proficiency_level: Optional[str] = Field("Intermediate", max_length=50)

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class TargetRolesResponse(BaseModel):
    roles: List[str] = Field(default_factory=list, description="Standard available target roles")
    categories: Dict[str, List[str]] = Field(default_factory=dict, description="Target roles grouped by category")

class CandidateProfileBase(BaseModel):
    education: Optional[str] = None
    experience_level: Optional[str] = "Entry-Level"
    experience_years: Optional[float] = 0.0
    raw_resume_text: Optional[str] = None
    parsed_skills: Optional[Union[List[Any], Dict[str, Any], Any]] = None
    preferred_roles: List[str] = Field(
        default_factory=list,
        description="Target job roles candidate wants to pursue"
    )
    preferred_locations: Optional[str] = None
    preferred_work_mode: Optional[str] = "Any"
    salary_expectation: Optional[str] = None

    @field_validator("preferred_roles", mode="before")
    @classmethod
    def validate_and_normalize_roles(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        v = parsed
                except Exception:
                    v = [item.strip() for item in v_str.split(",") if item.strip()]
            else:
                v = [item.strip() for item in v_str.split(",") if item.strip()]
        if isinstance(v, list):
            seen = set()
            normalized = []
            for item in v:
                if item is None:
                    continue
                clean = " ".join(str(item).strip().split())
                if clean and clean.lower() not in seen and len(clean) <= 100:
                    seen.add(clean.lower())
                    normalized.append(clean)
            return normalized
        return []

class CandidateProfileUpdate(CandidateProfileBase):
    skills: Optional[List[SkillCreate]] = None

class CandidateProfileResponse(CandidateProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    skills: List[SkillResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ResumeUploadResponse(BaseModel):
    message: str
    filename: str
    pages_parsed: int
    extracted_text_preview: str
    extracted_skills: List[str]
    draft_suggestions: List[SkillCreate]
    current_skills: List[SkillResponse]
    warning: Optional[str] = None

class ConfirmSkillsRequest(BaseModel):
    skills: List[SkillCreate]

