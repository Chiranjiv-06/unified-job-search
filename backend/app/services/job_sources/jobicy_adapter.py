import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings
from app.services.job_sources.base import BaseJobSourceAdapter, clean_html_text, validate_web_url, USER_AGENT
from app.services.resume_service import extract_skills_from_text

logger = logging.getLogger(__name__)


class JobicyAdapter(BaseJobSourceAdapter):
    """
    Adapter for the official public Jobicy REST API.
    Provides verified remote engineering, developer, and tech listings worldwide.
    """
    source_name: str = "Jobicy"

    def is_enabled(self) -> bool:
        return bool(settings.JOBICY_ENABLED)

    def fetch_raw_listings(self, limit: int = 20) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        }
        url = settings.JOBICY_API_URL
        params = {"count": min(limit, 50)}

        with httpx.Client(timeout=self.request_timeout, follow_redirects=True) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Handle {"jobs": [...]} format
        if isinstance(data, dict):
            raw_jobs = data.get("jobs", [])
        elif isinstance(data, list):
            raw_jobs = data
        else:
            logger.warning("Jobicy API returned unexpected root type: %s", type(data))
            return []

        listings: List[Dict[str, Any]] = []
        for item in raw_jobs:
            if isinstance(item, dict) and item.get("jobTitle") and item.get("companyName"):
                listings.append(item)
                if len(listings) >= limit:
                    break

        return listings

    def normalize_listing(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None

        title = str(raw.get("jobTitle") or "").strip()
        company = str(raw.get("companyName") or "").strip()
        if not title or not company:
            return None

        # Clean description HTML
        raw_desc = raw.get("jobDescription") or raw.get("jobExcerpt") or ""
        clean_desc = clean_html_text(str(raw_desc))

        # External IDs and URLs
        raw_id = raw.get("id")
        external_id = str(raw_id).strip() if raw_id is not None and str(raw_id).strip() else None

        source_url = validate_web_url(raw.get("url"))

        # Skills from title and description
        extracted_skills = [s.strip().lower() for s in extract_skills_from_text(f"{title} {clean_desc}")]

        # Employment type
        raw_type = raw.get("jobType")
        employment_type = "Full-time"
        if isinstance(raw_type, list) and raw_type:
            raw_type_str = str(raw_type[0]).lower()
        elif isinstance(raw_type, str):
            raw_type_str = raw_type.lower()
        else:
            raw_type_str = ""

        if "contract" in raw_type_str or "freelance" in raw_type_str:
            employment_type = "Contract"
        elif "part-time" in raw_type_str or "part time" in raw_type_str:
            employment_type = "Part-time"
        elif "intern" in raw_type_str:
            employment_type = "Internship"

        # Experience level
        raw_level = str(raw.get("jobLevel") or "").strip()
        if raw_level:
            experience_level = raw_level
        else:
            t_low = title.lower()
            if "intern" in t_low:
                experience_level = "Intern"
            elif any(k in t_low for k in ("lead", "staff", "principal", "director")):
                experience_level = "Lead"
            elif "senior" in t_low:
                experience_level = "Senior"
            elif any(k in t_low for k in ("junior", "entry", "associate")):
                experience_level = "Entry-Level"
            else:
                experience_level = "Mid-Level"

        # Salary parsing with sanity validation
        sal_min = None
        sal_max = None
        currency = str(raw.get("salaryCurrency") or "USD").strip().upper()
        try:
            if raw.get("annualSalaryMin") is not None and str(raw["annualSalaryMin"]).strip():
                sal_min = float(raw["annualSalaryMin"])
            if raw.get("annualSalaryMax") is not None and str(raw["annualSalaryMax"]).strip():
                sal_max = float(raw["annualSalaryMax"])
            if sal_min is not None and sal_max is not None and sal_min > sal_max:
                sal_min, sal_max = sal_max, sal_min
        except (ValueError, TypeError):
            pass

        salary_range = None
        if sal_min is not None and sal_max is not None:
            salary_range = f"${int(sal_min):,} - ${int(sal_max):,} {currency}"
        elif sal_min is not None:
            salary_range = f"From ${int(sal_min):,} {currency}"

        # Date parsing
        posting_date = None
        raw_date = raw.get("pubDate")
        if raw_date:
            try:
                # Jobicy format: "2026-10-25 08:30:00" or ISO
                posting_date = datetime.fromisoformat(str(raw_date).replace(" ", "T"))
                if posting_date.tzinfo is None:
                    posting_date = posting_date.replace(tzinfo=timezone.utc)
            except Exception:
                try:
                    from email.utils import parsedate_to_datetime
                    posting_date = parsedate_to_datetime(str(raw_date))
                except Exception:
                    posting_date = datetime.now(timezone.utc)
        else:
            posting_date = datetime.now(timezone.utc)

        location = str(raw.get("jobGeo") or "Remote / Anywhere").strip()

        return {
            "title": title[:255],
            "company_name": company[:255],
            "description": clean_desc,
            "required_skills": extracted_skills[:20],
            "preferred_skills": [],
            "experience_years_required": 0.0,
            "experience_level": experience_level[:50],
            "education_requirement": None,
            "employment_type": employment_type,
            "location": location[:255],
            "work_mode": "Remote",
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": currency[:10],
            "salary_range": salary_range,
            "source_platform": self.source_name,
            "source_url": source_url,
            "company_url": None,
            "external_id": external_id,
            "posting_date": posting_date,
            "first_seen_at": datetime.now(timezone.utc),
            "last_seen_at": datetime.now(timezone.utc),
            "is_expired": False,
            "import_status": "active",
            "raw_metadata": {
                "jobicy_id": external_id,
                "company_logo": raw.get("companyLogo"),
                "job_geo": raw.get("jobGeo"),
                "job_level": raw.get("jobLevel")
            }
        }
