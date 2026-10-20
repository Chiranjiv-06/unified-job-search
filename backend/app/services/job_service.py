import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate
from app.services.resume_service import extract_skills_from_text

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 UnifiedJobSearchBot/1.0"


def extract_domain_from_url(url: Optional[str]) -> Optional[str]:
    """Extracts base registered domain name from a URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # Remove port if present
        return netloc.split(":")[0] if netloc else None
    except Exception:
        return None


def detect_source_platform(url: str) -> str:
    """Detects source job portal or sets to Careers Page / Web."""
    domain = extract_domain_from_url(url)
    if not domain:
        return "Web"
    
    if "linkedin" in domain:
        return "LinkedIn"
    if "naukri" in domain:
        return "Naukri"
    if "indeed" in domain:
        return "Indeed"
    if "foundit" in domain or "monster" in domain:
        return "Foundit"
    if "glassdoor" in domain:
        return "Glassdoor"
    if "wellfound" in domain or "angel" in domain:
        return "Wellfound"
    if "internshala" in domain:
        return "Internshala"
    if "github" in domain:
        return "GitHub Jobs"
    
    return "Careers Portal"


def get_or_create_company(db: Session, company_name: str, source_url: Optional[str] = None) -> Company:
    """
    Finds an existing company by case-insensitive name match or creates a new entry.
    """
    clean_name = company_name.strip()
    company = db.execute(
        select(Company).where(func.lower(Company.name) == func.lower(clean_name))
    ).scalar_one_or_none()

    if not company:
        domain = extract_domain_from_url(source_url)
        company = Company(
            name=clean_name,
            domain=domain,
            careers_url=source_url if domain else None,
            is_verified=False,
            fraud_score=0.0
        )
        db.add(company)
        db.flush()

    return company


def create_job(db: Session, job_in: JobCreate, user_id: Optional[int] = None) -> Job:
    """
    Creates a new job posting record and associates or creates its company.
    Auto-enriches technical skills if required_skills is empty.
    """
    company = get_or_create_company(db, job_in.company_name, job_in.source_url)

    # If required_skills not supplied, extract from description
    skills = list(job_in.required_skills or [])
    if not skills and job_in.description:
        skills = extract_skills_from_text(job_in.description)

    job = Job(
        company_id=company.id,
        title=job_in.title.strip(),
        company_name=company.name,
        description=job_in.description,
        required_skills=skills,
        preferred_skills=job_in.preferred_skills or [],
        experience_years_required=job_in.experience_years_required or 0.0,
        experience_level=job_in.experience_level or "Entry-Level",
        education_requirement=job_in.education_requirement,
        location=job_in.location,
        work_mode=job_in.work_mode or "Any",
        salary_min=job_in.salary_min,
        salary_max=job_in.salary_max,
        salary_currency=job_in.salary_currency or "INR",
        salary_range=job_in.salary_range,
        source_platform=job_in.source_platform or "Manual",
        source_url=job_in.source_url,
        posting_date=job_in.posting_date or datetime.now(timezone.utc),
        is_active=True,
        created_by_user_id=user_id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def parse_job_html_content(html: str, source_url: str) -> Dict[str, Any]:
    """
    Parses job posting HTML using Schema.org JobPosting JSON-LD or standard HTML meta tags.
    Extracts title, company, description, work mode, and technical skills.
    """
    soup = BeautifulSoup(html, "html.parser")
    parsed_data: Dict[str, Any] = {
        "title": "Imported Job Opportunity",
        "company_name": "Unknown Company",
        "description": "",
        "location": "Not Specified",
        "work_mode": "Any",
        "source_url": source_url,
        "source_platform": detect_source_platform(source_url),
        "required_skills": [],
        "experience_level": "Entry-Level"
    }

    # 1. Try Schema.org JobPosting JSON-LD
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    for script in json_ld_scripts:
        try:
            if not script.string:
                continue
            data = json.loads(script.string)
            # Could be a single object or a graph
            candidates = []
            if isinstance(data, dict):
                if data.get("@type") == "JobPosting":
                    candidates.append(data)
                elif "@graph" in data and isinstance(data["@graph"], list):
                    candidates.extend([c for c in data["@graph"] if c.get("@type") == "JobPosting"])
            elif isinstance(data, list):
                candidates.extend([c for c in data if isinstance(c, dict) and c.get("@type") == "JobPosting"])

            if candidates:
                jp = candidates[0]
                if jp.get("title"):
                    parsed_data["title"] = jp["title"].strip()
                if jp.get("hiringOrganization") and isinstance(jp["hiringOrganization"], dict):
                    parsed_data["company_name"] = jp["hiringOrganization"].get("name", "Unknown Company").strip()
                if jp.get("description"):
                    # Strip html tags from description if needed
                    desc_soup = BeautifulSoup(jp["description"], "html.parser")
                    parsed_data["description"] = desc_soup.get_text(separator="\n").strip()
                if jp.get("jobLocation"):
                    loc = jp["jobLocation"]
                    if isinstance(loc, dict) and "address" in loc:
                        addr = loc["address"]
                        if isinstance(addr, dict):
                            loc_str = ", ".join(filter(None, [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]))
                            if loc_str:
                                parsed_data["location"] = loc_str
                break
        except Exception as json_err:
            logger.debug("Failed parsing JSON-LD script: %s", json_err)

    # 2. Fallbacks from meta tags / headers if JSON-LD wasn't sufficient
    if parsed_data["title"] == "Imported Job Opportunity":
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            parsed_data["title"] = og_title["content"].strip()
        elif soup.title and soup.title.string:
            parsed_data["title"] = soup.title.string.strip()

    if parsed_data["company_name"] == "Unknown Company":
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            parsed_data["company_name"] = og_site["content"].strip()
        else:
            # Fallback to domain host name
            domain = extract_domain_from_url(source_url)
            if domain:
                parsed_data["company_name"] = domain.split(".")[0].capitalize()

    if not parsed_data["description"]:
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if meta_desc and meta_desc.get("content"):
            parsed_data["description"] = meta_desc["content"].strip()
        else:
            # Grab main text content from body paragraphs
            paragraphs = [p.get_text().strip() for p in soup.find_all(["p", "li"]) if len(p.get_text().strip()) > 20]
            parsed_data["description"] = "\n".join(paragraphs[:15])

    # 3. Detect work mode from description / title
    full_text_search = f"{parsed_data['title']} {parsed_data['description']}".lower()
    if re.search(r"\bremote\b|\bwork from home\b|\bwfh\b", full_text_search):
        parsed_data["work_mode"] = "Remote"
    elif re.search(r"\bhybrid\b", full_text_search):
        parsed_data["work_mode"] = "Hybrid"
    elif re.search(r"\bon-?site\b|\bin-?office\b", full_text_search):
        parsed_data["work_mode"] = "On-site"

    # 4. Extract required technical skills from the parsed description
    if parsed_data["description"]:
        parsed_data["required_skills"] = extract_skills_from_text(parsed_data["description"])

    return parsed_data


def import_job_from_url(db: Session, url: str, user_id: Optional[int] = None) -> Job:
    """
    Safely fetches and imports a job opportunity from a user-provided HTTP/HTTPS URL.
    Respects robots/terms, parses metadata, extracts skills, and saves job record.
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )

    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
            follow_redirects=True
        ) as client:
            resp = client.get(clean_url)
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target job URL returned HTTP status {resp.status_code}. The page may be private or removed."
                )
            html_text = resp.text
    except httpx.RequestError as exc:
        logger.error("Failed to connect to job URL %s: %s", clean_url, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to connect to the provided job URL. Network error: {str(exc)}"
        )

    parsed = parse_job_html_content(html_text, clean_url)

    job_create = JobCreate(
        title=parsed["title"],
        company_name=parsed["company_name"],
        description=parsed["description"],
        required_skills=parsed["required_skills"],
        preferred_skills=[],
        experience_years_required=0.0,
        experience_level=parsed["experience_level"],
        location=parsed["location"],
        work_mode=parsed["work_mode"],
        source_platform=parsed["source_platform"],
        source_url=clean_url,
        posting_date=datetime.now(timezone.utc)
    )

    return create_job(db, job_create, user_id)


