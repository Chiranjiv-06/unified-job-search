from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.main import app
from app.db.session import get_db

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Unified Job Search" in data["app"]

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data

def test_health_check_db_connected():
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

def test_health_check_db_failure_returns_503():
    # Mock database session failure to verify 503 response and no secret leakage
    mock_db = MagicMock()
    mock_db.execute.side_effect = OperationalError("connection failure", params=None, orig=Exception("Connection refused"))
    
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/health/db")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"] == "Database service unavailable"
        assert "password" not in response.text.lower()
        assert "refused" not in response.text.lower()
    finally:
        app.dependency_overrides.clear()
