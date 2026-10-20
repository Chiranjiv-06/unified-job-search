from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ReminderAlertResponse(BaseModel):
    id: str = Field(..., description="Unique alert identifier")
    application_id: int
    company_name: str
    job_title: str
    alert_type: str = Field(..., description="ASSESSMENT_DUE | INTERVIEW_UPCOMING | FOLLOW_UP_NEEDED | STALE_LEAD")
    priority: str = Field(..., description="URGENT | HIGH | MEDIUM | LOW")
    title: str
    message: str
    action_label: str
    days_since_activity: int
    due_date: Optional[str] = None
    meeting_link: Optional[str] = None
    recruiter_email: Optional[str] = None
    stage: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertsListResponse(BaseModel):
    alerts: List[ReminderAlertResponse]
    total_alerts: int
    urgent_count: int = 0
    follow_up_count: int = 0
    interview_count: int = 0
    assessment_count: int = 0

class DraftFollowUpRequest(BaseModel):
    tone: Optional[str] = Field("professional", description="Tone style: 'polite', 'professional', or 'firm'")
    custom_notes: Optional[str] = Field(None, description="Additional context or specific discussion points to include")

class FollowUpDraftResponse(BaseModel):
    application_id: int
    company_name: str
    job_title: str
    stage: str
    tone: str
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    subject: str
    body: str
    mailto_link: str
    candidate_name: str

class LogFollowUpRequest(BaseModel):
    notes: Optional[str] = Field("Follow-up email sent to hiring team", description="Notes recorded in application timeline")
