import pytest
from app.services.verification_service import VerificationService
from app.models.job import Job

def register_and_login(client, email: str, name: str = "Candidate User") -> dict:
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


def test_verification_endpoints_unauthenticated_rejected(client):
    """Unauthenticated requests to verify and verification endpoints must be rejected with 401."""
    resp_verify = client.post("/api/jobs/1/verify")
    assert resp_verify.status_code == 401

    resp_get = client.get("/api/jobs/1/verification")
    assert resp_get.status_code == 401


def test_legitimate_corporate_job_verification(client):
    """Legitimate corporate posting on company careers portal receives LOW_RISK and verified status."""
    headers = register_and_login(client, "legit_test@example.com")

    # Create legitimate opportunity
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Senior Cloud Infrastructure Engineer",
        "company_name": "Google",
        "source_url": "https://careers.google.com/jobs/results/12345678",
        "description": "Design and build scalable cloud microservices. Experience with distributed systems and Kubernetes required."
    })
    job_id = job_resp.json()["id"]

    # Trigger verification audit
    verify_resp = client.post(f"/api/jobs/{job_id}/verify", headers=headers)
    assert verify_resp.status_code == 200
    data = verify_resp.json()

    assert data["job_id"] == job_id
    assert data["company_name"] == "Google"
    assert data["official_posting_matched"] is True
    assert data["risk_score"] <= 25.0
    assert data["risk_level"] == "LOW_RISK"
    assert data["is_verified"] is True
    assert len(data["scam_flags"]) == 0
    assert any("Official Company Careers Portal" in ep or "Careers" in ep for ep in data["evidence_points"])
    assert any("Clean" in ep for ep in data["evidence_points"])


def test_known_ats_job_verification(client):
    """Job posted through a verified enterprise ATS (Greenhouse) is corroborated with low risk."""
    headers = register_and_login(client, "ats_test@example.com")

    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Full Stack Engineer",
        "company_name": "Stripe",
        "source_url": "https://boards.greenhouse.io/stripe/jobs/456789",
        "description": "Develop payment APIs and modern dashboard interfaces using React and Python."
    })
    job_id = job_resp.json()["id"]

    verify_resp = client.post(f"/api/jobs/{job_id}/verify", headers=headers)
    assert verify_resp.status_code == 200
    data = verify_resp.json()

    assert data["official_posting_matched"] is True
    assert data["risk_score"] <= 25.0
    assert data["risk_level"] == "LOW_RISK"
    assert any("Applicant Tracking System (ATS)" in ep for ep in data["evidence_points"])


def test_scam_job_with_fee_demand(client):
    """Job demanding security deposit or application fee raises critical alerts and elevated risk score."""
    headers = register_and_login(client, "scam_fee_test@example.com")

    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Remote Data Entry Assistant",
        "company_name": "FastCash Global Services",
        "description": (
            "Immediate hiring for home-based data entry. "
            "Selected candidates must pay a refundable security deposit of $200 for laptop and software registration fee."
        )
    })
    job_id = job_resp.json()["id"]

    verify_resp = client.post(f"/api/jobs/{job_id}/verify", headers=headers)
    assert verify_resp.status_code == 200
    data = verify_resp.json()

    assert data["is_verified"] is False
    assert data["risk_score"] >= 60.0
    assert data["risk_level"] in ("HIGH_RISK", "CRITICAL_RISK")
    assert len(data["scam_flags"]) >= 1

    # Check evidence points and scam flags
    flags_text = " ".join(data["scam_flags"]).lower()
    assert "deposit" in flags_text or "fee" in flags_text
    assert any("CRITICAL ALERT" in ep for ep in data["evidence_points"])


def test_scam_job_with_telegram_interview_and_shortener(client):
    """Job with bit.ly link and Telegram interview references triggers multiple scam heuristics."""
    headers = register_and_login(client, "telegram_scam_test@example.com")

    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Online Typing Assistant",
        "company_name": "Global Work Solutions",
        "source_url": "https://bit.ly/secret-job-application-form",
        "description": "Earn $50/hour. Interviews are conducted exclusively via Telegram. Contact @recruiter_online on Telegram."
    })
    job_id = job_resp.json()["id"]

    verify_resp = client.post(f"/api/jobs/{job_id}/verify", headers=headers)
    assert verify_resp.status_code == 200
    data = verify_resp.json()

    assert data["is_verified"] is False
    assert data["risk_score"] >= 75.0
    assert data["risk_level"] == "CRITICAL_RISK"
    assert len(data["scam_flags"]) >= 2

    flags_text = " ".join(data["scam_flags"]).lower()
    assert "generic form or shortener" in flags_text
    assert "messaging app" in flags_text or "telegram" in flags_text


def test_free_email_recruiter_domain_heuristic(db_session):
    """Free public email provider used for enterprise recruitment triggers scam flag and risk penalty."""
    job = Job(
        title="Software Engineer",
        company_name="MegaEnterprise Corp",
        description="Standard enterprise engineering role with Python and SQL."
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    result = VerificationService.audit_job_legitimacy(
        db=db_session,
        job=job,
        recruiter_email_or_domain="hiring.megaenterprise@gmail.com"
    )

    assert result.is_verified is False
    assert result.risk_score >= 50.0
    flags_text = " ".join(result.scam_flags).lower()
    assert "public email domain" in flags_text
    assert any("Free/disposable email provider" in ep for ep in result.evidence_points)


def test_get_job_verification_endpoint(client):
    """GET /api/jobs/{job_id}/verification returns latest audit report with evidence signals."""
    headers = register_and_login(client, "get_verify_test@example.com")

    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Frontend React Developer",
        "company_name": "Vercel",
        "source_url": "https://vercel.com/careers/frontend-engineer",
        "description": "Build high-performance web applications with Next.js and React."
    })
    job_id = job_resp.json()["id"]

    get_resp = client.get(f"/api/jobs/{job_id}/verification", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["job_id"] == job_id
    assert data["company_name"] == "Vercel"
    assert "risk_score" in data
    assert "risk_level" in data
    assert "evidence_points" in data
    assert len(data["evidence_points"]) > 0
