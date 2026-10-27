"""
Automated regression and functional tests for the Target Roles feature.
Covers:
1. Retrieval of extensible standard target roles list via GET /api/profile/target-roles.
2. Saving, retrieving, updating, and clearing persistent target roles in Candidate Profile.
3. Whitespace normalization, deduplication, and invalid string handling.
4. User isolation and authorization guarantees.
5. Compatibility with existing profile fields and legacy string input formats.
6. Relevance scoring benefits for direct target role matches and canonical aliases.
7. Related tech family partial alignment vs unrelated role mismatches.
8. Substring safety (e.g. Java Developer != JavaScript Developer).
9. Baseline score preservation when candidate has no target roles configured.
10. Score bounding within [0, 100] with positive and negative explanation agreement.
"""

import pytest
from app.services.matching_service import (
    compute_job_match,
    check_target_role_match,
    STANDARD_ROLE_TAXONOMY,
    IT_ROLE_FAMILIES
)
from app.models.profile import CandidateProfile, CandidateSkill
from app.models.job import Job


def register_and_login(client, email: str, name: str = "Test Candidate") -> dict:
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
# Test 1: Standard Target Roles Endpoint
# -------------------------------------------------------------------------
def test_get_available_target_roles_endpoint(client):
    res = client.get("/api/profile/target-roles")
    assert res.status_code == 200
    data = res.json()
    assert "roles" in data
    assert "categories" in data
    assert len(data["roles"]) >= 12

    # Verify example target roles from specification
    expected_examples = [
        "Backend Developer",
        "Software Developer",
        "Full Stack Developer",
        "Python Developer",
        "Java Developer",
        "Data Analyst",
        "Data Scientist",
        "AI/ML Engineer",
        "DevOps Engineer",
        "QA / Test Engineer",
        "Database Developer",
        "Cybersecurity Analyst"
    ]
    for role in expected_examples:
        assert role in data["roles"], f"Expected '{role}' in available target roles"


# -------------------------------------------------------------------------
# Test 2: Saving and Retrieving Multiple Target Roles
# -------------------------------------------------------------------------
def test_save_and_retrieve_multiple_target_roles(client):
    headers = register_and_login(client, "target_roles_user1@example.com", "Roles User 1")

    selected_roles = ["Backend Developer", "Python Developer", "DevOps Engineer"]
    update_res = client.put("/api/profile", headers=headers, json={
        "education": "B.Tech in Computer Science, 2026",
        "experience_level": "Entry-Level",
        "preferred_roles": selected_roles,
        "preferred_work_mode": "Remote"
    })
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["preferred_roles"] == selected_roles

    # Verify GET persistence
    get_res = client.get("/api/profile", headers=headers)
    assert get_res.status_code == 200
    persisted_data = get_res.json()
    assert persisted_data["preferred_roles"] == selected_roles


# -------------------------------------------------------------------------
# Test 3: Updating and Clearing Target Roles
# -------------------------------------------------------------------------
def test_update_and_clear_target_roles(client):
    headers = register_and_login(client, "target_roles_user2@example.com", "Roles User 2")

    # Set initial roles
    client.put("/api/profile", headers=headers, json={
        "preferred_roles": ["Data Analyst", "Data Scientist"]
    })

    # Update to a single role
    upd1 = client.put("/api/profile", headers=headers, json={
        "preferred_roles": ["AI/ML Engineer"]
    }).json()
    assert upd1["preferred_roles"] == ["AI/ML Engineer"]

    # Clear selections completely
    upd2 = client.put("/api/profile", headers=headers, json={
        "preferred_roles": []
    }).json()
    assert upd2["preferred_roles"] == []

    # Verify GET returns empty list
    get_res = client.get("/api/profile", headers=headers).json()
    assert get_res["preferred_roles"] == []


# -------------------------------------------------------------------------
# Test 4: Deduplication and Whitespace Normalization
# -------------------------------------------------------------------------
def test_duplicate_and_whitespace_normalization(client):
    headers = register_and_login(client, "target_roles_user3@example.com", "Roles User 3")

    messy_roles = [
        "   Backend    Developer   ",
        "backend developer",
        "BACKEND DEVELOPER",
        "   Data Analyst  ",
        "   ",
        None
    ]
    res = client.put("/api/profile", headers=headers, json={
        "preferred_roles": messy_roles
    })
    assert res.status_code == 200
    data = res.json()
    # Must normalize internal whitespace, trim, and deduplicate case-insensitively
    assert len(data["preferred_roles"]) == 2
    assert "Backend Developer" in data["preferred_roles"]
    assert "Data Analyst" in data["preferred_roles"]


