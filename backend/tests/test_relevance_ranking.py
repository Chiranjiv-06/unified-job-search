"""
Comprehensive automated tests for Explainable Job Relevance and Ranking.
Covers Phase 5 requirements:
1. Entry-level Python/backend job ranks highly for matching IT profile.
2. Data analyst job with matching SQL/Python skills receives meaningful score.
3. Director/senior leadership job is ranked lower for entry-level profile.
4. Unrelated sales/marketing role is down-ranked for IT profile.
5. Job missing description or experience data is handled safely (capped score).
6. Profile with no skills receives safe, explainable result.
7. Skill matching is case-insensitive and avoids substring false positives (go != django, c != css).
8. Existing source/employment filters and date sorting continue to work.
9. Authentication, user isolation, job retrieval, and application tracking intact.
10. Deterministic ranking order with stable tie-breaker.
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.services.matching_service import (
    evaluate_job_match,
    normalize_skill,
    contains_skill,
    IT_ROLE_FAMILIES,
    SENIOR_LEADERSHIP_INDICATORS,
    NON_IT_DOMAINS
)
from app.models.profile import CandidateProfile, CandidateSkill
from app.models.job import Job
from app.models.user import User


def register_and_login(client, email: str, name: str = "Test Student") -> dict:
    """Helper to register user, log in, and return Authorization headers."""
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


# -------------------------------------------------------------------------
# Test Case 1: Entry-level Python/Backend Job Ranks Highly
# -------------------------------------------------------------------------
def test_entry_level_backend_ranks_highly_for_matching_it_profile(client):
    headers = register_and_login(client, "student2027_it@example.com", "IT Student 2027")

    # Profile: 2027 B.Tech IT student targeting backend software engineering
    client.put("/api/profile", headers=headers, json={
        "headline": "Aspiring Backend Developer | B.Tech IT 2027",
        "education": "B.Tech in Information Technology",
        "experience_years": 0.5,
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Advanced"},
            {"skill_name": "FastAPI", "proficiency_level": "Intermediate"},
            {"skill_name": "PostgreSQL", "proficiency_level": "Intermediate"},
            {"skill_name": "Docker", "proficiency_level": "Beginner"}
        ]
    })

    # Job: Entry-level Junior Backend Developer
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Backend Developer (Python / FastAPI)",
        "company_name": "Acme Cloud Systems",
        "description": "Looking for a junior software engineer or 2026/2027 graduate to build high-performance APIs.",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["PostgreSQL", "Docker"],
        "experience_level": "Entry-Level",
        "experience_years_required": 0.0,
        "employment_type": "Full-time"
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    # Must rank highly: >= 80
    assert data["match_score"] >= 80.0
    assert "Python" in data["matched_skills"]
    assert "FastAPI" in data["matched_skills"]
    assert len(data["missing_critical_skills"]) == 0
    assert any("entry-level" in r.lower() or "junior" in r.lower() for r in data["positive_reasons"])
    assert any("skills" in r.lower() or "core" in r.lower() for r in data["positive_reasons"])


# -------------------------------------------------------------------------
# Test Case 2: Data Analyst Job Receives Meaningful Score
# -------------------------------------------------------------------------
def test_data_analyst_receives_meaningful_score(client):
    headers = register_and_login(client, "analyst_cand@example.com", "Data Enthusiast")

    client.put("/api/profile", headers=headers, json={
        "headline": "Aspiring Data Analyst | Python & SQL",
        "education": "B.Tech in Information Technology",
        "experience_years": 0.0,
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Advanced"},
            {"skill_name": "SQL", "proficiency_level": "Advanced"},
            {"skill_name": "Pandas", "proficiency_level": "Intermediate"}
        ]
    })

    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Data Analyst",
        "company_name": "Metrics Global",
        "description": "Seeking an entry level data analyst skilled in SQL querying, Python analytics, and business insights.",
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["Pandas", "Power BI"],
        "experience_level": "Entry-Level",
        "experience_years_required": 0.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    assert data["match_score"] >= 70.0
    assert "SQL" in data["matched_skills"] or "sql" in [s.lower() for s in data["matched_skills"]]
    assert "Python" in data["matched_skills"] or "python" in [s.lower() for s in data["matched_skills"]]
    assert any("data" in r.lower() or "analyst" in r.lower() for r in data["positive_reasons"])


# -------------------------------------------------------------------------
# Test Case 3: Director/Senior Leadership Job Down-Ranked for Entry Profile
# -------------------------------------------------------------------------
def test_senior_leadership_penalized_for_entry_profile(client):
    headers = register_and_login(client, "entry_dev@example.com", "Junior Developer")

    client.put("/api/profile", headers=headers, json={
        "headline": "Junior Software Engineer",
        "experience_years": 0.5,
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Intermediate"},
            {"skill_name": "PostgreSQL", "proficiency_level": "Intermediate"}
        ]
    })

    # Director role requiring 10 years experience
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Director of Software Engineering",
        "company_name": "Enterprise Holdings",
        "description": "Executive leader managing multiple engineering managers and departmental budget.",
        "required_skills": ["Python", "PostgreSQL"],
        "experience_level": "Director",
        "experience_years_required": 10.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    # Penalized heavily: score should be below 40 despite overlapping Python/PostgreSQL skills
    assert data["match_score"] <= 40.0
    assert any("leadership" in neg.lower() or "director" in neg.lower() for neg in data["negative_reasons"])
    assert data["experience_status"] == "GAP_WARNING"
    assert data["experience_gap_years"] >= 9.0


# -------------------------------------------------------------------------
# Test Case 4: Unrelated Sales/Marketing Role Down-Ranked
# -------------------------------------------------------------------------
def test_unrelated_sales_role_down_ranked_for_it_profile(client):
    headers = register_and_login(client, "it_dev_only@example.com", "IT Engineer")

    client.put("/api/profile", headers=headers, json={
        "headline": "Software Developer (IT Roles Only)",
        "experience_years": 1.0,
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Advanced"},
            {"skill_name": "SQL", "proficiency_level": "Intermediate"}
        ]
    })

    # Non-IT Sales job that happens to mention "software sales" and "sql reports"
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Senior Account Executive - Enterprise Sales",
        "company_name": "SalesForce Dynamics",
        "description": "B2B SaaS outbound cold-calling, quota carrying, enterprise software sales pipelines.",
        "required_skills": ["B2B Sales", "Cold Calling", "CRM"],
        "experience_level": "Mid-Level",
        "experience_years_required": 3.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    assert data["match_score"] <= 25.0
    assert any("non-it" in neg.lower() or "sales" in neg.lower() for neg in data["negative_reasons"])


# -------------------------------------------------------------------------
# Test Case 5: Job Missing Description or Experience Data Handled Safely
# -------------------------------------------------------------------------
def test_job_missing_data_handled_safely(client):
    headers = register_and_login(client, "safe_eval@example.com", "Safety User")

    client.put("/api/profile", headers=headers, json={
        "experience_years": 1.0,
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Advanced"}
        ]
    })

    # Empty description, no required skills, no experience specified
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Generic Posting",
        "company_name": "Mystery Corp",
        "description": "",
        "required_skills": [],
        "experience_years_required": None
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    # Must be safely capped and not receive a high score
    assert data["match_score"] <= 35.0
    assert any("insufficient" in neg.lower() or "description" in neg.lower() or "missing" in neg.lower() for neg in data["negative_reasons"])


# -------------------------------------------------------------------------
# Test Case 6: Profile With No Skills Receives Safe Explainable Result
# -------------------------------------------------------------------------
def test_profile_with_no_skills_receives_safe_result(client):
    headers = register_and_login(client, "no_skills@example.com", "Empty Profile User")

    # Profile without any skills
    client.put("/api/profile", headers=headers, json={
        "headline": "Student looking for work",
        "experience_years": 0.0,
        "skills": []
    })

    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Python Developer",
        "company_name": "Tech Co",
        "description": "Python web developer role.",
        "required_skills": ["Python", "FastAPI"],
        "experience_years_required": 1.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    # Capped low
    assert data["match_score"] <= 25.0
    assert len(data["matched_skills"]) == 0
    assert any("skills" in neg.lower() for neg in data["negative_reasons"])

    # In matches endpoint, has_profile_skills must be False
    rank_resp = client.get("/api/jobs/matches", headers=headers)
    assert rank_resp.status_code == 200
    rank_data = rank_resp.json()
    assert rank_data["has_profile_skills"] is False


# -------------------------------------------------------------------------
# Test Case 7: Skill Matching Avoids Substring False Positives
# -------------------------------------------------------------------------
def test_skill_matching_avoids_substring_false_positives():
    """Verify regex boundary matching prevents false positives like go in django or c in css."""
    # "go" should NOT match in "django"
    assert contains_skill("django framework with python", "go") is False
    assert contains_skill("golang backend services", "go") is True

    # "c" should NOT match in "css"
    assert contains_skill("frontend development with css and html", "c") is False
    assert contains_skill("embedded c systems programming", "c") is True

    # "java" should NOT match in "javascript"
    assert contains_skill("javascript react frontend developer", "java") is False
    assert contains_skill("java spring boot backend engineer", "java") is True

    # Case-insensitivity:
    assert contains_skill("PYTHON FASTAPI DOCKER", "python") is True
    assert contains_skill("python fastapi docker", "FASTAPI") is True


# -------------------------------------------------------------------------
# Test Case 8: Existing Source, Employment Filters and Date Sorting Work
# -------------------------------------------------------------------------
def test_filters_and_sorting_coexist_with_ranking(client):
    headers = register_and_login(client, "filter_user@example.com", "Filter User")

    client.put("/api/profile", headers=headers, json={
        "headline": "Fullstack Developer",
        "skills": [{"skill_name": "Python", "proficiency_level": "Expert"}]
    })

    # Seed jobs with distinct sources and employment types
    client.post("/api/jobs", headers=headers, json={
        "title": "RemoteOK Python Job",
        "company_name": "SourceOne",
        "source_platform": "RemoteOK",
        "employment_type": "Full-time",
        "required_skills": ["Python"]
    })

    client.post("/api/jobs", headers=headers, json={
        "title": "Jobicy Contract Gig",
        "company_name": "SourceTwo",
        "source_platform": "Jobicy",
        "employment_type": "Contract",
        "required_skills": ["Python"]
    })

    # 1. Filter by source=RemoteOK
    resp_src = client.get("/api/jobs?source=RemoteOK", headers=headers)
    assert resp_src.status_code == 200
    jobs_src = resp_src.json()["jobs"]
    assert all(j["source_platform"] == "RemoteOK" for j in jobs_src)

    # 2. Filter by employment_type=Contract
    resp_emp = client.get("/api/jobs?employment_type=Contract", headers=headers)
    assert resp_emp.status_code == 200
    jobs_emp = resp_emp.json()["jobs"]
    assert all(j["employment_type"] == "Contract" for j in jobs_emp)

    # 3. Sort by recent
    resp_recent = client.get("/api/jobs?sort_by=recent", headers=headers)
    assert resp_recent.status_code == 200
    assert len(resp_recent.json()["jobs"]) >= 2

    # 4. Sort by match on standard /api/jobs
    resp_match_sort = client.get("/api/jobs?sort_by=match", headers=headers)
    assert resp_match_sort.status_code == 200
    jobs_match = resp_match_sort.json()["jobs"]
    # match_score is present
    assert all("match_score" in j for j in jobs_match)

    # 5. Filter within /api/jobs/matches
    resp_match_filtered = client.get("/api/jobs/matches?source=RemoteOK", headers=headers)
    assert resp_match_filtered.status_code == 200
    for item in resp_match_filtered.json()["rankings"]:
        assert item["job"]["source_platform"] == "RemoteOK"


# -------------------------------------------------------------------------
# Test Case 9: Authentication & User Isolation Intact
# -------------------------------------------------------------------------
def test_user_isolation_and_application_tracking(client):
    headers_a = register_and_login(client, "candidate_a@example.com", "Alice")
    headers_b = register_and_login(client, "candidate_b@example.com", "Bob")

    # Alice has Python
    client.put("/api/profile", headers=headers_a, json={
        "skills": [{"skill_name": "Python", "proficiency_level": "Expert"}]
    })

    # Bob has only Go
    client.put("/api/profile", headers=headers_b, json={
        "skills": [{"skill_name": "Go", "proficiency_level": "Expert"}]
    })

    job_resp = client.post("/api/jobs", headers=headers_a, json={
        "title": "Python Microservices Engineer",
        "company_name": "CloudNine",
        "required_skills": ["Python"]
    })
    job_id = job_resp.json()["id"]

    # Alice matches high
    score_a = client.post(f"/api/jobs/{job_id}/match", headers=headers_a).json()["match_score"]
    # Bob matches low
    score_b = client.post(f"/api/jobs/{job_id}/match", headers=headers_b).json()["match_score"]

    assert score_a > score_b
    assert score_a >= 80.0
    assert score_b <= 35.0

    # Application tracking works seamlessly
    track_resp = client.post(f"/api/jobs/{job_id}/apply", headers=headers_a, json={
        "notes": "Applied via relevance recommendation"
    })
    assert track_resp.status_code == 201
    app_data = track_resp.json()
    assert app_data["job_id"] == job_id


# -------------------------------------------------------------------------
# Test Case 10: Deterministic Ranking Order with Stable Tie-Breaker
# -------------------------------------------------------------------------
def test_ranking_is_deterministic_with_tie_breaker(client):
    headers = register_and_login(client, "determ_user@example.com", "Deterministic User")

    client.put("/api/profile", headers=headers, json={
        "skills": [{"skill_name": "Python", "proficiency_level": "Intermediate"}]
    })

    # Two identical jobs created at slightly different times
    j1 = client.post("/api/jobs", headers=headers, json={
        "title": "Python Junior Dev A",
        "company_name": "Company Alpha",
        "required_skills": ["Python"]
    }).json()

    j2 = client.post("/api/jobs", headers=headers, json={
        "title": "Python Junior Dev B",
        "company_name": "Company Beta",
        "required_skills": ["Python"]
    }).json()

    # Run ranking 3 times in a row
    r1 = client.get("/api/jobs/matches", headers=headers).json()["rankings"]
    r2 = client.get("/api/jobs/matches", headers=headers).json()["rankings"]
    r3 = client.get("/api/jobs/matches", headers=headers).json()["rankings"]

    order1 = [item["job"]["id"] for item in r1]
    order2 = [item["job"]["id"] for item in r2]
    order3 = [item["job"]["id"] for item in r3]

    # Determinism check: All 3 invocations must produce the identical order
    assert order1 == order2 == order3


# -------------------------------------------------------------------------
# Test Case 11: Unauthenticated Job Retrieval Is Safe & Leak-Free
# -------------------------------------------------------------------------
def test_unauthenticated_jobs_retrieval_safe(client):
    """Unauthenticated users can browse jobs; no private profile scores are leaked."""
    # 1. Unauthenticated GET /api/jobs with recent sort
    resp_anon = client.get("/api/jobs")
    assert resp_anon.status_code == 200
    data_anon = resp_anon.json()
    assert "jobs" in data_anon
    # For unauthenticated requests, match_score is None (no leakage)
    for j in data_anon["jobs"]:
        assert j.get("match_score") is None
        assert j.get("match_summary") is None

    # 2. Unauthenticated GET /api/jobs with sort_by=match works safely
    resp_anon_match = client.get("/api/jobs?sort_by=match")
    assert resp_anon_match.status_code == 200
    data_anon_match = resp_anon_match.json()
    assert "jobs" in data_anon_match


# -------------------------------------------------------------------------
# Test Case 12: Global Sorting Across Pagination (No Partial Page Sorting)
# -------------------------------------------------------------------------
def test_global_ranking_pagination(client):
    """Relevance ranking applies to the full filtered set before pagination slicing."""
    headers = register_and_login(client, "page_user@example.com", "Pagination User")

    client.put("/api/profile", headers=headers, json={
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Expert"},
            {"skill_name": "FastAPI", "proficiency_level": "Advanced"}
        ]
    })

    # Create 3 jobs with strictly tiered relevance:
    # Top: Python + FastAPI
    top_j = client.post("/api/jobs", headers=headers, json={
        "title": "Top Python FastAPI Dev",
        "company_name": "TierOne",
        "required_skills": ["Python", "FastAPI"],
        "experience_years_required": 0.0
    }).json()

    # Mid: Python only
    mid_j = client.post("/api/jobs", headers=headers, json={
        "title": "Mid Python Dev",
        "company_name": "TierTwo",
        "required_skills": ["Python"],
        "experience_years_required": 0.0
    }).json()

    # Low: Ruby only
    low_j = client.post("/api/jobs", headers=headers, json={
        "title": "Low Ruby Specialist",
        "company_name": "TierThree",
        "required_skills": ["Ruby"],
        "experience_years_required": 5.0
    }).json()

    # Request Page 1: skip=0, limit=2
    p1 = client.get("/api/jobs?sort_by=match&skip=0&limit=2", headers=headers).json()
    # Request Page 2: skip=2, limit=2
    p2 = client.get("/api/jobs?sort_by=match&skip=2&limit=2", headers=headers).json()

    p1_ids = [j["id"] for j in p1["jobs"]]
    p2_ids = [j["id"] for j in p2["jobs"]]

    # Page 1 must contain Top and Mid (or higher score)
    assert top_j["id"] in p1_ids
    # Page 1 scores must be >= Page 2 scores
    p1_min_score = min(j["match_score"] for j in p1["jobs"])
    if p2["jobs"]:
        p2_max_score = max(j["match_score"] for j in p2["jobs"])
        assert p1_min_score >= p2_max_score


# -------------------------------------------------------------------------
# Test Case 13: Malformed & Missing Optional Fields Resilience
# -------------------------------------------------------------------------
def test_malformed_and_missing_optional_fields_resilience(client):
    """Evaluator does not crash on None, empty, or unexpected data types."""
    # Test compute_job_match with completely bare objects
    bare_job = Job(
        id=99999,
        title=None,
        company_name=None,
        description=None,
        required_skills=None,
        preferred_skills=None,
        experience_level=None,
        experience_years_required=None,
        education_requirement=None
    )
    bare_profile = CandidateProfile(
        experience_years=None,
        experience_level=None,
        education=None,
        preferred_roles=None,
        parsed_skills=None
    )

    from app.services.matching_service import compute_job_match
    breakdown = compute_job_match(bare_profile, bare_job)

    assert 0.0 <= breakdown.match_score <= 100.0
    assert isinstance(breakdown.positive_reasons, list)
    assert isinstance(breakdown.negative_reasons, list)
    assert isinstance(breakdown.explanation, str)
