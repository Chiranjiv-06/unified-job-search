import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.application import Application
from app.models.company import Company
from app.models.user import User
from app.models.profile import CandidateProfile, CandidateSkill
from app.core.enums import ApplicationStatus
from app.schemas.reminder import (
    ReminderAlertResponse,
    AlertsListResponse,
    FollowUpDraftResponse
)

class ReminderService:
    @staticmethod
    def calculate_aging_status(application: Application, now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculates time elapsed since last activity and evaluates stage-specific aging thresholds.
        Safety Rule: Never automatically updates application status to REJECTED due to silence.
        """
        now = now or datetime.now(timezone.utc)
        ref_date = application.last_activity_at or application.applied_at or application.created_at or now
        if ref_date.tzinfo is None:
            ref_date = ref_date.replace(tzinfo=timezone.utc)

        delta = now - ref_date
        days_elapsed = max(0, delta.days)

        status_key = application.status
        aging_category = "RECENT"
        aging_message = "Application is active and recently updated."
        follow_up_recommended = False

        if status_key == ApplicationStatus.APPLIED:
            if days_elapsed < 3:
                aging_category = "RECENT"
                aging_message = "Application submitted recently. No follow-up needed yet."
            elif 3 <= days_elapsed <= 10:
                aging_category = "FOLLOW_UP_SUGGESTED"
                aging_message = f"Application submitted {days_elapsed} days ago with no update. A polite status inquiry is recommended."
                follow_up_recommended = True
            else:
                aging_category = "STALE_LEAD"
                aging_message = f"No activity for {days_elapsed} days. This lead may be stalled."
                follow_up_recommended = True

        elif status_key == ApplicationStatus.INTERVIEW:
            if days_elapsed < 2:
                aging_category = "RECENT"
                aging_message = "Interview scheduled or completed recently."
            elif 2 <= days_elapsed <= 7:
                aging_category = "FOLLOW_UP_SUGGESTED"
                aging_message = f"Interview occurred/scheduled {days_elapsed} days ago. Send a thank-you note or check next steps."
                follow_up_recommended = True
            else:
                aging_category = "STALE_LEAD"
                aging_message = f"No interview update for {days_elapsed} days. Inquire about the hiring timeline."
                follow_up_recommended = True

        elif status_key == ApplicationStatus.ASSESSMENT:
            if days_elapsed < 2:
                aging_category = "RECENT"
                aging_message = "Assessment assigned recently."
            elif 2 <= days_elapsed <= 5:
                aging_category = "FOLLOW_UP_SUGGESTED"
                aging_message = f"Assessment submitted or pending for {days_elapsed} days. Confirm submission or check results."
                follow_up_recommended = True
            else:
                aging_category = "STALE_LEAD"
                aging_message = f"Assessment idle for {days_elapsed} days."
                follow_up_recommended = True

        elif status_key == ApplicationStatus.OFFER:
            if days_elapsed > 3:
                aging_category = "FOLLOW_UP_SUGGESTED"
                aging_message = f"Offer pending consideration for {days_elapsed} days. Ensure timely response to employer."
                follow_up_recommended = True

        return {
            "days_elapsed": days_elapsed,
            "aging_category": aging_category,
            "aging_message": aging_message,
            "follow_up_recommended": follow_up_recommended
        }

    @classmethod
    def get_alerts_for_user(cls, db: Session, user_id: int) -> AlertsListResponse:
        """
        Scans candidate's active applications to generate prioritized action alerts:
        1. Urgent coding assessment deadlines
        2. Upcoming interviews
        3. Stalled applications requiring follow-up
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(Application)
            .where(
                Application.user_id == user_id,
                Application.status.not_in([ApplicationStatus.REJECTED, ApplicationStatus.STALE])
            )
            .order_by(Application.last_activity_at.asc())
        )
        apps = db.execute(stmt).scalars().all()

        alerts: List[ReminderAlertResponse] = []
        urgent_count = 0
        follow_up_count = 0
        interview_count = 0
        assessment_count = 0

        for app in apps:
            company_name = app.company.name if app.company else "Employer"
            aging_info = cls.calculate_aging_status(app, now)
            days = aging_info["days_elapsed"]

            # Extract recruiter email if present
            recruiter_email = None
            if app.recruiter_contact:
                import re
                email_match = re.search(r"[\w\.-]+@[\w\.-]+", app.recruiter_contact)
                if email_match:
                    recruiter_email = email_match.group(0)

            # 1. Check Assessment Deadlines
            if app.status == ApplicationStatus.ASSESSMENT or (app.interview_details and "assessment" in app.interview_details.lower()):
                details_text = app.interview_details or ""
                # Check for deadline
                is_urgent = False
                due_date_str = None

                if app.response_deadline:
                    rd = app.response_deadline
                    if rd.tzinfo is None:
                        rd = rd.replace(tzinfo=timezone.utc)
                    hours_left = (rd - now).total_seconds() / 3600
                    due_date_str = rd.strftime("%b %d, %Y")
                    if 0 <= hours_left <= 24:
                        is_urgent = True
                elif "deadline" in details_text.lower():
                    due_date_str = details_text
                    if "within 24" in details_text.lower() or "today" in details_text.lower():
                        is_urgent = True

                priority = "URGENT" if is_urgent else "HIGH"
                alerts.append(ReminderAlertResponse(
                    id=f"alert_assessment_{app.id}",
                    application_id=app.id,
                    company_name=company_name,
                    job_title=app.job_title,
                    alert_type="ASSESSMENT_DUE",
                    priority=priority,
                    title=f"Assessment Due: {company_name}",
                    message=f"Technical coding assessment deadline pending for {app.job_title}. Review and complete test before expiration.",
                    action_label="Take Assessment",
                    days_since_activity=days,
                    due_date=due_date_str or "Approaching Soon",
                    meeting_link=None,
                    recruiter_email=recruiter_email,
                    stage=app.status.value,
                    created_at=now
                ))
                assessment_count += 1
                if is_urgent:
                    urgent_count += 1

            # 2. Check Upcoming Interviews
            elif app.status == ApplicationStatus.INTERVIEW:
                meeting_link = None
                if app.interview_details and ("http" in app.interview_details or "zoom" in app.interview_details or "meet" in app.interview_details):
                    import re
                    url_match = re.search(r"https?:\/\/[^\s\|<>\"']+", app.interview_details)
                    if url_match:
                        meeting_link = url_match.group(0)

                alerts.append(ReminderAlertResponse(
                    id=f"alert_interview_{app.id}",
                    application_id=app.id,
                    company_name=company_name,
                    job_title=app.job_title,
                    alert_type="INTERVIEW_UPCOMING",
                    priority="HIGH",
                    title=f"Interview Scheduled: {company_name}",
                    message=f"Upcoming technical discussion for {app.job_title}. Review job details and candidate strengths.",
                    action_label="Join Interview" if meeting_link else "Prepare Interview",
                    days_since_activity=days,
                    due_date=None,
                    meeting_link=meeting_link,
                    recruiter_email=recruiter_email,
                    stage=app.status.value,
                    created_at=now
                ))
                interview_count += 1

            # 3. Check Stalled Applications / Follow-Up Needed
            if aging_info["follow_up_recommended"]:
                alert_type = "FOLLOW_UP_NEEDED" if aging_info["aging_category"] == "FOLLOW_UP_SUGGESTED" else "STALE_LEAD"
                priority = "MEDIUM" if alert_type == "FOLLOW_UP_NEEDED" else "LOW"
                alerts.append(ReminderAlertResponse(
                    id=f"alert_followup_{app.id}",
                    application_id=app.id,
                    company_name=company_name,
                    job_title=app.job_title,
                    alert_type=alert_type,
                    priority=priority,
                    title=f"Follow-Up Suggested: {company_name}",
                    message=aging_info["aging_message"],
                    action_label="Draft Follow-Up",
                    days_since_activity=days,
                    due_date=None,
                    meeting_link=None,
                    recruiter_email=recruiter_email,
                    stage=app.status.value,
                    created_at=now
                ))
                follow_up_count += 1

        # Sort priority: URGENT -> HIGH -> MEDIUM -> LOW
        priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts.sort(key=lambda a: (priority_order.get(a.priority, 4), -a.days_since_activity))

        return AlertsListResponse(
            alerts=alerts,
            total_alerts=len(alerts),
            urgent_count=urgent_count,
            follow_up_count=follow_up_count,
            interview_count=interview_count,
            assessment_count=assessment_count
        )

    @classmethod
    def generate_followup_draft(
        cls,
        db: Session,
        user_id: int,
        application_id: int,
        tone: str = "professional",
        custom_notes: Optional[str] = None
    ) -> FollowUpDraftResponse:
        """
        Drafts a context-aware, polite email follow-up tailored to stage, company metadata, and tone.
        Safety Rule: STRICT NO AUTO-SEND. Only returns draft content for candidate review and copying.
        """
        app = db.execute(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id
            )
        ).scalar_one_or_none()

        if not app:
            raise ValueError("Application not found or access denied.")

        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        candidate_name = user.full_name if user and user.full_name else "Candidate"

        # Fetch candidate skills from profile
        profile = db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        ).scalar_one_or_none()

        top_skills = []
        if profile and profile.skills:
            top_skills = [s.name for s in profile.skills[:3]]
        elif profile and profile.parsed_skills and isinstance(profile.parsed_skills, list):
            top_skills = profile.parsed_skills[:3]
        skills_str = ", ".join(top_skills) if top_skills else "software engineering and system design"

        company_name = app.company.name if app.company else "your team"
        job_title = app.job_title
        applied_date_str = app.applied_at.strftime("%B %d") if app.applied_at else "recently"

        # Resolve recruiter contact info
        recruiter_name = None
        recruiter_email = None
        if app.recruiter_contact:
            import re
            email_match = re.search(r"[\w\.-]+@[\w\.-]+", app.recruiter_contact)
            if email_match:
                recruiter_email = email_match.group(0)
            # Try to extract name
            name_part = app.recruiter_contact.split("@")[0]
            if len(name_part) > 2 and not name_part.lower().startswith("recruiter") and not name_part.lower().startswith("talent"):
                recruiter_name = name_part.replace(".", " ").title()

        salutation = f"Dear {recruiter_name}," if recruiter_name else f"Dear {company_name} Hiring Team,"

        tone_clean = (tone or "professional").lower()

        # Build Stage-Specific Email Drafts
        if app.status == ApplicationStatus.INTERVIEW:
            if tone_clean == "polite":
                subject = f"Thank you for the interview - {job_title} ({candidate_name})"
                body = (
                    f"{salutation}\n\n"
                    f"I wanted to thank you and the team for taking the time to speak with me regarding the {job_title} position at {company_name}. "
                    f"I thoroughly enjoyed learning more about your technical vision and collaborative engineering culture.\n\n"
                    f"Our discussion further confirmed my enthusiasm for the role, especially given my background in {skills_str}. "
                    f"Please let me know if there are any follow-up materials or code samples I can provide to support your decision.\n\n"
                    f"I look forward to hearing about the next steps.\n\n"
                    f"Warm regards,\n{candidate_name}"
                )
            elif tone_clean == "firm":
                subject = f"Follow-up regarding interview status: {job_title} - {candidate_name}"
                body = (
                    f"{salutation}\n\n"
                    f"I am writing to check in on the status of my application for the {job_title} role at {company_name} following our recent interview.\n\n"
                    f"I remain very interested in the opportunity and confident in the value I can bring to your team. "
                    f"Could you please share an anticipated timeline for your hiring decision?\n\n"
                    f"Thank you for your time and guidance.\n\n"
                    f"Sincerely,\n{candidate_name}"
                )
            else:  # professional
                subject = f"Following up on our interview - {job_title} - {candidate_name}"
                body = (
                    f"{salutation}\n\n"
                    f"Thank you for the opportunity to interview for the {job_title} position at {company_name}. "
                    f"I appreciated learning more about the engineering challenges your team is currently solving.\n\n"
                    f"I remain very excited about this opportunity and believe my experience with {skills_str} makes me a strong fit for your goals. "
                    f"Could you please provide an update regarding the timeline for the next phase of the process?\n\n"
                    f"Thank you again for your time and consideration.\n\n"
                    f"Best regards,\n{candidate_name}"
                )

        elif app.status == ApplicationStatus.ASSESSMENT:
            if tone_clean == "polite":
                subject = f"Technical Assessment Completed - {job_title} at {company_name} ({candidate_name})"
                body = (
                    f"{salutation}\n\n"
                    f"I have successfully completed the technical assessment for the {job_title} position at {company_name}.\n\n"
                    f"I really enjoyed working through the problem scenarios and demonstrating my technical skills. "
                    f"Please let me know once your team has had a chance to evaluate the submission.\n\n"
                    f"Thank you for this opportunity,\n{candidate_name}"
                )
            elif tone_clean == "firm":
                subject = f"Assessment Submission Status: {job_title} at {company_name} - {candidate_name}"
                body = (
                    f"{salutation}\n\n"
                    f"I am confirming that I completed and submitted the technical assessment for {job_title}.\n\n"
                    f"Could you please confirm receipt of the submission and advise when I can expect feedback on the results?\n\n"
                    f"Best regards,\n{candidate_name}"
                )
            else:  # professional
                subject = f"Confirmation of Assessment Submission - {job_title} at {company_name} - {candidate_name}"
                body = (
                    f"{salutation}\n\n"
                    f"I am writing to confirm that I have completed the online technical assessment for the {job_title} position at {company_name}.\n\n"
                    f"I enjoyed the challenge and look forward to discussing my implementation and solution approach with your engineering team. "
                    f"Please let me know if you need any additional details from my end.\n\n"
                    f"Best regards,\n{candidate_name}"
                )

        else:  # APPLIED or General Silence
            if tone_clean == "polite":
                subject = f"Checking in on my application for {job_title} at {company_name} - {candidate_name}"
                body = (
                    f"{salutation}\n\n"
                    f"I hope you are having a wonderful week.\n\n"
                    f"I applied for the {job_title} position at {company_name} on {applied_date_str} and wanted to politely reiterate my excitement about this role. "
                    f"With my strong background in {skills_str}, I am enthusiastic about the opportunity to contribute to your team.\n\n"
                    f"Please let me know if any supplementary information or portfolio materials would be helpful at this stage.\n\n"
                    f"Warm regards,\n{candidate_name}"
                )
            elif tone_clean == "firm":
                subject = f"Status inquiry: {job_title} application at {company_name} - {candidate_name}"
                body = (
                    f"{salutation}\n\n"
                    f"I am writing to inquire about the review status of my application for the {job_title} position submitted on {applied_date_str}.\n\n"
                    f"As I am currently actively interviewing and evaluating timelines, I would appreciate an update on whether your team has begun reviewing candidates for this role.\n\n"
                    f"Thank you for your time and assistance.\n\n"
                    f"Sincerely,\n{candidate_name}"
                )
            else:  # professional
                subject = f"Inquiry regarding {job_title} application at {company_name} - {candidate_name}"
                body = (
                    f"{salutation}\n\n"
                    f"I hope this note finds you well.\n\n"
                    f"I submitted my application for the {job_title} role at {company_name} on {applied_date_str}. "
                    f"Given my hands-on background with {skills_str}, I remain very enthusiastic about the prospect of joining your team.\n\n"
                    f"Could you kindly let me know if you have an estimated timeline for the initial review of applications?\n\n"
                    f"Thank you for your consideration.\n\n"
                    f"Best regards,\n{candidate_name}"
                )

        # Append custom notes if provided
        if custom_notes and custom_notes.strip():
            body += f"\n\nP.S. {custom_notes.strip()}"

        # Build mailto link
        recipient = recruiter_email or ""
        encoded_subject = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(body)
        mailto_link = f"mailto:{recipient}?subject={encoded_subject}&body={encoded_body}"

        return FollowUpDraftResponse(
            application_id=app.id,
            company_name=company_name,
            job_title=job_title,
            stage=app.status.value,
            tone=tone_clean,
            recipient_email=recruiter_email,
            recipient_name=recruiter_name,
            subject=subject,
            body=body,
            mailto_link=mailto_link,
            candidate_name=candidate_name
        )

    @classmethod
    def log_followup_activity(
        cls,
        db: Session,
        user_id: int,
        application_id: int,
        notes: str
    ) -> Application:
        """
        Logs follow-up communication in application timeline and refreshes last_activity_at timestamp.
        """
        app = db.execute(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id
            )
        ).scalar_one_or_none()

        if not app:
            raise ValueError("Application not found or access denied.")

        now = datetime.now(timezone.utc)
        app.last_activity_at = now

        events = list(app.timeline_events or [])
        events.append({
            "stage": app.status.value,
            "timestamp": now.isoformat(),
            "notes": f"Candidate Follow-Up: {notes.strip()}"
        })
        app.timeline_events = events

        db.commit()
        db.refresh(app)
        return app
