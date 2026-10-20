from datetime import datetime, timezone
import pytest
from app.core.enums import ApplicationStatus, EmailCategory
from app.workers.tasks import process_incoming_email_task
from app.models.application import Application

def get_auth_token(client, email="email_spec_tester@example.com"):
    client.post("/api/auth/register", json={
        "full_name": "Email Spec Candidate",
        "email": email,
        "password": "Password123!"
    })
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    return res.json()["access_token"]

def test_inbound_email_ingest_and_celery_task_execution(client, db_session):
    """
    Verifies that POST /api/v1/emails/ingest accepts incoming recruitment emails
    and Celery worker task process_incoming_email_task processes payload asynchronously or inline.
    """
    token = get_auth_token(client, "ingest_cand@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create application for Datadog
    app_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Datadog Cloud",
        "job_title": "Distributed Systems Engineer",
        "source_platform": "Direct",
        "status": "APPLIED"
    })
    assert app_res.status_code == 201
    user_id = app_res.json()["user_id"]
    app_id = app_res.json()["id"]

    # 1. Test POST /api/v1/emails/ingest
    ingest_payload = {
        "message_id": "msg_datadog_ingest_001",
        "sender": "recruiter@datadogcloud.com",
        "subject": "Datadog Application Received: Distributed Systems Engineer",
        "body": "Thank you for applying to Datadog Cloud. We have received your application successfully.",
        "user_id": user_id,
        "date": datetime.now(timezone.utc).isoformat()
    }
    ingest_res = client.post("/api/v1/emails/ingest", json=ingest_payload)
    assert ingest_res.status_code == 202
    data = ingest_res.json()
    assert data["message_id"] == "msg_datadog_ingest_001"
    assert data["status"] in ["queued", "completed_inline"]

    # 2. Test Celery Worker Task Execution with db_session
    task_payload = {
        "message_id": "msg_datadog_worker_002",
        "sender_email": "recruiting@datadogcloud.com",
        "subject": "Interview Invitation: Distributed Systems Engineer at Datadog Cloud",
        "body_text": "We would like to schedule an interview with you. Please join via Google Meet: https://meet.google.com/xyz-abcd-efg",
        "user_id": user_id
    }
    async_res = process_incoming_email_task.apply(args=[task_payload], kwargs={"db_session": db_session})
    result = async_res.get()
    assert result["status"] == "success"
    assert result["linked_application_id"] == app_id
    assert result["detected_category"] == "INTERVIEW"
    assert result["parsed_details"]["platform"] == "Google Meet"
    assert "https://meet.google.com/xyz-abcd-efg" in result["parsed_details"]["meeting_link"]

def test_assessment_invite_parsing_and_deadline_extraction(client, db_session):
    """
    Verifies assessment invite detection, platform identification, deadline extraction,
    and automatic application advancement from APPLIED to ASSESSMENT.
    """
    token = get_auth_token(client, "assessment_cand@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Setup application in APPLIED stage
    app_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Goldman Sachs",
        "job_title": "Analyst Developer",
        "status": "APPLIED"
    })
    app_id = app_res.json()["id"]
    user_id = app_res.json()["user_id"]

    # Simulate Celery processing of HackerRank assessment
    email_data = {
        "message_id": "msg_gs_hackerrank_999",
        "sender_email": "talent@goldmansachs.com",
        "subject": "Goldman Sachs Online Assessment Invitation - Analyst Developer",
        "body_text": "Please complete your HackerRank technical assessment by deadline: 2026-11-05. Link: https://www.hackerrank.com/tests/gs-1234",
        "user_id": user_id
    }
    async_res = process_incoming_email_task.apply(args=[email_data], kwargs={"db_session": db_session})
    result = async_res.get()

    assert result["status"] == "success"
    assert result["detected_category"] == "ASSESSMENT"
    assert result["linked_application_id"] == app_id
    assert result["parsed_details"]["platform"] == "HackerRank"
    assert "2026-11-05" in result["parsed_details"]["assessment_deadline"]

    # Verify application stage was advanced to ASSESSMENT
    get_app = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_app.status_code == 200
    app_data = get_app.json()
    assert app_data["status"] == "ASSESSMENT"
    assert "HackerRank" in (app_data["interview_details"] or "")
    assert len(app_data["timeline_events"]) >= 1

def test_interview_invite_parsing_and_stage_advancement(client, db_session):
    """
    Verifies that interview invite emails extract Zoom/Google Meet links and advance stage to INTERVIEW.
    """
    token = get_auth_token(client, "interview_cand@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    app_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Snowflake",
        "job_title": "Infrastructure Engineer",
        "status": "APPLIED"
    })
    app_id = app_res.json()["id"]
    user_id = app_res.json()["user_id"]

    email_data = {
        "message_id": "msg_snowflake_zoom_888",
        "sender_email": "hiring@snowflake.com",
        "subject": "Technical Round Interview with Snowflake",
        "body_text": "You are invited to schedule an interview technical round with our team. Meeting link: https://zoom.us/j/9876543210. Complete by 2026-10-30.",
        "user_id": user_id
    }
    async_res = process_incoming_email_task.apply(args=[email_data], kwargs={"db_session": db_session})
    result = async_res.get()

    assert result["status"] == "success"
    assert result["detected_category"] == "INTERVIEW"
    assert result["linked_application_id"] == app_id
    assert result["parsed_details"]["platform"] == "Zoom"
    assert "https://zoom.us/j/9876543210" in result["parsed_details"]["meeting_link"]

    # Verify application stage updated to INTERVIEW
    get_app = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_app.status_code == 200
    assert get_app.json()["status"] == "INTERVIEW"

