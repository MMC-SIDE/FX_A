#!/bin/bash

# FX Trading System - 本番環境初期セットアップスクリプト
# サーバー初回構築用の完全自動化スクリプト

set -euo pipefail

# 基本設定
SETUP_LOG="/var/log/production_setup.log"
FX_USER="fxtrading"
FX_HOME="/app"
DOCKER_COMPOSE_VERSION="v2.23.0"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$SETUP_LOG"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# 前提条件チェック
check_prerequisites() {
    log "前提条件をチェック中..."
    
    # OS確認
    if [ ! -f /etc/os-release ]; then
        error_exit "サポートされていないOS"
    fi
    
    . /etc/os-release
    if [[ ! "$ID" =~ ^(ubuntu|debian|centos|rhel)$ ]]; then
        error_exit "サポートされていないOS: $ID"
    fi
    
    # root権限確認
    if [ "$EUID" -ne 0 ]; then
        error_exit "このスクリプトはroot権限で実行してください"
    fi
    
    # ネットワーク接続確認
    if ! ping -c 1 google.com &>/dev/null; then
        error_exit "インターネット接続が必要です"
    fi
    
    log "前提条件チェック完了"
}

# システム更新
update_system() {
    log "システムを更新中..."
    
    case "$ID" in
        ubuntu|debian)
            export DEBIAN_FRONTEND=noninteractive
            apt-get update && apt-get upgrade -y
            apt-get install -y curl wget gnupg2 software-properties-common apt-transport-https ca-certificates lsb-release
            ;;
        centos|rhel)
            yum update -y
            yum install -y curl wget gnupg2 yum-utils device-mapper-persistent-data lvm2
            ;;
    esac
    
    log "システム更新完了"
}

# 必要なパッケージインストール
install_packages() {
    log "必要なパッケージをインストール中..."
    
    local packages=(
        "git"
        "htop"
        "iotop"
        "netstat-tools"
        "unzip"
        "jq"
        "tree"
        "vim"
        "tmux"
        "fail2ban"
        "ufw"
        "logrotate"
        "cron"
        "rsync"
        "aws-cli"
    )
    
    case "$ID" in
        ubuntu|debian)
            # 追加リポジトリ
            add-apt-repository -y universe
            apt-get update
            
            # パッケージインストール
            for package in "${packages[@]}"; do
                apt-get install -y "$package" || log "WARNING: $package のインストールに失敗"
            done
            ;;
        centos|rhel)
            # EPEL有効化
            yum install -y epel-release
            
            # パッケージインストール
            for package in "${packages[@]}"; do
                yum install -y "$package" || log "WARNING: $package のインストールに失敗"
            done
            ;;
    esac
    
    log "パッケージインストール完了"
}

# Dockerインストール
install_docker() {
    log "Dockerをインストール中..."
    
    # 既存のDockerを削除
    case "$ID" in
        ubuntu|debian)
            apt-get remove -y docker docker-engine docker.io containerd runc || true
            
            # Docker公式リポジトリ追加
            curl -fsSL https://download.docker.com/linux/$ID/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$ID $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        centos|rhel)
            yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine || true
            
            # Docker公式リポジトリ追加
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
    esac
    
    # Dockerサービス開始・有効化
    systemctl start docker
    systemctl enable docker
    
    # Docker Compose インストール
    curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    # 動作確認
    docker --version
    docker-compose --version
    
    log "Docker インストール完了"
}

# ユーザー作成・設定
setup_user() {
    log "FXアプリケーション用ユーザーを設定中..."
    
    # ユーザー作成
    if ! id "$FX_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$FX_USER"
        log "ユーザー作成: $FX_USER"
    fi
    
    # Dockerグループに追加
    usermod -aG docker "$FX_USER"
    
    # sudoers設定
    echo "$FX_USER ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/local/bin/docker-compose, /bin/systemctl" > "/etc/sudoers.d/$FX_USER"
    
    # SSH鍵設定（公開鍵を配置）
    local ssh_dir="/home/$FX_USER/.ssh"
    mkdir -p "$ssh_dir"
    chmod 700 "$ssh_dir"
    
    # 必要に応じて公開鍵を配置
    # echo "ssh-rsa YOUR_PUBLIC_KEY_HERE" > "$ssh_dir/authorized_keys"
    # chmod 600 "$ssh_dir/authorized_keys"
    # chown -R "$FX_USER:$FX_USER" "$ssh_dir"
    
    log "ユーザー設定完了"
}

