import pytest
from app.core.enums import ApplicationStatus

def register_and_login(client, email: str, name: str = "Tracking Candidate") -> dict:
    """Helper to register user, log in, and return Authorization headers"""
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!",
            "full_name": name
        }
    )
    login_resp = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "StrongPassword123!"
        }
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_direct_job_tracking_and_company_autolink(client):
    """Tracking a discovered job automatically associates company and creates pipeline application."""
    headers = register_and_login(client, "tracker_user1@example.com")

    # 1. Create a discovered job
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Backend Distributed Systems Engineer",
        "company_name": "CloudScale Systems",
        "location": "Bengaluru",
        "work_mode": "Hybrid",
        "source_platform": "LinkedIn"
    })
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 2. Track into pipeline via /api/jobs/{job_id}/apply
    track_resp = client.post(f"/api/jobs/{job_id}/apply", headers=headers, json={
        "notes": "Applied via referral link from LinkedIn connection.",
        "recruiter_contact": "recruiter@cloudscale.io",
        "resume_version": "v2_backend_systems"
    })
    assert track_resp.status_code == 201
    app_data = track_resp.json()

    assert app_data["job_id"] == job_id
    assert app_data["job_title"] == "Backend Distributed Systems Engineer"
    assert app_data["company"]["name"] == "CloudScale Systems"
    assert app_data["status"] == "APPLIED"
    assert app_data["notes"] == "Applied via referral link from LinkedIn connection."
    assert app_data["recruiter_contact"] == "recruiter@cloudscale.io"
    assert app_data["resume_version"] == "v2_backend_systems"
    assert len(app_data["timeline_events"]) == 1
    assert app_data["timeline_events"][0]["stage"] == "APPLIED"


def test_duplicate_application_detection(client):
    """Submitting duplicate application for the same job or same company and title returns 409 Conflict."""
    headers = register_and_login(client, "duplicate_tester@example.com")

    # Create job
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Site Reliability Engineer",
        "company_name": "InfraCore Networks",
        "source_platform": "Direct"
    })
    job_id = job_resp.json()["id"]

    # First apply succeeds
    first_apply = client.post(f"/api/jobs/{job_id}/apply", headers=headers)
    assert first_apply.status_code == 201

    # Second apply to same job fails with 409
    dup_apply = client.post(f"/api/jobs/{job_id}/apply", headers=headers)
    assert dup_apply.status_code == 409
    assert "already have an active application" in dup_apply.json()["detail"].lower()


def test_reapply_after_rejection_allowed(client):
    """Verifies that a candidate can reapply for a role after a previous application was REJECTED."""
    headers = register_and_login(client, "reapply_user@example.com")

    # 1. Create initial application
    first_app = client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Platform Security Engineer",
        "company_name": "SecureCorp",
        "status": "APPLIED"
    })
    assert first_app.status_code == 201
    app_id = first_app.json()["id"]

    # 2. Duplicate while active returns 409
    dup_app = client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Platform Security Engineer",
        "company_name": "SecureCorp",
        "status": "APPLIED"
    })
    assert dup_app.status_code == 409

    # 3. Transition first application to REJECTED
    client.patch(f"/api/v1/applications/{app_id}/stage", headers=headers, json={
        "status": "REJECTED",
        "notes": "Position closed for current quarter"
    })

    # 4. Re-applying after rejection succeeds with 201
    reapply_res = client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Platform Security Engineer",
        "company_name": "SecureCorp",
        "status": "APPLIED",
        "notes": "Re-applying for new opening in next cycle"
    })
    assert reapply_res.status_code == 201
    assert reapply_res.json()["id"] != app_id

    # 5. Applying again while the new application is active returns 409
    dup_reapply = client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Platform Security Engineer",
        "company_name": "SecureCorp",
        "status": "APPLIED"
    })
    assert dup_reapply.status_code == 409


