import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi import status
from sqlalchemy import select, func

from app.models.job import Job
from app.models.company import Company
from app.services.job_sources.remoteok_adapter import RemoteOKAdapter
from app.services.job_sources.jobicy_adapter import JobicyAdapter
from app.services.job_ingestion_service import JobIngestionService, normalize_job_url
from app.services.job_service import list_jobs
from app.workers.tasks import orchestrate_job_ingestion_task


# =========================================================
# 1. Adapter Normalization Tests
# =========================================================

def test_remoteok_adapter_normalization_success():
    adapter = RemoteOKAdapter()
    raw = {
        "id": "987654",
        "position": "Senior Backend Python / FastAPI Engineer",
        "company": "CloudScale Systems",
        "description": "<p>We are seeking a <b>Senior Engineer</b> with strong FastAPI, PostgreSQL, and Docker skills.</p>",
        "tags": ["python", "fastapi", "docker", "postgres", "remote"],
        "location": "Worldwide",
        "salary_min": 110000,
        "salary_max": 150000,
        "url": "https://remoteok.com/remote-jobs/987654-senior-backend-engineer",
        "date": "2026-10-25T12:00:00Z"
    }

    norm = adapter.normalize_listing(raw)
    assert norm is not None
    assert norm["title"] == "Senior Backend Python / FastAPI Engineer"
    assert norm["company_name"] == "CloudScale Systems"
    assert norm["source_platform"] == "RemoteOK"
    assert norm["external_id"] == "987654"
    assert norm["work_mode"] == "Remote"
    assert norm["employment_type"] == "Full-time"
    assert norm["salary_min"] == 110000.0
    assert norm["salary_max"] == 150000.0
    assert "$110,000 - $150,000 USD" in norm["salary_range"]
    assert "fastapi" in norm["required_skills"]
    assert "docker" in norm["required_skills"]
    assert "<p>" not in norm["description"]  # HTML stripped


def test_remoteok_adapter_skips_legal_and_empty_rows():
    adapter = RemoteOKAdapter()

    # Metadata header object without position
    assert adapter.normalize_listing({"legal": "Notice..."}) is None

    # Empty position or company
    assert adapter.normalize_listing({"position": "", "company": "Acme"}) is None
    assert adapter.normalize_listing({"position": "Dev", "company": ""}) is None


def test_jobicy_adapter_normalization_success():
    adapter = JobicyAdapter()
    raw = {
        "id": 54321,
        "jobTitle": "Lead Full Stack Developer (React / Python)",
        "companyName": "Nexus Innovations",
        "jobDescription": "<div>Build cutting-edge applications with React, TypeScript, and Python.</div>",
        "jobType": ["contract"],
        "jobGeo": "USA, Canada, Remote",
        "jobLevel": "Senior",
        "annualSalaryMin": 95000,
        "annualSalaryMax": 130000,
        "salaryCurrency": "USD",
        "url": "https://jobicy.com/jobs/54321-lead-full-stack",
        "pubDate": "2026-10-26 14:00:00"
    }

    norm = adapter.normalize_listing(raw)
    assert norm is not None
    assert norm["title"] == "Lead Full Stack Developer (React / Python)"
    assert norm["company_name"] == "Nexus Innovations"
    assert norm["source_platform"] == "Jobicy"
    assert norm["external_id"] == "54321"
    assert norm["employment_type"] == "Contract"
    assert norm["work_mode"] == "Remote"
    assert norm["salary_min"] == 95000.0
    assert norm["salary_max"] == 130000.0
    assert "react" in norm["required_skills"]


def test_jobicy_adapter_handles_missing_fields_gracefully():
    adapter = JobicyAdapter()
    raw = {
        "jobTitle": "Software Intern",
        "companyName": "Startup Hub",
        # Missing id, salary, pubDate, geo
    }
    norm = adapter.normalize_listing(raw)
    assert norm is not None
    assert norm["title"] == "Software Intern"
    assert norm["company_name"] == "Startup Hub"
    assert norm["salary_min"] is None
    assert norm["salary_range"] is None
    assert norm["location"] == "Remote / Anywhere"


# =========================================================
# 2. URL Normalization & Deduplication Tests
# =========================================================

