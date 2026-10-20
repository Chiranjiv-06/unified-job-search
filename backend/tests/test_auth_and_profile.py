from datetime import timedelta
import pytest
from app.core.security import create_access_token

def test_registration_success(client):
    response = client.post("/api/auth/register", json={
        "full_name": "Pankaj Sharma",
        "email": "pankaj@example.com",
        "password": "StrongPassword123!"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "pankaj@example.com"
    assert data["full_name"] == "Pankaj Sharma"
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data

def test_duplicate_registration_rejected(client):
    # Register once
    client.post("/api/auth/register", json={
        "full_name": "Pankaj Sharma",
        "email": "duplicate@example.com",
        "password": "StrongPassword123!"
    })
    # Register again with same email
    response = client.post("/api/auth/register", json={
        "full_name": "Duplicate User",
        "email": "duplicate@example.com",
        "password": "AnotherPassword456!"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()

def test_login_success(client):
    client.post("/api/auth/register", json={
        "full_name": "Login User",
        "email": "login@example.com",
        "password": "CorrectPassword123!"
    })
    response = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "CorrectPassword123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"
    assert "access_token" in response.cookies

def test_login_incorrect_password_rejected(client):
    client.post("/api/auth/register", json={
        "full_name": "Wrong Pass User",
        "email": "wrongpass@example.com",
        "password": "CorrectPassword123!"
    })
    response = client.post("/api/auth/login", json={
        "email": "wrongpass@example.com",
        "password": "WrongPassword999!"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_login_nonexistent_email_rejected(client):
    response = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "SomePassword123!"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_current_user_me(client):
    client.post("/api/auth/register", json={
        "full_name": "Me User",
        "email": "me@example.com",
        "password": "Password123!"
    })
    login_res = client.post("/api/auth/login", json={
        "email": "me@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    
    # Access /api/auth/me with Bearer token
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"

def test_unauthenticated_access_rejected(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_invalid_and_expired_tokens(client):
    # Invalid token
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.payload"})
    assert response.status_code == 401
    assert "invalid or expired" in response.json()["detail"].lower()

    # Expired token
    expired_token = create_access_token({"sub": "me@example.com"}, expires_delta=timedelta(seconds=-10))
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "invalid or expired" in response.json()["detail"].lower()

def test_profile_creation_and_update(client):
    client.post("/api/auth/register", json={
        "full_name": "Profile User",
        "email": "profile@example.com",
        "password": "Password123!"
    })
    login_res = client.post("/api/auth/login", json={
        "email": "profile@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch initial profile
    get_res = client.get("/api/profile", headers=headers)
    assert get_res.status_code == 200
    profile_data = get_res.json()
    assert profile_data["experience_level"] == "Entry-Level"

    # Update profile with education, preferences, and skills
    update_res = client.put("/api/profile", headers=headers, json={
        "education": "B.Tech in Information Technology",
        "experience_level": "Entry-Level",
        "preferred_roles": "Software Engineer, Full Stack Developer",
        "preferred_locations": "Bengaluru, Pune, Remote",
        "preferred_work_mode": "Hybrid",
        "salary_expectation": "6-10 LPA",
        "skills": [
            {"skill_name": "Python", "proficiency_level": "Advanced"},
            {"skill_name": "React", "proficiency_level": "Intermediate"},
            {"skill_name": "SQL", "proficiency_level": "Intermediate"}
        ]
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["education"] == "B.Tech in Information Technology"
    assert updated["preferred_work_mode"] == "Hybrid"
    assert len(updated["skills"]) == 3
    skill_names = [s["skill_name"] for s in updated["skills"]]
    assert "Python" in skill_names
    assert "React" in skill_names

def test_user_isolation(client):
    # Register User A
    client.post("/api/auth/register", json={
        "full_name": "User Alpha",
        "email": "alpha@example.com",
        "password": "Password123!"
    })
    token_a = client.post("/api/auth/login", json={
        "email": "alpha@example.com",
        "password": "Password123!"
    }).json()["access_token"]

    # Register User B
    client.post("/api/auth/register", json={
        "full_name": "User Beta",
        "email": "beta@example.com",
        "password": "Password123!"
    })
    token_b = client.post("/api/auth/login", json={
        "email": "beta@example.com",
        "password": "Password123!"
    }).json()["access_token"]

    # User A updates their profile
    client.put("/api/profile", headers={"Authorization": f"Bearer {token_a}"}, json={
        "education": "IIT Bombay - Computer Science",
        "preferred_roles": "AI Researcher"
    })

    # User B checks their profile - must not see User A's data
    profile_b = client.get("/api/profile", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert profile_b["education"] != "IIT Bombay - Computer Science"
    assert profile_b["preferred_roles"] != "AI Researcher"
