# Job Source Setup & Integration Guide — Unified Job Search

## Overview

Unified Job Search supports multi-source job discovery via a modular, extensible adapter architecture. The system ingests public, permitted developer job feeds and APIs, validates metadata, applies multi-tier deduplication, and normalizes records into a common schema.

---

## 1. Supported Ingestion Sources

### 1. RemoteOK (`RemoteOKAdapter`)
- **Type:** Official Public Developer JSON API.
- **Endpoint:** `https://remoteok.com/api`
- **Authentication:** No API key required. Requests require a descriptive `User-Agent`.
- **Feed Characteristics:** Remote engineering, programming, and DevOps listings. Includes tags, salary ranges, and direct application links.
- **Rate Limit Policy:** Recommended at most 1 request per second. Handled automatically with polite exponential backoff.
- **Config Toggle:** `REMOTEOK_ENABLED=True`

### 2. Jobicy (`JobicyAdapter`)
- **Type:** Official Public REST API.
- **Endpoint:** `https://jobicy.com/api/v2/remote-jobs`
- **Authentication:** No API key required for public feed indexing.
- **Feed Characteristics:** Structured remote tech jobs with explicit employment types (`Full-time`, `Contract`), regions (`jobGeo`), levels, and salary ranges.
- **Rate Limit Policy:** 20-50 listings per batch request.
- **Config Toggle:** `JOBICY_ENABLED=True`

### 3. User-Initiated URL Import (`import_job_from_url`)
- **Type:** On-demand single posting scraper with SSRF defense.
- **Security:** Socket-level TCP pinning (`PinnedSyncBackend`) against DNS rebinding, upfront `Content-Length` inspection, 2 MB streaming limits, and CIDR private IP blocks.
- **Access:** Available to authenticated candidates via UI ("Import from URL") or `POST /api/jobs/import-url`.

---

## 2. Environment Configuration

Add or adjust the following variables in your `.env` file (template available in `.env.example`):

```ini
# Multi-Source Job Discovery & Ingestion
REMOTEOK_ENABLED=True
REMOTEOK_API_URL=https://remoteok.com/api

JOBICY_ENABLED=True
JOBICY_API_URL=https://jobicy.com/api/v2/remote-jobs

# Throttling and Batch Size
JOB_INGESTION_RATE_LIMIT_SECONDS=1.0
JOB_INGESTION_MAX_JOBS_PER_SOURCE=25
```

---

## 3. Database Migration Commands

Apply the multi-source schema extension (migration `e4f5a6b7c8d9`):

```bash
# Upgrade to head migration
alembic upgrade head

# To verify SQL output without applying to database:
alembic upgrade head --sql
```

This migration extends the `jobs` table with:
- `employment_type` (`VARCHAR(50)`)
- `company_url` (`VARCHAR(1000)`)
- `external_id` (`VARCHAR(255)`)
- `first_seen_at` (`TIMESTAMP WITH TIME ZONE`)
- `last_seen_at` (`TIMESTAMP WITH TIME ZONE`)
- `is_expired` (`BOOLEAN DEFAULT FALSE`)
- `import_status` (`VARCHAR(50)`)
- `raw_metadata` (`JSONB`)
- Indexes: `ix_jobs_external_id`, `ix_jobs_employment_type`, `ix_jobs_is_expired`, and composite `ix_jobs_source_external_id`.

---

## 4. How to Start the Services

### Local Windows Development (Two Options)

#### Option A: Quick Full-Stack Launch (via Launcher Scripts)
```cmd
# 1. Start Web Platform (Backend + Frontend):
run.bat

# 2. (Optional) Start Celery Worker & 6-Hour Scheduler in separate window:
start_worker.bat
```
- `run.bat` starts FastAPI (port 8000) and Vite (port 5173). It diagnoses Redis connectivity without launching a background scheduler, keeping manual ingestion ("Sync Feeds" in UI) fully functional with zero Redis dependency and eliminating accidental duplicate Beat schedulers.
- `start_worker.bat` is the dedicated launcher for background processing. It validates Redis on port 6379, guards against running duplicate Celery processes, and starts the worker with embedded Beat (`-B --pool=solo`) as a single scheduler instance.