def list_jobs(
    db: Session,
    q: Optional[str] = None,
    location: Optional[str] = None,
    work_mode: Optional[str] = None,
    skill: Optional[str] = None,
    company_id: Optional[int] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 20
) -> Tuple[List[Job], int]:
    """
    Searches and filters job records with multi-parameter criteria and pagination.
    """
    query = select(Job).where(Job.is_active == is_active)

    if q:
        term = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Job.title).like(term),
                func.lower(Job.company_name).like(term),
                func.lower(Job.description).like(term)
            )
        )

    if location:
        query = query.where(func.lower(Job.location).like(f"%{location.strip().lower()}%"))

    if work_mode and work_mode.lower() != "any":
        query = query.where(func.lower(Job.work_mode) == work_mode.strip().lower())

    if company_id:
        query = query.where(Job.company_id == company_id)

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()

    # Apply sorting and pagination
    query = query.order_by(desc(Job.created_at)).offset(skip).limit(limit)
    jobs = list(db.execute(query).scalars().all())

    # If skill filter was provided, filter memory list to ensure JSON array match
    if skill:
        skill_clean = skill.strip().lower()
        jobs = [
            j for j in jobs
            if any(skill_clean in s.lower() for s in (j.required_skills or []))
            or any(skill_clean in s.lower() for s in (j.preferred_skills or []))
        ]

    return jobs, total


def get_job_by_id(db: Session, job_id: int) -> Job:
    """Retrieves a single job by its ID or raises 404."""
    job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job opportunity with ID {job_id} not found."
        )
    return job


def update_job(db: Session, job_id: int, job_in: JobUpdate, user_id: Optional[int] = None) -> Job:
    """Updates an existing job posting record."""
    job = get_job_by_id(db, job_id)

    update_dict = job_in.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job_id: int) -> None:
    """Deactivates/soft-deletes a job posting."""
    job = get_job_by_id(db, job_id)
    job.is_active = False
    db.commit()
