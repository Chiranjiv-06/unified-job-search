@echo off
title Unified Job Search - Background Worker & Scheduler
color 0b

echo ======================================================================
echo     UNIFIED JOB SEARCH - CELERY WORKER & 6-HOUR SCHEDULER
echo ======================================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

if not exist "%ROOT_DIR%backend\.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at %ROOT_DIR%backend\.venv
    pause
    exit /b 1
)

:: Test Redis connection
"%ROOT_DIR%backend\.venv\Scripts\python.exe" -c "import socket; s = socket.socket(); s.settimeout(1.0); exit(0 if s.connect_ex(('127.0.0.1', 6379)) == 0 else 1" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Redis server is not reachable on localhost:6379.
    echo.
    echo The Celery worker and periodic scheduler require an active Redis instance.
    echo To resolve:
    echo   1. Ensure Redis is running locally on port 6379, or
    echo   2. Run Redis in Docker: docker run -d -p 6379:6379 --name ujs-redis redis:7-alpine
    echo.
    echo Note: Manual job ingestion ("Sync Feeds" button) does NOT require Redis.
    echo.
    pause
    exit /b 1
)

echo [OK] Redis connection verified on localhost:6379.

:: Guard against running duplicate Celery Beat instances
powershell -NoProfile -Command "if (Get-Process -Name celery -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] An active Celery process is already running on this machine!
    echo Running multiple Celery Beat schedulers simultaneously will cause duplicate periodic jobs.
    echo If you wish to restart the worker, close the existing window first.
    echo.
    set /p CONFIRM="Do you still want to start another instance? (y/N): "
    if /i not "%CONFIRM%"=="y" exit /b 0
)

echo Starting Celery worker with embedded Beat scheduler (--pool=solo)...
echo Periodic schedule: "sync-jobs-periodic-6h" (every 6 hours)
echo.

cd /d "%ROOT_DIR%backend"
call .venv\Scripts\activate.bat
set PYTHONPATH=.
celery -A app.workers.celery_app.celery_app worker -B --loglevel=info --pool=solo
