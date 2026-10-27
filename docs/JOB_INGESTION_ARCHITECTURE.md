# Job Ingestion & Multi-Source Architecture — Unified Job Search

## Architecture Overview

The multi-source job ingestion engine bridges external job boards and feeds into a normalized, deduplicated canonical job catalog. The architecture is modular, decoupled, and designed with error isolation so that failure in one source never disrupts other ingestion pipelines.

```
                      +-----------------------------+
                      |   Scheduled Celery Beat /   |
                      |   Manual Sync API Trigger   |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   JobIngestionService       |
                      |   (Orchestrator & Status)   |
                      +--------------+--------------+
                                     |
              +----------------------+----------------------+
              |                                             |
              v                                             v
  +------------------------+                    +------------------------+
  |    RemoteOKAdapter     |                    |     JobicyAdapter      |
  |  (Official JSON Feed)  |                    |   (Official REST API)  |
  +-----------+------------+                    +-----------+------------+
              |                                             |
              +----------------------+----------------------+
                                     | Normalized Job Dictionaries
                                     v
                      +-----------------------------+
                      |   Multi-Tier Deduplication  |
                      |   1. Source + External ID   |
                      |   2. Normalized Source URL  |
                      |   3. Fuzzy Title + Company  |
                      +--------------+--------------+
                                     |
                         +-----------+-----------+
                         |                       |
                     [Match]                 [No Match]
                         |                       |
                         v                       v
               +--------------------+  +--------------------+
               | Update in Place    |  | Insert New Job &   |
               | (last_seen_at,     |  | Company Record     |
               |  salary, desc)     |  | (first_seen_at)    |
               +--------------------+  +--------------------+
```

---

## 1. Common Job Schema

Every imported job posting conforms to the canonical SQLAlchemy `Job` model (`backend/app/models/job.py`):

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `Integer` | Primary key |
| `title` | `String(255)` | Standardized job title |
| `company_name` | `String(255)` | Company name |
| `company_id` | `Integer` | Foreign key referencing `companies.id` |
| `description` | `Text` | Cleaned plain-text / HTML-stripped job description |
| `required_skills` | `JSONB` | Extracted & normalized technical skills list |
| `preferred_skills` | `JSONB` | Secondary or bonus skills |
| `employment_type` | `String(50)` | `Full-time`, `Contract`, `Part-time`, `Internship` |
| `experience_level` | `String(50)` | `Entry-Level`, `Mid-Level`, `Senior`, `Lead` |
| `location` | `String(255)` | Geographic location or `Remote / Worldwide` |
| `work_mode` | `String(50)` | `Remote`, `Hybrid`, `On-site`, `Any` |
| `salary_min` / `max` | `Float` | Numerical compensation bounds |
| `salary_currency` | `String(10)` | ISO currency code (default: `INR` or `USD`) |
| `salary_range` | `String(100)` | Human-readable compensation string |
| `source_platform` | `String(100)` | Source identifier (`RemoteOK`, `Jobicy`, `Manual`) |
| `source_url` | `String(1000)` | Direct URL to listing |
| `external_id` | `String(255)` | Unique identifier within the originating source |
| `posting_date` | `DateTime` | Original publication date |
| `first_seen_at` | `DateTime` | Timestamp of initial ingestion |
| `last_seen_at` | `DateTime` | Timestamp of most recent observation |
| `is_active` | `Boolean` | True if record is active in catalog |
| `is_expired` | `Boolean` | True if listing has closed or hasn't appeared for > 30 days |
| `import_status` | `String(50)` | `active`, `updated`, `expired`, `archived` |
| `raw_metadata` | `JSONB` | Complete raw payload for auditability without data loss |

---

## 2. Source-Adapter Contract (`BaseJobSourceAdapter`)

Each source adapter implements `backend/app/services/job_sources/base.py`:
- `is_enabled() -> bool`: Verifies settings flag (`REMOTEOK_ENABLED`, `JOBICY_ENABLED`).
- `fetch_raw_listings(limit: int) -> List[Dict[str, Any]]`: Performs throttled HTTP requests with timeout, custom `User-Agent`, and error handling.
- `normalize_listing(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]`: Maps raw feed structure into the common job dictionary. Strips HTML, normalizes skills, and extracts compensation.
- `fetch_and_normalize(limit: int) -> Tuple[List[Dict], Dict[str, Any]]`: Orchestrates fetching and records duration, success counts, and error messages.

---

## 3. Multi-Tier Deduplication Strategy

To prevent redundant records and preserve candidate application history, `JobIngestionService.find_existing_duplicate_job` performs a three-tier inspection:

### Tier 1: Exact Source + External ID Match
```sql
SELECT * FROM jobs
WHERE source_platform = :source
  AND external_id = :external_id
```
If an external listing with the same source ID has already been imported, it is guaranteed to be the exact same posting.

### Tier 2: Normalized URL Match
```sql
SELECT * FROM jobs
WHERE source_url = :source_url
   OR source_url = :normalized_url
```
URLs are normalized via `normalize_job_url()` which strips UTM marketing parameters (`utm_source`, `utm_medium`, `utm_campaign`), tracking IDs (`ref`, `fbclid`, `gclid`), and trailing slashes.

### Tier 3: Conservative Fuzzy Matching
```sql
SELECT * FROM jobs
WHERE lower(company_name) = :company
  AND lower(title) = :title
  AND lower(location) = :location
  AND created_at >= NOW() - INTERVAL '60 DAYS'
```
Catches identical openings cross-posted or discovered across multiple channels.

### Upsert Behavior
- **Existing Record Found:** Updates `last_seen_at = NOW()`, confirms `is_expired = False`, enriches empty fields (salary, detailed description), merges `raw_metadata`, and leaves `id` unchanged. Existing applications linked to this job in candidate trackers remain intact!
- **No Existing Record:** Resolves or creates the corresponding `Company`, sets `first_seen_at = NOW()`, and inserts a new canonical `Job` row.

---

## 4. Freshness and Expiry Engine

Listings that have closed or disappeared from feeds are managed gracefully:
1. `mark_stale_jobs_as_expired(db, older_than_days=30)` queries active external jobs where `last_seen_at < (NOW() - 30 days)`.
2. Sets `is_expired = True` and `import_status = "expired"`.
3. Candidate applications linked to the job remain accessible, but discovery cards display a visible "Expired" badge.
4. `source_platform == "Manual"` records are exempt from automatic expiry.

---

## 5. Security & Reliability Controls

- **Error Isolation:** If `RemoteOK` returns `HTTP 503`, `Jobicy` and manual imports continue processing normally. Errors are captured per-source in `source_results`.
- **SSRF Hardening:** User-initiated URL imports route through `PinnedSyncBackend`, locking TCP connections to pre-validated public IPs while preserving TLS SNI and cert validation.
- **Transaction Safety:** Individual listings are upserted within isolated sub-transactions with `db.rollback()` on error, preventing corrupt rows from rolling back valid ingestions.
- **Rate Limiting:** Synchronization triggers are rate-limited (`rate_limit("job-sources-sync", max_requests=10, window_seconds=60)`).