def test_normalize_job_url():
    url_with_tracking = "https://remoteok.com/remote-jobs/12345/?utm_source=newsletter&utm_medium=email&ref=jobboard"
    cleaned = normalize_job_url(url_with_tracking)
    assert cleaned == "https://remoteok.com/remote-jobs/12345"
    assert "utm_source" not in cleaned
    assert "ref" not in cleaned


def test_job_ingestion_deduplication_exact_external_id(db_session):
    adapter = RemoteOKAdapter()
    raw = {
        "id": "112233",
        "position": "Backend Go Engineer",
        "company": "Distributed Labs",
        "description": "Initial short job description",
        "tags": ["go", "docker"],
        "url": "https://remoteok.com/remote-jobs/112233"
    }
    norm1 = adapter.normalize_listing(raw)

    # First ingestion -> imported
    job1, action1 = JobIngestionService.upsert_normalized_job(db=db_session, norm_job=norm1)
    assert action1 == "imported"
    assert job1.id is not None
    initial_id = job1.id

    # Second ingestion with updated description -> updated in place
    raw["description"] = "Updated full description with comprehensive architecture details"
    raw["salary_min"] = 120000
    raw["salary_max"] = 160000
    norm2 = adapter.normalize_listing(raw)

    job2, action2 = JobIngestionService.upsert_normalized_job(db=db_session, norm_job=norm2)
    assert action2 == "updated"
    assert job2.id == initial_id  # Same database row!
    assert "comprehensive architecture details" in job2.description
    assert job2.salary_min == 120000.0

    # Verify total job count is still 1
    total_jobs = db_session.execute(select(Job)).scalars().all()
    assert len(total_jobs) == 1


def test_job_ingestion_deduplication_by_normalized_url(db_session):
    adapter = JobicyAdapter()
    raw1 = {
        "id": 9991,
        "jobTitle": "DevOps Engineer",
        "companyName": "InfraCore",
        "url": "https://jobicy.com/jobs/9991-devops?utm_source=aggregators"
    }
    norm1 = adapter.normalize_listing(raw1)
    job1, action1 = JobIngestionService.upsert_normalized_job(db=db_session, norm_job=norm1)
    assert action1 == "imported"

    # Same job, different tracking query
    raw2 = {
        "id": 9991,
        "jobTitle": "DevOps Engineer",
        "companyName": "InfraCore",
        "url": "https://jobicy.com/jobs/9991-devops?ref=direct"
    }
    norm2 = adapter.normalize_listing(raw2)
    job2, action2 = JobIngestionService.upsert_normalized_job(db=db_session, norm_job=norm2)
    assert action2 == "updated"
    assert job2.id == job1.id


def test_job_ingestion_fuzzy_deduplication_title_company_location(db_session):
    # Two listings without external_id but identical company, title, location
    norm1 = {
        "title": "Machine Learning Engineer",
        "company_name": "Vision AI",
        "location": "Remote",
        "description": "Original posting",
        "source_platform": "Direct",
        "source_url": "https://visionai.com/job1"
    }
    job1, action1 = JobIngestionService.upsert_normalized_job(db=db_session, norm_job=norm1)
    assert action1 == "imported"

    norm2 = {
        "title": "Machine Learning Engineer",
        "company_name": "Vision AI",
        "location": "Remote",
        "description": "Cross-posted opportunity",
        "source_platform": "Aggregator",
        "source_url": "https://aggregator.com/job1"
    }
    job2, action2 = JobIngestionService.upsert_normalized_job(db=db_session, norm_job=norm2)
    assert action2 == "updated"
    assert job2.id == job1.id


# =========================================================
# 3. Freshness & Expiry Tests
# =========================================================

def test_mark_stale_jobs_as_expired(db_session):
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=45)

    # 1. External feed job that hasn't been seen in 45 days -> should expire
    stale_job = Job(
        title="Outdated Developer",
        company_name="OldCorp",
        source_platform="RemoteOK",
        is_active=True,
        is_expired=False,
        last_seen_at=old_date
    )
    # 2. Fresh external feed job seen today -> should NOT expire
    fresh_job = Job(
        title="Fresh Developer",
        company_name="NewCorp",
        source_platform="Jobicy",
        is_active=True,
        is_expired=False,
        last_seen_at=now
    )
    # 3. Manual job created 50 days ago -> should NOT expire (manual user records are protected)
    manual_job = Job(
        title="Personal Opportunity",
        company_name="MyNetwork",
        source_platform="Manual",
        is_active=True,
        is_expired=False,
        last_seen_at=old_date
    )
    db_session.add_all([stale_job, fresh_job, manual_job])
    db_session.commit()

    expired_count = JobIngestionService.mark_stale_jobs_as_expired(db_session, older_than_days=30)
    assert expired_count == 1

    db_session.refresh(stale_job)
    db_session.refresh(fresh_job)
    db_session.refresh(manual_job)

    assert stale_job.is_expired is True
    assert stale_job.import_status == "expired"
    assert fresh_job.is_expired is False
    assert manual_job.is_expired is False


