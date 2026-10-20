from enum import Enum

class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    APPLIED = "APPLIED"
    ASSESSMENT = "ASSESSMENT"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    STALE = "STALE"

class EmailCategory(str, Enum):
    CONFIRMATION = "CONFIRMATION"
    ASSESSMENT = "ASSESSMENT"
    INTERVIEW = "INTERVIEW"
    REJECTION = "REJECTION"
    SCAM_ALERT = "SCAM_ALERT"
