#!/bin/bash

# FX Trading System - ログローテーションスクリプト
# 本番環境用ログ管理・圧縮・削除システム

set -euo pipefail

# 設定値読み込み
source /app/.env.prod 2>/dev/null || {
    echo "ERROR: .env.prod ファイルが見つかりません"
    exit 1
}

# 基本設定
LOG_BASE_DIR="/app/logs"
ARCHIVE_DIR="/app/logs/archive"
RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"
COMPRESS_DAYS=1  # 1日経過したログを圧縮
LOG_FILE="/var/log/cron/log_rotation_$(date +%Y%m%d).log"

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
    log "ログローテーション処理を開始します"
    
    # ディレクトリ作成
    mkdir -p "$ARCHIVE_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # ディスク容量確認
    local available_space=$(df "$LOG_BASE_DIR" | awk 'NR==2 {print $4}')
    local available_gb=$((available_space / 1024 / 1024))
    
    if [ "$available_gb" -lt 1 ]; then
        error_exit "ディスク容量が不足しています (利用可能: ${available_gb}GB)"
    fi
    
    log "利用可能ディスク容量: ${available_gb}GB"
}

# アプリケーションログのローテーション
rotate_application_logs() {
    log "アプリケーションログをローテーション中..."
    
    local log_dirs=(
        "backend"
        "frontend" 
        "celery"
        "nginx"
        "postgres"
    )
    
    for dir in "${log_dirs[@]}"; do
        local log_dir="$LOG_BASE_DIR/$dir"
        
        if [ ! -d "$log_dir" ]; then
            log "WARNING: ログディレクトリが見つかりません: $log_dir"
            continue
        fi
        
        log "処理中: $log_dir"
        
        # .logファイルをローテーション
        find "$log_dir" -name "*.log" -type f | while read -r logfile; do
            local basename=$(basename "$logfile" .log)
            local dirname=$(dirname "$logfile")
            local timestamp=$(date +%Y%m%d_%H%M%S)
            local rotated_file="${dirname}/${basename}_${timestamp}.log"
            
            # ファイルサイズチェック（10MB以上の場合ローテーション）
            local file_size=$(stat -c%s "$logfile" 2>/dev/null || echo 0)
            
            if [ "$file_size" -gt 10485760 ]; then  # 10MB
                log "ローテーション: $logfile (サイズ: $((file_size / 1024 / 1024))MB)"
                
                # ファイル移動
                mv "$logfile" "$rotated_file"
                
                # 新しいログファイル作成
                touch "$logfile"
                chmod 644 "$logfile"
                
                # アプリケーションプロセスにSIGUSR1送信（ログファイル再開）
                case "$dir" in
                    "nginx")
                        docker kill -s USR1 fx_nginx 2>/dev/null || true
                        ;;
                    "backend"|"celery")
                        docker kill -s USR1 fx_backend fx_celery 2>/dev/null || true
                        ;;
                esac
            fi
        done
        
        log "完了: $log_dir"
    done
}

# 古いログファイルの圧縮
compress_old_logs() {
    log "古いログファイルを圧縮中..."
    
    # 1日以上前のログファイルを圧縮
    find "$LOG_BASE_DIR" -name "*.log" -type f -mtime +$COMPRESS_DAYS | while read -r logfile; do
        if [[ ! "$logfile" == *.gz ]]; then
            log "圧縮中: $logfile"
            
            gzip "$logfile" 2>>"$LOG_FILE"
            
            if [ $? -eq 0 ]; then
                log "圧縮完了: ${logfile}.gz"
            else
                log "WARNING: 圧縮に失敗しました: $logfile"
            fi
        fi
    done
    
    log "ログファイル圧縮が完了しました"
}

