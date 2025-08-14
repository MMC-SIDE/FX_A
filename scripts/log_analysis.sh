#!/bin/bash

# FX Trading System - ログ分析スクリプト
# エラー検出・パフォーマンス分析・異常検出システム

set -euo pipefail

# 設定値読み込み
source /app/.env.prod 2>/dev/null || {
    echo "ERROR: .env.prod ファイルが見つかりません"
    exit 1
}

# 基本設定
LOG_BASE_DIR="/app/logs"
ANALYSIS_DIR="/var/log/analysis"
REPORT_DIR="/var/log/reports"
LOG_FILE="/var/log/cron/log_analysis_$(date +%Y%m%d).log"

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
    log "ログ分析処理を開始します"
    
    # ディレクトリ作成
    mkdir -p "$ANALYSIS_DIR"
    mkdir -p "$REPORT_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log "分析対象期間: 過去24時間"
}

# エラーログ分析
analyze_error_logs() {
    log "エラーログを分析中..."
    
    local error_report="$ANALYSIS_DIR/error_analysis_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "FX Trading System エラーログ分析レポート"
        echo "分析期間: $(date -d '24 hours ago' '+%Y-%m-%d %H:%M:%S') - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "========================================================"
        echo ""
        
        # バックエンドエラー
        echo "【バックエンドエラー】"
        find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "error\|exception\|traceback" 2>/dev/null | \
        grep -v "INFO\|DEBUG" | \
        sort | uniq -c | sort -rn | head -20 || echo "エラーなし"
        echo ""
        
        # MT5接続エラー
        echo "【MT5接続エラー】"
        find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "mt5\|metatrader.*error\|connection.*failed" 2>/dev/null | \
        wc -l | awk '{print "MT5関連エラー: " $1 "件"}'
        echo ""
        
        # データベースエラー
        echo "【データベースエラー】"
        find "$LOG_BASE_DIR/postgres" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "error\|fatal\|panic" 2>/dev/null | \
        grep -v "connection.*terminated" | \
        wc -l | awk '{print "データベースエラー: " $1 "件"}'
        echo ""
        
        # Nginxエラー
        echo "【Nginxエラー】"
        find "$LOG_BASE_DIR/nginx" -name "*error*.log*" -type f -mtime -1 | \
        xargs grep -v "info" 2>/dev/null | \
        awk '{print $4}' | sort | uniq -c | sort -rn | head -10 || echo "エラーなし"
        echo ""
        
        # 取引エラー
        echo "【取引エラー】"
        find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "trading.*error\|order.*failed\|position.*error" 2>/dev/null | \
        wc -l | awk '{print "取引エラー: " $1 "件"}'
        
    } > "$error_report"
    
    log "エラーログ分析完了: $error_report"
    
    # 重要エラーの閾値チェック
    local critical_errors=$(find "$LOG_BASE_DIR" -name "*.log*" -type f -mtime -1 | \
                           xargs grep -i "critical\|fatal\|panic" 2>/dev/null | wc -l)
    
    if [ "$critical_errors" -gt 10 ]; then
        send_alert "critical" "重要エラーが多発しています (件数: $critical_errors)"
    fi
}

# パフォーマンス分析
analyze_performance() {
    log "パフォーマンスログを分析中..."
    
    local perf_report="$ANALYSIS_DIR/performance_analysis_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "FX Trading System パフォーマンス分析レポート"
        echo "分析期間: $(date -d '24 hours ago' '+%Y-%m-%d %H:%M:%S') - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "==========================================================="
        echo ""
        
        # API応答時間分析
        echo "【API応答時間分析】"
        if [ -f "$LOG_BASE_DIR/nginx/access.log" ]; then
            awk '$NF > 2.0 {print $NF}' "$LOG_BASE_DIR/nginx/access.log" | \
            sort -rn | head -10 | \
            awk '{print "遅い応答時間: " $1 "秒"}' || echo "データなし"
        fi
        echo ""
        
        # データベースクエリ分析
        echo "【データベースクエリ分析】"
        find "$LOG_BASE_DIR/postgres" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "duration:" 2>/dev/null | \
        awk '{print $NF}' | sed 's/ms//' | \
        awk '$1 > 1000 {count++} END {print "1秒以上のクエリ: " (count ? count : 0) "件"}'
        echo ""
        
        # メモリ使用量警告
        echo "【リソース使用量】"
        find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "memory\|oom\|out of memory" 2>/dev/null | \
        wc -l | awk '{print "メモリ関連警告: " $1 "件"}'
        echo ""
        
        # 取引処理時間
        echo "【取引処理時間】"
        find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "order.*executed.*duration" 2>/dev/null | \
        awk '{print $(NF-1)}' | sed 's/ms//' | \
        awk '{sum+=$1; count++} END {if(count>0) print "平均取引処理時間: " sum/count "ms"; else print "取引データなし"}'
        
    } > "$perf_report"
    
    log "パフォーマンス分析完了: $perf_report"
}

