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


def test_login_and_logout_cookie_lifecycle(client):
    """Verifies that login sets HttpOnly cookie and logout clears it."""
    client.post("/api/auth/register", json={
        "full_name": "Cookie User",
        "email": "cookie_tester@example.com",
        "password": "Password123!"
    })
    login_res = client.post("/api/auth/login", json={
        "email": "cookie_tester@example.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.cookies

    # Access /api/auth/me using the cookie (without Authorization header)
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "cookie_tester@example.com"

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # Cookie is invalidated/cleared
    cookie_val = client.cookies.get("access_token")
    assert cookie_val is None or cookie_val == ""


def test_rate_limiter_blocks_excessive_requests(client):
    """Verifies that exceeding rate limit threshold returns 429 Too Many Requests."""
    from unittest.mock import patch, MagicMock

    mock_redis = MagicMock()
    mock_redis.incr.return_value = 25  # Exceeds max_requests of 20
    mock_redis.ttl.return_value = 45

    with patch("app.core.rate_limiter.get_redis_client", return_value=mock_redis):
        res = client.post("/api/auth/login", json={
            "email": "ratelimit@example.com",
            "password": "Password123!"
        })
        assert res.status_code == 429
        assert "Too many requests" in res.json()["detail"]
        assert "Retry-After" in res.headers


def test_rate_limiter_fails_open_when_redis_offline(client):
    """Verifies that rate limiter fails open without blocking requests if Redis is offline."""
    from unittest.mock import patch

    with patch("app.core.rate_limiter.get_redis_client", return_value=None):
        res = client.post("/api/auth/login", json={
            "email": "nonexistent_failopen@example.com",
            "password": "Password123!"
        })
        # Fails open: returns normal business logic 401 instead of crashing with 500 or 429
        assert res.status_code == 401


def test_rate_limiter_trusted_proxy_and_client_ip_resolution(client):
    """
    Verifies that client IPs behind trusted proxies are resolved correctly,
    spoofed headers from untrusted direct peers are ignored,
    and multiple clients receive independent rate limiting counters.
    """
    from unittest.mock import patch, MagicMock
    from fastapi import Request
    from app.core.rate_limiter import get_client_ip

    trusted = ["127.0.0.1", "172.16.0.0/12"]

    # 1. Direct request without proxy headers -> uses direct peer IP
    scope_direct = {"type": "http", "client": ("203.0.113.10", 54321), "headers": []}
    req_direct = Request(scope_direct)
    assert get_client_ip(req_direct, trusted_proxies=trusted) == "203.0.113.10"

    # 2. Untrusted peer sending spoofed X-Forwarded-For -> ignores header, uses direct peer IP
    scope_spoof = {
        "type": "http",
        "client": ("198.51.100.55", 54321),
        "headers": [(b"x-forwarded-for", b"8.8.8.8, 1.1.1.1")]
    }
    req_spoof = Request(scope_spoof)
    assert get_client_ip(req_spoof, trusted_proxies=trusted) == "198.51.100.55"

    # 3. Trusted reverse proxy (e.g. Nginx at 172.18.0.2) forwarding valid client IP
    scope_proxy = {
        "type": "http",
        "client": ("172.18.0.2", 8000),
        "headers": [(b"x-forwarded-for", b"203.0.113.77")]
    }
    req_proxy = Request(scope_proxy)
    assert get_client_ip(req_proxy, trusted_proxies=trusted) == "203.0.113.77"

    # 4. Trusted proxy chain with internal proxy hops -> selects rightmost untrusted IP
    scope_chain = {
        "type": "http",
        "client": ("172.18.0.2", 8000),
        "headers": [(b"x-forwarded-for", b"198.51.100.1, 203.0.113.99, 172.18.0.10")]
    }
    req_chain = Request(scope_chain)
    assert get_client_ip(req_chain, trusted_proxies=trusted) == "203.0.113.99"

    # 5. Trusted proxy with X-Real-IP fallback
    scope_real_ip = {
        "type": "http",
        "client": ("127.0.0.1", 8000),
        "headers": [(b"x-real-ip", b"203.0.113.88")]
    }
    req_real_ip = Request(scope_real_ip)
    assert get_client_ip(req_real_ip, trusted_proxies=trusted) == "203.0.113.88"

    # 6. End-to-end integration: Two clients behind trusted Nginx get distinct rate limiting keys
    mock_redis = MagicMock()
    redis_keys = []

    def mock_incr(key):
        redis_keys.append(key)
        return len(redis_keys)

    mock_redis.incr.side_effect = mock_incr
    mock_redis.ttl.return_value = 60

    with patch("app.core.rate_limiter.get_redis_client", return_value=mock_redis):
        # Client 1 behind Nginx
        client.post(
            "/api/auth/login",
            headers={"X-Forwarded-For": "203.0.113.1"},
            json={"email": "c1@example.com", "password": "Password123!"}
        )
        # Client 2 behind Nginx
        client.post(
            "/api/auth/login",
            headers={"X-Forwarded-For": "203.0.113.2"},
            json={"email": "c2@example.com", "password": "Password123!"}
        )

    assert "rl:login:203.0.113.1" in redis_keys
    assert "rl:login:203.0.113.2" in redis_keys


