#!/bin/bash

# FX Trading System - Cron ジョブセットアップスクリプト
# 本番環境用の定期実行タスク設定

set -euo pipefail

# 設定
SCRIPT_DIR="/app/scripts"
LOG_DIR="/var/log/cron"
CRONTAB_FILE="$SCRIPT_DIR/crontab"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# 前処理チェック
pre_setup_checks() {
    log "Cron設定の前処理チェックを実行中..."
    
    # 必要なディレクトリの存在確認
    if [ ! -d "$SCRIPT_DIR" ]; then
        error_exit "スクリプトディレクトリが存在しません: $SCRIPT_DIR"
    fi
    
    # Crontabファイルの存在確認
    if [ ! -f "$CRONTAB_FILE" ]; then
        error_exit "Crontabファイルが存在しません: $CRONTAB_FILE"
    fi
    
    # cronサービスの確認
    if ! systemctl is-active --quiet cron; then
        log "cronサービスを開始します"
        systemctl start cron
        systemctl enable cron
    fi
    
    log "前処理チェックが完了しました"
}

# ログディレクトリ作成
create_log_directories() {
    log "ログディレクトリを作成中..."
    
    # ベースログディレクトリ
    mkdir -p "$LOG_DIR"
    
    # 個別ログディレクトリ
    local log_dirs=(
        "backup"
        "health"
        "maintenance"
        "security"
        "monitoring"
        "reports"
        "cleanup"
    )
    
    for dir in "${log_dirs[@]}"; do
        mkdir -p "$LOG_DIR/$dir"
        log "作成済み: $LOG_DIR/$dir"
    done
    
    # ログディレクトリの権限設定
    chown -R root:root "$LOG_DIR"
    chmod -R 755 "$LOG_DIR"
    
    log "ログディレクトリの作成が完了しました"
}

# スクリプトファイルの権限設定
set_script_permissions() {
    log "スクリプトファイルの権限を設定中..."
    
    # 実行可能なスクリプトファイル
    local script_files=(
        "backup_database.sh"
        "restore_database.sh"
        "health_check.sh"
        "disk_check.sh"
        "db_maintenance.sh"
        "db_vacuum.sh"
        "timescale_compression_check.sh"
        "timescale_maintenance.sh"
        "security_audit.sh"
        "ssl_check.sh"
        "metrics_alert.sh"
        "prometheus_check.sh"
        "generate_daily_report.sh"
        "generate_weekly_report.sh"
        "generate_monthly_report.sh"
        "update_check.sh"
        "container_update_check.sh"
    )
    
    for script in "${script_files[@]}"; do
        local script_path="$SCRIPT_DIR/$script"
        if [ -f "$script_path" ]; then
            chmod +x "$script_path"
            log "実行権限設定済み: $script_path"
        else
            log "WARNING: スクリプトファイルが見つかりません: $script_path"
        fi
    done
    
    log "スクリプトファイルの権限設定が完了しました"
}

# Crontab設定の適用
install_crontab() {
    log "Crontab設定を適用中..."
    
    # 現在のcrontabをバックアップ
    local backup_file="/tmp/crontab_backup_$(date +%Y%m%d_%H%M%S)"
    if crontab -l > "$backup_file" 2>/dev/null; then
        log "既存のcrontabをバックアップしました: $backup_file"
    fi
    
    # 新しいcrontabを適用
    if crontab "$CRONTAB_FILE"; then
        log "Crontab設定が正常に適用されました"
    else
        error_exit "Crontab設定の適用に失敗しました"
    fi
    
    # 設定確認
    log "適用されたCrontab設定:"
    crontab -l | head -20
    
    log "Crontab設定の適用が完了しました"
}

# logrotate設定
setup_logrotate() {
    log "Logrotate設定を作成中..."
    
    local logrotate_config="/etc/logrotate.d/fx_trading"
    
    cat > "$logrotate_config" << 'EOF'
# FX Trading System - Logrotate設定

# アプリケーションログ
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        /usr/bin/docker kill -s USR1 fx_backend 2>/dev/null || true
    endscript
}

# Cronログ
/var/log/cron/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 root root
}

# Nginxログ
/app/logs/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 nginx nginx
    postrotate
        /usr/bin/docker kill -s USR1 fx_nginx 2>/dev/null || true
    endscript
}

