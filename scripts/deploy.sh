#!/bin/bash

# FX Trading System - 自動デプロイメントスクリプト
# 本番環境用のゼロダウンタイムデプロイメント

set -euo pipefail

# 設定値読み込み
source /app/.env.prod 2>/dev/null || {
    echo "ERROR: .env.prod ファイルが見つかりません"
    exit 1
}

# 基本設定
DEPLOY_DIR="/app"
BACKUP_DIR="/app/backups/deploy"
LOG_FILE="/var/log/deployment/deploy_$(date +%Y%m%d_%H%M%S).log"
ROLLBACK_LIMIT=3
HEALTH_CHECK_TIMEOUT=300

# デプロイメント設定
GIT_REPO="https://github.com/your-org/fx-trading-system.git"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
MIGRATION_TIMEOUT=600

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# 使用方法表示
usage() {
    cat << EOF
使用方法: $0 [オプション] <アクション>

アクション:
  deploy [ブランチ名]     新バージョンをデプロイ (デフォルト: main)
  rollback [バージョン]  指定バージョンにロールバック
  status                 デプロイメント状況確認
  health                 ヘルスチェック実行
  list                   デプロイ履歴表示

オプション:
  -h, --help            このヘルプを表示
  -f, --force           確認なしで実行
  -m, --migrate         データベースマイグレーション実行
  -s, --skip-tests      テストをスキップ
  -v, --verbose         詳細ログ出力

例:
  $0 deploy main
  $0 deploy feature/new-algorithm -m
  $0 rollback v1.2.3
  $0 status
EOF
}

# 前処理チェック
pre_deploy_checks() {
    log "デプロイメント前チェックを実行中..."
    
    # ディレクトリ作成
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Git確認
    if ! command -v git &> /dev/null; then
        error_exit "Gitがインストールされていません"
    fi
    
    # Docker確認
    if ! command -v docker &> /dev/null; then
        error_exit "Dockerがインストールされていません"
    fi
    
    if ! docker info &>/dev/null; then
        error_exit "Dockerデーモンが実行されていません"
    fi
    
    # Docker Compose確認
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Composeがインストールされていません"
    fi
    
    # ディスク容量確認
    local available_space=$(df "$DEPLOY_DIR" | awk 'NR==2 {print $4}')
    local available_gb=$((available_space / 1024 / 1024))
    
    if [ "$available_gb" -lt 2 ]; then
        error_exit "ディスク容量が不足しています (利用可能: ${available_gb}GB)"
    fi
    
    log "前チェック完了 (利用可能容量: ${available_gb}GB)"
}

# 現在のバージョン取得
get_current_version() {
    if [ -f "$DEPLOY_DIR/.deploy_version" ]; then
        cat "$DEPLOY_DIR/.deploy_version"
    else
        echo "unknown"
    fi
}

# バックアップ作成
create_backup() {
    local version="$1"
    local backup_path="$BACKUP_DIR/backup_${version}_$(date +%Y%m%d_%H%M%S)"
    
    log "現在の環境をバックアップ中: $backup_path"
    
    # アプリケーションファイルのバックアップ
    mkdir -p "$backup_path"
    
    # 重要なファイル・ディレクトリをバックアップ
    local backup_items=(
        "backend"
        "frontend" 
        "scripts"
        "config"
        "docker-compose.prod.yml"
        ".env.prod"
        "monitoring"
        "nginx"
        ".deploy_version"
    )
    
    for item in "${backup_items[@]}"; do
        if [ -e "$DEPLOY_DIR/$item" ]; then
            cp -r "$DEPLOY_DIR/$item" "$backup_path/" 2>>"$LOG_FILE" || true
        fi
    done
    
    # データベースバックアップ
    if docker ps | grep -q "fx_postgres"; then
        log "データベースバックアップを作成中..."
        
        local db_backup="$backup_path/database_backup.sql.gz"
        docker exec fx_postgres pg_dump \
            -U fx_user \
            -d fx_trading \
            --format=custom \
            --compress=9 | gzip > "$db_backup" 2>>"$LOG_FILE"
        
        if [ $? -eq 0 ]; then
            log "データベースバックアップ完了: $db_backup"
        else
            log "WARNING: データベースバックアップに失敗しました"
        fi
    fi
    
    # バックアップメタデータ
    cat > "$backup_path/backup_info.txt" << EOF
Backup Information
==================
Creation Time: $(date '+%Y-%m-%d %H:%M:%S')
Previous Version: $version
Backup Path: $backup_path
Docker Images:
$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}" | grep fx_)
EOF
    
    log "バックアップ作成完了: $backup_path"
    echo "$backup_path"
}

