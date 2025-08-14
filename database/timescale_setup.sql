-- TimescaleDB 設定スクリプト
-- 価格データテーブルをハイパーテーブルに変換

-- TimescaleDBがロードされているか確認
SELECT * FROM pg_extension WHERE extname = 'timescaledb';

-- price_dataテーブルをハイパーテーブルに変換
SELECT create_hypertable('price_data', 'time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- 圧縮ポリシーの設定（7日以上古いデータを圧縮）
ALTER TABLE price_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,timeframe'
);

SELECT add_compression_policy('price_data', INTERVAL '7 days');

-- データ保持ポリシーの設定（1年以上古いデータを削除）
SELECT add_retention_policy('price_data', INTERVAL '1 year');

-- 統計情報の自動更新設定
SELECT add_job('SELECT analyze_table(''price_data'');', '1 hour');

-- 連続集計ビューの作成（1時間、日次、週次の OHLC データ）
CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_1h
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) as time_bucket,
    symbol,
    timeframe,
    first(open, time) as open,
    max(high) as high,
    min(low) as low,
    last(close, time) as close,
    sum(tick_volume) as tick_volume
FROM price_data
WHERE timeframe = 'M1'
GROUP BY time_bucket, symbol, timeframe;

CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_1d
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) as time_bucket,
    symbol,
    first(open, time) as open,
    max(high) as high,
    min(low) as low,
    last(close, time) as close,
    sum(tick_volume) as tick_volume
FROM price_data
WHERE timeframe IN ('M1', 'M5', 'M15', 'M30', 'H1')
GROUP BY time_bucket, symbol;

-- 連続集計ビューのリフレッシュポリシー設定
SELECT add_continuous_aggregate_policy('price_data_1h',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('price_data_1d',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- パフォーマンス最適化のための追加インデックス
CREATE INDEX IF NOT EXISTS idx_price_data_time_symbol 
ON price_data (time DESC, symbol);

CREATE INDEX IF NOT EXISTS idx_price_data_symbol_timeframe_time 
ON price_data (symbol, timeframe, time DESC);

-- システムログテーブルもハイパーテーブルに変換（作成されている場合）
SELECT create_hypertable('system_logs', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ログテーブルの圧縮・保持ポリシー
SELECT add_compression_policy('system_logs', INTERVAL '3 days');
SELECT add_retention_policy('system_logs', INTERVAL '30 days');

COMMIT;