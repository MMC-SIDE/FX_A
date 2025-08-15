"""
時間帯分析用のtradesテーブル作成とサンプルデータ挿入
"""
import psycopg2
from backend.core.database import DatabaseManager
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_trades_table():
    """tradesテーブル作成"""
    try:
        db_manager = DatabaseManager()
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # trades テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20) NOT NULL,
                        order_type VARCHAR(10) NOT NULL,
                        entry_time TIMESTAMP NOT NULL,
                        exit_time TIMESTAMP,
                        entry_price DECIMAL(10,5) NOT NULL,
                        exit_price DECIMAL(10,5),
                        volume DECIMAL(8,2) NOT NULL,
                        profit_loss DECIMAL(15,2),
                        magic_number INTEGER DEFAULT 0,
                        comment TEXT,
                        is_closed BOOLEAN DEFAULT false,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # インデックス作成
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_symbol_entry_time 
                    ON trades(symbol, entry_time)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_is_closed 
                    ON trades(is_closed)
                """)
                
                conn.commit()
                logger.info("Trades table created successfully")
                
    except Exception as e:
        logger.error(f"Error creating trades table: {e}")
        raise

def insert_sample_trades():
    """サンプル取引データ挿入"""
    try:
        db_manager = DatabaseManager()
        
        # サンプルデータ生成
        np.random.seed(42)
        random.seed(42)
        
        symbols = ['USDJPY', 'EURJPY', 'GBPJPY']
        order_types = ['BUY', 'SELL']
        
        # 過去1年のランダムな取引を生成
        start_date = datetime.now() - timedelta(days=365)
        sample_data = []
        
        for i in range(500):  # 500取引生成
            symbol = random.choice(symbols)
            order_type = random.choice(order_types)
            
            # ランダムな取引時間（市場時間を考慮）
            days_offset = random.randint(0, 365)
            hour = random.choices(
                range(24), 
                weights=[1, 1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 6, 5, 4, 3, 5, 7, 9, 8, 6, 4, 2]  # 市場時間の重み
            )[0]
            minute = random.randint(0, 59)
            
            entry_time = start_date + timedelta(days=days_offset, hours=hour, minutes=minute)
            
            # 基準価格（シンボル別）
            base_prices = {
                'USDJPY': 150.0,
                'EURJPY': 160.0,
                'GBPJPY': 180.0
            }
            
            base_price = base_prices[symbol]
            price_variation = np.random.normal(0, 2.0)  # ±2円程度の変動
            entry_price = base_price + price_variation
            
            # 取引時間（30分〜8時間）
            duration_hours = random.uniform(0.5, 8.0)
            exit_time = entry_time + timedelta(hours=duration_hours)
            
            # 勝率を時間帯によって変化させる
            if 9 <= hour <= 15:  # 東京時間
                win_probability = 0.55
            elif 16 <= hour <= 24:  # ロンドン時間
                win_probability = 0.60
            elif 21 <= hour <= 24 or 0 <= hour <= 6:  # NY時間
                win_probability = 0.58
            else:
                win_probability = 0.45
            
            # 利益/損失決定
            is_win = random.random() < win_probability
            
            if is_win:
                if order_type == 'BUY':
                    price_change = random.uniform(0.10, 0.50)  # 10-50pips
                    exit_price = entry_price + price_change
                else:
                    price_change = random.uniform(0.10, 0.50)
                    exit_price = entry_price - price_change
            else:
                if order_type == 'BUY':
                    price_change = random.uniform(-0.40, -0.10)  # -40 to -10pips
                    exit_price = entry_price + price_change
                else:
                    price_change = random.uniform(-0.40, -0.10)
                    exit_price = entry_price - price_change
            
            # ロット数
            volume = random.choice([0.1, 0.2, 0.5, 1.0])
            
            # 損益計算（簡略化）
            if order_type == 'BUY':
                profit_loss = (exit_price - entry_price) * volume * 1000  # 1000通貨単位
            else:
                profit_loss = (entry_price - exit_price) * volume * 1000
            
            # 手数料とスプレッド考慮
            commission = volume * 500  # 500円/lot
            profit_loss -= commission
            
            sample_data.append({
                'symbol': symbol,
                'order_type': order_type,
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_price': round(float(entry_price), 3),
                'exit_price': round(float(exit_price), 3),
                'volume': float(volume),
                'profit_loss': round(float(profit_loss), 2),
                'magic_number': 12345,
                'comment': f'Auto Trade #{i+1}',
                'is_closed': True
            })
        
        # データベースに挿入
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                for data in sample_data:
                    cursor.execute("""
                        INSERT INTO trades 
                        (symbol, order_type, entry_time, exit_time, entry_price, exit_price, 
                         volume, profit_loss, magic_number, comment, is_closed)
                        VALUES (%(symbol)s, %(order_type)s, %(entry_time)s, %(exit_time)s, 
                                %(entry_price)s, %(exit_price)s, %(volume)s, %(profit_loss)s, 
                                %(magic_number)s, %(comment)s, %(is_closed)s)
                    """, data)
                
                conn.commit()
                logger.info(f"Inserted {len(sample_data)} sample trades")
                
                # 統計情報表示
                cursor.execute("SELECT COUNT(*) FROM trades WHERE is_closed = true")
                total_trades = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM trades WHERE is_closed = true AND profit_loss > 0")
                winning_trades = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(profit_loss) FROM trades WHERE is_closed = true")
                avg_profit = cursor.fetchone()[0]
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                logger.info(f"Total trades: {total_trades}")
                logger.info(f"Winning trades: {winning_trades}")
                logger.info(f"Win rate: {win_rate:.1f}%")
                logger.info(f"Average P&L: ¥{avg_profit:.2f}")
                
    except Exception as e:
        logger.error(f"Error inserting sample trades: {e}")
        raise

if __name__ == "__main__":
    print("Creating trades table...")
    create_trades_table()
    
    print("Inserting sample trade data...")
    insert_sample_trades()
    
    print("Setup completed!")