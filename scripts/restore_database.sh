#!/bin/bash

# FX Trading System - データベースリストアスクリプト
# 本番環境用データベース復旧システム

set -euo pipefail

# 設定値読み込み
source /app/.env.prod 2>/dev/null || {
    echo "ERROR: .env.prod ファイルが見つかりません"
    exit 1
}

# 基本設定
BACKUP_DIR="/backups"
LOG_FILE="/var/log/backup/restore_$(date +%Y%m%d_%H%M%S).log"
POSTGRES_CONTAINER="fx_postgres"
DB_NAME="${POSTGRES_DB:-fx_trading}"
DB_USER="${POSTGRES_USER:-fx_user}"

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
使用方法: $0 [オプション] <バックアップファイル>

オプション:
  -h, --help          このヘルプを表示
  -f, --force         確認なしで実行
  -s, --s3            S3からバックアップをダウンロード
  -l, --list          利用可能なバックアップファイルを表示
  -v, --verify        リストア後にデータ検証を実行

例:
  $0 /backups/fx_trading_backup_20240101_120000.sql.gz
  $0 -s fx_trading_backup_20240101_120000.sql.gz
  $0 -l
EOF
}

# バックアップファイル一覧表示
list_backups() {
    log "利用可能なローカルバックアップファイル:"
    ls -la "$BACKUP_DIR"/fx_trading_backup_*.sql.gz 2>/dev/null | \
    awk '{print $9, $5, $6, $7, $8}' | \
    sort -r || log "ローカルバックアップファイルが見つかりません"
    
    # S3のバックアップファイル一覧
    if [ -n "${BACKUP_S3_BUCKET:-}" ] && command -v aws &> /dev/null; then
        log ""
        log "利用可能なS3バックアップファイル:"
        aws s3 ls "s3://$BACKUP_S3_BUCKET/backups/" --recursive | \
        grep "fx_trading_backup_" | \
        sort -r -k1,2 || log "S3バックアップファイルが見つかりません"
    fi
}

# S3からバックアップダウンロード
download_from_s3() {
    local filename="$1"
    local local_file="$BACKUP_DIR/$filename"
    
    if [ -z "${BACKUP_S3_BUCKET:-}" ]; then
        error_exit "S3バケットが設定されていません"
    fi
    
    if ! command -v aws &> /dev/null; then
        error_exit "AWS CLIがインストールされていません"
    fi
    
    log "S3からバックアップファイルをダウンロード中: $filename"
    
    aws s3 cp "s3://$BACKUP_S3_BUCKET/backups/$filename" "$local_file" \
        --region "${AWS_REGION:-ap-northeast-1}" 2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log "ダウンロードが完了しました: $local_file"
        echo "$local_file"
    else
        error_exit "S3からのダウンロードに失敗しました"
    fi
}

# データベース停止前の確認
pre_restore_checks() {
    local backup_file="$1"
    
    log "リストア前チェックを実行中..."
    
    # バックアップファイルの存在確認
    if [ ! -f "$backup_file" ]; then
        error_exit "バックアップファイルが見つかりません: $backup_file"
    fi
    
    # ファイル整合性確認
    if [[ "$backup_file" == *.gz ]]; then
        if ! gzip -t "$backup_file" 2>>"$LOG_FILE"; then
            error_exit "バックアップファイルが破損しています: $backup_file"
        fi
    fi
    
    # コンテナ確認
    if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
        error_exit "PostgreSQLコンテナ（$POSTGRES_CONTAINER）が実行されていません"
    fi
    
    # データベース接続確認
    if ! docker exec "$POSTGRES_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" &>/dev/null; then
        error_exit "データベースに接続できません"
    fi
    
    log "リストア前チェックが完了しました"
}

# アクティブ接続の終了
terminate_connections() {
    log "アクティブなデータベース接続を終了中..."
    
    docker exec "$POSTGRES_CONTAINER" psql \
        -U "$DB_USER" \
        -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
        2>>"$LOG_FILE" || true
    
    log "アクティブ接続の終了が完了しました"
}

# データベースリストア実行
restore_database() {
    local backup_file="$1"
    
    log "データベースリストアを開始します: $backup_file"
    
    # アクティブ接続終了
    terminate_connections
    
    # 現在のデータベースをバックアップ（安全のため）
    local pre_restore_backup="/backups/pre_restore_backup_$(date +%Y%m%d_%H%M%S).sql"
    log "リストア前のデータベースをバックアップ中..."
    
    docker exec "$POSTGRES_CONTAINER" pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --format=custom \
        --compress=9 > "$pre_restore_backup" 2>>"$LOG_FILE" || {
        log "WARNING: リストア前バックアップに失敗しました"
    }
    
    # データベース削除・再作成
    log "データベースを再作成中..."
    
    docker exec "$POSTGRES_CONTAINER" psql \
        -U "$DB_USER" \
        -d postgres \
        -c "DROP DATABASE IF EXISTS $DB_NAME;" \
        2>>"$LOG_FILE"
    
    docker exec "$POSTGRES_CONTAINER" psql \
        -U "$DB_USER" \
        -d postgres \
        -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" \
        2>>"$LOG_FILE"
    
    # TimescaleDB拡張の有効化
    docker exec "$POSTGRES_CONTAINER" psql \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "CREATE EXTENSION IF NOT EXISTS timescaledb;" \
        2>>"$LOG_FILE"
    
    # リストア実行
    log "バックアップファイルからリストア中..."
    
    if [[ "$backup_file" == *.gz ]]; then
        # 圧縮ファイルの場合
        zcat "$backup_file" | docker exec -i "$POSTGRES_CONTAINER" pg_restore \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --verbose \
            --no-owner \
            --no-privileges \
            --clean \
            --if-exists \
            2>>"$LOG_FILE"
    else
        # 非圧縮ファイルの場合
        docker exec -i "$POSTGRES_CONTAINER" pg_restore \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --verbose \
            --no-owner \
            --no-privileges \
            --clean \
            --if-exists \
            < "$backup_file" \
            2>>"$LOG_FILE"
    fi
    
    if [ $? -eq 0 ]; then
        log "データベースリストアが完了しました"
    else
        error_exit "データベースリストアに失敗しました"
    fi
}

