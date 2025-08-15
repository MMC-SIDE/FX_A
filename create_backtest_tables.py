"""
バックテスト用データベーステーブル作成
"""
import psycopg2
from backend.core.database import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_backtest_tables():
    """バックテスト用テーブル作成"""
    try:
        db_manager = DatabaseManager()
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # backtest_results テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_results (
                        id SERIAL PRIMARY KEY,
                        test_id VARCHAR(255) UNIQUE NOT NULL,
                        symbol VARCHAR(20) NOT NULL,
                        timeframe VARCHAR(10) NOT NULL,
                        period_start TIMESTAMP NOT NULL,
                        period_end TIMESTAMP NOT NULL,
                        initial_balance DECIMAL(15,2) NOT NULL,
                        final_balance DECIMAL(15,2) NOT NULL,
                        total_trades INTEGER NOT NULL,
                        winning_trades INTEGER NOT NULL,
                        win_rate DECIMAL(5,2) NOT NULL,
                        profit_factor DECIMAL(8,4) NOT NULL,
                        max_drawdown DECIMAL(8,4) NOT NULL,
                        sharpe_ratio DECIMAL(8,4) NOT NULL,
                        parameters TEXT,
                        statistics TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # backtest_equity_curves テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_equity_curves (
                        id SERIAL PRIMARY KEY,
                        test_id VARCHAR(255) NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        equity DECIMAL(15,2) NOT NULL,
                        balance DECIMAL(15,2) NOT NULL,
                        unrealized_pnl DECIMAL(15,2) DEFAULT 0,
                        FOREIGN KEY (test_id) REFERENCES backtest_results(test_id) ON DELETE CASCADE
                    )
                """)
                
                # backtest_trades テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_trades (
                        id SERIAL PRIMARY KEY,
                        test_id VARCHAR(255) NOT NULL,
                        entry_time TIMESTAMP NOT NULL,
                        exit_time TIMESTAMP NOT NULL,
                        type VARCHAR(10) NOT NULL,
                        entry_price DECIMAL(10,5) NOT NULL,
                        exit_price DECIMAL(10,5) NOT NULL,
                        lot_size DECIMAL(8,2) NOT NULL,
                        profit_loss DECIMAL(15,2) NOT NULL,
                        duration_hours DECIMAL(8,2) NOT NULL,
                        exit_reason VARCHAR(50) NOT NULL,
                        FOREIGN KEY (test_id) REFERENCES backtest_results(test_id) ON DELETE CASCADE
                    )
                """)
                
                # price_data テーブル（バックテスト用データ）
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS price_data (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20) NOT NULL,
                        timeframe VARCHAR(10) NOT NULL,
                        time TIMESTAMP NOT NULL,
                        open DECIMAL(10,5) NOT NULL,
                        high DECIMAL(10,5) NOT NULL,
                        low DECIMAL(10,5) NOT NULL,
                        close DECIMAL(10,5) NOT NULL,
                        tick_volume BIGINT DEFAULT 0,
                        UNIQUE(symbol, timeframe, time)
                    )
                """)
                
                # インデックス作成
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_backtest_results_symbol_timeframe 
                    ON backtest_results(symbol, timeframe)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_price_data_symbol_timeframe_time 
                    ON price_data(symbol, timeframe, time)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_backtest_equity_curves_test_id_timestamp 
                    ON backtest_equity_curves(test_id, timestamp)
                """)
                
                conn.commit()
                logger.info("Backtest tables created successfully")
                
    except Exception as e:
        logger.error(f"Error creating backtest tables: {e}")
        raise

def insert_sample_price_data():
    """サンプル価格データ挿入"""
    try:
        db_manager = DatabaseManager()
        
        # サンプルデータ生成
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # USDJPYの1時間足データを30日分生成
        start_date = datetime.now() - timedelta(days=30)
        dates = pd.date_range(start=start_date, periods=720, freq='H')  # 30日 * 24時間
        
        # 価格データ生成（簡易版）
        np.random.seed(42)
        base_price = 150.0
        price_changes = np.random.normal(0, 0.001, len(dates))  # 0.1%程度の変動
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # OHLC生成
        sample_data = []
        for i, (date, close_price) in enumerate(zip(dates, prices)):
            # 簡易的なOHLC生成
            volatility = 0.001  # 1時間での変動幅
            high = close_price * (1 + np.random.uniform(0, volatility))
            low = close_price * (1 - np.random.uniform(0, volatility))
            
            if i == 0:
                open_price = close_price
            else:
                open_price = prices[i-1]
            
            sample_data.append({
                'symbol': 'USDJPY',
                'timeframe': 'H1',
                'time': date,
                'open': float(round(open_price, 3)),
                'high': float(round(high, 3)),
                'low': float(round(low, 3)),
                'close': float(round(close_price, 3)),
                'tick_volume': int(np.random.randint(100, 1000))
            })
        
        # データベースに挿入
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                for data in sample_data:
                    cursor.execute("""
                        INSERT INTO price_data 
                        (symbol, timeframe, time, open, high, low, close, tick_volume)
                        VALUES (%(symbol)s, %(timeframe)s, %(time)s, %(open)s, %(high)s, %(low)s, %(close)s, %(tick_volume)s)
                        ON CONFLICT (symbol, timeframe, time) DO NOTHING
                    """, data)
                
                conn.commit()
                logger.info(f"Inserted {len(sample_data)} price data records")
                
    except Exception as e:
        logger.error(f"Error inserting sample price data: {e}")
        raise

if __name__ == "__main__":
    print("Creating backtest tables...")
    create_backtest_tables()
    
    print("Inserting sample price data...")
    insert_sample_price_data()
    
    print("Setup completed!")