# セキュリティログ分析
analyze_security_logs() {
    log "セキュリティログを分析中..."
    
    local security_report="$ANALYSIS_DIR/security_analysis_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "FX Trading System セキュリティ分析レポート"
        echo "分析期間: $(date -d '24 hours ago' '+%Y-%m-%d %H:%M:%S') - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "=========================================================="
        echo ""
        
        # 認証失敗分析
        echo "【認証失敗分析】"
        find "$LOG_BASE_DIR/nginx" -name "*access*.log*" -type f -mtime -1 | \
        xargs grep " 401 \| 403 " 2>/dev/null | \
        awk '{print $1}' | sort | uniq -c | sort -rn | head -10 | \
        awk '{print "IP: " $2 " 失敗回数: " $1}' || echo "認証失敗なし"
        echo ""
        
        # 不正アクセス試行
        echo "【不正アクセス試行】"
        find "$LOG_BASE_DIR/nginx" -name "*access*.log*" -type f -mtime -1 | \
        xargs grep -E "(admin|login|wp-|phpmyadmin)" 2>/dev/null | \
        grep " 404 " | \
        awk '{print $1}' | sort | uniq -c | sort -rn | head -5 | \
        awk '{print "IP: " $2 " 試行回数: " $1}' || echo "不正アクセス試行なし"
        echo ""
        
        # 大量アクセス
        echo "【大量アクセス検出】"
        find "$LOG_BASE_DIR/nginx" -name "*access*.log*" -type f -mtime -1 | \
        xargs awk '{print $1}' 2>/dev/null | \
        sort | uniq -c | sort -rn | head -5 | \
        awk '$1 > 1000 {print "IP: " $2 " アクセス数: " $1}' || echo "大量アクセスなし"
        echo ""
        
        # SQLインジェクション試行
        echo "【SQLインジェクション試行】"
        find "$LOG_BASE_DIR/nginx" -name "*access*.log*" -type f -mtime -1 | \
        xargs grep -i -E "(union|select|drop|insert|update|delete).*=" 2>/dev/null | \
        wc -l | awk '{print "SQLインジェクション試行: " $1 "件"}'
        
    } > "$security_report"
    
    log "セキュリティ分析完了: $security_report"
    
    # セキュリティ異常の閾値チェック
    local failed_auths=$(find "$LOG_BASE_DIR/nginx" -name "*access*.log*" -type f -mtime -1 | \
                         xargs grep " 401 \| 403 " 2>/dev/null | wc -l)
    
    if [ "$failed_auths" -gt 100 ]; then
        send_alert "security" "認証失敗が多発しています (件数: $failed_auths)"
    fi
}

# 取引ログ分析
analyze_trading_logs() {
    log "取引ログを分析中..."
    
    local trading_report="$ANALYSIS_DIR/trading_analysis_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "FX Trading System 取引分析レポート"
        echo "分析期間: $(date -d '24 hours ago' '+%Y-%m-%d %H:%M:%S') - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "================================================="
        echo ""
        
        # 取引回数
        echo "【取引統計】"
        local trades_count=$(find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
                            xargs grep -i "order.*executed" 2>/dev/null | wc -l)
        echo "総取引回数: $trades_count"
        
        # 取引成功率
        local success_count=$(find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
                             xargs grep -i "order.*executed.*success" 2>/dev/null | wc -l)
        if [ "$trades_count" -gt 0 ]; then
            local success_rate=$((success_count * 100 / trades_count))
            echo "取引成功率: ${success_rate}%"
        fi
        echo ""
        
        # 通貨ペア別取引
        echo "【通貨ペア別取引回数】"
        find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "order.*executed" 2>/dev/null | \
        grep -oE "(USD|EUR|GBP|AUD|NZD|CAD|CHF|JPY){3,6}" | \
        sort | uniq -c | sort -rn || echo "データなし"
        echo ""
        
        # エラー分析
        echo "【取引エラー】"
        find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "trading.*error\|order.*failed" 2>/dev/null | \
        wc -l | awk '{print "取引エラー: " $1 "件"}'
        echo ""
        
        # MT5接続状況
        echo "【MT5接続状況】"
        find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "mt5.*connected\|mt5.*disconnected" 2>/dev/null | \
        tail -10 || echo "接続ログなし"
        
    } > "$trading_report"
    
    log "取引分析完了: $trading_report"
}

