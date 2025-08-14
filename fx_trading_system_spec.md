#### DQN（強化学習）
```python
{
    'state_size': 50,  # 状態空間の次元
    'action_size': 3,  # 行動空間（買い/売り/待機）
    'memory_size': 2000,
    'epsilon': 1.0,
    'epsilon_decay': 0.995,
    'epsilon_min': 0.01,
    'learning_rate': 0.001,
    'gamma': 0.95  # 割引率
}
```

## 5. リスク管理仕様

### 5.1 リスクリワード設定
```python
{
    'default_risk_reward': 2.0,  # デフォルト値
    'available_ratios': [1.0, 1.5, 2.0, 2.5, 3.0],  # 選択可能な比率
    'dynamic_adjustment': True,  # 市場状況に応じた動的調整
    'min_ratio': 1.0,
    'max_ratio': 5.0
}
```

### 5.2 ポジション管理
- **最大同時ポジション数**: 通貨ペアごとに1つ
- **最大総ポジション数**: 5
- **資金管理**: ケリー基準またはf値による最適化
- **1取引あたりのリスク**: 口座残高の1-2%

### 5.3 損切り・利確設定
```python
{
    'stop_loss_methods': [
        'fixed_pips',      # 固定pips
        'atr_based',       # ATRベース
        'support_resistance',  # サポート/レジスタンス
        'trailing_stop'    # トレーリングストップ
    ],
    'take_profit_methods': [
        'risk_reward_based',  # リスクリワード比率
        'resistance_level',   # レジスタンスレベル
        'partial_close'       # 分割決済
    ]
}
```

### 5.4 リスク指標監視
- **最大ドローダウン**: 20%で自動停止
- **連続損失回数**: 5回で一時停止
- **日次損失上限**: 5%
- **証拠金維持率**: 200%以上を維持

## 6. バックテスト機能

### 6.1 バックテスト設定
```python
{
    'period': {
        'start_date': '2020-01-01',
        'end_date': 'current',
        'test_periods': ['1M', '3M', '6M', '1Y', '3Y', '5Y']
    },
    'initial_balance': 1000000,  # 初期資金（円）
    'spread_simulation': True,
    'slippage': 0.5,  # pips
    'commission': 0.005  # 0.5%
}
```

### 6.2 評価指標
- **収益性指標**
  - 総利益/総損失
  - 平均利益/平均損失
  - プロフィットファクター
  - 期待値
  
- **リスク指標**
  - 最大ドローダウン
  - シャープレシオ
  - ソルティノレシオ
  - カルマーレシオ
  
- **取引統計**
  - 勝率
  - リスクリワード実績
  - 平均保有時間
  - 取引頻度

## 7. 最適化機能

### 7.1 パラメータ最適化
```python
{
    'optimization_method': 'bayesian',  # ベイズ最適化
    'parameters_to_optimize': {
        'risk_reward_ratio': [1.0, 5.0],
        'stop_loss_pips': [10, 100],
        'take_profit_pips': [20, 200],
        'ma_periods': [5, 200],
        'rsi_period': [7, 30],
        'position_size': [0.01, 0.1]
    },
    'optimization_metric': 'sharpe_ratio',  # 最適化対象
    'n_iterations': 100
}
```

### 7.2 ウォークフォワード分析
- インサンプル期間: 6ヶ月
- アウトオブサンプル期間: 2ヶ月
- ローリング最適化: 月次

## 8. WEBアプリケーション仕様

### 8.1 ダッシュボード
- **リアルタイム監視**
  - 現在のポジション
  - 損益状況
  - 証拠金維持率
  - アクティブな通貨ペア
  
- **パフォーマンス表示**
  - 損益曲線グラフ
  - 月次/週次/日次収益
  - 通貨ペア別成績
  - 時間帯別成績

### 8.2 バックテスト画面
- **設定パネル**
  - 通貨ペア選択（複数選択可）
  - 時間軸選択
  - 期間設定
  - パラメータ設定
  
- **結果表示**
  - 詳細な統計テーブル
  - チャート（エントリー/エグジットポイント表示）
  - ドローダウングラフ
  - 月別成績ヒートマップ

### 8.3 設定管理
- **戦略設定**
  - 機械学習モデル選択
  - 特徴量選択
  - リスクパラメータ設定
  
- **通知設定**
  - メール通知
  - LINE通知
  - Slack連携

### 8.4 ログビューア
- **取引ログ**
  - エントリー/エグジット履歴
  - 注文詳細
  - 損益記録
  
- **システムログ**
  - エラーログ
  - 警告ログ
  - デバッグログ

## 9. データベース設計

