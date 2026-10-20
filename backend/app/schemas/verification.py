from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class VerificationRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255, description="Name of company to verify")
    job_url: Optional[str] = Field(None, max_length=1000, description="Job application or posting URL")
    recruiter_domain: Optional[str] = Field(None, max_length=255, description="Domain from recruiter email or profile")

class VerificationResponse(BaseModel):
    company_id: Optional[int] = None
    company_name: str
    domain: Optional[str] = None
    domain_valid: bool
    mx_records_found: bool
    official_posting_matched: bool
    scam_flags: List[str] = []
    fraud_score: float = Field(..., ge=0.0, le=100.0, description="Risk/fraud score from 0 (verified safe) to 100 (high risk)")
    is_verified: bool
    checked_at: datetime
    evidence_summary: str
    details: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)
