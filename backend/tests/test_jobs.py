import pytest
from unittest.mock import patch, MagicMock
from app.core.security import create_access_token

MOCK_JOB_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Senior Backend Engineer - Example Corp Careers</title>
    <meta property="og:title" content="Senior Backend Engineer at Example Corp" />
    <meta property="og:site_name" content="Example Corp" />
    <script type="application/ld+json">
    {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": "Senior Backend Engineer",
        "hiringOrganization": {
            "@type": "Organization",
            "name": "Example Corp"
        },
        "description": "We are seeking a Backend Engineer with deep knowledge of Python, FastAPI, Docker, and PostgreSQL. Experience with Redis and AWS is a plus.",
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Bengaluru",
                "addressRegion": "Karnataka",
                "addressCountry": "India"
            }
        }
    }
    </script>
</head>
<body>
    <h1>Senior Backend Engineer</h1>
</body>
</html>
"""

def register_and_login(client, email: str, name: str = "Candidate User") -> dict:
    """Helper to register user and obtain Authorization header"""
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


def test_create_job_unauthenticated_rejected(client):
    """Unauthenticated requests to create a job must be rejected with 401."""
    response = client.post("/api/jobs", json={
        "title": "Software Engineer",
        "company_name": "Acme Corp"
    })
    assert response.status_code == 401


def test_create_job_manual_success(client):
    """Authenticated user can create a job manually with auto company and skill extraction."""
    headers = register_and_login(client, "recruiter_test@example.com")

    payload = {
        "title": "Full Stack Developer",
        "company_name": "Innovatech Solutions",
        "description": "Build high-scale web apps using Python, React, PostgreSQL, and Docker.",
        "location": "Bengaluru, India",
        "work_mode": "Hybrid",
        "salary_range": "10 - 15 LPA",
        "experience_years_required": 2.0,
        "experience_level": "Mid-Level",
        "source_platform": "Manual"
    }

    response = client.post("/api/jobs", headers=headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Full Stack Developer"
    assert data["company_name"] == "Innovatech Solutions"
    assert data["company_id"] is not None
    assert data["work_mode"] == "Hybrid"
    assert data["location"] == "Bengaluru, India"
    assert "Python" in data["required_skills"]
    assert "React" in data["required_skills"]
    assert "Docker" in data["required_skills"]


def test_list_jobs_and_search_filtering(client):
    """Can list jobs and filter by keyword, location, work mode, and skills."""
    headers = register_and_login(client, "lister@example.com")

    # Seed 3 distinct jobs
    client.post("/api/jobs", headers=headers, json={
        "title": "Python Backend Engineer",
        "company_name": "PyCorp",
        "description": "FastAPI, PostgreSQL and Redis expert needed.",
        "location": "Hyderabad",
        "work_mode": "Remote",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"]
    })
    client.post("/api/jobs", headers=headers, json={
        "title": "Frontend React Specialist",
        "company_name": "WebFlow",
        "description": "React and TypeScript engineer.",
        "location": "Bengaluru",
        "work_mode": "On-site",
        "required_skills": ["React", "TypeScript"]
    })
    client.post("/api/jobs", headers=headers, json={
        "title": "DevOps Engineer",
        "company_name": "CloudOps",
        "description": "Kubernetes and Docker platform.",
        "location": "Pune",
        "work_mode": "Hybrid",
        "required_skills": ["Docker", "Kubernetes"]
    })

    # 1. Search by keyword
    search_resp = client.get("/api/jobs?q=Frontend")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert any(j["title"] == "Frontend React Specialist" for j in search_data["jobs"])

    # 2. Filter by location
    loc_resp = client.get("/api/jobs?location=Hyderabad")
    assert loc_resp.status_code == 200
    assert any(j["location"] == "Hyderabad" for j in loc_resp.json()["jobs"])

    # 3. Filter by work mode
    wm_resp = client.get("/api/jobs?work_mode=Remote")
    assert wm_resp.status_code == 200
    assert all(j["work_mode"] == "Remote" for j in wm_resp.json()["jobs"])

    # 4. Filter by skill
    skill_resp = client.get("/api/jobs?skill=Kubernetes")
    assert skill_resp.status_code == 200
    assert any("Kubernetes" in j["required_skills"] for j in skill_resp.json()["jobs"])

    # 5. Pagination
    page_resp = client.get("/api/jobs?skip=0&limit=1")
    assert page_resp.status_code == 200
    assert len(page_resp.json()["jobs"]) == 1
    assert page_resp.json()["total"] >= 3


def test_get_job_by_id_and_not_found(client):
    """Can retrieve a job by ID and handles 404 for nonexistent jobs."""
    headers = register_and_login(client, "getter@example.com")

    create_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Data Analyst",
        "company_name": "DataGen",
        "description": "SQL and Python for data pipelines."
    })
    job_id = create_resp.json()["id"]

    # Valid get
    get_resp = client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Junior Data Analyst"

    # Nonexistent get
    nf_resp = client.get("/api/jobs/999999")
    assert nf_resp.status_code == 404
    assert "not found" in nf_resp.json()["detail"].lower()


def test_update_and_delete_job(client):
    """Can update job fields and deactivate job."""
    headers = register_and_login(client, "updater@example.com")

    create_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Cloud Architect",
        "company_name": "SkyTech",
        "salary_range": "20 - 25 LPA"
    })
    job_id = create_resp.json()["id"]

    # Update job
    update_resp = client.put(f"/api/jobs/{job_id}", headers=headers, json={
        "salary_range": "25 - 30 LPA",
        "work_mode": "Remote"
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["salary_range"] == "25 - 30 LPA"
    assert update_resp.json()["work_mode"] == "Remote"

    # Delete (deactivate) job
    del_resp = client.delete(f"/api/jobs/{job_id}", headers=headers)
    assert del_resp.status_code == 200

    # Verify inactive job doesn't appear in default list
    list_resp = client.get("/api/jobs")
    active_ids = [j["id"] for j in list_resp.json()["jobs"]]
    assert job_id not in active_ids


def test_import_job_from_url_success(client):
    """Can import job details from a mock HTTP job posting URL."""
    headers = register_and_login(client, "importer@example.com")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = MOCK_JOB_HTML

    with patch("httpx.Client.get", return_value=mock_response):
        import_resp = client.post(
            "/api/jobs/import-url",
            headers=headers,
            json={"url": "https://examplecorp.com/careers/senior-backend-engineer"}
        )
        assert import_resp.status_code == 201
        data = import_resp.json()
        assert data["title"] == "Senior Backend Engineer"
        assert data["company_name"] == "Example Corp"
        assert "Bengaluru" in data["location"]
        assert "Python" in data["required_skills"]
        assert "FastAPI" in data["required_skills"]
        assert "Docker" in data["required_skills"]
        assert "PostgreSQL" in data["required_skills"]
        assert data["source_platform"] == "Careers Portal"


def test_import_job_invalid_url_rejected(client):
    """Invalid URL formats must be rejected with 400 Bad Request."""
    headers = register_and_login(client, "bad_url@example.com")

    response = client.post(
        "/api/jobs/import-url",
        headers=headers,
        json={"url": "ftp://not-a-web-url.com/job"}
    )
    assert response.status_code == 400
    assert "must start with http" in response.json()["detail"].lower()