# コードベース更新
update_codebase() {
    local branch="$1"
    
    log "コードベースを更新中: ブランチ $branch"
    
    # 現在のディレクトリ移動
    cd "$DEPLOY_DIR"
    
    # Git設定確認
    if [ ! -d ".git" ]; then
        log "リポジトリを初期化中..."
        git init
        git remote add origin "$GIT_REPO"
    fi
    
    # 最新コード取得
    log "最新コードを取得中..."
    git fetch origin "$branch" 2>>"$LOG_FILE"
    
    # ローカル変更の退避
    if ! git diff --quiet; then
        log "ローカル変更を退避中..."
        git stash push -m "Auto-stash before deploy $(date)" 2>>"$LOG_FILE"
    fi
    
    # チェックアウト
    git checkout "$branch" 2>>"$LOG_FILE"
    git reset --hard "origin/$branch" 2>>"$LOG_FILE"
    
    # サブモジュール更新
    if [ -f ".gitmodules" ]; then
        git submodule update --init --recursive 2>>"$LOG_FILE"
    fi
    
    # 新しいバージョン取得
    local new_version=$(git rev-parse --short HEAD)
    echo "$new_version" > "$DEPLOY_DIR/.deploy_version"
    
    log "コードベース更新完了: バージョン $new_version"
    echo "$new_version"
}

# テスト実行
run_tests() {
    if [ "${SKIP_TESTS:-false}" = "true" ]; then
        log "テストをスキップします"
        return 0
    fi
    
    log "テストを実行中..."
    
    # バックエンドテスト
    if [ -f "$DEPLOY_DIR/backend/requirements-test.txt" ]; then
        log "バックエンドテストを実行中..."
        
        docker run --rm \
            -v "$DEPLOY_DIR/backend:/app" \
            -v "$DEPLOY_DIR/config:/app/config:ro" \
            -e ENVIRONMENT=test \
            python:3.9-slim \
            bash -c "cd /app && pip install -r requirements-test.txt && python -m pytest tests/ -v" \
            2>>"$LOG_FILE"
        
        if [ $? -ne 0 ]; then
            error_exit "バックエンドテストが失敗しました"
        fi
    fi
    
    # フロントエンドテスト
    if [ -f "$DEPLOY_DIR/frontend/package.json" ]; then
        log "フロントエンドテストを実行中..."
        
        docker run --rm \
            -v "$DEPLOY_DIR/frontend:/app" \
            -w /app \
            node:18-alpine \
            sh -c "npm ci && npm run test" \
            2>>"$LOG_FILE"
        
        if [ $? -ne 0 ]; then
            error_exit "フロントエンドテストが失敗しました"
        fi
    fi
    
    log "テスト実行完了"
}

# Dockerイメージビルド
build_images() {
    log "Dockerイメージをビルド中..."
    
    # 既存イメージのタグ付け（ロールバック用）
    local current_version=$(get_current_version)
    if [ "$current_version" != "unknown" ]; then
        docker tag fx_backend:latest "fx_backend:$current_version" 2>/dev/null || true
        docker tag fx_frontend:latest "fx_frontend:$current_version" 2>/dev/null || true
    fi
    
    # 新しいイメージビルド
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache 2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log "Dockerイメージビルド完了"
    else
        error_exit "Dockerイメージビルドに失敗しました"
    fi
}

# データベースマイグレーション
run_migrations() {
    if [ "${RUN_MIGRATIONS:-false}" = "false" ]; then
        log "データベースマイグレーションをスキップします"
        return 0
    fi
    
    log "データベースマイグレーションを実行中..."
    
    # マイグレーション実行
    timeout "$MIGRATION_TIMEOUT" docker-compose -f "$DOCKER_COMPOSE_FILE" run --rm backend \
        python -m alembic upgrade head 2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log "データベースマイグレーション完了"
    else
        error_exit "データベースマイグレーションに失敗しました"
    fi
}

# サービス停止
stop_services() {
    log "サービスを停止中..."
    
    # 現在実行中のサービス一覧
    local running_services=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps --services --filter "status=running")
    
    if [ -n "$running_services" ]; then
        # Graceful shutdown
        docker-compose -f "$DOCKER_COMPOSE_FILE" stop 2>>"$LOG_FILE"
        
        # 停止確認
        sleep 10
        
        # 強制停止（必要な場合）
        docker-compose -f "$DOCKER_COMPOSE_FILE" kill 2>>"$LOG_FILE" || true
        docker-compose -f "$DOCKER_COMPOSE_FILE" down 2>>"$LOG_FILE" || true
    fi
    
    log "サービス停止完了"
}

# サービス開始
start_services() {
    log "サービスを開始中..."
    
    # サービス開始
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d 2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log "サービス開始完了"
    else
        error_exit "サービス開始に失敗しました"
    fi
}