# 異常検出
detect_anomalies() {
    log "異常検出を実行中..."
    
    local anomaly_report="$ANALYSIS_DIR/anomaly_detection_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "FX Trading System 異常検出レポート"
        echo "検出期間: $(date -d '24 hours ago' '+%Y-%m-%d %H:%M:%S') - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "=============================================="
        echo ""
        
        # ログ出力量の異常
        echo "【ログ出力量異常】"
        local today_logs=$(find "$LOG_BASE_DIR" -name "*.log" -type f -mtime -1 -exec wc -l {} + | \
                          awk '{sum+=$1} END {print sum}')
        local yesterday_logs=$(find "$LOG_BASE_DIR" -name "*.log*" -type f -mtime -2 -mtime +1 -exec zcat -f {} \; 2>/dev/null | wc -l)
        
        if [ "$today_logs" -gt 0 ] && [ "$yesterday_logs" -gt 0 ]; then
            local log_ratio=$((today_logs * 100 / yesterday_logs))
            if [ "$log_ratio" -gt 200 ]; then
                echo "警告: ログ出力量が異常に増加 (前日比: ${log_ratio}%)"
            elif [ "$log_ratio" -lt 50 ]; then
                echo "警告: ログ出力量が異常に減少 (前日比: ${log_ratio}%)"
            else
                echo "正常: ログ出力量 (前日比: ${log_ratio}%)"
            fi
        fi
        echo ""
        
        # 繰り返しエラーの検出
        echo "【繰り返しエラー検出】"
        find "$LOG_BASE_DIR" -name "*.log*" -type f -mtime -1 | \
        xargs grep -i "error" 2>/dev/null | \
        awk '{print substr($0, index($0, "error"))}' | \
        sort | uniq -c | sort -rn | head -5 | \
        awk '$1 > 10 {print "頻発エラー: " $0}' || echo "頻発エラーなし"
        echo ""
        
        # 急激な処理時間変化
        echo "【処理時間異常】"
        find "$LOG_BASE_DIR/nginx" -name "*access*.log*" -type f -mtime -1 | \
        xargs awk '$NF > 5.0' 2>/dev/null | \
        wc -l | awk '{if($1 > 50) print "警告: 遅い応答時間が多発 (" $1 "件)"; else print "正常: 応答時間"}'
        
    } > "$anomaly_report"
    
    log "異常検出完了: $anomaly_report"
}

# 日次サマリーレポート生成
generate_daily_summary() {
    log "日次サマリーレポートを生成中..."
    
    local summary_report="$REPORT_DIR/daily_summary_$(date +%Y%m%d).txt"
    
    {
        echo "FX Trading System 日次サマリーレポート"
        echo "対象日: $(date '+%Y年%m月%d日')"
        echo "生成時刻: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "============================================="
        echo ""
        
        # システム稼働状況
        echo "【システム稼働状況】"
        local uptime_hours=$(docker ps --format "table {{.Status}}" | grep -o "Up [0-9]* hours" | \
                            awk '{print $2}' | head -1)
        echo "稼働時間: ${uptime_hours:-N/A} 時間"
        echo ""
        
        # エラーサマリー
        echo "【エラーサマリー】"
        local total_errors=$(find "$LOG_BASE_DIR" -name "*.log*" -type f -mtime -1 | \
                            xargs grep -i "error" 2>/dev/null | wc -l)
        echo "総エラー数: $total_errors"
        echo ""
        
        # 取引サマリー
        echo "【取引サマリー】"
        local total_trades=$(find "$LOG_BASE_DIR/backend" -name "*.log*" -type f -mtime -1 | \
                            xargs grep -i "order.*executed" 2>/dev/null | wc -l)
        echo "総取引数: $total_trades"
        echo ""
        
        # リソース使用量
        echo "【リソース使用量】"
        echo "ディスク使用量: $(du -sh "$LOG_BASE_DIR" | awk '{print $1}')"
        echo ""
        
        # 推奨アクション
        echo "【推奨アクション】"
        if [ "$total_errors" -gt 100 ]; then
            echo "- エラー調査を実施してください"
        fi
        if [ "$total_trades" -eq 0 ]; then
            echo "- 取引システムの動作確認を行ってください"
        fi
        echo "- 定期的なシステムメンテナンスを実施してください"
        
    } > "$summary_report"
    
    log "日次サマリーレポート生成完了: $summary_report"
}

# アラート送信
send_alert() {
    local severity="$1"
    local message="$2"
    
    # Slack通知
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local color="warning"
        if [ "$severity" = "critical" ]; then
            color="danger"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[FX Trading System] ログ分析アラート\\n重要度: $severity\\n内容: $message\"}" \
            "$SLACK_WEBHOOK_URL" 2>>"$LOG_FILE" || true
    fi
}

# メイン処理
main() {
    local start_time=$(date +%s)
    
    # 前処理
    setup
    
    # 各種分析実行
    analyze_error_logs
    analyze_performance
    analyze_security_logs
    analyze_trading_logs
    detect_anomalies
    generate_daily_summary
    
    # 処理時間計算
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "ログ分析処理が正常に完了しました (処理時間: ${duration}秒)"
}

# エラーハンドリング
trap 'error_exit "ログ分析処理中にエラーが発生しました"' ERR

# スクリプト実行
main "$@"

log "ログ分析スクリプトが正常に終了しました"