# Implementation Audit & Stabilization Report — Unified Job Search

**Date:** 2026-10-27
**Branch:** `Profile/multi-source-job`
**Baseline Commit:** `604fe3c` (*fix: harden job search application security*)

---

## 1. Existing & Reusable Functionality

| Module | Location | Capabilities & Architecture | Reuse Strategy |
| :--- | :--- | :--- | :--- |
| **Authentication & Profile** | `backend/app/api/routes/auth.py`<br>`backend/app/api/routes/profile.py` | JWT authentication with dual cookie (`HttpOnly; SameSite=Lax`) and header bearer token support. User registration, login, logout, current user `/me`, candidate profile CRUD, and skills review. | Fully reused. Protects user-owned records across candidate profile, pipeline tracking, email events, and reminders. |
| **Resume Extraction** | `backend/app/services/resume_service.py` | PDF parsing via PyPDF, extraction of skills against synonym dictionaries, candidate review confirmation flow. | Fully reused. Ingestion skills extraction reuses canonical skill normalization from this module. |
| **Job CRUD & Single-URL Import** | `backend/app/services/job_service.py`<br>`backend/app/api/routes/jobs.py` | Job listing with query filters (`q`, `location`, `work_mode`, `skill`), single-job retrieval, manual creation, update, deactivation. SSRF-protected URL import with socket-level IP pinning (`PinnedSyncBackend`), 2 MB streaming limits, upfront `Content-Length` checks. | Base for Phase 1 multi-source ingestion. Model and service will be extended to support source adapters, external source IDs, and deduplication. |
| **Explainable Job Matching** | `backend/app/services/matching_service.py` | Transparent matching algorithm calculating skill overlap, critical missing skills, experience delta, and ranking active jobs for authenticated profile. | Fully reused. Will seamlessly rank all newly ingested multi-source job postings. |
| **Legitimacy Verification Signals** | `backend/app/services/verification_service.py` | Domain validation, MX DNS record verification, known ATS domain matching, scam keyword/payment pattern heuristics, verification logs persistence. | Fully reused. Multi-source listings can be audited on-demand by candidates. |
| **Application Pipeline Tracking** | `backend/app/services/application_service.py`<br>`backend/app/api/v1/applications.py` | Kanban pipeline management (`DRAFT`, `APPLIED`, `INTERVIEWING`, `OFFERED`, `REJECTED`, `WITHDRAWN`), stage transitions, timeline events, duplicate detection (allowing re-application post rejection), pipeline metrics. | Fully reused. Candidates can track multi-source jobs directly into their pipeline via `/api/jobs/{job_id}/apply`. |
| **Email Intelligence & Webhooks** | `backend/app/services/email_service.py`<br>`backend/app/api/v1/emails.py` | Inbound email classification (interview, assessment, confirmation, rejection, scam), Celery task execution, manual linking to applications. | Fully preserved without disruption. |
| **Reminders & Follow-Up Assistant** | `backend/app/services/reminder_service.py`<br>`backend/app/api/v1/reminders.py` | Aging engine, configurable reminder alerts (3/7/14 days), template-based follow-up drafting assistant. | Fully preserved without disruption. |
| **Rate Limiter & Proxy Traversal** | `backend/app/core/rate_limiter.py` | Proxy-aware IP extraction (`TRUSTED_PROXIES` CIDR evaluation, `X-Forwarded-For` right-to-left traversal), atomic Redis counters, fail-open resiliency. | Reused to rate-limit job discovery endpoints, manual sync triggers, and external API requests. |

---

## 2. Partially Implemented Functionality

1. **Job Model Schema (`backend/app/models/job.py`):**
   - *Status:* Contains basic fields (`title`, `company_name`, `description`, `required_skills`, `preferred_skills`, `experience_years_required`, `experience_level`, `education_requirement`, `location`, `work_mode`, `salary_*`, `source_platform`, `source_url`, `posting_date`, `is_active`).
   - *Gaps:* Missing `employment_type` (Full-time, Part-time, Contract, Internship), `company_url`, `external_id` (source unique ID), `last_seen_at` (freshness), `first_seen_at`, `is_expired`, `import_status`, and `raw_metadata` (JSONB).
