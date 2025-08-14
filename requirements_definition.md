# FX自動売買システム要件定義書

## 1. プロジェクト概要

### 1.1 システム名
FX自動売買システム（FX_A）

### 1.2 目的
MetaTrader5（MT5）とPython、LightGBM機械学習モデルを統合し、XMTradingで自動売買を行うシステムの構築

### 1.3 初期運用条件
- **取引プラットフォーム**: MetaTrader5（XMTrading）
- **初期資金**: 10万円
- **口座タイプ**: 本番口座
- **運用形態**: 特定時間帯での自動売買
- **運用環境**: ローカル環境（将来的にクラウド移行予定）

## 2. 機能要件

### 2.1 第1段階実装（必須機能）

#### 2.1.1 基本取引機能
- **自動売買エンジン**
  - MT5 APIを通じた自動注文執行
  - リアルタイム価格データ取得
  - ポジション管理（エントリー/エグジット）
  - 同時監視通貨ペア数: 1ペア

#### 2.1.2 機械学習エンジン（LightGBM）
- **特徴量**
  - テクニカル指標（RSI, MACD, ボリンジャーバンド等）
  - 価格パターン認識
  - 市場ボラティリティ指標
  - 時間的特徴（時間帯、曜日）
- **予測機能**
  - エントリーシグナル生成
  - エグジットタイミング予測

#### 2.1.3 バックテスト機能
- **検証期間**: 過去1年分のデータ
- **全通貨ペア・全時間軸検証**
  - 対象通貨ペア: USD/JPY, EUR/JPY, GBP/JPY, AUD/JPY, NZD/JPY, CAD/JPY, CHF/JPY
  - 時間軸: M1, M5, M15, M30, H1, H4, D1
- **最適パラメータ自動選択**

#### 2.1.4 時間帯分析機能
- **市場別分析**
  - 東京時間（9:00-15:00）
  - ロンドン時間（16:00-24:00）
  - ニューヨーク時間（21:00-6:00）
- **曜日別パフォーマンス分析**
- **勝率の高い時間帯の自動検出**

#### 2.1.5 リスク管理機能
- **設定可能パラメータ**
  ```json
  {
    "max_risk_per_trade": {
      "default": 20,
      "min": 0.5,
      "max": 100,
      "unit": "percent"
    },
    "max_drawdown": {
      "default": 20,
      "min": 5,
      "max": 50,
      "unit": "percent"
    },
    "use_nanpin": {
      "default": true,
      "max_count": 3,
      "interval_pips": 10,
      "lot_multiplier": 1.0
    }
  }
  ```

#### 2.1.6 Web管理画面
- **ダッシュボード**
  - リアルタイム損益表示
  - 現在のポジション状況
  - 本日の取引履歴
- **設定画面**
  - リスクパラメータ設定
  - 取引時間帯設定
  - 通貨ペア・時間軸選択
- **バックテスト実行画面**
  - パラメータ設定
  - 結果表示（グラフ・統計）

#### 2.1.7 リアルタイム監視機能
- **アラート機能**
  - 大きな損失発生時
  - システムエラー発生時
  - ドローダウン閾値到達時
- **ログ表示**
  - 取引ログ
  - システムログ
  - エラーログ

#### 2.1.8 経済指標カレンダー連携
- **重要指標の自動取得**
- **指標発表前後の取引制限**
- **ボラティリティ予測への活用**

### 2.2 設定ファイル管理
- **MT5認証情報** (config/mt5_config.json)
  ```json
  {
    "login": "アカウント番号",
    "password": "暗号化されたパスワード",
    "server": "XMTrading-MT5",
    "timeout": 60000,
    "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
  }
  ```

## 3. 非機能要件

### 3.1 パフォーマンス要件
- **注文執行時間**: 1分以内
- **バックテスト処理**: 1通貨ペア・1年分を10分以内
- **Web画面レスポンス**: 3秒以内

### 3.2 信頼性要件
- **稼働率**: 99%以上（メンテナンス時間除く）
- **自動復旧機能**: 接続断時の自動再接続
- **データ整合性**: トランザクション管理

### 3.3 セキュリティ要件
- **認証情報の暗号化保存**
- **JWT認証によるWeb画面アクセス制御**
- **SSL/TLS通信**
- **ログのマスキング処理**

### 3.4 運用・保守要件
- **ログ保存期間**: 3ヶ月
- **バックアップ**: 起動時に自動バックアップ
- **監視項目**
  - システムリソース（CPU、メモリ）
  - MT5接続状態
  - エラー発生率

## 4. システム構成

### 4.1 技術スタック
```yaml
Backend:
  - Language: Python 3.9+
  - Framework: FastAPI
  - ML Library: LightGBM
  - MT5 Integration: MetaTrader5 Python Package
  - Database: PostgreSQL + TimescaleDB
  - Cache: Redis
  - Task Queue: Celery

Frontend:
  - Framework: React.js
  - Language: TypeScript
  - UI Library: Material-UI or Ant Design
  - Charts: Chart.js or Recharts

Infrastructure:
  - OS: Windows 10/11
  - Development: Local
  - Production: Cloud (将来)
```

