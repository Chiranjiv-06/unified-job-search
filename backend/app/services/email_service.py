import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.application import Application
from app.models.company import Company
from app.models.email_event import EmailEvent
from app.core.enums import EmailCategory, ApplicationStatus
from app.schemas.email_event import EmailWebhookPayload

CATEGORY_PATTERNS = [
    (
        EmailCategory.SCAM_ALERT,
        [
            r"\b(wire transfer|crypto|cryptocurrency|cashier'?s check|payment required|send money|telegram interview|whatsapp interview only)\b",
            r"\b(western union|moneygram|processing fee)\b"
        ]
    ),
    (
        EmailCategory.INTERVIEW,
        [
            r"\b(interview invitation|schedule an interview|invitation to interview|technical round|coding challenge interview|phone screen|panel interview|zoom link.*interview)\b"
        ]
    ),
    (
        EmailCategory.ASSESSMENT,
        [
            r"\b(online assessment|hackerrank|codesignal|codility|assessment link|take-home|technical test|complete the test)\b"
        ]
    ),
    (
        EmailCategory.REJECTION,
        [
            r"\b(unfortunately|not moving forward|decided to pursue other|after careful consideration|will not be moving forward|position has been filled)\b"
        ]
    ),
    (
        EmailCategory.CONFIRMATION,
        [
            r"\b(application received|thank you for applying|received your application|successfully submitted|application confirmation|offer of employment|job offer)\b"
        ]
    ),
]

class EmailService:
    @staticmethod
    def classify_email(subject: str, body_text: str) -> Tuple[EmailCategory, Dict[str, Any]]:
        text_to_analyze = f"{subject}\n{body_text}".lower()

        for category, patterns in CATEGORY_PATTERNS:
            for pattern in patterns:
                match = re.search(pattern, text_to_analyze, re.IGNORECASE)
                if match:
                    return category, {"matched_pattern": match.group(0)}

        return EmailCategory.CONFIRMATION, {"matched_pattern": "default_confirmation"}

    @staticmethod
    def extract_domain_from_email(email_str: str) -> str:
        if "@" in email_str:
            return email_str.split("@")[-1].strip().lower()
        return ""

    @classmethod
    def resolve_application_for_email(
        cls,
        db: Session,
        user_id: int,
        sender_email: str,
        subject: str,
        body_text: str
    ) -> Optional[Application]:
        sender_domain = cls.extract_domain_from_email(sender_email)
        combined_text = f"{subject} {body_text}".lower()

        # Step 1: Match by Company Domain
        if sender_domain:
            stmt = (
                select(Application)
                .join(Company, Application.company_id == Company.id)
                .where(
                    Application.user_id == user_id,
                    func.lower(Company.domain) == sender_domain
                )
                .order_by(Application.last_activity_at.desc())
            )
            app = db.execute(stmt).scalars().first()
            if app:
                return app

        # Step 2: Match by Company Name in Subject or Body
        all_user_apps = db.execute(
            select(Application)
            .join(Company, Application.company_id == Company.id, isouter=True)
            .where(Application.user_id == user_id)
            .order_by(Application.last_activity_at.desc())
        ).scalars().all()

        for app in all_user_apps:
            if app.company and app.company.name.lower() in combined_text:
                return app
            if app.job_title and app.job_title.lower() in combined_text:
                return app

        return None

    @classmethod
    def ingest_email_event(
        cls,
        db: Session,
        payload: EmailWebhookPayload
    ) -> EmailEvent:
        # Prevent duplicate email event
        existing = db.execute(
            select(EmailEvent).where(EmailEvent.message_id == payload.message_id)
        ).scalar_one_or_none()
        if existing:
            return existing

        category, meta = cls.classify_email(payload.subject, payload.body_text)
        linked_application = cls.resolve_application_for_email(
            db=db,
            user_id=payload.user_id,
            sender_email=payload.sender_email,
            subject=payload.subject,
            body_text=payload.body_text
        )

        now = payload.received_at or datetime.now(timezone.utc)
        parsed_details = {
            "classification": meta,
            "sender_domain": cls.extract_domain_from_email(payload.sender_email),
            "linked_application_id": linked_application.id if linked_application else None
        }

        email_event = EmailEvent(
            application_id=linked_application.id if linked_application else None,
            user_id=payload.user_id,
            message_id=payload.message_id,
            sender_email=payload.sender_email,
            subject=payload.subject,
            detected_category=category,
            parsed_details=parsed_details,
            received_at=now
        )
        db.add(email_event)

        # Update application state and activity if linked
        if linked_application:
            linked_application.last_activity_at = now
            if category == EmailCategory.INTERVIEW and linked_application.status in [ApplicationStatus.APPLIED, ApplicationStatus.ASSESSMENT]:
                linked_application.status = ApplicationStatus.INTERVIEW
            elif category == EmailCategory.ASSESSMENT and linked_application.status == ApplicationStatus.APPLIED:
                linked_application.status = ApplicationStatus.ASSESSMENT
            elif category == EmailCategory.REJECTION and linked_application.status != ApplicationStatus.OFFER:
                linked_application.status = ApplicationStatus.REJECTED

        db.commit()
        db.refresh(email_event)
        return email_event