# -------------------------------------------------------------------------
# Test 5: Empty Target Roles for Existing Users
# -------------------------------------------------------------------------
def test_empty_target_roles_for_existing_users(client):
    headers = register_and_login(client, "existing_user_default@example.com", "Existing User")

    # Brand new or legacy profile with no roles
    res = client.get("/api/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["preferred_roles"], list)
    assert data["preferred_roles"] == []


# -------------------------------------------------------------------------
# Test 6: User Data Isolation for Target Roles
# -------------------------------------------------------------------------
def test_user_isolation_for_target_roles(client):
    headers_a = register_and_login(client, "user_isolated_a@example.com", "Candidate A")
    headers_b = register_and_login(client, "user_isolated_b@example.com", "Candidate B")

    client.put("/api/profile", headers=headers_a, json={
        "preferred_roles": ["Backend Developer", "Java Developer"]
    })
    client.put("/api/profile", headers=headers_b, json={
        "preferred_roles": ["Cybersecurity Analyst"]
    })

    profile_a = client.get("/api/profile", headers=headers_a).json()
    profile_b = client.get("/api/profile", headers=headers_b).json()

    assert profile_a["preferred_roles"] == ["Backend Developer", "Java Developer"]
    assert profile_b["preferred_roles"] == ["Cybersecurity Analyst"]
    assert "Cybersecurity Analyst" not in profile_a["preferred_roles"]
    assert "Backend Developer" not in profile_b["preferred_roles"]


# -------------------------------------------------------------------------
# Test 7: Target Role Matching Relevance Boost
# -------------------------------------------------------------------------
def test_target_role_matching_relevance_boost(client):
    headers = register_and_login(client, "candidate_targeting_backend@example.com", "Backend Candidate")

    client.put("/api/profile", headers=headers, json={
        "preferred_roles": ["Backend Developer"],
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Advanced"},
            {"skill_name": "FastAPI", "proficiency_level": "Intermediate"}
        ]
    })

    # Job A: Matches target role "Backend Developer"
    job_a_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Backend Developer",
        "company_name": "TechCore",
        "description": "Building microservices APIs with Python and FastAPI.",
        "required_skills": ["Python", "FastAPI"],
        "experience_level": "Entry-Level",
        "experience_years_required": 0.0
    })
    job_a_id = job_a_resp.json()["id"]

    match_a = client.post(f"/api/jobs/{job_a_id}/match", headers=headers).json()
    assert match_a["role_score"] == 20.0
    assert any("Target Role Match" in r for r in match_a["positive_reasons"])


# -------------------------------------------------------------------------
# Test 8: Unrelated Role Receives No Target Boost
# -------------------------------------------------------------------------
def test_unrelated_role_receives_no_target_boost(client):
    headers = register_and_login(client, "candidate_targeting_data@example.com", "Data Analyst Candidate")

    client.put("/api/profile", headers=headers, json={
        "preferred_roles": ["Data Analyst"],
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Intermediate"},
            {"skill_name": "SQL", "proficiency_level": "Advanced"}
        ]
    })

    # Job: Full Stack Developer (unrelated to candidate's Data Analyst target)
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Full Stack Developer",
        "company_name": "WebAgency",
        "description": "Looking for web developer with Python and SQL knowledge.",
        "required_skills": ["Python", "SQL"],
        "experience_level": "Entry-Level",
        "experience_years_required": 0.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers).json()
    # Must receive reduced role_score (6.0) due to target role mismatch
    assert match_resp["role_score"] == 6.0
    assert any("Target Role Mismatch" in r for r in match_resp["negative_reasons"])


# -------------------------------------------------------------------------
# Test 9: Canonical Role Aliases Handled Correctly
# -------------------------------------------------------------------------
def test_canonical_role_aliases(client):
    headers = register_and_login(client, "candidate_alias_test@example.com", "Alias Candidate")

    # Target: Backend Developer
    client.put("/api/profile", headers=headers, json={
        "preferred_roles": ["Backend Developer"],
        "skills": [{"skill_name": "Python", "proficiency_level": "Advanced"}]
    })

    # Job with alias title: "Backend Engineer"
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Backend Engineer",
        "company_name": "CloudScale",
        "description": "Backend software engineering.",
        "required_skills": ["Python"],
        "experience_level": "Entry-Level"
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers).json()
    # "Backend Engineer" is an alias of "Backend Developer" -> full 20.0
    assert match_resp["role_score"] == 20.0
    assert any("Target Role Match" in r for r in match_resp["positive_reasons"])


