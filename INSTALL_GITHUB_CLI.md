# GitHub CLI インストールガイド

GitHub CLI (gh) は GitHub の公式コマンドラインツールです。
リポジトリの作成、Issue の管理、Pull Request の作成などが可能です。

## Windows

### 方法1: winget (推奨)
```powershell
winget install --id GitHub.cli
```

### 方法2: Chocolatey
```powershell
choco install gh
```

### 方法3: Scoop
```powershell
scoop install gh
```

### 方法4: 直接ダウンロード
1. https://cli.github.com/ にアクセス
2. Windows 用インストーラーをダウンロード
3. インストーラーを実行

## macOS

### Homebrew
```bash
brew install gh
```

### MacPorts
```bash
sudo port install gh
```

## Linux

### Debian/Ubuntu
```bash
# 鍵の追加
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg

# リポジトリ追加
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null

# インストール
sudo apt update
sudo apt install gh
```

### Fedora/CentOS/RHEL
```bash
sudo dnf install 'dnf-command(config-manager)'
sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
sudo dnf install gh
```

### Arch Linux
```bash
sudo pacman -S github-cli
```

## インストール確認

```bash
gh --version
```

## 初回設定（認証）

```bash
# 対話形式で認証
gh auth login

# 以下の質問に答える:
# 1. GitHub.com を選択
# 2. HTTPS を選択
# 3. Y (認証する)
# 4. ブラウザで認証を選択
# 5. ブラウザが開くので GitHub にログイン
# 6. 認証コードを確認して許可
```

## 認証状態の確認

```bash
gh auth status
```

## よく使うコマンド

```bash
# リポジトリ作成
gh repo create my-repo --private

# リポジトリクローン
gh repo clone owner/repo

# Issue 作成
gh issue create

# Pull Request 作成
gh pr create

# ワークフロー確認
gh workflow list

# リポジトリをブラウザで開く
gh repo view --web
```

## トラブルシューティング

### 認証エラーの場合
```bash
# 認証をリセット
gh auth logout
gh auth login
```

### プロキシ環境の場合
```bash
# プロキシ設定
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
gh auth login
```

## 参考リンク

- [GitHub CLI 公式サイト](https://cli.github.com/)
- [GitHub CLI マニュアル](https://cli.github.com/manual/)
- [GitHub CLI リポジトリ](https://github.com/cli/cli)