import io
from datetime import datetime, timezone, timedelta
import pytest
from app.core.config import Settings
from app.models.application import Application
from app.core.enums import ApplicationStatus

SAMPLE_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 85 >>
stream
BT
/F1 12 Tf
100 700 Td
(Principal Full-Stack Engineer skilled in Python, FastAPI, PostgreSQL, Docker, and React.) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000379 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
456
%%EOF
"""

def register_user(client, email: str, name: str = "Lifecycle Candidate"):
    client.post("/api/auth/register", json={
        "full_name": name,
        "email": email,
        "password": "Password123!"
    })
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert res.status_code == 200
    return res.json()["access_token"]


def test_complete_candidate_lifecycle_end_to_end(client, db_session):
    """
    Phase 11 End-to-End System Smoke Test:
    Executes complete end-to-end user journey across all integrated subsystems:
    1. Register user & authenticate
    2. Configure candidate profile
    3. Upload & parse resume PDF, confirm extracted technical skills
    4. Discover corporate job posting
    5. Run company & job verification signal audit
    6. Compute transparent explainable match breakdown
    7. Track discovered opportunity into active Kanban pipeline
    8. Ingest recruitment communication email
    9. Detect application aging / action alerts and draft stage-aware follow-up
    10. Log follow-up outreach into application timeline
    """
    email = "lifecycle_principal@example.com"
    token = register_user(client, email, "Alice Engineer")
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Verify current authenticated user
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_id = me_res.json()["id"]
    assert me_res.json()["email"] == email

    # Step 2: Initialize & update candidate profile
    profile_update = {
        "education": "M.S. in Computer Science",
        "experience_level": "Senior",
        "experience_years": 6.0,
        "preferred_roles": ["Principal Engineer", "Senior Backend Engineer"],
        "preferred_locations": "Remote, San Francisco",
        "preferred_work_mode": "Remote",
        "salary_expectation": "$185,000"
    }
    prof_res = client.put("/api/profile", headers=headers, json=profile_update)
    assert prof_res.status_code == 200
    assert prof_res.json()["education"] == "M.S. in Computer Science"

    # Step 3: Upload resume PDF & parse skills
    pdf_file = ("alice_resume.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")
    upload_res = client.post(
        "/api/profile/resume",
        headers=headers,
        files={"file": pdf_file}
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "Python" in upload_data["extracted_skills"] or len(upload_data["extracted_skills"]) > 0

    # Confirm approved skills
    confirm_res = client.post(
        "/api/profile/confirm-skills",
        headers=headers,
        json={
            "skills": [
                {"skill_name": "Python", "proficiency_level": "Expert"},
                {"skill_name": "FastAPI", "proficiency_level": "Advanced"},
                {"skill_name": "PostgreSQL", "proficiency_level": "Advanced"},
                {"skill_name": "React", "proficiency_level": "Advanced"}
            ]
        }
    )
    assert confirm_res.status_code == 200
    saved_skills = [s["skill_name"] for s in confirm_res.json()["skills"]]
    assert "Python" in saved_skills

    # Step 4: Discover & store job record
    job_payload = {
        "title": "Principal Backend Architect",
        "company_name": "Stripe Payments",
        "location": "San Francisco, CA",
        "work_mode": "Remote",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "Kubernetes"],
        "experience_years_required": 5,
        "description": "Architect high-throughput payment infrastructure with Python, FastAPI, and PostgreSQL."
    }
    job_res = client.post("/api/jobs", headers=headers, json=job_payload)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Step 5: Run evidence-based verification signals check
    verify_res = client.post(f"/api/jobs/{job_id}/verify", headers=headers)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert "signals" in verify_data or "domain_valid" in verify_data or "evidence" in verify_data

    # Step 6: Run explainable delta match
    match_res = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_res.status_code == 200
    match_data = match_res.json()
    assert match_data["match_score"] > 70
    assert "Python" in match_data["matched_skills"]

    # Step 7: Apply and track job into active pipeline
    apply_res = client.post(
        f"/api/jobs/{job_id}/apply",
        headers=headers,
        json={"notes": "Applied with confirmed senior profile"}
    )
    assert apply_res.status_code == 201
    app_id = apply_res.json()["id"]
    assert apply_res.json()["status"] == "APPLIED"

    # Step 8: Ingest recruitment communication email
    email_payload = {
        "message_id": "msg_stripe_e2e_999",
        "sender": "talent@stripe.com",
        "subject": "Interview Scheduling: Principal Backend Architect at Stripe Payments",
        "body": "Hi Alice, we reviewed your application and would like to schedule a technical round via Google Meet: https://meet.google.com/stripe-eng-interview",
        "user_id": user_id,
        "date": datetime.now(timezone.utc).isoformat()
    }
    email_res = client.post("/api/v1/emails/ingest", headers=headers, json=email_payload)
    assert email_res.status_code == 202

    # Step 9: Verify reminder alert generation & draft follow-up
    # Artificially age the application to trigger a follow-up alert
    app_record = db_session.get(Application, app_id)
    now = datetime.now(timezone.utc)
    app_record.last_activity_at = now - timedelta(days=6)
    app_record.applied_at = now - timedelta(days=6)
    db_session.commit()

    alerts_res = client.get("/api/v1/reminders/alerts", headers=headers)
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    assert alerts_data["total_alerts"] >= 1

    # Generate customizable follow-up email draft (Strict candidate consent: no auto-send)
    draft_res = client.post(
        f"/api/v1/reminders/draft-followup/{app_id}",
        headers=headers,
        json={"tone": "professional"}
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert "Stripe Payments" in draft_data["company_name"]
    assert "Principal Backend Architect" in draft_data["job_title"]
    assert "mailto:" in draft_data["mailto_link"]
    assert len(draft_data["body"]) > 50

    # Step 10: Log follow-up outreach note in application timeline
    log_res = client.post(
        f"/api/v1/reminders/log-followup/{app_id}",
        headers=headers,
        json={"notes": "Follow-up email dispatched via candidate's client"}
    )
    assert log_res.status_code == 200
    log_data = log_res.json()
    assert log_data["id"] == app_id
    assert len(log_data["timeline_events"]) > 0


def test_cross_candidate_data_isolation(client, db_session):
    """
    Security Audit: Verifies that Candidate B cannot access, read, or modify
    Candidate A's profile, applications, or reminder follow-up drafts.
    """
    # Candidate A setup
    token_a = register_user(client, "alice_isolated@example.com", "Alice")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    app_a = client.post("/api/v1/applications", headers=headers_a, json={
        "company_name": "Private Alpha Corp",
        "job_title": "Staff Engineer",
        "source_platform": "Direct",
        "status": "APPLIED"
    })
    assert app_a.status_code == 201
    app_a_id = app_a.json()["id"]

    # Candidate B setup
    token_b = register_user(client, "bob_isolated@example.com", "Bob")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Candidate B cannot view Candidate A's application details
    get_res = client.get(f"/api/v1/applications/{app_a_id}", headers=headers_b)
    assert get_res.status_code in [403, 404]

    # 2. Candidate B cannot draft follow-up for Candidate A's application
    draft_res = client.post(
        f"/api/v1/reminders/draft-followup/{app_a_id}",
        headers=headers_b,
        json={"tone": "polite"}
    )
    assert draft_res.status_code in [403, 404]

    # 3. Candidate B cannot modify Candidate A's application stage
    stage_res = client.patch(
        f"/api/v1/applications/{app_a_id}/stage",
        headers=headers_b,
        json={"status": "INTERVIEW"}
    )
    assert stage_res.status_code in [403, 404]


def test_production_security_hardening_validation():
    """
    Security Audit: Verifies that in production mode, default or placeholder
    SECRET_KEY and default database credentials raise a critical ValueError on startup.
    """
    # Default placeholder key should raise ValueError in production
    with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="temporary_secret_key_change_in_production_min_32_characters",
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg2://ujs_prod:P@ssw0rd99!@db.internal:5432/ujs"
        )

    # Docker-compose 60-char placeholder must be rejected
    with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="generate_a_cryptographically_secure_random_key_min_32_characters",
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg2://ujs_prod:P@ssw0rd99!@db.internal:5432/ujs"
        )

    # Short key (< 32 chars) should raise ValueError in production
    with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short_key_12345",
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg2://ujs_prod:P@ssw0rd99!@db.internal:5432/ujs"
        )

    # Default postgres:postgres credentials must raise ValueError in production
    with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a_very_secure_cryptographic_random_string_over_32_characters_long!",
            DEBUG=False,
            DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/unified_job_search"
        )

    # Valid 32+ char key with strong DB credentials and DEBUG=False should succeed in production
    prod_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a_very_secure_cryptographic_random_string_over_32_characters_long!",
        DEBUG=False,
        DATABASE_URL="postgresql+psycopg2://ujs_prod_user:StrongRandomProductionPassword2026!@prod-db.internal:5432/ujs_prod"
    )
    assert prod_settings.ENVIRONMENT == "production"
    assert prod_settings.DEBUG is False