2. **Dashboard UI (`frontend/src/pages/Dashboard.jsx`):**
   - *Status:* Displays cards for Candidate Profile, Resume Management, and Job Discovery, but refers to "Phase 3 Active".
   - *Gaps:* Lacks quick-access navigation cards for Application Tracker (`/tracker`), Email Hub (`/emails`), and Reminders Hub (`/reminders`).
3. **Job Discovery UI (`frontend/src/pages/JobDiscovery.jsx`):**
   - *Status:* Supports search, location filter, work mode filter, skill filter, URL import modal, manual creation modal, match breakdown modal, verification modal, and "Apply & Track" button.
   - *Gaps:* No source filter dropdown (e.g. All Sources, RemoteOK, Jobicy, Manual), no employment type filter, no freshness/expired badges on job cards, and no manual trigger button for multi-source synchronization.

---

## 3. Missing Functionality (Phase 1 Multi-Source Scope)

1. **Source Adapter Framework:**
   - Abstract adapter interface (`BaseJobSourceAdapter`) defining standard contract: `fetch_jobs()`, `normalize_job()`, source health check, rate limiting, and error handling.
   - Genuine, permitted public source adapters:
     - **RemoteOK Adapter:** Official public developer API (`https://remoteok.com/api`).
     - **Jobicy Adapter:** Official public REST API (`https://jobicy.com/api/v2/remote-jobs`).
2. **Deduplication & Job Freshness Engine:**
   - Multi-tier deduplication: exact match on `(source_platform, external_id)`, normalized URL matching, and conservative fuzzy fallback on `(company_name, title, location)`.
   - Update-in-place logic: updating `last_seen_at`, syncing changed descriptions/salaries, preserving source attribution without creating duplicate rows.
   - Expiration rule: marking stale records as `is_expired = True`.
3. **Ingestion Orchestrator & Celery Task:**
   - Celery background task `orchestrate_job_ingestion_task(sources, limit_per_source)`.
   - Ingestion run tracker recording execution status (`success`, `partial_failure`, `failed`), counts (fetched, imported, updated, skipped), and error messages.
   - Manual synchronization endpoint (`POST /api/jobs/sources/sync`) and source status query (`GET /api/jobs/sources/status`).
4. **Database Migration for Extended Job Schema:**
   - Alembic migration adding nullable columns `employment_type`, `company_url`, `external_id`, `last_seen_at`, `first_seen_at`, `is_expired`, `import_status`, `raw_metadata`, along with relevant indexes.

---

## 4. Integration Defects & Observations

1. **Dashboard Disconnection:** The main landing dashboard only presents 3 of the 6 functional workflows, creating the impression that Tracker, Email Hub, and Reminders are disconnected.
2. **Missing Source Attribution in Discovery:** Jobs currently default `source_platform` to `"Manual"` or URL host; there is no standardized source badge or direct source link indicator on cards.
3. **Job Expiry State:** Jobs are currently either active or deleted (`is_active=False`); there is no non-destructive way to flag a listing as expired or stale while keeping historical records intact.

---

## 5. Security & Data Integrity Considerations

1. **Rate Limiting External Source APIs:** Source adapters must respect third-party API rate limits and include descriptive `User-Agent` headers.
2. **SSRF Safety:** Any URL provided by external feeds or user URL imports must continue to pass through `validate_url_destination` and socket-level IP pinning (`PinnedSyncBackend`) to block internal network scanning or metadata exploitation.
3. **Safe Ingestion Transactions:** Database ingestion must process records in safe transactions so that a failure in one item or adapter does not roll back successfully ingested items or crash other adapters.
4. **Data Truncation Prevention:** Field lengths must accommodate varying external lengths (`title: 255`, `company_name: 255`, `external_id: 255`, `source_url: 1000`, `company_url: 1000`, `description: Text`).

---

## 6. Files Proposed for Modification & Creation

