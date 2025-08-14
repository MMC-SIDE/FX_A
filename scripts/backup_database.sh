#!/bin/bash

# FX Trading System - データベースバックアップスクリプト
# 本番環境用自動バックアップシステム

set -euo pipefail

# 設定値読み込み
source /app/.env.prod 2>/dev/null || {
    echo "ERROR: .env.prod ファイルが見つかりません"
    exit 1
}

# 基本設定
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="/var/log/backup/backup_${TIMESTAMP}.log"
POSTGRES_CONTAINER="fx_postgres"
DB_NAME="${POSTGRES_DB:-fx_trading}"
DB_USER="${POSTGRES_USER:-fx_user}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# S3設定（オプション）
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# 前処理
setup() {
    log "バックアップ処理を開始します"
    
    # ディレクトリ作成
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # コンテナが実行中か確認
    if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
        error_exit "PostgreSQLコンテナ（$POSTGRES_CONTAINER）が実行されていません"
    fi
    
    log "バックアップ先: $BACKUP_DIR"
    log "データベース: $DB_NAME"
}

# データベースバックアップ実行
backup_database() {
    log "データベースバックアップを実行中..."
    
    local backup_file="${BACKUP_DIR}/fx_trading_backup_${TIMESTAMP}.sql"
    local compressed_file="${backup_file}.gz"
    
    # pg_dump実行
    docker exec "$POSTGRES_CONTAINER" pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --blobs \
        --create \
        --clean \
        --if-exists > "$backup_file" 2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log "データベースバックアップが完了しました: $backup_file"
        
        # 圧縮
        gzip "$backup_file"
        log "バックアップファイルを圧縮しました: $compressed_file"
        
        # ファイルサイズ確認
        local file_size=$(du -h "$compressed_file" | cut -f1)
        log "圧縮後のファイルサイズ: $file_size"
        
        echo "$compressed_file"
    else
        error_exit "データベースバックアップに失敗しました"
    fi
}

# TimescaleDBの連続集計ビューをバックアップ
backup_continuous_aggregates() {
    log "TimescaleDB連続集計ビューのバックアップを実行中..."
    
    local cagg_backup_file="${BACKUP_DIR}/timescale_caggs_${TIMESTAMP}.sql"
    
    # 連続集計ビューの定義をエクスポート
    docker exec "$POSTGRES_CONTAINER" psql \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "\\copy (SELECT schemaname, matviewname, definition FROM pg_matviews WHERE schemaname = 'public') TO STDOUT WITH CSV HEADER" \
        > "$cagg_backup_file" 2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        gzip "$cagg_backup_file"
        log "連続集計ビューのバックアップが完了しました: ${cagg_backup_file}.gz"
    else
        log "WARNING: 連続集計ビューのバックアップに失敗しました"
    fi
}

# 設定ファイルのバックアップ
backup_configs() {
    log "設定ファイルのバックアップを実行中..."
    
    local config_backup_file="${BACKUP_DIR}/configs_${TIMESTAMP}.tar.gz"
    
    tar -czf "$config_backup_file" \
        -C /app \
        config/ \
        docker-compose.prod.yml \
        nginx/nginx.conf \
        monitoring/ \
        2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log "設定ファイルのバックアップが完了しました: $config_backup_file"
    else
        log "WARNING: 設定ファイルのバックアップに失敗しました"
    fi
}

# S3へのアップロード
upload_to_s3() {
    local backup_file="$1"
    
    if [ -z "$S3_BUCKET" ]; then
        log "S3バケットが設定されていません。ローカルバックアップのみ実行します"
        return 0
    fi
    
    log "S3へのアップロードを開始します: $S3_BUCKET"
    
    # AWS CLIの確認
    if ! command -v aws &> /dev/null; then
        log "WARNING: AWS CLIがインストールされていません。S3アップロードをスキップします"
        return 0
    fi
    
    # S3アップロード
    local s3_key="backups/$(basename "$backup_file")"
    
    aws s3 cp "$backup_file" "s3://$S3_BUCKET/$s3_key" \
        --region "$AWS_REGION" \
        --storage-class STANDARD_IA \
        2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log "S3アップロードが完了しました: s3://$S3_BUCKET/$s3_key"
    else
        log "WARNING: S3アップロードに失敗しました"
    fi
}

# 古いバックアップファイルの削除
cleanup_old_backups() {
    log "古いバックアップファイルのクリーンアップを実行中..."
    
    # ローカルファイルの削除
    find "$BACKUP_DIR" -name "fx_trading_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE"
    find "$BACKUP_DIR" -name "timescale_caggs_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE"
    find "$BACKUP_DIR" -name "configs_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE"
    
    log "ローカルの古いバックアップファイルを削除しました（${RETENTION_DAYS}日以上前）"
    
    # S3の古いファイル削除
    if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)
        
        aws s3 ls "s3://$S3_BUCKET/backups/" --recursive | \
        awk -v cutoff="$cutoff_date" '$1 < cutoff {print $4}' | \
        while read -r key; do
            aws s3 rm "s3://$S3_BUCKET/$key" 2>>"$LOG_FILE"
        done
        
        log "S3の古いバックアップファイルを削除しました"
    fi
}

# バックアップ完了通知
send_notification() {
    local status="$1"
    local message="$2"
    
    # Slack通知
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[FX Trading System] バックアップ$status: $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>>"$LOG_FILE" || true
    fi
    
    # Discord通知
    if [ -n "${DISCORD_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"content\":\"[FX Trading System] バックアップ$status: $message\"}" \
            "$DISCORD_WEBHOOK_URL" 2>>"$LOG_FILE" || true
    fi
    
    # メール通知（簡易版）
    if [ -n "${EMAIL_TO:-}" ] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "[FX Trading] バックアップ$status" "$EMAIL_TO" 2>>"$LOG_FILE" || true
    fi
}

# バックアップ検証
verify_backup() {
    local backup_file="$1"
    
    log "バックアップファイルの検証を実行中..."
    
    # ファイルの存在確認
    if [ ! -f "$backup_file" ]; then
        error_exit "バックアップファイルが見つかりません: $backup_file"
    fi
    
    # ファイルサイズ確認（最低1MB必要）
    local file_size=$(stat -c%s "$backup_file")
    if [ "$file_size" -lt 1048576 ]; then
        error_exit "バックアップファイルのサイズが小さすぎます: $file_size bytes"
    fi
    
    # gzipファイルの整合性確認
    if [[ "$backup_file" == *.gz ]]; then
        if ! gzip -t "$backup_file" 2>>"$LOG_FILE"; then
            error_exit "バックアップファイルが破損しています: $backup_file"
        fi
    fi
    
    log "バックアップファイルの検証が完了しました"
}

# メイン処理
main() {
    local start_time=$(date +%s)
    
    # 前処理
    setup
    
    # バックアップ実行
    local backup_file
    backup_file=$(backup_database)
    
    # バックアップ検証
    verify_backup "$backup_file"
    
    # 追加バックアップ
    backup_continuous_aggregates
    backup_configs
    
    # S3アップロード
    upload_to_s3 "$backup_file"
    
    # クリーンアップ
    cleanup_old_backups
    
    # 処理時間計算
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    local success_message="バックアップが正常に完了しました。処理時間: ${duration}秒"
    log "$success_message"
    
    # 成功通知
    send_notification "成功" "$success_message"
}

# エラーハンドリング
trap 'error_exit "バックアップ処理中にエラーが発生しました"' ERR

# スクリプト実行
main "$@"

log "バックアップスクリプトが正常に終了しました"