### 4.2 ディレクトリ構成
```
FX_A/
├── backend/
│   ├── api/                 # FastAPI エンドポイント
│   ├── core/                # コア機能
│   │   ├── mt5_client.py   # MT5接続
│   │   ├── trading_engine.py
│   │   └── risk_manager.py
│   ├── ml/                  # 機械学習
│   │   ├── models/
│   │   ├── features.py
│   │   └── predictor.py
│   ├── backtest/            # バックテスト
│   ├── analysis/            # 分析機能
│   └── config/              # 設定
├── frontend/                # React アプリ
├── database/               # DB スキーマ
├── logs/                   # ログファイル
├── data/                   # データ保存
├── config/                 # 設定ファイル
│   └── mt5_config.json
├── tests/                  # テスト
└── docker/                 # Docker設定
```

## 5. データベース設計

### 5.1 主要テーブル

#### trades（取引履歴）
```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    order_type VARCHAR(10) NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    entry_price DECIMAL(10,5) NOT NULL,
    exit_time TIMESTAMP,
    exit_price DECIMAL(10,5),
    volume DECIMAL(10,2) NOT NULL,
    profit_loss DECIMAL(10,2),
    commission DECIMAL(10,2),
    swap DECIMAL(10,2),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### price_data（価格データ）
```sql
CREATE TABLE price_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    time TIMESTAMP NOT NULL,
    open DECIMAL(10,5) NOT NULL,
    high DECIMAL(10,5) NOT NULL,
    low DECIMAL(10,5) NOT NULL,
    close DECIMAL(10,5) NOT NULL,
    tick_volume BIGINT,
    spread INT,
    real_volume BIGINT,
    UNIQUE(symbol, timeframe, time)
);
```

#### backtest_results（バックテスト結果）
```sql
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    test_id UUID NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    initial_balance DECIMAL(10,2) NOT NULL,
    final_balance DECIMAL(10,2) NOT NULL,
    total_trades INT NOT NULL,
    winning_trades INT NOT NULL,
    losing_trades INT NOT NULL,
    profit_factor DECIMAL(5,2),
    max_drawdown DECIMAL(5,2),
    sharpe_ratio DECIMAL(5,2),
    parameters JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 6. API仕様

### 6.1 主要エンドポイント

```yaml
Trading:
  POST /api/v1/trading/start: 自動売買開始
  POST /api/v1/trading/stop: 自動売買停止
  GET /api/v1/trading/status: 稼働状態取得
  GET /api/v1/positions: 現在のポジション取得
  GET /api/v1/trades: 取引履歴取得

Backtest:
  POST /api/v1/backtest/run: バックテスト実行
  GET /api/v1/backtest/results/{id}: 結果取得
  GET /api/v1/backtest/optimal-params: 最適パラメータ取得

Analysis:
  GET /api/v1/analysis/timeframe: 時間帯別分析
  GET /api/v1/analysis/market-sessions: 市場別分析
  GET /api/v1/analysis/weekday: 曜日別分析

Settings:
  GET /api/v1/settings: 設定取得
  PUT /api/v1/settings: 設定更新
  POST /api/v1/settings/validate: 設定検証

Market:
  GET /api/v1/market/symbols: 利用可能通貨ペア
  GET /api/v1/market/prices: リアルタイム価格
  GET /api/v1/market/calendar: 経済指標カレンダー
```

## 7. 開発スケジュール

### Phase 1: 基盤構築（2週間）
- [ ] 開発環境セットアップ
- [ ] MT5接続テスト
- [ ] データベース構築
- [ ] 基本的なプロジェクト構造作成

### Phase 2: コア機能実装（3週間）
- [ ] MT5データ取得機能
- [ ] LightGBMモデル実装
- [ ] 基本的な売買ロジック
- [ ] リスク管理機能

### Phase 3: バックテスト機能（2週間）
- [ ] バックテストエンジン
- [ ] パラメータ最適化
- [ ] 結果分析機能

### Phase 4: 分析機能（1週間）
- [ ] 時間帯分析
- [ ] 市場セッション分析
- [ ] 経済指標連携

### Phase 5: Web UI実装（2週間）
- [ ] ダッシュボード
- [ ] 設定画面
- [ ] バックテスト画面
- [ ] ログビューア

### Phase 6: テスト・調整（2週間）
- [ ] 統合テスト
- [ ] パフォーマンステスト
- [ ] デモ環境での検証
- [ ] ドキュメント作成

## 8. リスクと対策

| リスク | 影響度 | 対策 |
|-------|--------|------|
| MT5接続の不安定性 | 高 | 自動再接続機能、接続状態監視 |
| 過度なドローダウン | 高 | 自動停止機能、アラート通知 |
| 過学習による性能低下 | 中 | 定期的な再学習、検証データ分離 |
| 経済指標による急変動 | 高 | 指標前後の取引制限機能 |

## 9. 成功基準

- **技術的成功基準**
  - 自動売買の安定稼働（99%以上の稼働率）
  - バックテストと実運用の乖離率10%以内
  - 注文執行成功率99%以上

- **ビジネス成功基準**
  - 月間プロフィットファクター1.5以上
  - 最大ドローダウン20%以内
  - 勝率40%以上（リスクリワード比を考慮）

## 10. 注意事項

- 初期はデモ口座で十分なテストを実施すること
- リスク設定は段階的に調整すること（初期は保守的に）
- システムの動作ログを詳細に記録し、問題発生時の原因究明を可能にすること
- 定期的なモデルの再学習と検証を行うこと

---
*作成日: 2025年8月13日*
*バージョン: 1.0*