# ヘルスチェック
health_check() {
    log "ヘルスチェックを実行中..."
    
    local start_time=$(date +%s)
    local timeout_time=$((start_time + HEALTH_CHECK_TIMEOUT))
    
    # 各サービスのヘルスチェック
    local services=("backend:8000/health" "frontend:3000" "postgres:5432")
    
    for service_info in "${services[@]}"; do
        local service_name=${service_info%:*}
        local endpoint=${service_info#*:}
        
        log "ヘルスチェック中: $service_name"
        
        while [ $(date +%s) -lt $timeout_time ]; do
            if docker ps | grep -q "fx_$service_name"; then
                # コンテナが実行中の場合、ヘルスチェック実行
                if [ "$service_name" = "backend" ] || [ "$service_name" = "frontend" ]; then
                    if curl -sf "http://localhost:$endpoint" &>/dev/null; then
                        log "✓ $service_name ヘルスチェック成功"
                        break
                    fi
                elif [ "$service_name" = "postgres" ]; then
                    if docker exec fx_postgres pg_isready -U fx_user -d fx_trading &>/dev/null; then
                        log "✓ $service_name ヘルスチェック成功"
                        break
                    fi
                fi
            fi
            
            sleep 5
        done
        
        # タイムアウトチェック
        if [ $(date +%s) -ge $timeout_time ]; then
            error_exit "$service_name のヘルスチェックがタイムアウトしました"
        fi
    done
    
    log "全サービスのヘルスチェック完了"
}

# デプロイメント実行
deploy() {
    local branch="${1:-main}"
    local current_version=$(get_current_version)
    
    log "デプロイメントを開始します"
    log "対象ブランチ: $branch"
    log "現在のバージョン: $current_version"
    
    # 確認
    if [ "${FORCE_DEPLOY:-false}" = "false" ]; then
        echo "本番環境にデプロイします。よろしいですか? [y/N]: "
        read -r response
        
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log "デプロイメントがキャンセルされました"
            exit 0
        fi
    fi
    
    # バックアップ作成
    local backup_path=$(create_backup "$current_version")
    
    # コードベース更新
    local new_version=$(update_codebase "$branch")
    
    # テスト実行
    run_tests
    
    # Dockerイメージビルド
    build_images
    
    # データベースマイグレーション（必要な場合）
    run_migrations
    
    # サービス停止・開始
    stop_services
    start_services
    
    # ヘルスチェック
    health_check
    
    # 古いバックアップクリーンアップ
    cleanup_old_backups
    
    # デプロイ完了通知
    send_deploy_notification "success" "$current_version" "$new_version"
    
    log "デプロイメントが正常に完了しました"
    log "新しいバージョン: $new_version"
    log "バックアップパス: $backup_path"
}

# ロールバック実行
rollback() {
    local target_version="$1"
    
    if [ -z "$target_version" ]; then
        # 利用可能なバックアップ一覧表示
        log "利用可能なバックアップ:"
        ls -la "$BACKUP_DIR" | grep "^d" | tail -5
        error_exit "ロールバック対象のバージョンを指定してください"
    fi
    
    # バックアップディレクトリ検索
    local backup_path=$(find "$BACKUP_DIR" -name "*${target_version}*" -type d | head -1)
    
    if [ -z "$backup_path" ]; then
        error_exit "指定されたバージョンのバックアップが見つかりません: $target_version"
    fi
    
    log "ロールバックを開始します: $target_version"
    log "バックアップパス: $backup_path"
    
    # 確認
    if [ "${FORCE_DEPLOY:-false}" = "false" ]; then
        echo "ロールバックを実行します。よろしいですか? [y/N]: "
        read -r response
        
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log "ロールバックがキャンセルされました"
            exit 0
        fi
    fi
    
    # 現在のバックアップ作成
    local current_version=$(get_current_version)
    create_backup "$current_version"
    
    # サービス停止
    stop_services
    
    # ファイル復元
    log "ファイルを復元中..."
    
    # アプリケーションファイル復元
    local restore_items=(
        "backend"
        "frontend"
        "scripts"
        "config"
        "docker-compose.prod.yml"
        "monitoring"
        "nginx"
    )
    
    for item in "${restore_items[@]}"; do
        if [ -e "$backup_path/$item" ]; then
            rm -rf "$DEPLOY_DIR/$item"
            cp -r "$backup_path/$item" "$DEPLOY_DIR/" 2>>"$LOG_FILE"
            log "復元完了: $item"
        fi
    done
    
    # バージョン情報復元
    if [ -f "$backup_path/.deploy_version" ]; then
        cp "$backup_path/.deploy_version" "$DEPLOY_DIR/"
    fi
    
    # データベース復元（オプション）
    if [ -f "$backup_path/database_backup.sql.gz" ]; then
        log "データベース復元を実行中..."
        
        # 一時的にPostgreSQLを起動
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres
        sleep 30
        
        # データベース復元
        zcat "$backup_path/database_backup.sql.gz" | \
        docker exec -i fx_postgres pg_restore \
            -U fx_user \
            -d fx_trading \
            --clean \
            --if-exists 2>>"$LOG_FILE"
        
        log "データベース復元完了"
    fi
    
    # サービス開始
    start_services
    
    # ヘルスチェック
    health_check
    
    # ロールバック完了通知
    send_deploy_notification "rollback" "$current_version" "$target_version"
    
    log "ロールバックが正常に完了しました"
    log "復元されたバージョン: $target_version"
}

# 古いバックアップクリーンアップ
cleanup_old_backups() {
    log "古いバックアップをクリーンアップ中..."
    
    # 古いバックアップディレクトリを削除（保持制限を超えた場合）
    local backup_count=$(ls -1d "$BACKUP_DIR"/backup_* 2>/dev/null | wc -l)
    
    if [ "$backup_count" -gt "$ROLLBACK_LIMIT" ]; then
        local delete_count=$((backup_count - ROLLBACK_LIMIT))
        
        ls -1dt "$BACKUP_DIR"/backup_* | tail -n "$delete_count" | while read -r old_backup; do
            log "削除: $old_backup"
            rm -rf "$old_backup"
        done
    fi
    
    log "バックアップクリーンアップ完了"
}

# デプロイ状況確認
check_status() {
    log "デプロイメント状況を確認中..."
    
    # 現在のバージョン
    local current_version=$(get_current_version)
    echo "現在のバージョン: $current_version"
    
    # コンテナ状況
    echo ""
    echo "コンテナ状況:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    # 最新のデプロイ履歴
    echo ""
    echo "最新のデプロイ履歴:"
    ls -la "$BACKUP_DIR" | grep "^d" | tail -5
    
    # システムリソース
    echo ""
    echo "システムリソース:"
    echo "CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "メモリ使用率: $(free | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
    echo "ディスク使用率: $(df "$DEPLOY_DIR" | awk 'NR==2{print $5}')"
}

# 通知送信
send_deploy_notification() {
    local status="$1"
    local old_version="$2"
    local new_version="$3"
    
    local message
    case "$status" in
        "success")
            message="✅ デプロイメント成功\\n旧バージョン: $old_version\\n新バージョン: $new_version"
            ;;
        "rollback")
            message="🔄 ロールバック完了\\n旧バージョン: $old_version\\n復元バージョン: $new_version"
            ;;
        "failure")
            message="❌ デプロイメント失敗\\n現在のバージョン: $old_version"
            ;;
    esac
    
    # Slack通知
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[FX Trading System] $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>>"$LOG_FILE" || true
    fi
    
    # Discord通知
    if [ -n "${DISCORD_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"content\":\"[FX Trading System] $message\"}" \
            "$DISCORD_WEBHOOK_URL" 2>>"$LOG_FILE" || true
    fi
}

