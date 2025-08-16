@echo off
title Network Monitor & Filter System

echo ========================================
echo Starting Network Monitor...
echo ========================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Starting the application...
echo Web Interface: http://localhost:8081
echo Proxy Port:    8080 (default)
echo Press Ctrl+C to stop the system.
echo ========================================
echo.

python main.py

echo.
echo System has been shut down.
pause