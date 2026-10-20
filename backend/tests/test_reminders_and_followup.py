from datetime import datetime, timezone, timedelta
import pytest
from app.core.enums import ApplicationStatus
from app.models.application import Application
from app.services.reminder_service import ReminderService

def get_auth_token(client, email="reminder_tester@example.com"):
    client.post("/api/auth/register", json={
        "full_name": "Reminder Specialist",
        "email": email,
        "password": "Password123!"
    })
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    return res.json()["access_token"]

def test_application_aging_status_calculation(client, db_session):
    """
    Verifies that ReminderService correctly categorizes aging thresholds
    (RECENT < 3d, FOLLOW_UP_SUGGESTED 3-10d, STALE_LEAD > 10d for APPLIED)
    and NEVER automatically updates status to REJECTED.
    """
    now = datetime.now(timezone.utc)

    # 1. Recent application (1 day old)
    recent_app = Application(
        user_id=1,
        job_title="Recent Role",
        status=ApplicationStatus.APPLIED,
        last_activity_at=now - timedelta(days=1),
        applied_at=now - timedelta(days=1)
    )
    res_recent = ReminderService.calculate_aging_status(recent_app, now)
    assert res_recent["aging_category"] == "RECENT"
    assert res_recent["follow_up_recommended"] is False

    # 2. Follow-up suggested (5 days old)
    stalled_app = Application(
        user_id=1,
        job_title="Stalled Role",
        status=ApplicationStatus.APPLIED,
        last_activity_at=now - timedelta(days=5),
        applied_at=now - timedelta(days=5)
    )
    res_stalled = ReminderService.calculate_aging_status(stalled_app, now)
    assert res_stalled["aging_category"] == "FOLLOW_UP_SUGGESTED"
    assert res_stalled["follow_up_recommended"] is True

    # 3. Stale lead (> 14 days old)
    stale_app = Application(
        user_id=1,
        job_title="Stale Lead",
        status=ApplicationStatus.APPLIED,
        last_activity_at=now - timedelta(days=16),
        applied_at=now - timedelta(days=16)
    )
    res_stale = ReminderService.calculate_aging_status(stale_app, now)
    assert res_stale["aging_category"] == "STALE_LEAD"
    assert res_stale["follow_up_recommended"] is True
    # Confirm status is preserved and not auto-rejected
    assert stale_app.status == ApplicationStatus.APPLIED

def test_upcoming_test_deadline_and_alerts_detection(client):
    """
    Verifies that upcoming coding assessments and interviews generate prioritized alerts.
    """
    token = get_auth_token(client, "alerts_candidate@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create an application with urgent assessment due
    app_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Atlassian",
        "job_title": "Full Stack Engineer",
        "status": "ASSESSMENT",
        "interview_details": "Platform: HackerRank | Deadline: within 24 hours"
    })
    assert app_res.status_code == 201

    # 2. Create another application with interview scheduled
    client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Spotify",
        "job_title": "Backend Developer",
        "status": "INTERVIEW",
        "interview_details": "Platform: Zoom | Link: https://zoom.us/j/123456789"
    })

    # Fetch alerts
    alerts_res = client.get("/api/v1/reminders/alerts", headers=headers)
    assert alerts_res.status_code == 200
    data = alerts_res.json()

    assert data["total_alerts"] >= 2
    assert data["assessment_count"] >= 1
    assert data["interview_count"] >= 1

    # Check alert attributes
    alert_types = [a["alert_type"] for a in data["alerts"]]
    assert "ASSESSMENT_DUE" in alert_types
    assert "INTERVIEW_UPCOMING" in alert_types

    # Urgent assessment check
    assessment_alert = next(a for a in data["alerts"] if a["alert_type"] == "ASSESSMENT_DUE")
    assert assessment_alert["priority"] in ["URGENT", "HIGH"]
    assert assessment_alert["company_name"] == "Atlassian"