def test_scam_alert_email_detection(client, db_session):
    """
    Verifies that fraudulent emails demanding wire transfer, cashier's checks,
    or telegram interview redirects are categorized as SCAM_ALERT with high-risk warnings.
    """
    token = get_auth_token(client, "scam_target@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Webhook ingestion of scam email
    scam_payload = {
        "message_id": "msg_scam_wire_fee_001",
        "sender": "recruiter_hr@freemailprovider.com",
        "subject": "Urgent Job Offer: Remote Executive Assistant - Equipment Deposit Required",
        "body": "Congratulations! Please send money wire transfer for $450 equipment deposit and contact @hr_recruiter_bot on telegram for telegram interview.",
        "user_id": 1
    }
    res = client.post("/api/v1/emails/ingest", json=scam_payload)
    assert res.status_code == 202

    # Run directly via task to inspect classification result
    async_res = process_incoming_email_task.apply(args=[scam_payload], kwargs={"db_session": db_session})
    result = async_res.get()

    assert result["status"] == "success"
    assert result["detected_category"] == "SCAM_ALERT"
    details = result["parsed_details"]
    assert details["is_scam"] is True
    assert len(details["scam_indicators"]) >= 2
    assert "warning_message" in details

def test_manual_email_to_application_link(client, db_session):
    """
    Verifies candidate can manually connect an ambiguous/unmatched email to an application,
    updating application status and timeline events.
    """
    token = get_auth_token(client, "manual_link_cand@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create candidate application
    app_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Canva",
        "job_title": "Frontend Architect",
        "status": "APPLIED"
    })
    app_id = app_res.json()["id"]
    user_id = app_res.json()["user_id"]

    # 2. Ingest ambiguous email (e.g. from generic recruiting agency without Canva in domain or text)
    ambiguous_payload = {
        "message_id": "msg_ambiguous_agency_777",
        "sender": "sarah@eliteheadhunters.com",
        "subject": "Next Round Interview Invitation",
        "body": "We would like to schedule an interview with the hiring manager on Google Meet: https://meet.google.com/executive-interview",
        "user_id": user_id
    }
    async_res = process_incoming_email_task.apply(args=[ambiguous_payload], kwargs={"db_session": db_session})
    result = async_res.get()
    email_id = result["email_event_id"]

    # Email initially flagged for review with no linked application
    assert result["linked_application_id"] is None
    assert result["parsed_details"]["requires_review"] is True

    # 3. Candidate manually links the email to their Canva application
    link_res = client.post(f"/api/v1/emails/{email_id}/link-application", headers=headers, json={
        "application_id": app_id
    })
    assert link_res.status_code == 200
    linked_data = link_res.json()
    assert linked_data["id"] == email_id
    assert linked_data["application_id"] == app_id
    assert linked_data["parsed_details"]["requires_review"] is False

    # 4. Verify application stage advanced to INTERVIEW and timeline recorded
    get_app = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_app.status_code == 200
    app_data = get_app.json()
    assert app_data["status"] == "INTERVIEW"
    timeline_notes = " ".join([evt.get("notes", "") for evt in app_data["timeline_events"]])
    assert "Manually linked email" in timeline_notes

def test_candidate_email_user_isolation(client, db_session):
    """
    Ensures candidates can only view and link their own email communications.
    """
    token_a = get_auth_token(client, "user_alpha@example.com")
    token_b = get_auth_token(client, "user_beta@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates application and receives email
    app_a = client.post("/api/v1/applications", headers=headers_a, json={
        "company_name": "AlphaCorp",
        "job_title": "Security Analyst",
        "status": "APPLIED"
    }).json()

    email_a_payload = {
        "message_id": "msg_user_a_private_001",
        "sender": "hr@alphacorp.com",
        "subject": "AlphaCorp Application Confirmation",
        "body": "Thank you for applying to AlphaCorp.",
        "user_id": app_a["user_id"]
    }
    async_res = process_incoming_email_task.apply(args=[email_a_payload], kwargs={"db_session": db_session})
    email_a_id = async_res.get()["email_event_id"]

    # User A can view their email
    list_a = client.get("/api/v1/emails", headers=headers_a)
    assert list_a.status_code == 200
    assert any(item["id"] == email_a_id for item in list_a.json()["items"])

    # User B cannot see User A's email
    list_b = client.get("/api/v1/emails", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(item["id"] == email_a_id for item in list_b.json()["items"])

    # User B cannot link User A's email to their own application
    app_b = client.post("/api/v1/applications", headers=headers_b, json={
        "company_name": "BetaCorp",
        "job_title": "DevOps Engineer",
        "status": "APPLIED"
    }).json()

    bad_link = client.post(f"/api/v1/emails/{email_a_id}/link-application", headers=headers_b, json={
        "application_id": app_b["id"]
    })
    assert bad_link.status_code == 404