| File | Nature of Change | Purpose |
| :--- | :--- | :--- |
| `backend/app/models/job.py` | Modification | Extend `Job` model with `employment_type`, `company_url`, `external_id`, `last_seen_at`, `first_seen_at`, `is_expired`, `import_status`, `raw_metadata`. |
| `backend/app/schemas/job.py` | Modification | Add extended fields to Pydantic schemas (`JobBase`, `JobCreate`, `JobUpdate`, `JobResponse`). Add schemas for source status and sync response. |
| `database/migrations/versions/<rev>_extend_job_schema_multi_source.py` | New File | Alembic migration for adding new nullable columns and indexes to `jobs` table with safe downgrade. |
| `backend/app/core/config.py` | Modification | Add settings for source enable toggles, API URLs, request rate limits, and batch ingestion sizes. |
| `backend/app/services/job_sources/base.py` | New File | Abstract base class `BaseJobSourceAdapter` for standardized job ingestion. |
| `backend/app/services/job_sources/remoteok_adapter.py` | New File | RemoteOK API adapter normalizing listings into canonical schema. |
| `backend/app/services/job_sources/jobicy_adapter.py` | New File | Jobicy API adapter normalizing listings into canonical schema. |
| `backend/app/services/job_ingestion_service.py` | New File | Deduplication engine, ingestion orchestrator, source execution tracking, and manual refresh handler. |
| `backend/app/workers/tasks.py` | Modification | Add Celery background task for asynchronous job ingestion and scheduled execution. |
| `backend/app/api/routes/jobs.py` | Modification | Add `POST /api/jobs/sources/sync` and `GET /api/jobs/sources/status`. Extend `GET /api/jobs` filter parameters (`source`, `employment_type`). |
| `frontend/src/services/api.js` | Modification | Add `syncJobSourcesApi()` and `getJobSourcesStatusApi()`. |
| `frontend/src/pages/JobDiscovery.jsx` | Modification | Add Source filter, Employment Type filter, manual Sync Sources button, freshness indicators, and source badges. |
| `frontend/src/pages/Dashboard.jsx` | Modification | Update module cards to include Application Tracker, Email Hub, and Reminders Hub. |
| `backend/tests/test_job_sources.py` | New File | Regression tests for source adapters, data normalization, deduplication, rate limiting, and partial failure handling. |
| `docs/JOB_SOURCE_SETUP.md` | New File | Guide on configuring and managing multi-source ingestion. |
| `docs/JOB_INGESTION_ARCHITECTURE.md` | New File | Architectural documentation of the adapter system, deduplication logic, and Celery orchestration. |

---

## 7. Implementation Order & Acceptance Criteria

1. **Phase 0 Integration Stabilization:**
   - Update `Dashboard.jsx` to bridge all 6 core workflows.
   - Verify candidate workflow: Profile -> Resume -> Job -> Match -> Verify -> Tracker.
   - *Acceptance:* All pages render cleanly, navigation is complete, no broken buttons or missing state.
2. **Phase 1 Step 3 — Common Job Schema & Migration:**
   - Extend `Job` SQLAlchemy model and Pydantic schemas.
   - Create Alembic migration with backward-compatible nullable columns and safe downgrade.
   - *Acceptance:* Offline SQL migration generates cleanly; existing test suite passes without schema errors.
3. **Phase 1 Step 4 — Source-Adapter Architecture:**
   - Implement `BaseJobSourceAdapter`, `RemoteOKAdapter`, and `JobicyAdapter`.
   - Enforce URL validation, schema mapping, rate limiting, and error handling.
   - *Acceptance:* Adapters handle valid data, incomplete fields, and network timeouts cleanly.
4. **Phase 1 Step 5 & 6 — Deduplication & Orchestration:**
   - Implement `JobIngestionService` with multi-tier deduplication and freshness tracking.
   - Add Celery background task `orchestrate_job_ingestion_task`.
   - Mount API endpoints: `POST /api/jobs/sources/sync`, `GET /api/jobs/sources/status`.
   - *Acceptance:* Ingestion runs idempotently without duplicating existing jobs; partial failures do not abort other sources.
5. **Phase 1 Step 7 — Frontend Integration:**
   - Extend `JobDiscovery.jsx` with source filtering, employment type filtering, source labels, and sync action.
   - *Acceptance:* User can filter by source, trigger manual refresh, and view source badges.
6. **Phase 1 Step 8 — Quality & Test Suite:**
   - Write comprehensive tests in `backend/tests/test_job_sources.py`.
   - Run unit and integration tests.
   - *Acceptance:* All tests pass.
7. **Phase 1 Step 9 — Documentation:**
   - Create `docs/JOB_SOURCE_SETUP.md` and `docs/JOB_INGESTION_ARCHITECTURE.md`.
   - Update `.env.example`.
