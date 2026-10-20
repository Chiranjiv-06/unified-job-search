import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from app.models.application import Application
from app.models.company import Company
from app.models.email_event import EmailEvent
from app.core.enums import EmailCategory, ApplicationStatus
from app.schemas.email_event import EmailIngestRequest

SCAM_PATTERNS = [
    r"\b(wire transfer|crypto|cryptocurrency|bitcoin|cashier'?s check|payment required|send money|western union|moneygram)\b",
    r"\b(processing fee|training fee|registration fee|security deposit|equipment deposit|refundable deposit)\b",
    r"\b(telegram interview|contact @[a-zA-Z0-9_]+ on telegram|whatsapp interview only|interview via telegram|t\.me\/)\b",
]

ASSESSMENT_PATTERNS = [
    r"\b(hackerrank|codesignal|codility|hackerearth|leetcode|testgorilla|karat|mettl|ikm)\b",
    r"\b(online assessment|coding assessment|technical assessment|take-home challenge|take-home test|coding test|complete the test|assessment link)\b"
]

INTERVIEW_PATTERNS = [
    r"\b(interview invitation|schedule an interview|invitation to interview|technical round|first round interview|panel interview|phone screen)\b",
    r"\b(zoom link.*interview|google meet.*interview|teams meeting|calendly\.com\/|interview slot|schedule your interview|meet the team)\b"
]

REJECTION_PATTERNS = [
    r"\b(unfortunately|not moving forward|decided to pursue other|after careful consideration|will not be moving forward|position has been filled)\b",
    r"\b(other candidates whose skills|not selected to move forward|unable to offer you an interview|wish you the best in your job search)\b"
]

CONFIRMATION_PATTERNS = [
    r"\b(application received|thank you for applying|received your application|successfully submitted|application confirmation|we have received your application|thanks for applying)\b",
    r"\b(offer of employment|job offer)\b"
]