# =========================================================
# 4. Partial Failure & Multi-Source Orchestration
# =========================================================

def test_sync_sources_partial_failure_isolation(db_session):
    mock_remoteok_jobs = [
        {
            "id": "rok-1",
            "position": "Frontend Vue Engineer",
            "company": "VueCraft",
            "description": "Vue 3 Developer",
            "tags": ["vue", "javascript"],
            "url": "https://remoteok.com/job/rok-1"
        }
    ]

    # RemoteOK succeeds, Jobicy raises network connection error
    with patch.object(RemoteOKAdapter, "fetch_raw_listings", return_value=mock_remoteok_jobs), \
         patch.object(JobicyAdapter, "fetch_raw_listings", side_effect=Exception("Jobicy API 503 Unavailable")):

        result = JobIngestionService.sync_sources(db=db_session)

        assert result["status"] == "completed"
        assert result["total_imported"] == 1
        assert "remoteok" in result["source_results"]
        assert result["source_results"]["remoteok"]["status"] == "success"
        assert result["source_results"]["jobicy"]["status"] == "error"
        assert "503" in result["source_results"]["jobicy"]["error"]


# =========================================================
# 5. Search & Filter Tests
# =========================================================

def test_list_jobs_filters_by_source_and_employment_type(db_session):
    j1 = Job(
        title="React Engineer",
        company_name="WebCorp",
        source_platform="RemoteOK",
        employment_type="Full-time",
        is_active=True
    )
    j2 = Job(
        title="Django Developer",
        company_name="PyCorp",
        source_platform="Jobicy",
        employment_type="Contract",
        is_active=True
    )
    j3 = Job(
        title="Go Architect",
        company_name="ScaleCorp",
        source_platform="Manual",
        employment_type="Full-time",
        is_active=True
    )
    db_session.add_all([j1, j2, j3])
    db_session.commit()

    # Filter by source RemoteOK
    jobs_rok, total_rok = list_jobs(db_session, source="RemoteOK")
    assert total_rok == 1
    assert jobs_rok[0].company_name == "WebCorp"

    # Filter by employment_type Contract
    jobs_contract, total_contract = list_jobs(db_session, employment_type="Contract")
    assert total_contract == 1
    assert jobs_contract[0].company_name == "PyCorp"


def register_and_login(client, email: str, name: str = "Job Hunter") -> dict:
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