# アーカイブへの移動
archive_old_logs() {
    log "古いログファイルをアーカイブに移動中..."
    
    # 7日以上前の圧縮ログファイルをアーカイブに移動
    find "$LOG_BASE_DIR" -name "*.log.gz" -type f -mtime +7 | while read -r logfile; do
        local relative_path=${logfile#$LOG_BASE_DIR/}
        local archive_path="$ARCHIVE_DIR/$(dirname "$relative_path")"
        
        mkdir -p "$archive_path"
        
        log "アーカイブ移動: $logfile -> $archive_path/"
        
        mv "$logfile" "$archive_path/" 2>>"$LOG_FILE"
        
        if [ $? -eq 0 ]; then
            log "移動完了: $logfile"
        else
            log "WARNING: 移動に失敗しました: $logfile"
        fi
    done
    
    log "ログファイルのアーカイブが完了しました"
}

# 古いログファイルの削除
cleanup_old_logs() {
    log "古いログファイルを削除中 (保持期間: ${RETENTION_DAYS}日)"
    
    local deleted_count=0
    
    # アーカイブディレクトリから古いファイルを削除
    find "$ARCHIVE_DIR" -type f -mtime +$RETENTION_DAYS | while read -r oldfile; do
        log "削除: $oldfile"
        rm -f "$oldfile" 2>>"$LOG_FILE"
        
        if [ $? -eq 0 ]; then
            ((deleted_count++))
        else
            log "WARNING: 削除に失敗しました: $oldfile"
        fi
    done
    
    # 空のディレクトリを削除
    find "$ARCHIVE_DIR" -type d -empty -delete 2>>"$LOG_FILE" || true
    
    log "古いログファイルの削除が完了しました (削除数: $deleted_count)"
}

# システムログのクリーンアップ
cleanup_system_logs() {
    log "システムログのクリーンアップを実行中..."
    
    # journalログのクリーンアップ
    if command -v journalctl &> /dev/null; then
        journalctl --vacuum-time=30d 2>>"$LOG_FILE" || true
        journalctl --vacuum-size=1G 2>>"$LOG_FILE" || true
        log "journalログのクリーンアップが完了しました"
    fi
    
    # syslogのクリーンアップ
    if [ -d "/var/log" ]; then
        find /var/log -name "*.log" -type f -mtime +30 -delete 2>>"$LOG_FILE" || true
        find /var/log -name "*.log.*.gz" -type f -mtime +30 -delete 2>>"$LOG_FILE" || true
        log "syslogのクリーンアップが完了しました"
    fi
}

# Dockerログのクリーンアップ
cleanup_docker_logs() {
    log "Dockerログのクリーンアップを実行中..."
    
    # 大きなDockerログファイルをトランケート
    docker ps -q | while read -r container_id; do
        if [ -n "$container_id" ]; then
            local log_file="/var/lib/docker/containers/${container_id}/${container_id}-json.log"
            
            if [ -f "$log_file" ]; then
                local file_size=$(stat -c%s "$log_file" 2>/dev/null || echo 0)
                local size_mb=$((file_size / 1024 / 1024))
                
                if [ "$size_mb" -gt 100 ]; then  # 100MB以上
                    log "Dockerログをトランケート: $container_id (サイズ: ${size_mb}MB)"
                    
                    # ログの最後の1000行を保持してトランケート
                    tail -n 1000 "$log_file" > "${log_file}.tmp" 2>/dev/null || true
                    mv "${log_file}.tmp" "$log_file" 2>/dev/null || true
                fi
            fi
        fi
    done
    
    log "Dockerログのクリーンアップが完了しました"
}

# ログ統計の生成
generate_log_statistics() {
    log "ログ統計を生成中..."
    
    local stats_file="/var/log/cron/log_stats_$(date +%Y%m%d).txt"
    
    {
        echo "FX Trading System ログ統計レポート"
        echo "生成日時: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "================================="
        echo ""
        
        echo "ディスク使用量:"
        du -sh "$LOG_BASE_DIR"/* 2>/dev/null | sort -hr || true
        echo ""
        
        echo "ファイル数統計:"
        echo "- 総ログファイル数: $(find "$LOG_BASE_DIR" -name "*.log*" -type f | wc -l)"
        echo "- 圧縮ファイル数: $(find "$LOG_BASE_DIR" -name "*.gz" -type f | wc -l)"
        echo "- アーカイブファイル数: $(find "$ARCHIVE_DIR" -type f | wc -l)"
        echo ""
        
        echo "最新ログファイル:"
        find "$LOG_BASE_DIR" -name "*.log" -type f -printf "%T@ %p\n" 2>/dev/null | \
        sort -rn | head -10 | while read -r timestamp file; do
            echo "- $(date -d @${timestamp%.*} '+%Y-%m-%d %H:%M:%S') $file"
        done
        
    } > "$stats_file"
    
    log "ログ統計が生成されました: $stats_file"
}

# アラート送信
send_completion_alert() {
    local stats="$1"
    
    # Slack通知
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[FX Trading System] ログローテーション完了\\n$stats\"}" \
            "$SLACK_WEBHOOK_URL" 2>>"$LOG_FILE" || true
    fi
}

# メイン処理
main() {
    local start_time=$(date +%s)
    
    # 前処理
    setup
    
    # ローテーション実行
    rotate_application_logs
    compress_old_logs
    archive_old_logs
    cleanup_old_logs
    cleanup_system_logs
    cleanup_docker_logs
    
    # 統計生成
    generate_log_statistics
    
    # 処理時間計算
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # 統計情報
    local total_files=$(find "$LOG_BASE_DIR" "$ARCHIVE_DIR" -type f 2>/dev/null | wc -l)
    local total_size=$(du -sh "$LOG_BASE_DIR" "$ARCHIVE_DIR" 2>/dev/null | awk '{sum+=$1} END {print sum}')
    
    local completion_stats="処理時間: ${duration}秒, 総ファイル数: $total_files, 総サイズ: ${total_size}KB"
    
    log "ログローテーション処理が正常に完了しました"
    log "$completion_stats"
    
    # 完了通知
    send_completion_alert "$completion_stats"
}

# エラーハンドリング
trap 'error_exit "ログローテーション処理中にエラーが発生しました"' ERR

# スクリプト実行
main "$@"

log "ログローテーションスクリプトが正常に終了しました"