# バックアップログ
/var/log/backup/*.log {
    weekly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF
    
    # logrotateの権限設定
    chmod 644 "$logrotate_config"
    
    # logrotateのテスト
    if logrotate -d "$logrotate_config" &>/dev/null; then
        log "Logrotate設定が正常に作成されました"
    else
        log "WARNING: Logrotate設定にエラーがあります"
    fi
    
    log "Logrotate設定の作成が完了しました"
}

# システムサービス設定
setup_systemd_services() {
    log "Systemdサービス設定を作成中..."
    
    # FX Trading Systemサービス
    cat > /etc/systemd/system/fx-trading.service << 'EOF'
[Unit]
Description=FX Trading System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=/app
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    # システムサービスのリロード
    systemctl daemon-reload
    systemctl enable fx-trading.service
    
    log "Systemdサービス設定が完了しました"
}

# ヘルスチェックスクリプトの作成
create_health_check_script() {
    log "ヘルスチェックスクリプトを作成中..."
    
    cat > "$SCRIPT_DIR/health_check.sh" << 'EOF'
#!/bin/bash

# FX Trading System - ヘルスチェックスクリプト

set -euo pipefail

LOG_FILE="/var/log/cron/health/health_$(date +%Y%m%d).log"
ALERT_THRESHOLD=3
ERROR_COUNT=0

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# アラート送信
send_alert() {
    local message="$1"
    
    # Slack通知
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[FX Trading System] ヘルスチェック異常: $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi
}

# コンテナヘルスチェック
check_containers() {
    local containers=("fx_backend" "fx_frontend" "fx_postgres" "fx_redis" "fx_nginx")
    
    for container in "${containers[@]}"; do
        if ! docker ps | grep -q "$container"; then
            log "ERROR: コンテナが停止しています: $container"
            ((ERROR_COUNT++))
        else
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health-check")
            if [ "$health" = "unhealthy" ]; then
                log "ERROR: コンテナが異常状態です: $container"
                ((ERROR_COUNT++))
            fi
        fi
    done
}

# データベース接続チェック
check_database() {
    if ! docker exec fx_postgres pg_isready -U fx_user -d fx_trading &>/dev/null; then
        log "ERROR: データベースに接続できません"
        ((ERROR_COUNT++))
    fi
}

# API応答チェック
check_api() {
    if ! curl -sf http://localhost:8000/health &>/dev/null; then
        log "ERROR: APIが応答しません"
        ((ERROR_COUNT++))
    fi
}

# ディスク容量チェック
check_disk_space() {
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$usage" -gt 85 ]; then
        log "WARNING: ディスク使用量が高いです: ${usage}%"
        if [ "$usage" -gt 95 ]; then
            ((ERROR_COUNT++))
        fi
    fi
}

# メモリ使用量チェック
check_memory() {
    local usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$usage" -gt 90 ]; then
        log "WARNING: メモリ使用量が高いです: ${usage}%"
        if [ "$usage" -gt 95 ]; then
            ((ERROR_COUNT++))
        fi
    fi
}

# メイン処理
main() {
    mkdir -p "$(dirname "$LOG_FILE")"
    
    check_containers
    check_database
    check_api
    check_disk_space
    check_memory
    
    if [ "$ERROR_COUNT" -ge "$ALERT_THRESHOLD" ]; then
        send_alert "${ERROR_COUNT}個の重大な問題が検出されました"
    fi
    
    log "ヘルスチェック完了 (エラー数: $ERROR_COUNT)"
}

main "$@"
EOF
    
    chmod +x "$SCRIPT_DIR/health_check.sh"
    log "ヘルスチェックスクリプトが作成されました"
}

# 設定確認
verify_setup() {
    log "設定確認を実行中..."
    
    # Crontab確認
    if crontab -l | grep -q "backup_database.sh"; then
        log "✓ Crontab設定が正常に確認されました"
    else
        log "✗ Crontab設定に問題があります"
    fi
    
    # ログディレクトリ確認
    if [ -d "$LOG_DIR" ] && [ -w "$LOG_DIR" ]; then
        log "✓ ログディレクトリが正常に設定されました"
    else
        log "✗ ログディレクトリに問題があります"
    fi
    
    # スクリプト権限確認
    if [ -x "$SCRIPT_DIR/backup_database.sh" ]; then
        log "✓ スクリプトファイルの権限が正常に設定されました"
    else
        log "✗ スクリプトファイルの権限に問題があります"
    fi
    
    log "設定確認が完了しました"
}

# メイン処理
main() {
    log "FX Trading System Cron設定を開始します"
    
    pre_setup_checks
    create_log_directories
    set_script_permissions
    create_health_check_script
    setup_logrotate
    setup_systemd_services
    install_crontab
    verify_setup
    
    log "Cron設定が正常に完了しました"
    log "次回の実行時刻:"
    crontab -l | grep -v '^#' | grep -v '^$' | head -5
}

# エラーハンドリング
trap 'error_exit "Cron設定中にエラーが発生しました"' ERR

# root権限確認
if [ "$EUID" -ne 0 ]; then
    error_exit "このスクリプトはroot権限で実行してください"
fi

# スクリプト実行
main "$@"

log "Cronセットアップスクリプトが正常に終了しました"