@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM FX Trading System - GitHub Repository Setup (Windows)
REM Automates repository creation, initialization, and push

REM Settings
set REPO_NAME=fx-trading-system
set REPO_DESCRIPTION="FX Trading System with MT5 and LightGBM"
set REPO_VISIBILITY=private

echo ==========================================
echo FX Trading System GitHub Setup
echo ==========================================
echo.

REM Check GitHub CLI
echo Checking GitHub CLI...
where gh >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo GitHub CLI is not installed
    echo.
    echo Installation methods:
    echo.
    echo Method 1: Using winget
    echo   winget install --id GitHub.cli
    echo.
    echo Method 2: Using Chocolatey
    echo   choco install gh
    echo.
    echo Method 3: Direct download
    echo   https://cli.github.com/
    echo.
    pause
    exit /b 1
)

echo GitHub CLI found
gh --version

REM Check GitHub authentication
echo.
echo Checking GitHub authentication...
gh auth status >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Not logged in to GitHub
    echo Do you want to login now? (Y/N)
    set /p LOGIN_CHOICE=
    if /i "!LOGIN_CHOICE!"=="Y" (
        gh auth login
    ) else (
        echo Please authenticate and run again
        pause
        exit /b 1
    )
)

REM Get username
for /f "tokens=*" %%i in ('gh api user --jq .login') do set GITHUB_USERNAME=%%i
echo Authenticated as: %GITHUB_USERNAME%

REM Initialize Git
echo.
echo Initializing Git repository...

if not exist .git (
    git init
    echo Git repository initialized
) else (
    echo Existing Git repository found
)

REM Configure Git
git config user.name "%GITHUB_USERNAME%"
git config user.email "%GITHUB_USERNAME%@users.noreply.github.com"

REM Create .gitignore
echo Creating .gitignore...
call :create_gitignore

REM Create README.md
echo Creating README.md...
call :create_readme

REM Stage files
echo.
echo Staging files...

git add .gitignore >nul 2>nul
git add README.md >nul 2>nul
git add backend >nul 2>nul
git add frontend >nul 2>nul
git add scripts >nul 2>nul
git add database >nul 2>nul
git add monitoring >nul 2>nul
git add nginx >nul 2>nul
git add logging >nul 2>nul
git add docker-compose.prod.yml >nul 2>nul
git add .env.prod.example >nul 2>nul
if exist .github git add .github >nul 2>nul

echo.
echo Creating initial commit...
git commit -m "Initial commit: FX Trading System" -m "- FastAPI backend implementation" -m "- Next.js frontend implementation" -m "- Docker production configuration" -m "- LightGBM ML models" -m "- MT5 integration" -m "- Monitoring system (Prometheus/Grafana)" -m "- Automated deployment setup"

REM Create GitHub repository
echo.
echo Creating GitHub repository...

REM Check if repository exists
gh repo view %GITHUB_USERNAME%/%REPO_NAME% >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Repository already exists: %GITHUB_USERNAME%/%REPO_NAME%
    echo Use existing repository? (Y/N)
    set /p USE_EXISTING=
    if /i not "!USE_EXISTING!"=="Y" (
        echo Repository creation cancelled
        pause
        exit /b 1
    )
    git remote remove origin >nul 2>nul
    git remote add origin https://github.com/%GITHUB_USERNAME%/%REPO_NAME%.git
) else (
    gh repo create %REPO_NAME% --description %REPO_DESCRIPTION% --%REPO_VISIBILITY% --source=. --remote=origin
    echo Repository created: %GITHUB_USERNAME%/%REPO_NAME%
)

REM Set main branch
git branch -M main

REM Push to GitHub
echo.
echo Pushing to GitHub...
git push -u origin main

