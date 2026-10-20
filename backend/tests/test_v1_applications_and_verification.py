from datetime import datetime, timezone
import pytest
from app.core.enums import ApplicationStatus, EmailCategory
from app.models.application import Application
from app.models.company import Company
from app.workers.tasks import process_incoming_email_task

def get_auth_token(client, email="test_architect@example.com"):
    client.post("/api/auth/register", json={
        "full_name": "Architect Tester",
        "email": email,
        "password": "Password123!"
    })
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    return res.json()["access_token"]

def test_create_and_list_applications(client):
    token = get_auth_token(client, "candidate_app@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Application
    create_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Stripe",
        "job_title": "Backend Software Engineer",
        "job_description": "Building scalable payment infrastructure",
        "source_platform": "LinkedIn",
        "source_url": "https://stripe.com/jobs/backend-1",
        "status": "APPLIED"
    })
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["job_title"] == "Backend Software Engineer"
    assert data["status"] == "APPLIED"
    assert data["company"]["name"] == "Stripe"
    app_id = data["id"]

    # 2. Duplicate Application Prevention (409 Conflict)
    dup_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Stripe",
        "job_title": "Backend Software Engineer",
        "source_platform": "Indeed"
    })
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"].lower()

    # 3. Create Second Application with different status & platform
    client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Google",
        "job_title": "Site Reliability Engineer",
        "source_platform": "CareersPortal",
        "status": "DRAFT"
    })

    # 4. List Applications without filter
    list_res = client.get("/api/v1/applications", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 2
    assert len(list_data["items"]) >= 2

    # 5. List with Status filter
    filtered_status = client.get("/api/v1/applications?status=APPLIED", headers=headers).json()
    assert all(item["status"] == "APPLIED" for item in filtered_status["items"])

    # 6. List with Platform filter
    filtered_platform = client.get("/api/v1/applications?platform=LinkedIn", headers=headers).json()
    assert all(item["source_platform"] == "LinkedIn" for item in filtered_platform["items"])

    # 7. Get single application
    single_res = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert single_res.status_code == 200
    assert single_res.json()["id"] == app_id

    # 8. Update stage to INTERVIEW
    stage_res = client.patch(f"/api/v1/applications/{app_id}/stage", headers=headers, json={
        "status": "INTERVIEW",
        "notes": "Invited for Round 1 Technical Interview"
    })
    assert stage_res.status_code == 200
    assert stage_res.json()["status"] == "INTERVIEW"

    # 9. Delete application
    del_res = client.delete(f"/api/v1/applications/{app_id}", headers=headers)
    assert del_res.status_code == 204

    # Confirm deletion
    get_del = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_del.status_code == 404

def test_verification_endpoint(client):
    token = get_auth_token(client, "verify_tester@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Case A: Legitimate Official Employer
    good_res = client.post("/api/v1/verify", headers=headers, json={
        "company_name": "Microsoft",
        "job_url": "https://careers.microsoft.com/us/en/job/123456",
        "recruiter_domain": "microsoft.com"
    })
    assert good_res.status_code == 200
    good_data = good_res.json()
    assert good_data["company_name"] == "Microsoft"
    assert good_data["official_posting_matched"] is True
    assert good_data["fraud_score"] <= 35.0

    # Case B: High-Risk Phishing / Scam Flags
    bad_res = client.post("/api/v1/verify", headers=headers, json={
        "company_name": "Acme Global Financial",
        "job_url": "https://forms.gle/suspiciousJobApplicationForm",
        "recruiter_domain": "gmail.com"
    })
    assert bad_res.status_code == 200
    bad_data = bad_res.json()
    assert bad_data["is_verified"] is False
    assert bad_data["fraud_score"] >= 60.0
    assert len(bad_data["scam_flags"]) >= 2
    # Verify scam flags caught public email and form shortener
    flag_text = " ".join(bad_data["scam_flags"]).lower()
    assert "public email domain" in flag_text
    assert "generic form" in flag_text

def test_email_webhook_and_celery_task(client, db_session):
    token = get_auth_token(client, "email_tester@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create an application first so email can resolve to it
    app_res = client.post("/api/v1/applications", headers=headers, json={
        "company_name": "Datadog",
        "job_title": "Software Engineer",
        "source_platform": "Direct",
        "status": "APPLIED"
    })
    app_id = app_res.json()["id"]

    # 1. Test Webhook Ingestion API
    webhook_res = client.post("/api/v1/emails/webhook", json={
        "message_id": "msg_datadog_interview_101",
        "sender_email": "recruiting@datadog.com",
        "subject": "Interview Invitation: Software Engineer at Datadog",
        "body_text": "We would like to schedule an interview technical round with you next week.",
        "user_id": app_res.json()["user_id"],
    })
    assert webhook_res.status_code == 202
    wb_data = webhook_res.json()
    assert wb_data["message_id"] == "msg_datadog_interview_101"

    # 2. Test Celery Task directly (simulating worker execution with db_session)
    task_payload = {
        "message_id": "msg_datadog_interview_102",
        "sender_email": "recruiter@datadog.com",
        "subject": "Technical Round Interview with Datadog",
        "body_text": "Please choose your interview invitation slot using the portal link.",
        "user_id": app_res.json()["user_id"],
    }
    async_res = process_incoming_email_task.apply(args=[task_payload], kwargs={"db_session": db_session})
    result = async_res.get()
    assert result["status"] == "success"
    assert result["linked_application_id"] == app_id
    assert result["detected_category"] == "INTERVIEW"