# ディレクトリ構造作成
create_directories() {
    log "ディレクトリ構造を作成中..."
    
    # アプリケーションディレクトリ
    mkdir -p "$FX_HOME"
    
    # ログディレクトリ
    mkdir -p "$FX_HOME/logs/"{backend,frontend,nginx,postgres,celery,monitoring}
    
    # データディレクトリ
    mkdir -p "$FX_HOME/data/"{postgres,redis,prometheus,grafana}
    
    # バックアップディレクトリ
    mkdir -p "$FX_HOME/backups/"{database,deploy,config}
    
    # 設定ディレクトリ
    mkdir -p "$FX_HOME/config"
    
    # スクリプトディレクトリ
    mkdir -p "$FX_HOME/scripts"
    
    # 監視ディレクトリ
    mkdir -p "$FX_HOME/monitoring/"{prometheus,grafana,alertmanager}
    
    # SSL証明書ディレクトリ
    mkdir -p "$FX_HOME/nginx/ssl"
    
    # 権限設定
    chown -R "$FX_USER:$FX_USER" "$FX_HOME"
    chmod -R 755 "$FX_HOME"
    
    # ログディレクトリの特別な権限
    chmod -R 777 "$FX_HOME/logs"
    chmod -R 755 "$FX_HOME/data"
    
    log "ディレクトリ構造作成完了"
}

# ファイアウォール設定
setup_firewall() {
    log "ファイアウォールを設定中..."
    
    # UFW設定
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # 必要なポートを開放
    ufw allow 22/tcp comment 'SSH'
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    ufw allow 3001/tcp comment 'Grafana'
    ufw allow 9090/tcp comment 'Prometheus'
    ufw allow from 172.20.0.0/16 comment 'Docker network'
    
    # UFW有効化
    ufw --force enable
    
    log "ファイアウォール設定完了"
}

# Fail2Ban設定
setup_fail2ban() {
    log "Fail2Banを設定中..."
    
    # SSH保護設定
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /app/logs/nginx/error.log
maxretry = 3
bantime = 3600

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /app/logs/nginx/error.log
maxretry = 10
bantime = 600
EOF
    
    # Fail2Banサービス再起動
    systemctl restart fail2ban
    systemctl enable fail2ban
    
    log "Fail2Ban設定完了"
}

# SSL証明書生成（自己署名証明書）
generate_ssl_certificates() {
    log "SSL証明書を生成中..."
    
    local ssl_dir="$FX_HOME/nginx/ssl"
    local cert_file="$ssl_dir/cert.pem"
    local key_file="$ssl_dir/key.pem"
    
    # 自己署名証明書生成
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$key_file" \
        -out "$cert_file" \
        -subj "/C=JP/ST=Tokyo/L=Tokyo/O=FX Trading System/CN=fx-trading.local"
    
    # 権限設定
    chmod 600 "$key_file"
    chmod 644 "$cert_file"
    chown "$FX_USER:$FX_USER" "$cert_file" "$key_file"
    
    log "SSL証明書生成完了"
    log "NOTE: 本番環境では有効なSSL証明書を使用してください"
}

# システム最適化
optimize_system() {
    log "システムを最適化中..."
    
    # カーネルパラメータ最適化
    cat > /etc/sysctl.d/99-fx-trading.conf << 'EOF'
# ネットワーク最適化
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15

# ファイルディスクリプタ
fs.file-max = 2097152

# 仮想メモリ
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF
    
    # 設定適用
    sysctl -p /etc/sysctl.d/99-fx-trading.conf
    
    # ulimit設定
    cat > /etc/security/limits.d/99-fx-trading.conf << 'EOF'
# FX Trading System limits
root soft nofile 1048576
root hard nofile 1048576
fxtrading soft nofile 1048576
fxtrading hard nofile 1048576
EOF
    
    # systemd設定
    mkdir -p /etc/systemd/system.conf.d
    cat > /etc/systemd/system.conf.d/limits.conf << 'EOF'
[Manager]
DefaultLimitNOFILE=1048576
EOF
    
    systemctl daemon-reload
    
    log "システム最適化完了"
}

# 監視エージェントインストール
install_monitoring_agents() {
    log "監視エージェントをインストール中..."
    
    # Node Exporter インストール
    local node_exporter_version="1.6.1"
    wget -q "https://github.com/prometheus/node_exporter/releases/download/v${node_exporter_version}/node_exporter-${node_exporter_version}.linux-amd64.tar.gz"
    tar xzf "node_exporter-${node_exporter_version}.linux-amd64.tar.gz"
    mv "node_exporter-${node_exporter_version}.linux-amd64/node_exporter" /usr/local/bin/
    rm -rf "node_exporter-${node_exporter_version}.linux-amd64"*
    
    # Node Exporter用ユーザー作成
    useradd --no-create-home --shell /bin/false node_exporter || true
    
    # Node Exporter systemdサービス
    cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=:9100

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable node_exporter
    systemctl start node_exporter
    
    log "監視エージェントインストール完了"
}

# 自動更新設定
setup_auto_updates() {
    log "自動更新を設定中..."
    
    case "$ID" in
        ubuntu|debian)
            # unattended-upgrades設定
            apt-get install -y unattended-upgrades
            
            cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::Package-Blacklist {
    "docker-ce";
    "docker-ce-cli";
    "containerd.io";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF
            
            cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
            ;;
        centos|rhel)
            # yum-cron設定
            yum install -y yum-cron
            
            sed -i 's/update_cmd = default/update_cmd = security/' /etc/yum/yum-cron.conf
            sed -i 's/apply_updates = no/apply_updates = yes/' /etc/yum/yum-cron.conf
            
            systemctl enable yum-cron
            systemctl start yum-cron
            ;;
    esac
    
    log "自動更新設定完了"
}