echo.
echo ==========================================
echo Setup completed successfully!
echo ==========================================
echo.
echo Repository URL: https://github.com/%GITHUB_USERNAME%/%REPO_NAME%
echo.
echo Next steps:
echo.
echo 1. View repository in browser:
echo    gh repo view --web
echo.
echo 2. Configure GitHub Actions secrets:
echo    Go to Settings - Secrets and variables - Actions
echo.
echo    Required secrets:
echo    - PRODUCTION_HOST
echo    - PRODUCTION_USER
echo    - PRODUCTION_SSH_KEY
echo    - SLACK_WEBHOOK_URL (optional)
echo.
echo 3. Deploy on production server:
echo    ./scripts/deploy.sh deploy main
echo.

pause
goto :eof

:create_gitignore
(
echo # Python
echo __pycache__/
echo *.py[cod]
echo venv/
echo env/
echo .env
echo .env.*
echo ^^!.env.example
echo.
echo # Node.js
echo node_modules/
echo .next/
echo out/
echo dist/
echo npm-debug.log*
echo yarn-error.log*
echo.
echo # Configuration
echo config/mt5_config.json
echo config/production.json
echo.
echo # Database
echo *.db
echo postgres_data/
echo redis_data/
echo.
echo # Logs
echo logs/
echo *.log
echo.
echo # IDE
echo .vscode/
echo .idea/
echo.
echo # OS
echo .DS_Store
echo Thumbs.db
echo.
echo # Docker volumes
echo prometheus_data/
echo grafana_data/
echo.
echo # Backups
echo backups/
echo *.sql.gz
echo.
echo # SSL
echo *.pem
echo *.key
echo *.crt
) > .gitignore
goto :eof

:create_readme
(
echo # FX Trading System
echo.
echo Advanced FX automated trading system integrating XMTrading MT5 with LightGBM machine learning models
echo.
echo ## Features
echo.
echo - **Automated Trading**: Full automation through MT5 API
echo - **Machine Learning**: High-accuracy price prediction with LightGBM
echo - **Real-time Monitoring**: Web dashboard for real-time monitoring
echo - **Risk Management**: Configurable automated risk management system
echo - **Backtesting**: Strategy validation with historical data
echo - **Time Analysis**: Automatic detection of optimal trading hours by market
echo.
echo ## Requirements
echo.
echo - Python 3.9+
echo - Node.js 18+
echo - PostgreSQL 14+ ^(TimescaleDB^)
echo - Redis 7+
echo - Docker and Docker Compose
echo - MetaTrader 5
echo.
echo ## Installation
echo.
echo ### 1. Clone Repository
echo.
echo ```bash
echo git clone https://github.com/%GITHUB_USERNAME%/%REPO_NAME%.git
echo cd %REPO_NAME%
echo ```
echo.
echo ### 2. Environment Setup
echo.
echo ```bash
echo cp .env.prod.example .env.prod
echo # Edit .env.prod with required settings
echo ```
echo.
echo ### 3. Start with Docker Compose
echo.
echo ```bash
echo docker-compose -f docker-compose.prod.yml up -d
echo ```
echo.
echo ### 4. Database Migration
echo.
echo ```bash
echo docker-compose -f docker-compose.prod.yml exec backend python -m alembic upgrade head
echo ```
echo.
echo ## Usage
echo.
echo 1. **Web UI**: https://localhost
echo 2. **API Documentation**: https://localhost/api/docs
echo 3. **Grafana Monitoring**: https://localhost:3001
echo.
echo ## Project Structure
echo.
echo ```
echo fx-trading-system/
echo ├── backend/          # FastAPI backend
echo ├── frontend/         # Next.js frontend
echo ├── scripts/          # Operational scripts
echo ├── monitoring/       # Prometheus/Grafana config
echo ├── database/         # DB schema and migrations
echo └── docker-compose.prod.yml
echo ```
echo.
echo ## License
echo.
echo Copyright © 2024 FX Trading System. All rights reserved.
echo.
echo ## Disclaimer
echo.
echo This system performs financial trading. Investment carries risk of loss.
echo Use at your own risk.
) > README.md
goto :eof