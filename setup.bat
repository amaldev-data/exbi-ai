@echo off
title Agentic Analytics OS Setup
echo ==========================================================
echo         Agentic Analytics OS Local Setup Tool
echo ==========================================================
echo.

:: Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your system PATH.
    echo Please install Python 3.10+ and check 'Add Python to PATH'.
    pause
    exit /b 1
)

:: Establish virtual environment
if not exist "venv" (
    echo Creating Python virtual environment (venv)...
    python -m venv venv
    echo Virtual environment created successfully.
) else (
    echo Virtual environment (venv) already detected.
)

:: Activate virtual environment and install packages
echo Activating virtual environment...
call venv\Scripts\activate

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ==========================================================
echo  Setup Completed Successfully!
echo ==========================================================
echo.
echo Launching the application...
echo.

:: Launch the application using run.bat
call run.bat