# メイン処理
main() {
    local action=""
    local branch="main"
    local target_version=""
    
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -f|--force)
                FORCE_DEPLOY=true
                shift
                ;;
            -m|--migrate)
                RUN_MIGRATIONS=true
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            deploy)
                action="deploy"
                shift
                if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
                    branch="$1"
                    shift
                fi
                ;;
            rollback)
                action="rollback"
                shift
                if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
                    target_version="$1"
                    shift
                fi
                ;;
            status)
                action="status"
                shift
                ;;
            health)
                action="health"
                shift
                ;;
            list)
                action="list"
                shift
                ;;
            -*)
                error_exit "不明なオプション: $1"
                ;;
            *)
                error_exit "不明なアクション: $1"
                ;;
        esac
    done
    
    # アクション確認
    if [ -z "$action" ]; then
        usage
        error_exit "アクションが指定されていません"
    fi
    
    # 前処理
    pre_deploy_checks
    
    # アクション実行
    case "$action" in
        "deploy")
            deploy "$branch"
            ;;
        "rollback")
            rollback "$target_version"
            ;;
        "status")
            check_status
            ;;
        "health")
            health_check
            ;;
        "list")
            ls -la "$BACKUP_DIR"
            ;;
        *)
            error_exit "不明なアクション: $action"
            ;;
    esac
}

# エラーハンドリング
trap 'send_deploy_notification "failure" "$(get_current_version)" "unknown"' ERR

# root権限確認
if [ "$EUID" -ne 0 ]; then
    error_exit "このスクリプトはroot権限で実行してください"
fi

# スクリプト実行
main "$@"

log "デプロイメントスクリプトが正常に終了しました"