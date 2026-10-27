import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, desc

from app.models.company import Company
from app.models.job import Job
from app.core.config import settings
from app.services.application_service import ApplicationService
from app.services.job_sources import BaseJobSourceAdapter, RemoteOKAdapter, JobicyAdapter

logger = logging.getLogger(__name__)

TRACKING_PARAM_PATTERNS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid"
}


def normalize_job_url(raw_url: Optional[str]) -> Optional[str]:
    """
    Cleans tracking parameters (utm_*, ref) and standardizes URL format for reliable deduplication.
    """
    if not raw_url or not isinstance(raw_url, str):
        return None
    try:
        parsed = urlparse(raw_url.strip())
        if not parsed.scheme or not parsed.netloc:
            return None

        # Filter out tracking query parameters
        filtered_queries = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAM_PATTERNS
        ]
        new_query = urlencode(filtered_queries)

        # Remove trailing slash from path for consistency
        clean_path = parsed.path.rstrip("/")
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            parsed.params,
            new_query,
            ""  # Strip fragment
        ))
        return normalized
    except Exception:
        return raw_url.strip()


class JobIngestionService:
    """
    Orchestrates multi-source job ingestion, multi-tier deduplication,
    in-place freshness updates, and source status reporting.
    """
    _registered_adapters: Dict[str, BaseJobSourceAdapter] = {
        "remoteok": RemoteOKAdapter(),
        "jobicy": JobicyAdapter()
    }

    # In-memory execution telemetry cache
    _source_stats: Dict[str, Dict[str, Any]] = {
        "remoteok": {
            "name": "RemoteOK",
            "enabled": True,
            "status": "ready",
            "last_sync_at": None,
            "last_sync_fetched": 0,
            "last_sync_imported": 0,
            "last_sync_updated": 0,
            "last_sync_skipped": 0,
            "total_fetched": 0,
            "total_imported": 0,
            "total_updated": 0,
            "total_skipped": 0,
            "last_error": None
        },
        "jobicy": {
            "name": "Jobicy",
            "enabled": True,
            "status": "ready",
            "last_sync_at": None,
            "last_sync_fetched": 0,
            "last_sync_imported": 0,
            "last_sync_updated": 0,
            "last_sync_skipped": 0,
            "total_fetched": 0,
            "total_imported": 0,
            "total_updated": 0,
            "total_skipped": 0,
            "last_error": None
        }
    }

    @classmethod
    def get_registered_adapters(cls) -> Dict[str, BaseJobSourceAdapter]:
        return cls._registered_adapters

    @classmethod
    def get_sources_status(cls, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Returns real-time status, health, and sync metrics for all job sources.
        """
        sources_status: List[Dict[str, Any]] = []
        for key, adapter in cls._registered_adapters.items():
            stats = dict(cls._source_stats.get(key, {}))
            is_enabled = adapter.is_enabled()
            stats["enabled"] = is_enabled
            if not is_enabled:
                stats["status"] = "disabled"
            sources_status.append(stats)

        total_jobs = 0
        if db:
            try:
                total_jobs = db.execute(select(func.count(Job.id))).scalar_one()
            except Exception:
                pass

        return {
            "sources": sources_status,
            "total_jobs": total_jobs,
            "active_sources_count": len([s for s in sources_status if s["enabled"]])
        }

    @classmethod
    def find_existing_duplicate_job(
        cls,
        db: Session,
        norm_job: Dict[str, Any]
    ) -> Optional[Job]:
        """
        Multi-tier deduplication algorithm:
        1. Exact match on (source_platform, external_id) if external_id is present.
        2. Exact match on normalized source_url.
        3. Conservative match on (company_name, title, location) within 60 days.
        Uses scalars().first() to avoid MultipleResultsFound when duplicate candidates exist.
        """
        source = norm_job.get("source_platform")
        ext_id = norm_job.get("external_id")
        source_url = norm_job.get("source_url")
        norm_url = normalize_job_url(source_url)
        company = (norm_job.get("company_name") or "").strip().lower()
        title = (norm_job.get("title") or "").strip().lower()
        location = (norm_job.get("location") or "").strip().lower()

        # Tier 1: Source + External ID match
        if source and ext_id:
            existing = db.execute(
                select(Job).where(
                    Job.source_platform == source,
                    Job.external_id == str(ext_id).strip()
                )
            ).scalars().first()
            if existing:
                return existing

        # Tier 2: Normalized source URL match
        if norm_url:
            parsed_norm = urlparse(norm_url)
            # Only use .like() prefix matching if the URL contains a substantive resource path
            if parsed_norm.path and len(parsed_norm.path.strip("/")) > 3:
                existing_url = db.execute(
                    select(Job).where(
                        or_(
                            Job.source_url == source_url,
                            Job.source_url == norm_url,
                            Job.source_url.like(f"{norm_url}%")
                        )
                    )
                ).scalars().first()
            else:
                existing_url = db.execute(
                    select(Job).where(
                        or_(
                            Job.source_url == source_url,
                            Job.source_url == norm_url
                        )
                    )
                ).scalars().first()
            if existing_url:
                return existing_url

        # Tier 3: Conservative Title + Company + Location match
        if company and title:
            sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)
            existing_fuzzy = db.execute(
                select(Job).where(
                    func.lower(Job.company_name) == company,
                    func.lower(Job.title) == title,
                    func.lower(Job.location) == location,
                    Job.created_at >= sixty_days_ago
                )
            ).scalars().first()
            if existing_fuzzy:
                return existing_fuzzy

        return None

    @classmethod
    def upsert_normalized_job(
        cls,
        db: Session,
        norm_job: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Tuple[Job, str]:
        """
        Inserts new job or safely updates existing job in-place.
        Returns (job_instance, 'imported' | 'updated').
        """
        now = datetime.now(timezone.utc)
        existing = cls.find_existing_duplicate_job(db, norm_job)

        if existing:
            # Update freshness & metadata in place
            existing.last_seen_at = now
            existing.is_expired = False
            existing.is_active = True
            existing.import_status = "active"

            # Update description if currently empty or updated
            if norm_job.get("description") and (not existing.description or len(norm_job["description"]) > len(existing.description)):
                existing.description = norm_job["description"]

            # Update salary if newly available
            if norm_job.get("salary_range") and not existing.salary_range:
                existing.salary_range = norm_job["salary_range"]
                existing.salary_min = norm_job.get("salary_min")
                existing.salary_max = norm_job.get("salary_max")
                existing.salary_currency = norm_job.get("salary_currency", "INR")

            # Update employment type if available
            if norm_job.get("employment_type") and not existing.employment_type:
                existing.employment_type = norm_job["employment_type"]

            # Merge raw metadata safely
            meta = dict(existing.raw_metadata or {})
            meta.update(norm_job.get("raw_metadata") or {})
            existing.raw_metadata = meta

            db.commit()
            db.refresh(existing)
            return existing, "updated"

        # Resolve or create associated Company
        company = ApplicationService.resolve_or_create_company(
            db=db,
            company_name=norm_job.get("company_name")
        )
        company_id = company.id if company else None

        new_job = Job(
            company_id=company_id,
            title=norm_job["title"][:255],
            company_name=norm_job["company_name"][:255],
            description=norm_job.get("description"),
            required_skills=norm_job.get("required_skills") or [],
            preferred_skills=norm_job.get("preferred_skills") or [],
            experience_years_required=norm_job.get("experience_years_required", 0.0),
            experience_level=norm_job.get("experience_level", "Entry-Level"),
            education_requirement=norm_job.get("education_requirement"),
            employment_type=norm_job.get("employment_type"),
            location=norm_job.get("location") or "Remote",
            work_mode=norm_job.get("work_mode") or "Remote",
            salary_min=norm_job.get("salary_min"),
            salary_max=norm_job.get("salary_max"),
            salary_currency=norm_job.get("salary_currency") or "INR",
            salary_range=norm_job.get("salary_range"),
            source_platform=norm_job.get("source_platform") or "Manual",
            source_url=norm_job.get("source_url"),
            company_url=norm_job.get("company_url"),
            external_id=norm_job.get("external_id"),
            posting_date=norm_job.get("posting_date") or now,
            first_seen_at=now,
            last_seen_at=now,
            is_active=True,
            is_expired=False,
            import_status="active",
            raw_metadata=norm_job.get("raw_metadata") or {},
            created_by_user_id=user_id
        )

        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        return new_job, "imported"

    @classmethod
    def mark_stale_jobs_as_expired(
        cls,
        db: Session,
        older_than_days: int = 30
    ) -> int:
        """
        Marks active jobs as expired if they haven't been observed from feeds for older_than_days.
        Preserves Manual postings without alteration.
        """
        threshold = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        stmt = (
            select(Job)
            .where(
                Job.is_active == True,
                Job.is_expired == False,
                Job.source_platform != "Manual",
                Job.last_seen_at < threshold
            )
        )
        stale_jobs = list(db.execute(stmt).scalars().all())
        for job in stale_jobs:
            job.is_expired = True
            job.import_status = "expired"

        if stale_jobs:
            db.commit()
            logger.info("Marked %d stale job opportunities as expired.", len(stale_jobs))

        return len(stale_jobs)

    @classmethod
    def sync_sources(
        cls,
        db: Session,
        sources: Optional[List[str]] = None,
        limit_per_source: int = 20,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Main multi-source sync pipeline:
        1. Identifies target adapters.
        2. Ingests and normalizes external listings.
        3. Deduplicates and upserts records into PostgreSQL.
        4. Updates telemetry and error tracking.
        5. Enforces isolation: failure in one adapter does not abort others.
        """
        target_keys = [s.strip().lower() for s in sources] if sources else list(cls._registered_adapters.keys())
        total_fetched = 0
        total_imported = 0
        total_updated = 0
        total_skipped = 0
        source_results: Dict[str, Any] = {}

        now = datetime.now(timezone.utc)

        for key in target_keys:
            adapter = cls._registered_adapters.get(key)
            if not adapter:
                logger.warning("Requested unknown job source adapter: %s", key)
                source_results[key] = {"error": f"Unknown source adapter '{key}'"}
                continue

            # Update cache to syncing
            if key in cls._source_stats:
                cls._source_stats[key]["status"] = "syncing"

            try:
                listings, stats = adapter.fetch_and_normalize(limit=limit_per_source)
                source_fetched = stats["fetched"]
                source_imported = 0
                source_updated = 0
                source_skipped = stats["skipped"]

                # Process each normalized job in isolated sub-transactions
                for norm_job in listings:
                    try:
                        _, action = cls.upsert_normalized_job(db=db, norm_job=norm_job, user_id=user_id)
                        if action == "imported":
                            source_imported += 1
                        elif action == "updated":
                            source_updated += 1
                    except Exception as item_err:
                        db.rollback()
                        logger.error("Failed to upsert job from %s: %s", adapter.source_name, item_err)
                        source_skipped += 1

                total_fetched += source_fetched
                total_imported += source_imported
                total_updated += source_updated
                total_skipped += source_skipped

                if source_fetched == 0 and stats.get("error"):
                    adapter_status = "error"
                elif stats.get("error"):
                    adapter_status = "partial_failure"
                else:
                    adapter_status = "success"

                source_summary = {
                    "source": adapter.source_name,
                    "status": adapter_status,
                    "fetched": source_fetched,
                    "imported": source_imported,
                    "updated": source_updated,
                    "skipped": source_skipped,
                    "duration_ms": stats.get("duration_ms", 0),
                    "error": stats.get("error")
                }
                source_results[key] = source_summary

                # Update execution stats cache
                if key in cls._source_stats:
                    cls._source_stats[key].update({
                        "status": source_summary["status"],
                        "last_sync_at": now,
                        "last_sync_fetched": source_fetched,
                        "last_sync_imported": source_imported,
                        "last_sync_updated": source_updated,
                        "last_sync_skipped": source_skipped,
                        "total_fetched": cls._source_stats[key].get("total_fetched", 0) + source_fetched,
                        "total_imported": cls._source_stats[key].get("total_imported", 0) + source_imported,
                        "total_updated": cls._source_stats[key].get("total_updated", 0) + source_updated,
                        "total_skipped": cls._source_stats[key].get("total_skipped", 0) + source_skipped,
                        "last_error": stats.get("error")
                    })

            except Exception as src_err:
                logger.error("Adapter %s threw unhandled exception during sync: %s", key, src_err, exc_info=True)
                source_results[key] = {
                    "source": adapter.source_name,
                    "status": "error",
                    "error": str(src_err)
                }
                if key in cls._source_stats:
                    cls._source_stats[key].update({
                        "status": "error",
                        "last_sync_at": now,
                        "last_sync_fetched": 0,
                        "last_sync_imported": 0,
                        "last_sync_updated": 0,
                        "last_sync_skipped": 0,
                        "last_error": str(src_err)
                    })

        # Run freshness cleanup
        try:
            cls.mark_stale_jobs_as_expired(db)
        except Exception as cleanup_err:
            logger.warning("Freshness check encountered error: %s", cleanup_err)

        return {
            "status": "completed",
            "total_fetched": total_fetched,
            "total_imported": total_imported,
            "total_updated": total_updated,
            "total_skipped": total_skipped,
            "source_results": source_results,
            "message": f"Multi-source job sync completed. {total_imported} new jobs imported, {total_updated} updated."
        }
