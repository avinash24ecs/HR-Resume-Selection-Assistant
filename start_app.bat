@echo off
title HR Resume Selection Assistant
echo ======================================================================
echo           HR Resume Selection Assistant - Live Launcher
echo ======================================================================
echo.

:: Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Node.js runtime detected.
    echo Starting live assistant server on http://localhost:5000 ...
    start "" "http://localhost:5000"
    node "%~dp0server.js"
    exit /b
)

:: Check Python
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Python runtime detected.
    echo Starting Flask assistant server on http://localhost:5000 ...
    start "" "http://localhost:5000"
    python "%~dp0api\index.py"
    exit /b
)

:: Fallback: Open standalone in browser directly
echo [Notice] Neither Node.js nor Python detected in PATH.
echo Launching Zero-Install Standalone Web App in your browser...
start "" "%~dp0public\index.html"
pause