#### Option B: Manual Command Line
```powershell
# 1. FastAPI Backend (Terminal 1)
cd D:\unified-job-search\backend
.\.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Frontend React/Vite (Terminal 2)
cd D:\unified-job-search\frontend
npm run dev

# 3. Celery Worker + 6h Beat Scheduler (Terminal 3, requires Redis on localhost:6379)
cd D:\unified-job-search\backend
.\.venv\Scripts\activate
$env:PYTHONPATH="."
celery -A app.workers.celery_app.celery_app worker -B --loglevel=info --pool=solo
```

#### Stopping Local Services:
- Press `Ctrl + C` in each terminal window, or close the spawned command prompt windows.

---

### Docker Compose Deployment

The Docker Compose configuration includes PostgreSQL, Redis, FastAPI Backend, Celery Worker, Celery Beat Scheduler, and Nginx Frontend.

#### Start All Services (Detached Mode):
```bash
docker compose up --build -d
```

#### Verify Running Containers:
```bash
docker compose ps
# Expected containers:
#   ujs-postgres   (healthy)
#   ujs-redis      (healthy)
#   ujs-backend    (running)
#   ujs-worker     (running)
#   ujs-beat       (running - single scheduler instance)
#   ujs-frontend   (running)
```

#### View Background Worker & Scheduler Logs:
```bash
# Celery Worker logs
docker compose logs -f worker

# Celery Beat Scheduler logs
docker compose logs -f beat
```

#### Stop All Services:
```bash
docker compose down
```

---

## 5. How to Run Ingestion & Diagnostics

### Manual Trigger via UI:
1. Navigate to **Job Discovery** (`http://localhost:5173/jobs`).
2. Click the **Sync Feeds** button in the header.
3. The platform executes the ingestion pipeline across all enabled sources and updates the view with fresh listings.

### Manual Trigger via API:
```bash
curl -X POST http://localhost:8000/api/jobs/sources/sync \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"limit_per_source": 20}'
```

### Check Source Health & Telemetry:
```bash
curl -X GET http://localhost:8000/api/jobs/sources/status \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```

Sample Response:
```json
{
  "sources": [
    {
      "name": "RemoteOK",
      "enabled": true,
      "status": "success",
      "last_sync_at": "2026-10-27T15:30:00Z",
      "total_fetched": 20,
      "total_imported": 15,
      "total_updated": 5,
      "total_skipped": 0,
      "last_error": null
    },
    {
      "name": "Jobicy",
      "enabled": true,
      "status": "success",
      "last_sync_at": "2026-10-27T15:30:05Z",
      "total_fetched": 20,
      "total_imported": 18,
      "total_updated": 2,
      "total_skipped": 0,
      "last_error": null
    }
  ],
  "total_jobs": 84,
  "active_sources_count": 2
}
```

---

## 6. How to Run Tests

```bash
# Run multi-source adapter and deduplication tests
pytest backend/tests/test_job_sources.py -v

# Run entire backend test suite
pytest -v

# Run frontend lint and build verification
cd frontend
npm run lint
npm run build
```

---

## 7. Troubleshooting Ingestion Issues

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `HTTP 503` / `ReadTimeout` on source sync | External feed API temporarily unavailable | Adapters automatically catch network errors and isolate failures. Ingestion reports partial failure without affecting other sources. |
| Duplicate listings appearing | Differences in URL parameters or casing | Verify `normalize_job_url` strips query parameters; check `ix_jobs_source_external_id` index. |
| Jobs marked expired prematurely | Job hasn't appeared in feed for > 30 days | `mark_stale_jobs_as_expired` flags listings when `last_seen_at < (now - 30 days)`. Can be customized in `JobIngestionService`. |
