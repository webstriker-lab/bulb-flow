@echo off
setlocal
title Bulb Flow — Launcher

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [Bulb Flow] Python 3.10+ was not found on PATH.
    echo Please install Python from https://www.python.org/downloads/ and check "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [Bulb Flow] Setting up your private Python environment for the first time...
    python -m venv .venv
    if errorlevel 1 (
        echo [Bulb Flow] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [Bulb Flow] Installing dependencies (PySide6, Faster-Whisper, API clients)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [Bulb Flow] Dependency installation failed. Check your internet connection and try again.
        pause
        exit /b 1
    )
)

echo [Bulb Flow] Starting Bulb Flow...
start "" ".venv\Scripts\pythonw.exe" main.py
endlocal