# -------------------------------------------------------------------------
# Test 10: Related Tech Family Partial Alignment
# -------------------------------------------------------------------------
def test_related_tech_family_partial_alignment(client):
    headers = register_and_login(client, "candidate_family_test@example.com", "Family Candidate")

    # Target: Python Developer (family: software_engineering)
    client.put("/api/profile", headers=headers, json={
        "preferred_roles": ["Python Developer"],
        "skills": [{"skill_name": "Python", "proficiency_level": "Advanced"}]
    })

    # Job in same family but different title: "Full Stack Engineer"
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Full Stack Engineer",
        "company_name": "OmniApp",
        "description": "Full stack engineering with Python.",
        "required_skills": ["Python"],
        "experience_level": "Entry-Level"
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers).json()
    # Related technical family receives 14.0 points (not 20.0, but not 6.0)
    assert match_resp["role_score"] == 14.0
    assert any("Related Role Focus" in r for r in match_resp["positive_reasons"])


# -------------------------------------------------------------------------
# Test 11: Substring Safety in Role Matching
# -------------------------------------------------------------------------
def test_substring_safety_in_role_matching():
    # Java Developer must NOT match JavaScript Developer
    is_match_js, _ = check_target_role_match("Senior JavaScript Developer", "Java Developer")
    assert not is_match_js, "Java Developer should not match JavaScript Developer"

    # Java Developer matches "Junior Java Developer"
    is_match_java, _ = check_target_role_match("Junior Java Developer", "Java Developer")
    assert is_match_java, "Java Developer should match Junior Java Developer"

    # C Developer must NOT match CSS Developer
    is_match_css, _ = check_target_role_match("CSS Developer", "C Developer")
    assert not is_match_css, "C Developer should not match CSS Developer"


# -------------------------------------------------------------------------
# Test 12: Missing Target Roles Preserves Baseline Behavior
# -------------------------------------------------------------------------
def test_missing_target_roles_preserves_baseline_behavior(client):
    headers = register_and_login(client, "candidate_no_roles@example.com", "General Candidate")

    client.put("/api/profile", headers=headers, json={
        "preferred_roles": [],
        "skills": [{"skill_name": "Python", "proficiency_level": "Intermediate"}]
    })

    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Software Engineer",
        "company_name": "General Tech",
        "description": "Software development opportunity.",
        "required_skills": ["Python"],
        "experience_level": "Entry-Level"
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers).json()
    # Baseline behavior: role in recognized IT family receives 20.0
    assert match_resp["role_score"] == 20.0
    assert any("target technical domain" in r.lower() for r in match_resp["positive_reasons"])


# -------------------------------------------------------------------------
# Test 13: Score Bounds and Reason Consistency
# -------------------------------------------------------------------------
def test_score_bounds_and_reason_consistency(client):
    headers = register_and_login(client, "candidate_bounds@example.com", "Bounds Candidate")

    client.put("/api/profile", headers=headers, json={
        "preferred_roles": ["Backend Developer"],
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Advanced"},
            {"skill_name": "FastAPI", "proficiency_level": "Advanced"},
            {"skill_name": "PostgreSQL", "proficiency_level": "Advanced"},
            {"skill_name": "Docker", "proficiency_level": "Advanced"}
        ],
        "education": "B.Tech in Information Technology",
        "experience_years": 0.5
    })

    # High match job
    job_resp = client.post("/api/jobs", headers=headers, json={
        "title": "Junior Backend Developer",
        "company_name": "TopTech",
        "description": "Entry level backend developer role.",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["PostgreSQL", "Docker"],
        "education_requirement": "B.Tech in Information Technology",
        "experience_level": "Entry-Level",
        "experience_years_required": 0.0
    })
    job_id = job_resp.json()["id"]

    match_resp = client.post(f"/api/jobs/{job_id}/match", headers=headers).json()
    assert 0.0 <= match_resp["match_score"] <= 100.0
    assert match_resp["match_score"] >= 85.0
    assert len(match_resp["positive_reasons"]) > 0
    assert any("Target Role Match" in r for r in match_resp["positive_reasons"])
