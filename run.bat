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

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend App (Port 5173)...
start "Frontend - Vite React App" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"

echo.
echo ======================================================================
echo Both servers have been launched!
echo   - Backend:  http://localhost:8000
echo   - Frontend: http://localhost:5173
echo ======================================================================
echo Press any key to close this launcher...
pause >nul