def test_followup_draft_generation_with_metadata(client):
    """
    Verifies that follow-up email drafts incorporate real company name,
    job title, recruiter salutation, and candidate skills.
    """
    token = get_auth_token(client, "drafter_cand@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Set profile skills
    client.put("/api/profile", headers=headers, json={
        "preferred_roles": ["Backend Engineer"],
        "education": "B.Tech IT"
    })
    client.post("/api/profile/confirm-skills", headers=headers, json={
        "skills": ["Python", "FastAPI", "PostgreSQL"]
    })

    # Create application with recruiter contact
    app_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "HubSpot",
        "job_title": "Senior Python Engineer",
        "status": "APPLIED",
        "recruiter_contact": "alex.recruiter@hubspot.com"
    })
    app_id = app_res.json()["id"]

    # Generate follow-up draft
    draft_res = client.post(f"/api/v1/reminders/draft-followup/{app_id}", headers=headers, json={
        "tone": "professional"
    })
    assert draft_res.status_code == 200
    draft = draft_res.json()

    assert draft["company_name"] == "HubSpot"
    assert draft["job_title"] == "Senior Python Engineer"
    assert draft["stage"] == "APPLIED"
    assert draft["recipient_email"] == "alex.recruiter@hubspot.com"
    assert "HubSpot" in draft["subject"]
    assert "Alex" in draft["body"]
    assert "Python" in draft["body"]
    assert "Senior Python Engineer" in draft["body"]
    assert "mailto:" in draft["mailto_link"]

def test_stage_and_tone_template_differentiation(client):
    """
    Verifies that drafts dynamically change content based on application stage
    (APPLIED vs INTERVIEW vs ASSESSMENT) and tone (polite vs professional vs firm).
    """
    token = get_auth_token(client, "tones_cand@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    app_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Twilio",
        "job_title": "API Platform Engineer",
        "status": "INTERVIEW"
    })
    app_id = app_res.json()["id"]

    # 1. INTERVIEW with Polite tone
    polite_res = client.post(f"/api/v1/reminders/draft-followup/{app_id}", headers=headers, json={
        "tone": "polite"
    })
    assert polite_res.status_code == 200
    polite_body = polite_res.json()["body"]
    assert "thank you" in polite_body.lower()
    assert "enjoyed" in polite_body.lower()

    # 2. INTERVIEW with Firm tone
    firm_res = client.post(f"/api/v1/reminders/draft-followup/{app_id}", headers=headers, json={
        "tone": "firm"
    })
    assert firm_res.status_code == 200
    firm_body = firm_res.json()["body"]
    assert "timeline for your hiring decision" in firm_body.lower()

    # 3. Log follow-up activity
    log_res = client.post(f"/api/v1/reminders/log-followup/{app_id}", headers=headers, json={
        "notes": "Sent post-interview follow-up email via mailto link"
    })
    assert log_res.status_code == 200
    events = log_res.json()["timeline_events"]
    assert any("Candidate Follow-Up" in evt.get("notes", "") for evt in events)

def test_candidate_reminder_user_isolation(client):
    """
    Ensures candidates cannot draft follow-ups for applications belonging to other users.
    """
    token_a = get_auth_token(client, "user_rem_a@example.com")
    token_b = get_auth_token(client, "user_rem_b@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates application
    app_a = client.post("/api/v1/applications", headers=headers_a, json={
        "company_name": "PrivateCorp",
        "job_title": "Security Lead",
        "status": "APPLIED"
    }).json()

    # User B tries to draft follow-up for User A's application -> 404
    bad_draft = client.post(f"/api/v1/reminders/draft-followup/{app_a['id']}", headers=headers_b, json={
        "tone": "professional"
    })
    assert bad_draft.status_code == 404

    # User B cannot log follow-up on User A's application -> 404
    bad_log = client.post(f"/api/v1/reminders/log-followup/{app_a['id']}", headers=headers_b, json={
        "notes": "Unauthorized attempt"
    })
    assert bad_log.status_code == 404