### 9.1 主要テーブル
```sql
-- 価格データ
CREATE TABLE price_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    timeframe VARCHAR(5),
    timestamp TIMESTAMPTZ,
    open DECIMAL(10,5),
    high DECIMAL(10,5),
    low DECIMAL(10,5),
    close DECIMAL(10,5),
    volume BIGINT,
    spread DECIMAL(10,5)
);

-- 取引履歴
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    order_id BIGINT,
    symbol VARCHAR(10),
    direction VARCHAR(4),
    entry_time TIMESTAMPTZ,
    entry_price DECIMAL(10,5),
    exit_time TIMESTAMPTZ,
    exit_price DECIMAL(10,5),
    volume DECIMAL(10,2),
    profit_loss DECIMAL(10,2),
    commission DECIMAL(10,2)
);

-- バックテスト結果
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    test_id UUID,
    created_at TIMESTAMPTZ,
    parameters JSONB,
    statistics JSONB,
    equity_curve JSONB
);

-- モデル管理
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    model_type VARCHAR(50),
    created_at TIMESTAMPTZ,
    parameters JSONB,
    performance_metrics JSONB,
    model_path VARCHAR(255),
    is_active BOOLEAN
);
```

## 10. API仕様

### 10.1 RESTful API エンドポイント
```
GET    /api/v1/market/symbols          # 利用可能な通貨ペア一覧
GET    /api/v1/market/prices/{symbol}  # 価格データ取得
GET    /api/v1/positions               # 現在のポジション
POST   /api/v1/orders                  # 注文発注
DELETE /api/v1/orders/{id}            # 注文キャンセル
GET    /api/v1/trades                  # 取引履歴
POST   /api/v1/backtest                # バックテスト実行
GET    /api/v1/backtest/{id}          # バックテスト結果取得
POST   /api/v1/optimize                # パラメータ最適化
GET    /api/v1/performance             # パフォーマンス統計
```

### 10.2 WebSocket
```
ws://localhost:8000/ws/market  # リアルタイム価格配信
ws://localhost:8000/ws/trades  # リアルタイム取引通知
ws://localhost:8000/ws/signals # 売買シグナル配信
```

## 11. セキュリティ要件

### 11.1 認証・認可
- JWT（JSON Web Token）による認証
- 2要素認証（2FA）対応
- APIキー管理
- IP制限

### 11.2 データ保護
- MT5認証情報の暗号化保存
- SSL/TLS通信
- データベース暗号化
- 定期的なバックアップ

## 12. 運用要件

### 12.1 システム要件
- **サーバー**: Ubuntu 20.04 LTS以上
- **CPU**: 4コア以上
- **メモリ**: 16GB以上
- **ストレージ**: SSD 500GB以上
- **ネットワーク**: 低遅延接続（VPS推奨）

### 12.2 監視項目
- システムリソース（CPU、メモリ、ディスク）
- API応答時間
- 取引執行遅延
- エラー率
- 接続状態

### 12.3 バックアップ
- データベース: 日次バックアップ
- モデルファイル: 更新時バックアップ
- 設定ファイル: 変更時バックアップ
- ログファイル: 週次アーカイブ

## 13. 開発ロードマップ

### Phase 1: 基礎構築（1-2ヶ月）
- [ ] MT5-Python連携環境構築
- [ ] 基本的なデータ取得機能
- [ ] データベース設計・実装
- [ ] 簡単なバックテスト機能

### Phase 2: 機械学習実装（2-3ヶ月）
- [ ] LightGBMモデル実装
- [ ] 特徴量エンジニアリング
- [ ] モデル学習・評価パイプライン
- [ ] リアルタイム予測機能

### Phase 3: リスク管理（1-2ヶ月）
- [ ] リスクリワード管理機能
- [ ] ポジションサイジング
- [ ] ドローダウン管理
- [ ] 緊急停止機能

### Phase 4: WEBアプリ開発（2-3ヶ月）
- [ ] ダッシュボード実装
- [ ] バックテスト画面
- [ ] 設定管理画面
- [ ] ログビューア

### Phase 5: 最適化・改善（継続）
- [ ] パラメータ最適化機能
- [ ] 深層学習モデル追加
- [ ] パフォーマンス改善
- [ ] UI/UX改善

## 14. テスト計画

### 14.1 単体テスト
- データ取得機能
- 売買ロジック
- リスク管理機能
- API エンドポイント

### 14.2 統合テスト
- MT5連携テスト
- エンドツーエンドテスト
- 負荷テスト
- セキュリティテスト

### 14.3 受入テスト
- デモ口座での実証実験
- パフォーマンス検証
- ユーザビリティテスト

## 15. 注意事項・推奨事項