def test_stage_transition_lifecycle_and_history(client):
    """Advancing application through pipeline stages logs timeline history and updates last_activity_at."""
    headers = register_and_login(client, "lifecycle_user@example.com")

    # 1. Create initial application in DRAFT
    create_resp = client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Frontend Architect",
        "company_name": "DesignCraft UI",
        "source_platform": "Naukri",
        "status": "DRAFT",
        "notes": "Drafting personalized cover letter"
    })
    assert create_resp.status_code == 201
    app_id = create_resp.json()["id"]

    # 2. Transition DRAFT -> APPLIED
    applied_resp = client.patch(f"/api/v1/applications/{app_id}/stage", headers=headers, json={
        "status": "APPLIED",
        "notes": "Submitted official application via company careers portal"
    })
    assert applied_resp.status_code == 200
    assert applied_resp.json()["status"] == "APPLIED"

    # 3. Transition APPLIED -> ASSESSMENT
    assess_resp = client.patch(f"/api/v1/applications/{app_id}/stage", headers=headers, json={
        "status": "ASSESSMENT",
        "notes": "Received HackerRank test link. Due Friday."
    })
    assert assess_resp.status_code == 200
    assert assess_resp.json()["status"] == "ASSESSMENT"

    # 4. Transition ASSESSMENT -> INTERVIEW
    interview_resp = client.patch(f"/api/v1/applications/{app_id}/stage", headers=headers, json={
        "status": "INTERVIEW",
        "notes": "Passed assessment! Scheduled technical system design round."
    })
    assert interview_resp.status_code == 200
    data = interview_resp.json()
    assert data["status"] == "INTERVIEW"

    # Verify timeline events history
    events = data["timeline_events"]
    assert len(events) >= 4
    stages_logged = [e["stage"] for e in events]
    assert "DRAFT" in stages_logged
    assert "APPLIED" in stages_logged
    assert "ASSESSMENT" in stages_logged
    assert "INTERVIEW" in stages_logged


def test_application_notes_and_contact_updates(client):
    """Candidate can update recruiter contact, interview platform link, and notes."""
    headers = register_and_login(client, "notes_tester@example.com")

    create_resp = client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Machine Learning Engineer",
        "company_name": "NeuroAI Labs",
        "status": "APPLIED"
    })
    app_id = create_resp.json()["id"]

    # Update contact and interview details
    update_resp = client.patch(f"/api/v1/applications/{app_id}", headers=headers, json={
        "recruiter_contact": "hr.lead@neuroai.com",
        "interview_details": "Google Meet: https://meet.google.com/abc-defg-hij",
        "resume_version": "v3_ml_pytorch",
        "notes": "Reviewed PyTorch transformer architectures prior to interview"
    })
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["recruiter_contact"] == "hr.lead@neuroai.com"
    assert updated["interview_details"] == "Google Meet: https://meet.google.com/abc-defg-hij"
    assert updated["resume_version"] == "v3_ml_pytorch"
    assert "PyTorch" in updated["notes"]


def test_pipeline_metrics_calculation(client):
    """GET /api/v1/applications/metrics calculates correct breakdown of stages and tasks."""
    headers = register_and_login(client, "metrics_tester@example.com")

    # Create 1 APPLIED, 2 ASSESSMENT, 1 INTERVIEW, 1 OFFER
    client.post("/api/v1/applications", headers=headers, json={
        "job_title": "DevOps Engineer", "company_name": "K8s Cloud", "status": "APPLIED"
    })
    client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Security Analyst", "company_name": "Securita Inc", "status": "ASSESSMENT"
    })
    client.post("/api/v1/applications", headers=headers, json={
        "job_title": "QA Lead", "company_name": "TestLab", "status": "ASSESSMENT"
    })
    client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Data Engineer", "company_name": "DataWorks", "status": "INTERVIEW"
    })
    client.post("/api/v1/applications", headers=headers, json={
        "job_title": "Senior Go Developer", "company_name": "FastGolang", "status": "OFFER"
    })

    metrics_resp = client.get("/api/v1/applications/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()

    assert metrics["total_applications"] == 5
    assert metrics["applied_count"] == 1
    assert metrics["assessment_count"] == 2
    assert metrics["interview_count"] == 1
    assert metrics["offer_count"] == 1
    assert metrics["active_interviews"] == 1
    assert metrics["tests_due"] == 2


def test_candidate_user_isolation(client):
    """Candidates cannot view, edit, or delete another candidate's pipeline applications."""
    user1_headers = register_and_login(client, "iso_user1@example.com")
    user2_headers = register_and_login(client, "iso_user2@example.com")

    # User 1 creates an application
    create_resp = client.post("/api/v1/applications", headers=user1_headers, json={
        "job_title": "Private Role",
        "company_name": "Confidential Corp",
        "status": "APPLIED"
    })
    app_id = create_resp.json()["id"]

    # User 2 attempts to read it -> 404
    get_resp = client.get(f"/api/v1/applications/{app_id}", headers=user2_headers)
    assert get_resp.status_code == 404

    # User 2 attempts to update stage -> 404
    patch_resp = client.patch(f"/api/v1/applications/{app_id}/stage", headers=user2_headers, json={
        "status": "OFFER"
    })
    assert patch_resp.status_code == 404

    # User 2 attempts to delete -> 404
    del_resp = client.delete(f"/api/v1/applications/{app_id}", headers=user2_headers)
    assert del_resp.status_code == 404