class EmailService:
    @staticmethod
    def extract_domain_from_email(email_str: str) -> str:
        if not email_str:
            return ""
        # Handle formats like "Recruiter <recruiter@company.com>"
        match = re.search(r"[\w\.-]+@([\w\.-]+)", email_str)
        if match:
            return match.group(1).lower().strip()
        if "@" in email_str:
            return email_str.split("@")[-1].strip().lower()
        return ""

    @staticmethod
    def extract_meeting_link(text: str) -> Optional[str]:
        # Google Meet, Zoom, Teams, Calendly
        patterns = [
            r"https?:\/\/meet\.google\.com\/[a-z0-9\-]+",
            r"https?:\/\/[a-z0-9\.]*zoom\.us\/j\/[0-9]+(?:\?[^\s<>\"']*)?",
            r"https?:\/\/teams\.microsoft\.com\/l\/meetup-join\/[^\s<>\"']+",
            r"https?:\/\/calendly\.com\/[a-zA-Z0-9\-_]+(?:\/[a-zA-Z0-9\-_]+)?",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    @staticmethod
    def extract_deadline(text: str) -> Optional[str]:
        patterns = [
            r"(?:due|deadline|complete by|valid until|submit by)\s*[:\-]?\s*([A-Za-z0-9,:\s\-]+?(?:\.|\n|$))",
            r"within\s+(\d+\s+(?:hours?|days?|business days?))",
            r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?[\s,]+\d{4}\b)",
            r"(\b\d{4}-\d{2}-\d{2}\b)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) <= 60:
                    return candidate
        return None

    @classmethod
    def classify_email(cls, subject: str, body_text: str) -> Tuple[EmailCategory, Dict[str, Any]]:
        text_to_analyze = f"{subject}\n{body_text}".lower()
        details: Dict[str, Any] = {}

        # 1. Check Scam Alert (Highest Priority Security Check)
        scam_flags = []
        for pat in SCAM_PATTERNS:
            matches = re.findall(pat, text_to_analyze, re.IGNORECASE)
            if matches:
                scam_flags.extend(matches)
        if scam_flags:
            details["is_scam"] = True
            details["scam_indicators"] = list(set(scam_flags))
            details["warning_message"] = "Suspicious recruitment fraud signals detected (fee demands or unverified chat redirects)."
            details["confidence"] = 0.95
            return EmailCategory.SCAM_ALERT, details

        # 2. Check Assessment Invite
        for pat in ASSESSMENT_PATTERNS:
            match = re.search(pat, text_to_analyze, re.IGNORECASE)
            if match:
                details["matched_pattern"] = match.group(0)
                details["confidence"] = 0.90
                # Identify platform
                for plat in ["HackerRank", "CodeSignal", "Codility", "HackerEarth", "LeetCode", "TestGorilla", "Karat"]:
                    if plat.lower() in text_to_analyze:
                        details["platform"] = plat
                        break
                if "platform" not in details:
                    details["platform"] = "Online Coding Assessment"

                deadline = cls.extract_deadline(text_to_analyze)
                if deadline:
                    details["assessment_deadline"] = deadline

                meeting_link = cls.extract_meeting_link(body_text)
                if meeting_link:
                    details["test_link"] = meeting_link

                return EmailCategory.ASSESSMENT, details

        # 3. Check Interview Invite
        for pat in INTERVIEW_PATTERNS:
            match = re.search(pat, text_to_analyze, re.IGNORECASE)
            if match:
                details["matched_pattern"] = match.group(0)
                details["confidence"] = 0.90
                # Identify platform
                if "zoom" in text_to_analyze:
                    details["platform"] = "Zoom"
                elif "meet.google.com" in text_to_analyze or "google meet" in text_to_analyze:
                    details["platform"] = "Google Meet"
                elif "teams" in text_to_analyze:
                    details["platform"] = "Microsoft Teams"
                elif "calendly" in text_to_analyze:
                    details["platform"] = "Calendly"
                else:
                    details["platform"] = "Technical Interview"

                meeting_link = cls.extract_meeting_link(body_text)
                if meeting_link:
                    details["meeting_link"] = meeting_link

                # Check for date in text
                deadline = cls.extract_deadline(text_to_analyze)
                if deadline:
                    details["scheduled_at"] = deadline

                return EmailCategory.INTERVIEW, details

        # 4. Check Rejection
        for pat in REJECTION_PATTERNS:
            match = re.search(pat, text_to_analyze, re.IGNORECASE)
            if match:
                details["matched_pattern"] = match.group(0)
                details["rejection_notice"] = True
                details["confidence"] = 0.95
                return EmailCategory.REJECTION, details

        # 5. Check Confirmation
        for pat in CONFIRMATION_PATTERNS:
            match = re.search(pat, text_to_analyze, re.IGNORECASE)
            if match:
                details["matched_pattern"] = match.group(0)
                details["confirmation"] = True
                details["confidence"] = 0.90
                return EmailCategory.CONFIRMATION, details

        # Default fallback
        details["matched_pattern"] = "default_confirmation"
        details["confidence"] = 0.60
        return EmailCategory.CONFIRMATION, details

    @classmethod
    def resolve_application_for_email(
        cls,
        db: Session,
        user_id: int,
        sender_email: str,
        subject: str,
        body_text: str
    ) -> Tuple[Optional[Application], float, bool, List[int]]:
        """
        Entity Resolution:
        Matches sender domain, company name, or recruiter contact against candidate applications.
        Returns: (matched_application, confidence_score, requires_review_flag, potential_application_ids)
        """
        sender_domain = cls.extract_domain_from_email(sender_email)
        combined_text = f"{subject} {body_text}".lower()

        # Step 1: Match by Company Domain (High Confidence)
        if sender_domain and sender_domain not in ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]:
            stmt = (
                select(Application)
                .join(Company, Application.company_id == Company.id)
                .where(
                    Application.user_id == user_id,
                    func.lower(Company.domain) == sender_domain
                )
                .order_by(Application.last_activity_at.desc())
            )
            matching_apps = db.execute(stmt).scalars().all()
            if len(matching_apps) == 1:
                return matching_apps[0], 0.95, False, [matching_apps[0].id]
            elif len(matching_apps) > 1:
                # Multiple roles active at same company -> requires review
                return matching_apps[0], 0.70, True, [a.id for a in matching_apps]

        # Step 2: Match by Recruiter Contact in Application
        all_user_apps = db.execute(
            select(Application)
            .join(Company, Application.company_id == Company.id, isouter=True)
            .where(Application.user_id == user_id)
            .order_by(Application.last_activity_at.desc())
        ).scalars().all()

        for app in all_user_apps:
            if app.recruiter_contact and sender_email.lower() in app.recruiter_contact.lower():
                return app, 0.95, False, [app.id]

        # Step 3: Match by Company Name in Subject or Body
        company_matched_apps = []
        for app in all_user_apps:
            if app.company and app.company.name and app.company.name.lower() in combined_text:
                company_matched_apps.append(app)

        if len(company_matched_apps) == 1:
            return company_matched_apps[0], 0.85, False, [company_matched_apps[0].id]
        elif len(company_matched_apps) > 1:
            return company_matched_apps[0], 0.65, True, [a.id for a in company_matched_apps]

        # Step 4: Match by Job Title in Subject or Body
        title_matched_apps = []
        for app in all_user_apps:
            if app.job_title and len(app.job_title) > 3 and app.job_title.lower() in combined_text:
                title_matched_apps.append(app)

        if len(title_matched_apps) == 1:
            return title_matched_apps[0], 0.75, False, [title_matched_apps[0].id]
        elif len(title_matched_apps) > 1:
            return title_matched_apps[0], 0.55, True, [a.id for a in title_matched_apps]

        # No match found -> requires manual review
        return None, 0.0, True, []

    @classmethod
    def ingest_email_event(
        cls,
        db: Session,
        payload: EmailIngestRequest
    ) -> EmailEvent:
        # Prevent duplicate email event by message_id
        existing = db.execute(
            select(EmailEvent).where(EmailEvent.message_id == payload.message_id)
        ).scalar_one_or_none()
        if existing:
            return existing

        category, meta = cls.classify_email(payload.subject, payload.body_text)

        target_user_id = payload.user_id
        if not target_user_id:
            # Fallback to first user in system if not explicitly passed
            from app.models.user import User
            first_user = db.execute(select(User).limit(1)).scalar_one_or_none()
            target_user_id = first_user.id if first_user else 1

        linked_app, confidence, requires_review, potential_ids = cls.resolve_application_for_email(
            db=db,
            user_id=target_user_id,
            sender_email=payload.sender_email,
            subject=payload.subject,
            body_text=payload.body_text
        )

        now = payload.received_at or datetime.now(timezone.utc)
        parsed_details = {
            **meta,
            "sender_domain": cls.extract_domain_from_email(payload.sender_email),
            "linked_application_id": linked_app.id if linked_app else None,
            "confidence": confidence,
            "requires_review": requires_review or (linked_app is None),
            "potential_application_ids": potential_ids,
        }

        email_event = EmailEvent(
            application_id=linked_app.id if linked_app else None,
            user_id=target_user_id,
            message_id=payload.message_id,
            sender_email=payload.sender_email,
            subject=payload.subject,
            detected_category=category,
            parsed_details=parsed_details,
            received_at=now
        )
        db.add(email_event)

        # Synchronize linked application lifecycle and timeline
        if linked_app:
            linked_app.last_activity_at = now
            original_status = linked_app.status

            if category in [EmailCategory.INTERVIEW, EmailCategory.INTERVIEW_INVITE]:
                if linked_app.status in [ApplicationStatus.DRAFT, ApplicationStatus.APPLIED, ApplicationStatus.ASSESSMENT]:
                    linked_app.status = ApplicationStatus.INTERVIEW
                # Save meeting link/scheduled time to interview_details
                if meta.get("meeting_link") or meta.get("scheduled_at"):
                    details_str = f"Platform: {meta.get('platform', 'Video')} | Link: {meta.get('meeting_link', 'TBD')} | Scheduled: {meta.get('scheduled_at', 'Pending')}"
                    linked_app.interview_details = details_str

            elif category in [EmailCategory.ASSESSMENT, EmailCategory.ASSESSMENT_INVITE]:
                if linked_app.status in [ApplicationStatus.DRAFT, ApplicationStatus.APPLIED]:
                    linked_app.status = ApplicationStatus.ASSESSMENT
                # Save assessment deadline
                if meta.get("assessment_deadline"):
                    details_str = f"Platform: {meta.get('platform', 'Assessment')} | Deadline: {meta.get('assessment_deadline')}"
                    linked_app.interview_details = details_str

            elif category in [EmailCategory.CONFIRMATION, EmailCategory.APPLICATION_CONFIRMATION]:
                if linked_app.status == ApplicationStatus.DRAFT:
                    linked_app.status = ApplicationStatus.APPLIED

            elif category == EmailCategory.REJECTION:
                if linked_app.status != ApplicationStatus.OFFER:
                    linked_app.status = ApplicationStatus.REJECTED

            # Record event in timeline_events
            timeline_list = list(linked_app.timeline_events or [])
            timeline_entry = {
                "stage": linked_app.status.value,
                "timestamp": now.isoformat(),
                "notes": f"Recruitment email received [{category.value}]: '{payload.subject}' from {payload.sender_email}"
            }
            if original_status != linked_app.status:
                timeline_entry["notes"] += f" (Stage updated to {linked_app.status.value})"
            timeline_list.append(timeline_entry)
            linked_app.timeline_events = timeline_list

        db.commit()
        db.refresh(email_event)
        return email_event

    @classmethod
    def link_email_to_application(
        cls,
        db: Session,
        user_id: int,
        email_id: int,
        application_id: int
    ) -> EmailEvent:
        """
        Manually connects an ambiguous or unlinked email event to a candidate application.
        """
        email_event = db.execute(
            select(EmailEvent).where(
                EmailEvent.id == email_id,
                EmailEvent.user_id == user_id
            )
        ).scalar_one_or_none()

        if not email_event:
            raise ValueError("Email event not found or access denied.")

        application = db.execute(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id
            )
        ).scalar_one_or_none()

        if not application:
            raise ValueError("Application not found or access denied.")

        # Update email event
        email_event.application_id = application.id
        details = dict(email_event.parsed_details or {})
        details["requires_review"] = False
        details["manually_linked"] = True
        details["linked_application_id"] = application.id
        email_event.parsed_details = details

        # Synchronize application stage
        now = datetime.now(timezone.utc)
        application.last_activity_at = now
        cat = email_event.detected_category

        if cat in [EmailCategory.INTERVIEW, EmailCategory.INTERVIEW_INVITE]:
            if application.status in [ApplicationStatus.DRAFT, ApplicationStatus.APPLIED, ApplicationStatus.ASSESSMENT]:
                application.status = ApplicationStatus.INTERVIEW
        elif cat in [EmailCategory.ASSESSMENT, EmailCategory.ASSESSMENT_INVITE]:
            if application.status in [ApplicationStatus.DRAFT, ApplicationStatus.APPLIED]:
                application.status = ApplicationStatus.ASSESSMENT
        elif cat == EmailCategory.REJECTION:
            if application.status != ApplicationStatus.OFFER:
                application.status = ApplicationStatus.REJECTED
        elif cat in [EmailCategory.CONFIRMATION, EmailCategory.APPLICATION_CONFIRMATION]:
            if application.status == ApplicationStatus.DRAFT:
                application.status = ApplicationStatus.APPLIED

        # Append timeline event
        timeline_list = list(application.timeline_events or [])
        timeline_list.append({
            "stage": application.status.value,
            "timestamp": now.isoformat(),
            "notes": f"Manually linked email [{cat.value}]: '{email_event.subject}'"
        })
        application.timeline_events = timeline_list

        db.commit()
        db.refresh(email_event)
        return email_event

    @classmethod
    def get_user_emails(
        cls,
        db: Session,
        user_id: int,
        category: Optional[str] = None,
        requires_review: Optional[bool] = None,
        application_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves paginated email events for candidate with linked application details.
        """
        query = (
            select(EmailEvent, Application, Company)
            .outerjoin(Application, EmailEvent.application_id == Application.id)
            .outerjoin(Company, Application.company_id == Company.id)
            .where(EmailEvent.user_id == user_id)
        )

        if category and category.upper() != "ALL":
            cat_upper = category.upper()
            if cat_upper in ["INTERVIEWS", "INTERVIEW"]:
                query = query.where(EmailEvent.detected_category.in_([EmailCategory.INTERVIEW, EmailCategory.INTERVIEW_INVITE]))
            elif cat_upper in ["ASSESSMENTS", "ASSESSMENT"]:
                query = query.where(EmailEvent.detected_category.in_([EmailCategory.ASSESSMENT, EmailCategory.ASSESSMENT_INVITE]))
            elif cat_upper in ["CONFIRMATIONS", "CONFIRMATION"]:
                query = query.where(EmailEvent.detected_category.in_([EmailCategory.CONFIRMATION, EmailCategory.APPLICATION_CONFIRMATION]))
            elif cat_upper in ["REJECTIONS", "REJECTION"]:
                query = query.where(EmailEvent.detected_category == EmailCategory.REJECTION)
            elif cat_upper in ["SCAM", "SCAM_ALERT", "SCAM WARNINGS"]:
                query = query.where(EmailEvent.detected_category == EmailCategory.SCAM_ALERT)

        if application_id is not None:
            query = query.where(EmailEvent.application_id == application_id)

        # Count total
        count_stmt = select(func.count(EmailEvent.id)).where(EmailEvent.user_id == user_id)
        total = db.execute(count_stmt).scalar() or 0

        # Paginate
        results = db.execute(
            query.order_by(EmailEvent.received_at.desc())
            .offset(skip)
            .limit(limit)
        ).all()

        items = []
        for event, app, comp in results:
            item_dict = {
                "id": event.id,
                "application_id": event.application_id,
                "user_id": event.user_id,
                "message_id": event.message_id,
                "sender_email": event.sender_email,
                "subject": event.subject,
                "detected_category": event.detected_category,
                "parsed_details": event.parsed_details or {},
                "received_at": event.received_at,
                "application_job_title": app.job_title if app else None,
                "application_company_name": comp.name if comp else None,
                "application_status": app.status.value if app else None,
            }
            if requires_review is not None:
                is_review = item_dict["parsed_details"].get("requires_review", False)
                if is_review != requires_review:
                    continue
            items.append(item_dict)

        return items, total
