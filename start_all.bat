@echo off
title FX Trading System

echo Starting FX Trading System...
echo.

start "Backend" cmd /k start_simple_backend.bat
timeout /t 3 /nobreak >nul

start "Frontend" cmd /k start_simple_frontend.bat
timeout /t 5 /nobreak >nul

echo.
echo System Started!
echo.
echo Backend: http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo.

start http://localhost:3000

pause