### 15.1 リスク管理の重要性
- リスクリワードとは「損失（リスク）と利益（リワード）の比率」のことで、FX取引で利益を上げるためには、リスクリワードを意識することが重要です
- FXにおける理想的なリスクリワードの比率は「1（損失）：3（利益）」と言われており、勝率60％以上を確保することが重要です
- 初期は小ロットでの運用を推奨（0.01ロット程度から開始）

### 15.2 機械学習モデルの選定
- LightGBMは勾配ブースティング決定木を実装した機械学習ライブラリで、高速で精度が高く、大規模なデータにも対応でき、FX自動売買で良好なパフォーマンスを示しています
- 深層強化学習（DQN）もオプションとして検討可能ですが、LightGBMと比較して勝率は低くなる傾向があるため、エントリー率の高さを活かした運用が必要です

### 15.3 データの整合性
- バックテストと実運用で同じデータソースを使用することが重要
- MT5から取得した四本値データを基にテクニカル指標を計算し、機械学習モデルに入力する一貫したパイプラインの構築が必要です

### 15.4 継続的な改善
- 「収益率」より「リスクリワードレシオ」と「最大ドローダウン」を重視した堅実な運用を心がけることが成功の鍵です
- 市場環境の変化に応じて、定期的なモデルの再学習とパラメータの見直しが必要

---
*この仕様書は継続的に更新・改善されることを前提としています。*
*実装時は各フェーズごとに詳細設計を行い、段階的に機能を追加していくことを推奨します。*# FX自動売買システム仕様書

## 1. システム概要

### 1.1 目的
MT5プラットフォームとPython、機械学習技術を統合した高度なFX自動売買システムの構築

### 1.2 主要機能
- MT5を介したリアルタイムデータ取得
- 機械学習モデルによる売買判断
- バックテスト機能
- パラメータ最適化
- リスク管理
- WEBベースの管理インターフェース
- 詳細なログ記録

### 1.3 システムアーキテクチャ
```
[MT5ターミナル] <--API--> [Pythonバックエンド] <--> [機械学習エンジン]
                               |
                               v
                         [WEBフロントエンド]
                               |
                               v
                          [データベース]
```

## 2. 技術スタック

### 2.1 コア技術
- **取引プラットフォーム**: MetaTrader 5 (MT5)
- **プログラミング言語**: Python 3.9以上
- **MT5連携**: MetaTrader5 Python API (最新版 5.0.5200)
- **WEBフレームワーク**: FastAPI または Django
- **フロントエンド**: React.js + TypeScript
- **データベース**: PostgreSQL (時系列データ用にTimescaleDB拡張)
- **キャッシュ**: Redis
- **タスクキュー**: Celery

### 2.2 機械学習ライブラリ
- **LightGBM**: 主要な予測モデル
- **TensorFlow/Keras**: ディープラーニング（LSTM、DQN）
- **scikit-learn**: データ前処理、評価
- **pandas**: データ操作
- **TA-Lib**: テクニカル指標計算

## 3. データ仕様

### 3.1 取得データ
#### 価格データ
- OHLCV（始値、高値、安値、終値、出来高）
- ティックボリューム
- スプレッド
- リアルボリューム

#### 時間軸
- 1分足 (M1)
- 5分足 (M5)
- 15分足 (M15)
- 30分足 (M30)
- 1時間足 (H1)
- 4時間足 (H4)
- 日足 (D1)

### 3.2 通貨ペア
#### 主要円ペア（優先実装）
- USD/JPY（米ドル/円）
- EUR/JPY（ユーロ/円）
- GBP/JPY（英ポンド/円）
- AUD/JPY（豪ドル/円）
- NZD/JPY（NZドル/円）
- CAD/JPY（カナダドル/円）
- CHF/JPY（スイスフラン/円）

#### 追加実装候補
- ZAR/JPY（南アフリカランド/円）
- TRY/JPY（トルコリラ/円）
- MXN/JPY（メキシコペソ/円）

### 3.3 特徴量エンジニアリング
#### テクニカル指標
```python
{
    'MA': [5, 10, 20, 30, 50, 100, 200],  # 移動平均線
    'EMA': [12, 26],                       # 指数移動平均
    'BBANDS': {'period': 20, 'nbdev': 2},  # ボリンジャーバンド
    'RSI': [14, 30],                       # RSI
    'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
    'ATR': 14,                              # Average True Range
    'STOCH': {'k': 14, 'd': 3},           # ストキャスティクス
    'ADX': 14,                              # 平均方向性指数
    'CCI': 20,                              # 商品チャンネル指数
    'WILLIAMS_R': 14                       # ウィリアムズ%R
}
```

#### 派生特徴量
- 価格変化率（1期前、5期前、10期前）
- ボラティリティ指標
- サポート・レジスタンスレベル
- トレンド強度
- 出来高加重平均価格（VWAP）

## 4. 機械学習モデル仕様

###