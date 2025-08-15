@echo off
title Backend API

if exist .venv (
    .venv\Scripts\python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
) else if exist venv (
    venv\Scripts\python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
) else (
    echo No virtual environment found!
    echo Run install_backend_simple.bat first
    pause
)