# TimescaleDB設定の再適用
reapply_timescale_config() {
    log "TimescaleDB設定を再適用中..."
    
    # TimescaleDB設定スクリプトの実行
    if [ -f "/app/database/timescale_setup.sql" ]; then
        docker exec -i "$POSTGRES_CONTAINER" psql \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            < /app/database/timescale_setup.sql \
            2>>"$LOG_FILE" || {
            log "WARNING: TimescaleDB設定の再適用に失敗しました"
        }
    fi
    
    log "TimescaleDB設定の再適用が完了しました"
}

# リストア後の検証
verify_restore() {
    log "リストア後の検証を実行中..."
    
    # データベース接続確認
    if ! docker exec "$POSTGRES_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" &>/dev/null; then
        error_exit "リストア後のデータベースに接続できません"
    fi
    
    # テーブル数確認
    local table_count=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" \
        2>>"$LOG_FILE" | tr -d ' ')
    
    log "テーブル数: $table_count"
    
    if [ "$table_count" -lt 5 ]; then
        log "WARNING: テーブル数が少ないです。リストアが不完全な可能性があります"
    fi
    
    # TimescaleDBハイパーテーブル確認
    local hypertable_count=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t -c "SELECT COUNT(*) FROM timescaledb_information.hypertables;" \
        2>>"$LOG_FILE" | tr -d ' ')
    
    log "ハイパーテーブル数: $hypertable_count"
    
    # データ件数確認（主要テーブル）
    for table in price_data trades backtest_results; do
        local count=$(docker exec "$POSTGRES_CONTAINER" psql \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            -t -c "SELECT COUNT(*) FROM $table;" \
            2>/dev/null | tr -d ' ' || echo "0")
        log "$table テーブルのレコード数: $count"
    done
    
    log "リストア後の検証が完了しました"
}

# 完了通知
send_notification() {
    local status="$1"
    local message="$2"
    
    # Slack通知
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[FX Trading System] リストア$status: $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>>"$LOG_FILE" || true
    fi
    
    # Discord通知
    if [ -n "${DISCORD_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"content\":\"[FX Trading System] リストア$status: $message\"}" \
            "$DISCORD_WEBHOOK_URL" 2>>"$LOG_FILE" || true
    fi
}

# メイン処理
main() {
    local backup_file=""
    local force_mode=false
    local download_s3=false
    local verify_mode=false
    
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -f|--force)
                force_mode=true
                shift
                ;;
            -s|--s3)
                download_s3=true
                shift
                ;;
            -l|--list)
                list_backups
                exit 0
                ;;
            -v|--verify)
                verify_mode=true
                shift
                ;;
            -*)
                error_exit "不明なオプション: $1"
                ;;
            *)
                backup_file="$1"
                shift
                ;;
        esac
    done
    
    # バックアップファイル指定確認
    if [ -z "$backup_file" ]; then
        log "バックアップファイルが指定されていません"
        usage
        exit 1
    fi
    
    # S3からダウンロード
    if [ "$download_s3" = true ]; then
        backup_file=$(download_from_s3 "$backup_file")
    fi
    
    # 絶対パス変換
    if [[ ! "$backup_file" = /* ]]; then
        backup_file="$BACKUP_DIR/$backup_file"
    fi
    
    # 前チェック
    pre_restore_checks "$backup_file"
    
    # 確認（force modeでない場合）
    if [ "$force_mode" = false ]; then
        echo "WARNING: この操作により現在のデータベースが完全に削除されます！"
        echo "バックアップファイル: $backup_file"
        echo -n "続行しますか? [y/N]: "
        read -r response
        
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log "リストア操作がキャンセルされました"
            exit 0
        fi
    fi
    
    local start_time=$(date +%s)
    
    # リストア実行
    mkdir -p "$(dirname "$LOG_FILE")"
    log "データベースリストアを開始します"
    
    restore_database "$backup_file"
    reapply_timescale_config
    
    # 検証
    if [ "$verify_mode" = true ]; then
        verify_restore
    fi
    
    # 処理時間計算
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    local success_message="リストアが正常に完了しました。処理時間: ${duration}秒"
    log "$success_message"
    
    # 成功通知
    send_notification "成功" "$success_message"
}

# エラーハンドリング
trap 'send_notification "失敗" "リストア処理中にエラーが発生しました"' ERR

# 前処理
mkdir -p "$BACKUP_DIR"

# スクリプト実行
main "$@"

log "リストアスクリプトが正常に終了しました"