def test_sync_sources_endpoint_unauthenticated_rejected(client):
    res = client.post("/api/jobs/sources/sync", json={})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_sync_sources_endpoint_success(client):
    headers = register_and_login(client, "sync_admin@example.com")
    mock_summary = {
        "status": "completed",
        "total_fetched": 10,
        "total_imported": 8,
        "total_updated": 2,
        "total_skipped": 0,
        "source_results": {},
        "message": "Sync completed successfully."
    }
    with patch.object(JobIngestionService, "sync_sources", return_value=mock_summary):
        res = client.post(
            "/api/jobs/sources/sync",
            json={"limit_per_source": 10},
            headers=headers
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["status"] == "completed"
        assert data["total_imported"] == 8


def test_sources_status_endpoint(client):
    headers = register_and_login(client, "status_checker@example.com")
    res = client.get("/api/jobs/sources/status", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "sources" in data
    assert "active_sources_count" in data
    assert len(data["sources"]) >= 2


# =========================================================
# 7. Celery Task Execution Test
# =========================================================

def test_orchestrate_job_ingestion_celery_task(db_session):
    mock_summary = {
        "status": "completed",
        "total_fetched": 5,
        "total_imported": 5,
        "total_updated": 0,
        "total_skipped": 0,
        "source_results": {},
        "message": "Celery job ingestion complete."
    }
    with patch.object(JobIngestionService, "sync_sources", return_value=mock_summary):
        result = orchestrate_job_ingestion_task(
            sources=["remoteok", "jobicy"],
            limit_per_source=15,
            db_session=db_session
        )
        assert result["status"] == "completed"
        assert result["total_imported"] == 5


# =========================================================
# 8. Repeat-Sync Deduplication, Count Accuracy & Telemetry
# =========================================================

def test_repeat_sync_deduplication_and_exact_count_accounting(db_session):
    """
    Tests the exact scenario observed in production:
    Cycle 1: 2 RemoteOK + 2 Jobicy listings ingested -> 4 new imported, 0 updated. Total in DB = 4.
    Cycle 2: Repeated synchronization of the same listings -> 0 new imported, 4 updated. Total in DB remains 4!
    """
    mock_remoteok_jobs = [
        {
            "id": "rok-101",
            "position": "Senior Backend Go Engineer",
            "company": "GoLang Corp",
            "description": "Go microservices",
            "tags": ["go", "docker"],
            "url": "https://remoteok.com/job/rok-101"
        },
        {
            "id": "rok-102",
            "position": "Site Reliability Engineer",
            "company": "Reliable Infra",
            "description": "Kubernetes platform",
            "tags": ["k8s", "aws"],
            "url": "https://remoteok.com/job/rok-102"
        }
    ]

    mock_jobicy_jobs = [
        {
            "id": 201,
            "jobTitle": "Lead Python Architect",
            "companyName": "Pythonic Inc",
            "jobDescription": "FastAPI and PostgreSQL",
            "jobType": "Full-time",
            "url": "https://jobicy.com/jobs/201-python"
        },
        {
            "id": 202,
            "jobTitle": "Frontend React Specialist",
            "companyName": "UI Masters",
            "jobDescription": "React and TypeScript",
            "jobType": "Contract",
            "url": "https://jobicy.com/jobs/202-react"
        }
    ]

    with patch.object(RemoteOKAdapter, "fetch_raw_listings", return_value=mock_remoteok_jobs), \
         patch.object(JobicyAdapter, "fetch_raw_listings", return_value=mock_jobicy_jobs):

        # ---- Run 1: Initial Ingestion ----
        res1 = JobIngestionService.sync_sources(db=db_session, limit_per_source=10)
        assert res1["status"] == "completed"
        assert res1["total_fetched"] == 4
        assert res1["total_imported"] == 4
        assert res1["total_updated"] == 0
        assert res1["total_skipped"] == 0
        assert "4 new jobs imported, 0 updated" in res1["message"]

        # Check DB row count
        db_count_1 = db_session.execute(select(func.count(Job.id))).scalar_one()
        assert db_count_1 == 4

        # Verify telemetry after Run 1
        status_1 = JobIngestionService.get_sources_status(db=db_session)
        assert status_1["total_jobs"] == 4
        rok_stat = next(s for s in status_1["sources"] if s["name"] == "RemoteOK")
        assert rok_stat["last_sync_imported"] == 2
        assert rok_stat["last_sync_updated"] == 0

        # ---- Run 2: Repeat Sync with identical external jobs ----
        res2 = JobIngestionService.sync_sources(db=db_session, limit_per_source=10)
        assert res2["status"] == "completed"
        assert res2["total_fetched"] == 4
        assert res2["total_imported"] == 0  # Zero new jobs imported!
        assert res2["total_updated"] == 4   # All 4 updated in place!
        assert res2["total_skipped"] == 0
        assert "0 new jobs imported, 4 updated" in res2["message"]

        # Check DB row count: MUST STILL BE 4 (no duplicates created!)
        db_count_2 = db_session.execute(select(func.count(Job.id))).scalar_one()
        assert db_count_2 == 4

        # Verify telemetry after Run 2
        status_2 = JobIngestionService.get_sources_status(db=db_session)
        rok_stat_2 = next(s for s in status_2["sources"] if s["name"] == "RemoteOK")
        assert rok_stat_2["last_sync_imported"] == 0
        assert rok_stat_2["last_sync_updated"] == 2
        assert rok_stat_2["total_imported"] >= 2


# =========================================================
# 9. Malformed Responses, HTTP Errors & Edge Cases
# =========================================================

def test_remoteok_adapter_malformed_and_error_handling():
    adapter = RemoteOKAdapter()

    # 1. Non-dict raw row
    assert adapter.normalize_listing(None) is None
    assert adapter.normalize_listing("invalid string") is None
    assert adapter.normalize_listing([]) is None

    # 2. Swapped min/max salary
    norm = adapter.normalize_listing({
        "position": "Backend Engineer",
        "company": "Tech Corp",
        "salary_min": 150000,
        "salary_max": 90000,
        "url": "https://remoteok.com/job/1"
    })
    assert norm is not None
    assert norm["salary_min"] == 90000.0
    assert norm["salary_max"] == 150000.0

    # 3. Epoch timestamp parsing
    norm_epoch = adapter.normalize_listing({
        "position": "Data Engineer",
        "company": "BigData Co",
        "epoch": 1700000000,
        "url": "https://remoteok.com/job/2"
    })
    assert norm_epoch is not None
    assert norm_epoch["posting_date"].year >= 2023

    # 4. Comma-separated tags string
    norm_tags = adapter.normalize_listing({
        "position": "DevOps Engineer",
        "company": "Cloud Co",
        "tags": "docker, kubernetes, terraform",
        "url": "https://remoteok.com/job/3"
    })
    assert norm_tags is not None
    assert "docker" in norm_tags["required_skills"]

    # 5. Fetch with HTTP error handling
    with patch.object(adapter, "fetch_raw_listings", side_effect=Exception("HTTP 502 Bad Gateway")):
        listings, stats = adapter.fetch_and_normalize()
        assert listings == []
        assert stats["fetched"] == 0
        assert "502" in stats["error"]


def test_jobicy_adapter_malformed_and_error_handling():
    adapter = JobicyAdapter()

    # 1. Non-dict raw row
    assert adapter.normalize_listing(None) is None
    assert adapter.normalize_listing(12345) is None

    # 2. String salary numbers with inverted values
    norm = adapter.normalize_listing({
        "jobTitle": "Lead Architect",
        "companyName": "Enterprise Inc",
        "annualSalaryMin": "160000",
        "annualSalaryMax": "110000",
        "salaryCurrency": "EUR",
        "url": "https://jobicy.com/jobs/99"
    })
    assert norm is not None
    assert norm["salary_min"] == 110000.0
    assert norm["salary_max"] == 160000.0
    assert "EUR" in norm["salary_range"]

    # 3. RFC-style date parsing
    norm_rfc = adapter.normalize_listing({
        "jobTitle": "Security Engineer",
        "companyName": "SafeNet",
        "pubDate": "Mon, 27 Oct 2026 10:00:00 +0000",
        "url": "https://jobicy.com/jobs/100"
    })
    assert norm_rfc is not None
    assert norm_rfc["posting_date"].year == 2026

    # 4. Fetch with HTTP error handling
    with patch.object(adapter, "fetch_raw_listings", side_effect=Exception("Connection timed out")):
        listings, stats = adapter.fetch_and_normalize()
        assert listings == []
        assert stats["fetched"] == 0
        assert "timed out" in stats["error"]


def test_deduplication_duplicate_url_multiple_rows_safe(db_session):
    """
    Ensures that if multiple rows exist in the database with the same source URL,
    find_existing_duplicate_job returns the first row safely without raising MultipleResultsFound.
    """
    url = "https://example.com/jobs/dev-1"
    j1 = Job(title="Dev 1", company_name="Corp", source_platform="RemoteOK", source_url=url, is_active=True)
    j2 = Job(title="Dev 1 Duplicate", company_name="Corp", source_platform="RemoteOK", source_url=url, is_active=True)
    db_session.add_all([j1, j2])
    db_session.commit()

    norm = {
        "title": "Dev 1",
        "company_name": "Corp",
        "source_platform": "RemoteOK",
        "source_url": url
    }
    # Should safely return without MultipleResultsFound
    dup = JobIngestionService.find_existing_duplicate_job(db=db_session, norm_job=norm)
    assert dup is not None
    assert dup.id in (j1.id, j2.id)


def test_sources_status_disabled_adapter():
    with patch.object(RemoteOKAdapter, "is_enabled", return_value=False):
        status = JobIngestionService.get_sources_status()
        rok = next(s for s in status["sources"] if s["name"] == "RemoteOK")
        assert rok["enabled"] is False
        assert rok["status"] == "disabled"
