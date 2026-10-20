import pytest

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


def test_matching_unauthenticated_rejected(client):
    """Unauthenticated requests to match endpoints must be rejected with 401."""
    resp_match = client.post("/api/jobs/1/match")
    assert resp_match.status_code == 401

    resp_rank = client.get("/api/jobs/matches")
    assert resp_rank.status_code == 401


def test_full_skill_match(client):
    """Candidate with all required & preferred skills and sufficient experience gets top score."""
    headers = register_and_login(client, "full_match@example.com")

    # Setup candidate profile
    client.put("/api/profile", headers=headers, json={
        "experience_years": 3.0,
        "education": "B.Tech in Computer Science",
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Expert"},
            {"skill_name": "FastAPI", "proficiency_level": "Advanced"},
            {"skill_name": "Docker", "proficiency_level": "Intermediate"},
            {"skill_name": "PostgreSQL", "proficiency_level": "Advanced"}
        ]
    })

    # Create job opportunity
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Backend Python Engineer",
        "company_name": "HyperScale Tech",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["Docker", "PostgreSQL"],
        "experience_years_required": 2.0
    })
    job_id = job_resp.json()["id"]

    # Match computation
    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    assert data["job_id"] == job_id
    assert data["match_score"] == 100.0
    assert "Python" in data["matched_skills"]
    assert "FastAPI" in data["matched_skills"]
    assert len(data["missing_critical_skills"]) == 0
    assert len(data["missing_secondary_skills"]) == 0
    assert data["meets_experience"] is True
    assert data["experience_gap"] == 0.0
    assert data["experience_warning"] is None
    assert "Strong" in data["explanation"]
    assert len(data["resume_advice"]) >= 1


def test_partial_match_with_missing_critical_skills(client):
    """Candidate missing core skills receives delta gap breakdown and lower score."""
    headers = register_and_login(client, "partial_match@example.com")

    # Candidate profile with only React
    client.put("/api/profile", headers=headers, json={
        "experience_years": 1.0,
        "skills": [
            {"skill_name": "React", "proficiency_level": "Intermediate"}
        ]
    })

    # Job requiring React, TypeScript, GraphQL, Node.js + preferred AWS
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Senior Fullstack Engineer",
        "company_name": "NextGen Systems",
        "required_skills": ["React", "TypeScript", "GraphQL", "Node.js"],
        "preferred_skills": ["AWS"],
        "experience_years_required": 1.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    assert "React" in data["matched_skills"]
    assert "TypeScript" in data["missing_critical_skills"]
    assert "GraphQL" in data["missing_critical_skills"]
    assert "Node.js" in data["missing_critical_skills"]
    assert "AWS" in data["missing_secondary_skills"]
    assert data["match_score"] < 50.0
    assert "Missing core requirements" in data["explanation"]
    assert any("TypeScript" in tip for tip in data["resume_advice"])


def test_experience_gap_calculation(client):
    """Experience gaps reduce the 15% experience weight and trigger clear warning message."""
    headers = register_and_login(client, "exp_gap@example.com")

    # Candidate has all skills but only 1 year experience
    client.put("/api/profile", headers=headers, json={
        "experience_years": 1.0,
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Advanced"},
            {"skill_name": "Django", "proficiency_level": "Advanced"}
        ]
    })

    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Lead Python Architect",
        "company_name": "BigCorp",
        "required_skills": ["Python", "Django"],
        "experience_years_required": 4.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    assert data["meets_experience"] is False
    assert data["candidate_experience_years"] == 1.0
    assert data["required_experience_years"] == 4.0
    assert data["experience_gap"] == 3.0
    assert data["experience_warning"] is not None
    assert "Requires 4.0 years" in data["experience_warning"]
    assert any("tenure gap" in tip or "experience" in tip.lower() for tip in data["resume_advice"])


def test_synonym_skill_matching(client):
    """Synonyms like react.js/react, postgres/postgresql, k8s/kubernetes are resolved as matches."""
    headers = register_and_login(client, "synonym_test@example.com")

    # Candidate uses slang/abbreviations
    client.put("/api/profile", headers=headers, json={
        "experience_years": 2.0,
        "skills": [
            {"skill_name": "react.js", "proficiency_level": "Intermediate"},
            {"skill_name": "postgres", "proficiency_level": "Intermediate"},
            {"skill_name": "k8s", "proficiency_level": "Intermediate"}
        ]
    })

    # Job uses canonical forms
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Platform Developer",
        "company_name": "DevOps Hub",
        "required_skills": ["React", "PostgreSQL", "Kubernetes"],
        "experience_years_required": 2.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers)
    assert match_resp.status_code == 200
    data = match_resp.json()

    assert len(data["missing_critical_skills"]) == 0
    assert data["match_score"] >= 95.0


def test_rank_active_jobs_for_candidate(client):
    """GET /api/jobs/matches returns active jobs sorted descending by match score."""
    headers = register_and_login(client, "ranking_user@example.com")

    # Candidate specializes in Python / FastAPI
    client.put("/api/profile", headers=headers, json={
        "experience_years": 2.0,
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Expert"},
            {"skill_name": "FastAPI", "proficiency_level": "Advanced"}
        ]
    })

    # Seed Job 1: High match (Python/FastAPI)
    client.post("/api/jobs", headers=headers, json={
        "title": "Python API Developer",
        "company_name": "PyFirm",
        "required_skills": ["Python", "FastAPI"],
        "experience_years_required": 2.0
    })

    # Seed Job 2: Low match (Ruby on Rails)
    client.post("/api/jobs", headers=headers, json={
        "title": "Ruby Rails Specialist",
        "company_name": "RubyWorks",
        "required_skills": ["Ruby", "Ruby on Rails"],
        "experience_years_required": 5.0
    })

    rank_resp = client.get("/api/jobs/matches", headers=headers)
    assert rank_resp.status_code == 200
    rank_data = rank_resp.json()

    assert rank_data["total_jobs_evaluated"] >= 2
    rankings = rank_data["rankings"]
    # Top ranked job should be Python API Developer
    assert rankings[0]["job"]["title"] == "Python API Developer"
    assert rankings[0]["match_score"] > rankings[1]["match_score"]
