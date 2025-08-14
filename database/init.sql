-- FX Trading System Database Schema
-- PostgreSQL + TimescaleDB

-- TimescaleDB拡張を有効化
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 価格データテーブル
CREATE TABLE IF NOT EXISTS price_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    open DECIMAL(10,5) NOT NULL,
    high DECIMAL(10,5) NOT NULL,
    low DECIMAL(10,5) NOT NULL,
    close DECIMAL(10,5) NOT NULL,
    tick_volume BIGINT DEFAULT 0,
    spread INT DEFAULT 0,
    real_volume BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, time)
);

-- TimescaleDBハイパーテーブル化
SELECT create_hypertable('price_data', 'time', if_not_exists => TRUE);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_price_data_symbol_timeframe 
ON price_data (symbol, timeframe);

CREATE INDEX IF NOT EXISTS idx_price_data_time 
ON price_data (time DESC);

CREATE INDEX IF NOT EXISTS idx_price_data_symbol_time 
ON price_data (symbol, time DESC);

-- 取引履歴テーブル
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    trade_id BIGINT UNIQUE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    order_type VARCHAR(10) NOT NULL, -- BUY, SELL
    order_id BIGINT,
    position_id BIGINT,
    entry_time TIMESTAMPTZ NOT NULL,
    entry_price DECIMAL(10,5) NOT NULL,
    exit_time TIMESTAMPTZ,
    exit_price DECIMAL(10,5),
    volume DECIMAL(10,2) NOT NULL,
    profit_loss DECIMAL(10,2) DEFAULT 0,
    swap DECIMAL(10,2) DEFAULT 0,
    commission DECIMAL(10,2) DEFAULT 0,
    comment VARCHAR(255),
    magic_number INTEGER DEFAULT 0,
    reason VARCHAR(50), -- EXPERT, MANUAL, MOBILE, etc.
    is_closed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 取引履歴インデックス
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades (entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_is_closed ON trades (is_closed);
CREATE INDEX IF NOT EXISTS idx_trades_magic_number ON trades (magic_number);

-- ポジション情報テーブル
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    position_id BIGINT UNIQUE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    type VARCHAR(10) NOT NULL, -- BUY, SELL
    volume DECIMAL(10,2) NOT NULL,
    price_open DECIMAL(10,5) NOT NULL,
    price_current DECIMAL(10,5),
    stop_loss DECIMAL(10,5),
    take_profit DECIMAL(10,5),
    profit DECIMAL(10,2) DEFAULT 0,
    swap DECIMAL(10,2) DEFAULT 0,
    commission DECIMAL(10,2) DEFAULT 0,
    magic_number INTEGER DEFAULT 0,
    comment VARCHAR(255),
    time_create TIMESTAMPTZ NOT NULL,
    time_update TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ポジションインデックス
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions (symbol);
CREATE INDEX IF NOT EXISTS idx_positions_is_active ON positions (is_active);
CREATE INDEX IF NOT EXISTS idx_positions_magic_number ON positions (magic_number);

-- バックテスト結果テーブル
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    test_id UUID NOT NULL,
    test_name VARCHAR(255) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2) DEFAULT 0,
    profit_factor DECIMAL(10,4) DEFAULT 0,
    max_drawdown DECIMAL(5,2) DEFAULT 0,
    total_profit DECIMAL(10,2) DEFAULT 0,
    avg_profit DECIMAL(10,2) DEFAULT 0,
    avg_loss DECIMAL(10,2) DEFAULT 0,
    largest_profit DECIMAL(10,2) DEFAULT 0,
    largest_loss DECIMAL(10,2) DEFAULT 0,
    parameters JSONB,
    metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- バックテストインデックス
