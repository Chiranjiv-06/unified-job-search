import io
import pytest
from app.core.security import create_access_token

SAMPLE_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 85 >>
stream
BT
/F1 12 Tf
100 700 Td
(Software Engineer skilled in Python, React, PostgreSQL, Docker, and FastAPI.) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000379 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
456
%%EOF
"""

def register_and_login(client, email: str, name: str = "Test Candidate") -> dict:
    """Helper to register user, log in, and return Authorization headers"""
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": name
        }
    )
    assert reg_resp.status_code == 201

    login_resp = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "Password123!"
        }
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_resume_upload_unauthenticated_rejected(client):
    """Unauthenticated requests to /api/profile/resume must be rejected with 401."""
    files = {"file": ("resume.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")}
    response = client.post("/api/profile/resume", files=files)
    assert response.status_code == 401
    assert "Authentication credentials were not provided" in response.json()["detail"]


def test_resume_upload_invalid_mime_type_rejected(client):
    """Non-PDF file uploads must be rejected with 400 Bad Request."""
    headers = register_and_login(client, "mime_test@example.com")
    
    # 1. Plain text file
    files = {"file": ("resume.txt", io.BytesIO(b"Hello world text file"), "text/plain")}
    response = client.post("/api/profile/resume", headers=headers, files=files)
    assert response.status_code == 400
    assert "Only PDF documents" in response.json()["detail"]

    # 2. PDF filename with disallowed MIME type
    files = {"file": ("resume.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "image/png")}
    response = client.post("/api/profile/resume", headers=headers, files=files)
    assert response.status_code == 400
    assert "Invalid MIME type" in response.json()["detail"]


def test_resume_upload_oversized_file_rejected(client):
    """Files exceeding 5MB must be rejected with 400 Bad Request."""
    headers = register_and_login(client, "oversized_test@example.com")
    
    # Create fake oversized content (> 5MB) starting with PDF magic bytes
    oversized_bytes = b"%PDF-" + (b"0" * (5 * 1024 * 1024 + 100))
    files = {"file": ("huge_resume.pdf", io.BytesIO(oversized_bytes), "application/pdf")}
    
    response = client.post("/api/profile/resume", headers=headers, files=files)
    assert response.status_code == 400
    assert "exceeds maximum allowed limit of 5MB" in response.json()["detail"]


def test_resume_upload_corrupt_pdf_rejected(client):
    """Invalid/corrupt PDF contents must be rejected gracefully with 400."""
    headers = register_and_login(client, "corrupt_test@example.com")
    
    files = {"file": ("corrupt.pdf", io.BytesIO(b"Not a real pdf at all"), "application/pdf")}
    response = client.post("/api/profile/resume", headers=headers, files=files)
    assert response.status_code == 400
    assert "Corrupted or invalid PDF" in response.json()["detail"]


def test_resume_upload_and_skill_extraction_success(client):
    """Valid PDF upload extracts text and returns draft skills without blindly overwriting profile."""
    headers = register_and_login(client, "resume_candidate@example.com")
    
    files = {"file": ("valid_resume.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")}
    response = client.post("/api/profile/resume", headers=headers, files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "valid_resume.pdf"
    assert data["pages_parsed"] >= 1
    assert "Python" in data["extracted_skills"]
    assert "FastAPI" in data["extracted_skills"]
    assert "PostgreSQL" in data["extracted_skills"]
    assert "Docker" in data["extracted_skills"]
    assert "React" in data["extracted_skills"]
    
    # Candidate Review Rule: Draft suggestions are returned
    assert len(data["draft_suggestions"]) >= 5
    draft_names = [d["skill_name"] for d in data["draft_suggestions"]]
    assert "Python" in draft_names
    
    # Verify profile does NOT automatically overwrite active profile skills
    profile_resp = client.get("/api/profile", headers=headers)
    assert profile_resp.status_code == 200
    profile_data = profile_resp.json()
    # Confirmed skills should remain empty or as previously set
    assert len(profile_data["skills"]) == 0
    # But raw_resume_text and parsed_skills metadata are stored
    assert "Software Engineer skilled in Python" in profile_data["raw_resume_text"]
    assert "Python" in profile_data["parsed_skills"]


def test_confirm_candidate_skills_review_flow(client):
    """Candidate can review draft skills and confirm selected skills."""
    headers = register_and_login(client, "confirm_skills@example.com")
    
    # 1. Upload resume to generate draft
    files = {"file": ("candidate_cv.pdf", io.BytesIO(SAMPLE_PDF_BYTES), "application/pdf")}
    upload_resp = client.post("/api/profile/resume", headers=headers, files=files)
    assert upload_resp.status_code == 200
    
    # 2. Candidate chooses to confirm Python and FastAPI with custom proficiencies
    confirmed_skills = [
        {"skill_name": "Python", "proficiency_level": "Expert"},
        {"skill_name": "FastAPI", "proficiency_level": "Advanced"}
    ]
    confirm_resp = client.post(
        "/api/profile/confirm-skills",
        headers=headers,
        json={"skills": confirmed_skills}
    )
    assert confirm_resp.status_code == 200
    updated_profile = confirm_resp.json()
    
    saved_skills = {s["skill_name"]: s["proficiency_level"] for s in updated_profile["skills"]}
    assert saved_skills.get("Python") == "Expert"
    assert saved_skills.get("FastAPI") == "Advanced"
    assert "Docker" not in saved_skills  # Excluded draft was not blindly added
