@echo off
title Unified Job Search - Local Launcher
color 0a

echo ======================================================================
echo           UNIFIED JOB SEARCH - STARTING LOCAL ENVIRONMENT
echo ======================================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

if not exist "%ROOT_DIR%backend\.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at %ROOT_DIR%backend\.venv
    pause
    exit /b 1
)

echo [1/2] Starting Backend API Server (Port 8000)...
start "Backend - FastAPI Server" cmd /k "cd /d "%ROOT_DIR%backend" && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Frontend App (Port 5173)...
start "Frontend - Vite React App" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"

timeout /t 1 /nobreak >nul

:: Diagnostic check for Redis and Background Worker
"%ROOT_DIR%backend\.venv\Scripts\python.exe" -c "import socket; s = socket.socket(); s.settimeout(0.5); exit(0 if s.connect_ex(('127.0.0.1', 6379)) == 0 else 1" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [Status] Redis is detected on localhost:6379.
    echo          Manual sync is ready. To run the 6-hour scheduler worker, open: start_worker.bat
) else (
    echo [Status] Redis is not running on localhost:6379.
    echo          Manual sync via "Sync Feeds" button remains fully functional without Redis.
    echo          To enable scheduled 6-hour background sync, start Redis and run: start_worker.bat
)

echo.
echo ======================================================================
echo Local development environment ready!
echo   - Backend API:   http://localhost:8000
echo   - API Docs:      http://localhost:8000/docs
echo   - Frontend UI:   http://localhost:5173
echo   - Ingestion:     Manual sync active ("Sync Feeds" button in UI)
echo                    Optional background sync: start_worker.bat
echo ======================================================================
echo Press any key to close this launcher...
pause >nul