@echo off
title Agentic Analytics OS Launcher
echo ==========================================================
echo           Agentic Analytics OS One-Click Launcher
echo ==========================================================
echo.

:: Check virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Please run 'setup.bat' first to install dependencies.
    pause
    exit /b 1
)

:: Create necessary runtime directories
if not exist "backend\uploads" (
    echo Creating missing directory: backend\uploads
    mkdir "backend\uploads"
)
if not exist "backend\reports" (
    echo Creating missing directory: backend\reports
    mkdir "backend\reports"
)

:: Activate virtual environment
call venv\Scripts\activate

:: Start Backend FastAPI server in a new command window
echo Launching FastAPI Backend Server...
start "Agentic Analytics OS Backend" cmd /k "call venv\Scripts\activate && python run.py"

:: Wait a brief moment for the backend to start
timeout /t 2 /nobreak >nul

:: Open browser to the frontend local server port
echo Opening web browser to http://localhost:3000...
start "" "http://localhost:3000"

:: Start Frontend local HTTP server in current window
echo Starting Frontend local server on port 3000...
echo (Keep this window open to access the application. Press Ctrl+C to stop)
echo.
python -m http.server 3000
