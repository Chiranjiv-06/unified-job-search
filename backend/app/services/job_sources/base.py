import abc
import logging
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import httpx

from app.core.config import settings
from app.services.resume_service import extract_skills_from_text

logger = logging.getLogger(__name__)

USER_AGENT = "UnifiedJobSearch/1.0 (+https://github.com/Chiranjiv-06/unified-job-search)"


def clean_html_text(raw_html: Optional[str]) -> str:
    """Strips HTML tags and normalizes whitespace."""
    if not raw_html:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        # Remove script and style tags
        for element in soup(["script", "style", "noscript"]):
            element.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()
    except Exception:
        clean = re.sub(r"<[^>]+>", " ", raw_html)
        return re.sub(r"\s+", " ", clean).strip()


def validate_web_url(url: Optional[str]) -> Optional[str]:
    """Validates that a URL is a syntactically valid HTTP/HTTPS link."""
    if not url or not isinstance(url, str):
        return None
    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
        if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
            return cleaned
    except Exception:
        pass
    return None


class BaseJobSourceAdapter(abc.ABC):
    """
    Abstract base class for all external job board and feed adapters.
    Enforces standardized contract for fetching, normalizing, error handling, and rate limiting.
    """
    source_name: str = "BaseSource"
    request_timeout: float = 8.0

    @abc.abstractmethod
    def is_enabled(self) -> bool:
        """Returns True if the source is active and configured in settings."""
        pass

    @abc.abstractmethod
    def fetch_raw_listings(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetches raw job listings from the source API or feed.
        Must handle network errors and timeouts gracefully without crashing.
        """
        pass

    @abc.abstractmethod
    def normalize_listing(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Maps raw source data into the common job schema dictionary.
        Returns None if listing is invalid, missing required fields, or unparseable.
        """
        pass

    def fetch_and_normalize(self, limit: int = 20) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Executes fetch and normalization pipeline, returning normalized records and execution stats.
        """
        stats: Dict[str, Any] = {
            "source": self.source_name,
            "enabled": self.is_enabled(),
            "fetched": 0,
            "normalized": 0,
            "skipped": 0,
            "error": None,
            "duration_ms": 0
        }

        if not self.is_enabled():
            stats["error"] = f"{self.source_name} adapter is disabled in configuration."
            logger.info("Skipping disabled job source adapter: %s", self.source_name)
            return [], stats

        start_time = time.time()
        try:
            raw_listings = self.fetch_raw_listings(limit=limit)
            stats["fetched"] = len(raw_listings)

            normalized_list: List[Dict[str, Any]] = []
            for item in raw_listings:
                try:
                    norm = self.normalize_listing(item)
                    if norm and norm.get("title") and norm.get("company_name"):
                        normalized_list.append(norm)
                        stats["normalized"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception as norm_err:
                    logger.debug("Failed to normalize listing from %s: %s", self.source_name, norm_err)
                    stats["skipped"] += 1

            stats["duration_ms"] = int((time.time() - start_time) * 1000)
            return normalized_list, stats

        except Exception as exc:
            duration = int((time.time() - start_time) * 1000)
            stats["duration_ms"] = duration
            stats["error"] = str(exc)
            logger.error("Job source adapter [%s] failed during execution: %s", self.source_name, exc)
            return [], stats
