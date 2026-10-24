import pytest
from unittest.mock import patch, MagicMock
import httpx
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


def test_import_job_ssrf_loopback_and_internal_hosts_rejected(client):
    """SSRF: Loopback addresses and internal docker hostnames must be rejected."""
    headers = register_and_login(client, "ssrf_loopback@example.com")

    blocked_targets = [
        "http://127.0.0.1:8000/api/health",
        "http://localhost:8000/api/health",
        "http://[::1]:8000/api/health",
        "http://0.0.0.0:8000/api/health",
        "http://postgres:5432/",
        "http://redis:6379/",
        "http://backend:8000/api/health",
    ]

    for target in blocked_targets:
        resp = client.post("/api/jobs/import-url", headers=headers, json={"url": target})
        assert resp.status_code == 400, f"Expected 400 for blocked target: {target}"
        detail = resp.json()["detail"].lower()
        assert any(term in detail for term in ("forbidden", "restricted", "private", "hostname")), f"Unexpected error detail: {detail}"


def test_import_job_ssrf_cloud_metadata_rejected(client):
    """SSRF: Cloud metadata endpoints (AWS/GCP/OpenStack) must be rejected."""
    headers = register_and_login(client, "ssrf_meta@example.com")

    metadata_targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]

    for target in metadata_targets:
        resp = client.post("/api/jobs/import-url", headers=headers, json={"url": target})
        assert resp.status_code == 400
        detail = resp.json()["detail"].lower()
        assert any(term in detail for term in ("forbidden", "restricted", "cloud metadata"))


def test_import_job_ssrf_private_networks_rejected(client):
    """SSRF: RFC 1918 private network addresses must be rejected."""
    headers = register_and_login(client, "ssrf_private@example.com")

    private_ips = [
        "http://10.0.0.1/admin",
        "http://172.16.0.10:8000/status",
        "http://192.168.1.1/router",
    ]

    for target in private_ips:
        resp = client.post("/api/jobs/import-url", headers=headers, json={"url": target})
        assert resp.status_code == 400
        assert "forbidden" in resp.json()["detail"].lower()


def test_import_job_ssrf_credentials_rejected(client):
    """SSRF: URLs containing embedded credentials must be rejected."""
    headers = register_and_login(client, "ssrf_creds@example.com")

    resp = client.post(
        "/api/jobs/import-url",
        headers=headers,
        json={"url": "http://admin:secret@example.com/careers/job"}
    )
    assert resp.status_code == 400
    assert "credentials" in resp.json()["detail"].lower()


def test_import_job_ssrf_hostname_resolving_to_private_ip(client):
    """SSRF: Public hostnames that resolve to private/internal IPs must be blocked."""
    headers = register_and_login(client, "ssrf_rebind@example.com")

    # Mock socket.getaddrinfo to simulate a domain resolving to a private IP
    mock_addr = [(2, 1, 6, '', ('10.0.0.5', 443))]
    with patch("socket.getaddrinfo", return_value=mock_addr):
        resp = client.post(
            "/api/jobs/import-url",
            headers=headers,
            json={"url": "https://malicious-internal-rebind.com/job"}
        )
        assert resp.status_code == 400
        assert "private" in resp.json()["detail"].lower() or "restricted" in resp.json()["detail"].lower()


def test_import_job_ssrf_redirect_to_private_ip_rejected(client):
    """SSRF: Redirects to private/internal addresses must be blocked."""
    headers = register_and_login(client, "ssrf_redirect@example.com")

    # Initial response is a 302 redirect to 127.0.0.1
    mock_redirect_resp = MagicMock()
    mock_redirect_resp.status_code = 302
    mock_redirect_resp.headers = {"location": "http://127.0.0.1:8000/internal-secret"}

    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
        with patch("httpx.Client.get", return_value=mock_redirect_resp):
            resp = client.post(
                "/api/jobs/import-url",
                headers=headers,
                json={"url": "https://examplecorp.com/redirect"}
            )
            assert resp.status_code == 400
            assert "forbidden" in resp.json()["detail"].lower() or "restricted" in resp.json()["detail"].lower()


def test_import_job_ssrf_oversized_response_rejected(client):
    """SSRF/DoS: Responses exceeding 2 MB must be rejected."""
    headers = register_and_login(client, "ssrf_size@example.com")

    oversized_content = b"A" * (2 * 1024 * 1024 + 1024)  # 2MB + 1KB
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.content = oversized_content
    mock_resp.text = oversized_content.decode("latin-1")

    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
        with patch("httpx.Client.get", return_value=mock_resp):
            resp = client.post(
                "/api/jobs/import-url",
                headers=headers,
                json={"url": "https://examplecorp.com/large-job"}
            )
            assert resp.status_code == 400
            assert "2 mb" in resp.json()["detail"].lower()


def test_import_job_ssrf_unsupported_content_type_rejected(client):
    """SSRF: Non-HTML content types (e.g. binary/pdf) must be rejected."""
    headers = register_and_login(client, "ssrf_content@example.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/pdf"}
    mock_resp.content = b"%PDF-1.4..."
    mock_resp.text = "%PDF-1.4..."

    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
        with patch("httpx.Client.get", return_value=mock_resp):
            resp = client.post(
                "/api/jobs/import-url",
                headers=headers,
                json={"url": "https://examplecorp.com/job.pdf"}
            )
            assert resp.status_code == 400
            assert "unsupported content type" in resp.json()["detail"].lower()


def test_import_job_ssrf_timeout_handling(client):
    """SSRF: Timeouts must return a safe error without leaking internals."""
    headers = register_and_login(client, "ssrf_timeout@example.com")

    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
        with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Read timed out")):
            resp = client.post(
                "/api/jobs/import-url",
                headers=headers,
                json={"url": "https://examplecorp.com/slow-job"}
            )
            assert resp.status_code == 400
            assert "timed out" in resp.json()["detail"].lower()

