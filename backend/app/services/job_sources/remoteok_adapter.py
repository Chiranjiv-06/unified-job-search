import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings
from app.services.job_sources.base import BaseJobSourceAdapter, clean_html_text, validate_web_url, USER_AGENT
from app.services.resume_service import extract_skills_from_text

logger = logging.getLogger(__name__)


class RemoteOKAdapter(BaseJobSourceAdapter):
    """
    Adapter for the official public RemoteOK developer API.
    Provides structured listings for remote software, DevOps, and technical roles.
    """
    source_name: str = "RemoteOK"

    def is_enabled(self) -> bool:
        return bool(settings.REMOTEOK_ENABLED)

    def fetch_raw_listings(self, limit: int = 20) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        }
        url = settings.REMOTEOK_API_URL

        with httpx.Client(timeout=self.request_timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, list):
            logger.warning("RemoteOK API returned non-list root response: %s", type(data))
            return []

        # Filter out header legal/meta element and collect up to requested limit
        listings: List[Dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict) and item.get("position") and item.get("company"):
                listings.append(item)
                if len(listings) >= limit:
                    break

        return listings

    def normalize_listing(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None

        title = str(raw.get("position") or "").strip()
        company = str(raw.get("company") or "").strip()
        if not title or not company:
            return None

        # Clean description HTML
        raw_desc = raw.get("description") or ""
        clean_desc = clean_html_text(str(raw_desc))

        # External IDs and URLs
        raw_id = raw.get("id")
        external_id = str(raw_id).strip() if raw_id is not None and str(raw_id).strip() else None

        source_url = validate_web_url(raw.get("url") or raw.get("apply_url"))
        if not source_url and external_id:
            source_url = f"https://remoteok.com/remote-jobs/{external_id}"

        company_url = validate_web_url(raw.get("company_url"))

        # Skills from tags + text analysis
        raw_tags = raw.get("tags")
        if isinstance(raw_tags, list):
            tags_skills = [str(t).strip().lower() for t in raw_tags if isinstance(t, (str, int)) and str(t).strip()]
        elif isinstance(raw_tags, str) and raw_tags.strip():
            tags_skills = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
        else:
            tags_skills = []

        extracted_skills = extract_skills_from_text(f"{title} {clean_desc}")

        # Merge tags and extracted skills uniquely
        combined_skills = list(dict.fromkeys(tags_skills + extracted_skills))

        # Employment type from tags
        employment_type = "Full-time"
        for tag in tags_skills:
            if "contract" in tag or "freelance" in tag:
                employment_type = "Contract"
                break
            elif "part-time" in tag or "part time" in tag:
                employment_type = "Part-time"
                break
            elif "intern" in tag:
                employment_type = "Internship"
                break

        # Salary parsing with sanity validation
        sal_min = None
        sal_max = None
        try:
            if raw.get("salary_min") is not None and str(raw["salary_min"]).strip():
                sal_min = float(raw["salary_min"])
            if raw.get("salary_max") is not None and str(raw["salary_max"]).strip():
                sal_max = float(raw["salary_max"])
            if sal_min is not None and sal_max is not None and sal_min > sal_max:
                sal_min, sal_max = sal_max, sal_min
        except (ValueError, TypeError):
            pass

        salary_range = None
        if sal_min is not None and sal_max is not None:
            salary_range = f"${int(sal_min):,} - ${int(sal_max):,} USD"
        elif sal_min is not None:
            salary_range = f"From ${int(sal_min):,} USD"

        # Robust Date parsing (ISO string, epoch timestamp, or fallback)
        posting_date = None
        raw_date = raw.get("date")
        raw_epoch = raw.get("epoch")
        if raw_date:
            try:
                posting_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            except Exception:
                pass

        if not posting_date and raw_epoch:
            try:
                posting_date = datetime.fromtimestamp(float(raw_epoch), tz=timezone.utc)
            except Exception:
                pass

        if not posting_date and raw_date:
            try:
                posting_date = datetime.fromtimestamp(float(raw_date), tz=timezone.utc)
            except Exception:
                pass

        if not posting_date:
            posting_date = datetime.now(timezone.utc)

        location = str(raw.get("location") or "Remote / Worldwide").strip()

        # Experience level classification from title
        t_low = title.lower()
        if "intern" in t_low:
            exp_level = "Intern"
        elif any(k in t_low for k in ("lead", "staff", "principal", "director", "head")):
            exp_level = "Lead"
        elif "senior" in t_low:
            exp_level = "Senior"
        elif any(k in t_low for k in ("junior", "entry", "associate")):
            exp_level = "Entry-Level"
        else:
            exp_level = "Mid-Level"

        return {
            "title": title[:255],
            "company_name": company[:255],
            "description": clean_desc,
            "required_skills": combined_skills[:20],
            "preferred_skills": [],
            "experience_years_required": 0.0,
            "experience_level": exp_level,
            "education_requirement": None,
            "employment_type": employment_type,
            "location": location[:255],
            "work_mode": "Remote",
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": "USD",
            "salary_range": salary_range,
            "source_platform": self.source_name,
            "source_url": source_url,
            "company_url": company_url,
            "external_id": external_id,
            "posting_date": posting_date,
            "first_seen_at": datetime.now(timezone.utc),
            "last_seen_at": datetime.now(timezone.utc),
            "is_expired": False,
            "import_status": "active",
            "raw_metadata": {
                "remoteok_id": external_id,
                "tags": raw_tags if isinstance(raw_tags, list) else [],
                "epoch": raw.get("epoch"),
                "apply_url": raw.get("apply_url")
            }
        }