# 初期設定ファイル作成
create_initial_configs() {
    log "初期設定ファイルを作成中..."
    
    # .env.prod テンプレート作成
    cat > "$FX_HOME/.env.prod.template" << 'EOF'
# FX Trading System - 本番環境設定テンプレート
# このファイルをコピーして .env.prod として設定してください

# データベース設定
DB_PASSWORD=your_secure_database_password_here
POSTGRES_DB=fx_trading
POSTGRES_USER=fx_user

# Redis設定
REDIS_PASSWORD=your_secure_redis_password_here

# JWT認証設定
JWT_SECRET=your_jwt_secret_key_minimum_32_characters_long
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 暗号化設定
ENCRYPTION_KEY=your_encryption_key_for_sensitive_data

# MT5設定
MT5_LOGIN=your_mt5_account_login
MT5_PASSWORD=your_mt5_account_password
MT5_SERVER=your_mt5_server_name

# 監視・可視化設定
GRAFANA_PASSWORD=your_grafana_admin_password

# アラート通知設定
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
EMAIL_TO=admin@your-domain.com

# ドメイン設定
FRONTEND_DOMAIN=fx-trading.local
API_DOMAIN=api.fx-trading.local
GRAFANA_DOMAIN=grafana.fx-trading.local

# セキュリティ設定
ALLOWED_HOSTS=fx-trading.local,api.fx-trading.local
CORS_ALLOWED_ORIGINS=https://fx-trading.local

# 環境設定
DEBUG=false
ENVIRONMENT=production
EOF
    
    # README作成
    cat > "$FX_HOME/README.md" << 'EOF'
# FX Trading System - 本番環境

## セットアップ完了事項

- [x] システム更新・最適化
- [x] Docker & Docker Compose インストール
- [x] アプリケーション用ユーザー作成
- [x] ディレクトリ構造作成
- [x] ファイアウォール設定
- [x] SSL証明書生成（自己署名）
- [x] 監視エージェントインストール

## 次の手順

1. `.env.prod.template` をコピーして `.env.prod` を作成
2. 必要な設定値を `.env.prod` に記入
3. アプリケーションコードをデプロイ
4. `./scripts/deploy.sh deploy main` でデプロイ実行

## 設定ファイル場所

- アプリケーション: `/app`
- ログ: `/app/logs`
- バックアップ: `/app/backups`
- 設定: `/app/config`

## サービス管理

```bash
# システム状況確認
sudo systemctl status fx-trading

# ログ確認
tail -f /app/logs/backend/app.log

# デプロイ
./scripts/deploy.sh deploy main

# ヘルスチェック
./scripts/deploy.sh health
```
EOF
    
    chown "$FX_USER:$FX_USER" "$FX_HOME/.env.prod.template" "$FX_HOME/README.md"
    
    log "初期設定ファイル作成完了"
}

# セットアップ完了確認
verify_setup() {
    log "セットアップ完了確認を実行中..."
    
    # サービス状態確認
    local services=("docker" "ufw" "fail2ban" "node_exporter")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log "✓ $service が正常に動作中"
        else
            log "✗ $service が停止しています"
        fi
    done
    
    # ポート確認
    local ports=("22" "80" "443" "9100")
    
    for port in "${ports[@]}"; do
        if netstat -tuln | grep -q ":$port "; then
            log "✓ ポート $port が開放されています"
        else
            log "✗ ポート $port が開放されていません"
        fi
    done
    
    # ディスク容量確認
    local available_gb=$(df "$FX_HOME" | awk 'NR==2 {print int($4/1024/1024)}')
    log "利用可能ディスク容量: ${available_gb}GB"
    
    # メモリ確認
    local total_mem=$(free -g | awk 'NR==2{print $2}')
    log "総メモリ容量: ${total_mem}GB"
    
    log "セットアップ完了確認終了"
}

# メイン処理
main() {
    log "FX Trading System 本番環境セットアップを開始します"
    
    # 確認
    echo "本番環境のセットアップを開始します。続行しますか? [y/N]: "
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log "セットアップがキャンセルされました"
        exit 0
    fi
    
    # セットアップ実行
    check_prerequisites
    update_system
    install_packages
    install_docker
    setup_user
    create_directories
    setup_firewall
    setup_fail2ban
    generate_ssl_certificates
    optimize_system
    install_monitoring_agents
    setup_auto_updates
    create_initial_configs
    verify_setup
    
    local setup_time=$(($(date +%s) - $(date -d "$(head -1 "$SETUP_LOG" | cut -d']' -f1 | tr -d '[')" +%s)))
    
    log "本番環境セットアップが正常に完了しました (所要時間: ${setup_time}秒)"
    log "次の手順については $FX_HOME/README.md を確認してください"
}

# エラーハンドリング
trap 'error_exit "セットアップ中にエラーが発生しました"' ERR

# ログディレクトリ作成
mkdir -p "$(dirname "$SETUP_LOG")"

# スクリプト実行
main "$@"

log "本番環境セットアップスクリプトが正常に終了しました"