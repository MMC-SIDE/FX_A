@echo off
REM FX Trading System - GitHub リポジトリセットアップ (Windows版)
REM リポジトリの作成、初期化、プッシュを自動化

setlocal enabledelayedexpansion

REM 設定
set REPO_NAME=fx-trading-system
set REPO_DESCRIPTION="XMTrading MT5 と LightGBM を統合した FX 自動売買システム"
set REPO_VISIBILITY=private

echo ==========================================
echo FX Trading System GitHub Setup
echo ==========================================
echo.

REM GitHub CLI の確認
echo GitHub CLI の確認中...
where gh >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo GitHub CLI がインストールされていません
    echo.
    echo インストール方法:
    echo.
    echo 方法1: winget を使用
    echo   winget install --id GitHub.cli
    echo.
    echo 方法2: Chocolatey を使用
    echo   choco install gh
    echo.
    echo 方法3: 直接ダウンロード
    echo   https://cli.github.com/ からダウンロード
    echo.
    pause
    exit /b 1
)

echo GitHub CLI が見つかりました
gh --version

REM GitHub 認証確認
echo.
echo GitHub 認証状態を確認中...
gh auth status >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo GitHub にログインしていません
    echo 今すぐログインしますか? (Y/N)
    set /p LOGIN_CHOICE=
    if /i "!LOGIN_CHOICE!"=="Y" (
        gh auth login
    ) else (
        echo 認証後に再実行してください
        pause
        exit /b 1
    )
)

REM ユーザー名取得
for /f "tokens=*" %%i in ('gh api user --jq .login') do set GITHUB_USERNAME=%%i
echo 認証済み: %GITHUB_USERNAME%

REM Git 初期化
echo.
echo Git リポジトリを初期化中...

if not exist .git (
    git init
    echo Git リポジトリを初期化しました
) else (
    echo 既存の Git リポジトリが見つかりました
)

REM Git 設定
git config user.name "%GITHUB_USERNAME%"
git config user.email "%GITHUB_USERNAME%@users.noreply.github.com"

REM .gitignore 作成
echo .gitignore を作成中...
(
echo # Python
echo __pycache__/
echo *.py[cod]
echo venv/
echo env/
echo .env
echo .env.*
echo !.env.example
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

REM README.md 作成
echo README.md を作成中...
(
echo # FX Trading System
echo.
echo XMTrading MT5 と LightGBM 機械学習モデルを統合した高度な FX 自動売買システム
echo.
echo ## 特徴
echo.
echo - 自動売買機能: MT5 API を通じた完全自動取引実行
echo - 機械学習予測: LightGBM による高精度な価格予測
echo - リアルタイム監視: Web ダッシュボードでリアルタイム監視
echo - リスク管理: 設定可能な自動リスク管理システム
echo - バックテスト: 過去データによる戦略検証機能
echo.
echo ## セットアップ
echo.
echo ```bash
echo # リポジトリクローン
echo git clone https://github.com/%GITHUB_USERNAME%/%REPO_NAME%.git
echo cd %REPO_NAME%
echo.
echo # 環境設定
echo cp .env.prod.example .env.prod
echo.
echo # Docker Compose で起動
echo docker-compose -f docker-compose.prod.yml up -d
echo ```
echo.
echo ## ライセンス
echo.
echo Copyright © 2024 FX Trading System. All rights reserved.
) > README.md

REM 初回コミット
echo.
echo ファイルをステージング中...

git add .gitignore
git add README.md
git add backend\
git add frontend\
git add scripts\
git add database\
git add monitoring\
git add nginx\
git add logging\
git add docker-compose.prod.yml
git add .env.prod.example
if exist .github git add .github\

echo.
echo 初回コミットを作成中...
git commit -m "Initial commit: FX Trading System" -m "- FastAPI backend" -m "- Next.js frontend" -m "- Docker production setup" -m "- LightGBM ML models" -m "- MT5 integration" -m "- Monitoring system"

REM GitHub リポジトリ作成
echo.
echo GitHub リポジトリを作成中...

REM リポジトリの存在確認
gh repo view %GITHUB_USERNAME%/%REPO_NAME% >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo リポジトリは既に存在します: %GITHUB_USERNAME%/%REPO_NAME%
    echo 既存のリポジトリを使用しますか? (Y/N^)
    set /p USE_EXISTING=
    if /i not "!USE_EXISTING!"=="Y" (
        echo リポジトリ作成をキャンセルしました
        pause
        exit /b 1
    )
) else (
    gh repo create %REPO_NAME% --description %REPO_DESCRIPTION% --%REPO_VISIBILITY% --source=. --remote=origin
    echo リポジトリを作成しました: %GITHUB_USERNAME%/%REPO_NAME%
)

REM ブランチ設定
git branch -M main

REM プッシュ
echo.
echo GitHub にプッシュ中...
git push -u origin main

echo.
echo ==========================================
echo セットアップが完了しました！
echo ==========================================
echo.
echo リポジトリ URL: https://github.com/%GITHUB_USERNAME%/%REPO_NAME%
echo.
echo 次のステップ:
echo.
echo 1. GitHub でリポジトリを確認:
echo    gh repo view --web
echo.
echo 2. GitHub Actions シークレットを設定:
echo    Settings → Secrets and variables → Actions
echo.
echo    必要なシークレット:
echo    - PRODUCTION_HOST
echo    - PRODUCTION_USER
echo    - PRODUCTION_SSH_KEY
echo    - SLACK_WEBHOOK_URL (オプション)
echo.
echo 3. 本番サーバーでデプロイ:
echo    ./scripts/deploy.sh deploy main
echo.

pause