CREATE INDEX IF NOT EXISTS idx_backtest_test_id ON backtest_results (test_id);
CREATE INDEX IF NOT EXISTS idx_backtest_symbol ON backtest_results (symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_created_at ON backtest_results (created_at DESC);

-- 経済指標テーブル
CREATE TABLE IF NOT EXISTS economic_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(50) UNIQUE,
    title VARCHAR(255) NOT NULL,
    country VARCHAR(10) NOT NULL,
    currency VARCHAR(5) NOT NULL,
    impact VARCHAR(10), -- HIGH, MEDIUM, LOW
    event_time TIMESTAMPTZ NOT NULL,
    forecast VARCHAR(50),
    previous VARCHAR(50),
    actual VARCHAR(50),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 経済指標インデックス
CREATE INDEX IF NOT EXISTS idx_economic_events_time ON economic_events (event_time);
CREATE INDEX IF NOT EXISTS idx_economic_events_currency ON economic_events (currency);
CREATE INDEX IF NOT EXISTS idx_economic_events_impact ON economic_events (impact);

-- システム設定テーブル
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    value_type VARCHAR(20) DEFAULT 'string', -- string, integer, float, boolean, json
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- システム設定のデフォルト値
INSERT INTO system_settings (key, value, value_type, description) VALUES
('trading.enabled', 'false', 'boolean', '自動売買の有効/無効'),
('trading.max_risk_per_trade', '0.02', 'float', '1取引あたりの最大リスク'),
('trading.max_drawdown', '0.20', 'float', '最大ドローダウン'),
('trading.use_nanpin', 'true', 'boolean', 'ナンピン機能の使用'),
('trading.nanpin_max_count', '3', 'integer', 'ナンピン最大回数'),
('trading.nanpin_interval_pips', '10', 'integer', 'ナンピン間隔（pips）'),
('system.log_level', 'INFO', 'string', 'ログレベル'),
('system.data_retention_days', '90', 'integer', 'データ保持期間（日）')
ON CONFLICT (key) DO NOTHING;

-- ログテーブル
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    module VARCHAR(100),
    function_name VARCHAR(100),
    line_number INTEGER,
    extra_data JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ログインデックス
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs (level);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_module ON system_logs (module);

-- パーティション設定（ログテーブルの月次パーティション）
-- SELECT create_hypertable('system_logs', 'created_at', if_not_exists => TRUE);

-- データ保持ポリシー（3ヶ月後に古いデータを削除）
-- SELECT add_retention_policy('price_data', INTERVAL '3 months');
-- SELECT add_retention_policy('system_logs', INTERVAL '3 months');

-- 統計ビュー
CREATE OR REPLACE VIEW v_trading_summary AS
SELECT 
    symbol,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
    ROUND(
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END)::decimal / COUNT(*)::decimal * 100, 
        2
    ) as win_rate,
    ROUND(SUM(profit_loss), 2) as total_profit,
    ROUND(AVG(profit_loss), 2) as avg_profit,
    ROUND(MAX(profit_loss), 2) as max_profit,
    ROUND(MIN(profit_loss), 2) as max_loss
FROM trades 
WHERE is_closed = true
GROUP BY symbol;

-- 日次損益ビュー
CREATE OR REPLACE VIEW v_daily_pnl AS
SELECT 
    DATE(entry_time) as trade_date,
    symbol,
    COUNT(*) as trades_count,
    ROUND(SUM(profit_loss), 2) as daily_pnl,
    ROUND(SUM(SUM(profit_loss)) OVER (
        PARTITION BY symbol 
        ORDER BY DATE(entry_time)
    ), 2) as cumulative_pnl
FROM trades 
WHERE is_closed = true
GROUP BY DATE(entry_time), symbol
ORDER BY trade_date DESC;

-- 時間帯別パフォーマンスビュー
CREATE OR REPLACE VIEW v_hourly_performance AS
SELECT 
    EXTRACT(HOUR FROM entry_time) as hour,
    symbol,
    COUNT(*) as trades_count,
    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
    ROUND(
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END)::decimal / COUNT(*)::decimal * 100, 
        2
    ) as win_rate,
    ROUND(SUM(profit_loss), 2) as total_profit
FROM trades 
WHERE is_closed = true
GROUP BY EXTRACT(HOUR FROM entry_time), symbol
ORDER BY hour, symbol;