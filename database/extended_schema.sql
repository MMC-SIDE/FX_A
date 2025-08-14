-- 追加テーブル定義
-- FX Trading System Extended Schema

-- MLモデル管理テーブル
CREATE TABLE IF NOT EXISTS ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- lightgbm, lstm, dqn
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    version VARCHAR(20) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    training_period_start DATE NOT NULL,
    training_period_end DATE NOT NULL,
    validation_score DECIMAL(8,4),
    test_score DECIMAL(8,4),
    parameters JSONB,
    feature_importance JSONB,
    feature_list JSONB,
    metrics JSONB,
    is_active BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_name, symbol, timeframe, version)
);

-- MLモデルインデックス
CREATE INDEX IF NOT EXISTS idx_ml_models_active ON ml_models (is_active, symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_ml_models_symbol_timeframe ON ml_models (symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_ml_models_created_at ON ml_models (created_at DESC);

-- 戦略実行履歴テーブル
CREATE TABLE IF NOT EXISTS strategy_executions (
    id SERIAL PRIMARY KEY,
    execution_id UUID NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    model_id INTEGER REFERENCES ml_models(id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'running', -- running, completed, failed, stopped
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    total_profit DECIMAL(10,2) DEFAULT 0,
    max_drawdown DECIMAL(5,2) DEFAULT 0,
    parameters JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 戦略実行履歴インデックス
CREATE INDEX IF NOT EXISTS idx_strategy_executions_strategy ON strategy_executions (strategy_name, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_executions_symbol ON strategy_executions (symbol, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_executions_status ON strategy_executions (status);

-- リスク管理ログテーブル
CREATE TABLE IF NOT EXISTS risk_management_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- position_limit, drawdown_limit, stop_trading, resume_trading
    symbol VARCHAR(10),
    trigger_value DECIMAL(10,4),
    threshold_value DECIMAL(10,4),
    action_taken VARCHAR(100),
    description TEXT,
    severity VARCHAR(10) DEFAULT 'INFO', -- INFO, WARNING, ERROR, CRITICAL
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- リスク管理ログインデックス
CREATE INDEX IF NOT EXISTS idx_risk_logs_event_type ON risk_management_logs (event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_logs_severity ON risk_management_logs (severity, created_at DESC);

-- 特徴量履歴テーブル
CREATE TABLE IF NOT EXISTS feature_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    features JSONB NOT NULL,
    target DECIMAL(10,5),
    is_training_data BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, time)
);

-- 特徴量データをハイパーテーブル化
SELECT create_hypertable('feature_data', 'time', if_not_exists => TRUE);

-- 特徴量履歴インデックス
CREATE INDEX IF NOT EXISTS idx_feature_data_symbol_timeframe ON feature_data (symbol, timeframe, time DESC);
CREATE INDEX IF NOT EXISTS idx_feature_data_training ON feature_data (is_training_data, symbol, timeframe);

-- 予測結果テーブル
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES ml_models(id),
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    prediction_time TIMESTAMPTZ NOT NULL,
    target_time TIMESTAMPTZ NOT NULL,
    predicted_direction VARCHAR(10), -- BUY, SELL, HOLD
    predicted_price DECIMAL(10,5),
    confidence_score DECIMAL(5,4),
    actual_price DECIMAL(10,5),
    accuracy DECIMAL(5,4),
    features_used JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 予測結果をハイパーテーブル化
SELECT create_hypertable('predictions', 'prediction_time', if_not_exists => TRUE);

-- 予測結果インデックス
CREATE INDEX IF NOT EXISTS idx_predictions_model_symbol ON predictions (model_id, symbol, prediction_time DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_accuracy ON predictions (accuracy, model_id);

-- アラート・通知テーブル
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL, -- profit_target, loss_limit, system_error, model_accuracy
    priority VARCHAR(10) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    symbol VARCHAR(10),
    trade_id BIGINT,
    strategy_name VARCHAR(100),
    triggered_value DECIMAL(10,4),
    threshold_value DECIMAL(10,4),
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- アラートインデックス
CREATE INDEX IF NOT EXISTS idx_alerts_type_priority ON alerts (alert_type, priority, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_unacknowledged ON alerts (is_acknowledged, priority, created_at DESC);

-- パフォーマンス統計テーブル
CREATE TABLE IF NOT EXISTS performance_stats (
    id SERIAL PRIMARY KEY,
    period_type VARCHAR(20) NOT NULL, -- daily, weekly, monthly, yearly
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    symbol VARCHAR(10),
    strategy_name VARCHAR(100),
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2) DEFAULT 0,
    total_profit DECIMAL(10,2) DEFAULT 0,
    total_loss DECIMAL(10,2) DEFAULT 0,
    net_profit DECIMAL(10,2) DEFAULT 0,
    profit_factor DECIMAL(8,4) DEFAULT 0,
    max_drawdown DECIMAL(5,2) DEFAULT 0,
    max_drawdown_amount DECIMAL(10,2) DEFAULT 0,
    avg_trade_duration INTERVAL,
    sharpe_ratio DECIMAL(8,4),
    sortino_ratio DECIMAL(8,4),
    calmar_ratio DECIMAL(8,4),
    recovery_factor DECIMAL(8,4),
    commission_paid DECIMAL(10,2) DEFAULT 0,
    swap_paid DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_type, period_start, symbol, strategy_name)
);

-- パフォーマンス統計インデックス
CREATE INDEX IF NOT EXISTS idx_performance_stats_period ON performance_stats (period_type, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_performance_stats_symbol ON performance_stats (symbol, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_performance_stats_strategy ON performance_stats (strategy_name, period_start DESC);

-- ユーザー認証テーブル
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user', -- admin, user, viewer
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMPTZ,
    preferences JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ユーザーインデックス
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active);

-- セッション管理テーブル
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- セッションインデックス
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions (expires_at);

-- 設定変更履歴テーブル
CREATE TABLE IF NOT EXISTS settings_history (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by INTEGER REFERENCES users(id),
    change_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 設定履歴インデックス
CREATE INDEX IF NOT EXISTS idx_settings_history_key ON settings_history (setting_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_settings_history_user ON settings_history (changed_by, created_at DESC);

-- システム設定の更新（既存テーブルに追加設定）
INSERT INTO system_settings (key, value, value_type, description) VALUES
('ml.model_retrain_days', '30', 'integer', 'モデル再学習間隔（日）'),
('ml.feature_update_hours', '1', 'integer', '特徴量更新間隔（時間）'),
('ml.prediction_confidence_threshold', '0.7', 'float', '予測信頼度閾値'),
('alerts.email_enabled', 'false', 'boolean', 'メール通知有効'),
('alerts.slack_enabled', 'false', 'boolean', 'Slack通知有効'),
('alerts.webhook_url', '', 'string', '通知Webhook URL'),
('performance.daily_report_enabled', 'true', 'boolean', '日次レポート有効'),
('performance.monthly_report_enabled', 'true', 'boolean', '月次レポート有効')
ON CONFLICT (key) DO NOTHING;

-- 拡張ビュー定義

-- モデル別パフォーマンスビュー
CREATE OR REPLACE VIEW v_model_performance AS
SELECT 
    m.id as model_id,
    m.model_name,
    m.symbol,
    m.timeframe,
    COUNT(p.id) as total_predictions,
    AVG(p.accuracy) as avg_accuracy,
    AVG(p.confidence_score) as avg_confidence,
    COUNT(CASE WHEN p.accuracy > 0.7 THEN 1 END) as high_accuracy_predictions,
    MAX(p.prediction_time) as last_prediction_time
FROM ml_models m
LEFT JOIN predictions p ON m.id = p.model_id
WHERE m.is_active = true
GROUP BY m.id, m.model_name, m.symbol, m.timeframe;

-- 戦略別パフォーマンスビュー
CREATE OR REPLACE VIEW v_strategy_performance AS
SELECT 
    strategy_name,
    symbol,
    COUNT(*) as total_executions,
    AVG(total_profit) as avg_profit,
    SUM(total_trades) as total_trades,
    AVG(CASE WHEN total_trades > 0 THEN winning_trades::float / total_trades ELSE 0 END) as avg_win_rate,
    MAX(total_profit) as best_profit,
    MIN(total_profit) as worst_profit,
    AVG(max_drawdown) as avg_drawdown
FROM strategy_executions
WHERE status = 'completed'
GROUP BY strategy_name, symbol;

-- アラート統計ビュー
CREATE OR REPLACE VIEW v_alert_summary AS
SELECT 
    alert_type,
    priority,
    COUNT(*) as total_alerts,
    COUNT(CASE WHEN is_acknowledged THEN 1 END) as acknowledged_count,
    COUNT(CASE WHEN NOT is_acknowledged THEN 1 END) as pending_count,
    AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at))/60) as avg_response_time_minutes
FROM alerts
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY alert_type, priority
ORDER BY priority DESC, total_alerts DESC;