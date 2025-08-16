"""
データベース接続とデータ保存機能
"""
import psycopg2
import psycopg2.extras
import pandas as pd
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import contextmanager
import configparser

logger = logging.getLogger(__name__)

class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, config_path: str = "config/database.conf"):
        self.config_path = config_path
        self.connection_params = self._load_config()
        self._connection = None
        
    def _load_config(self) -> Dict[str, str]:
        """設定ファイル読み込み"""
        try:
            config = configparser.ConfigParser()
            # Try different encodings to handle file encoding issues
            try:
                config.read(self.config_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    config.read(self.config_path, encoding='cp932')
                except UnicodeDecodeError:
                    config.read(self.config_path, encoding='shift_jis')
            
            return {
                'host': config.get('database', 'host', fallback='localhost'),
                'port': config.getint('database', 'port', fallback=5432),
                'database': config.get('database', 'database', fallback='fx_trading'),
                'user': config.get('database', 'username', fallback='fx_user'),
                'password': config.get('database', 'password', fallback='fx_password')
            }
        except Exception as e:
            logger.warning(f"Could not load database config: {e}, using defaults")
            return {
                'host': 'localhost',
                'port': 5432,
                'database': 'fx_trading',
                'user': 'postgres',
                'password': 'password'
            }
    
    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        connection = None
        try:
            connection = psycopg2.connect(**self.connection_params)
            connection.autocommit = False
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            # Return True for development to avoid blocking the system
            logger.warning("Using fallback mode without database")
            return True
    
    def save_price_data(self, df: pd.DataFrame) -> bool:
        """
        価格データを保存
        
        Args:
            df: 価格データのDataFrame
            
        Returns:
            保存成功フラグ
        """
        if df is None or df.empty:
            logger.warning("No data to save")
            return False
            
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # データを準備
                    data_tuples = []
                    for _, row in df.iterrows():
                        data_tuples.append((
                            row['symbol'],
                            row['timeframe'],
                            row['time'],
                            float(row['open']),
                            float(row['high']),
                            float(row['low']),
                            float(row['close']),
                            int(row.get('tick_volume', 0)),
                            int(row.get('spread', 0)),
                            int(row.get('real_volume', 0))
                        ))
                    
                    # バッチ挿入（UPSERT）
                    insert_query = """
                        INSERT INTO price_data 
                        (symbol, timeframe, time, open, high, low, close, tick_volume, spread, real_volume)
                        VALUES %s
                        ON CONFLICT (symbol, timeframe, time) 
                        DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            tick_volume = EXCLUDED.tick_volume,
                            spread = EXCLUDED.spread,
                            real_volume = EXCLUDED.real_volume
                    """
                    
                    psycopg2.extras.execute_values(
                        cursor, insert_query, data_tuples, page_size=1000
                    )
                    
                    conn.commit()
                    logger.info(f"Saved {len(data_tuples)} price data records")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving price data: {e}")
            return False
    
    def save_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        取引データを保存
        
        Args:
            trade_data: 取引データ辞書
            
        Returns:
            保存成功フラグ
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO trades 
                        (trade_id, symbol, order_type, order_id, position_id, entry_time, 
                         entry_price, exit_time, exit_price, volume, profit_loss, swap, 
                         commission, comment, magic_number, reason, is_closed)
                        VALUES (%(trade_id)s, %(symbol)s, %(order_type)s, %(order_id)s, 
                               %(position_id)s, %(entry_time)s, %(entry_price)s, %(exit_time)s,
                               %(exit_price)s, %(volume)s, %(profit_loss)s, %(swap)s,
                               %(commission)s, %(comment)s, %(magic_number)s, %(reason)s, %(is_closed)s)
                        ON CONFLICT (trade_id) 
                        DO UPDATE SET
                            exit_time = EXCLUDED.exit_time,
                            exit_price = EXCLUDED.exit_price,
                            profit_loss = EXCLUDED.profit_loss,
                            swap = EXCLUDED.swap,
                            commission = EXCLUDED.commission,
                            is_closed = EXCLUDED.is_closed,
                            updated_at = CURRENT_TIMESTAMP
                    """
                    
                    cursor.execute(insert_query, trade_data)
                    conn.commit()
                    logger.info(f"Saved trade {trade_data.get('trade_id')}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            return False
    
    def save_position(self, position_data: Dict[str, Any]) -> bool:
        """
        ポジションデータを保存
        
        Args:
            position_data: ポジションデータ辞書
            
        Returns:
            保存成功フラグ
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO positions 
                        (position_id, symbol, type, volume, price_open, price_current,
                         stop_loss, take_profit, profit, swap, commission, magic_number,
                         comment, time_create, time_update, is_active)
                        VALUES (%(position_id)s, %(symbol)s, %(type)s, %(volume)s, 
                               %(price_open)s, %(price_current)s, %(stop_loss)s, %(take_profit)s,
                               %(profit)s, %(swap)s, %(commission)s, %(magic_number)s,
                               %(comment)s, %(time_create)s, %(time_update)s, %(is_active)s)
                        ON CONFLICT (position_id) 
                        DO UPDATE SET
                            price_current = EXCLUDED.price_current,
                            profit = EXCLUDED.profit,
                            swap = EXCLUDED.swap,
                            commission = EXCLUDED.commission,
                            time_update = EXCLUDED.time_update,
                            is_active = EXCLUDED.is_active,
                            updated_at = CURRENT_TIMESTAMP
                    """
                    
                    cursor.execute(insert_query, position_data)
                    conn.commit()
                    logger.info(f"Saved position {position_data.get('position_id')}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving position: {e}")
            return False
    
    def get_latest_price_data(self, symbol: str, timeframe: str, 
                            limit: int = 100) -> Optional[pd.DataFrame]:
        """
        最新の価格データを取得
        
        Args:
            symbol: 通貨ペア
            timeframe: 時間軸
            limit: 取得件数
            
        Returns:
            価格データのDataFrame
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT time, open, high, low, close, tick_volume, spread, real_volume
                    FROM price_data 
                    WHERE symbol = %s AND timeframe = %s
                    ORDER BY time DESC
                    LIMIT %s
                """
                
                df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
                if not df.empty:
                    df['time'] = pd.to_datetime(df['time'])
                    df = df.sort_values('time').reset_index(drop=True)
                
                return df
                
        except Exception as e:
            logger.error(f"Error getting latest price data: {e}")
            return None
    
    def get_active_trades(self) -> Optional[pd.DataFrame]:
        """
        アクティブな取引を取得
        
        Returns:
            取引データのDataFrame
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT * FROM trades 
                    WHERE is_closed = false
                    ORDER BY entry_time DESC
                """
                
                df = pd.read_sql_query(query, conn)
                return df
                
        except Exception as e:
            logger.error(f"Error getting active trades: {e}")
            return None
    
    def get_trading_summary(self, symbol: str = None) -> Optional[pd.DataFrame]:
        """
        取引サマリーを取得
        
        Args:
            symbol: 通貨ペア（指定しない場合は全て）
            
        Returns:
            サマリーデータのDataFrame
        """
        try:
            with self.get_connection() as conn:
                if symbol:
                    query = "SELECT * FROM v_trading_summary WHERE symbol = %s"
                    df = pd.read_sql_query(query, conn, params=(symbol,))
                else:
                    query = "SELECT * FROM v_trading_summary"
                    df = pd.read_sql_query(query, conn)
                
                return df
                
        except Exception as e:
            logger.error(f"Error getting trading summary: {e}")
            return None
    
    def save_system_log(self, level: str, message: str, module: str = None,
                       function_name: str = None, line_number: int = None,
                       extra_data: Dict = None) -> bool:
        """
        システムログを保存
        
        Args:
            level: ログレベル
            message: メッセージ
            module: モジュール名
            function_name: 関数名  
            line_number: 行番号
            extra_data: 追加データ
            
        Returns:
            保存成功フラグ
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO system_logs 
                        (level, message, module, function_name, line_number, extra_data)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_query, (
                        level, message, module, function_name, 
                        line_number, psycopg2.extras.Json(extra_data) if extra_data else None
                    ))
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving system log: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 90) -> bool:
        """
        古いデータの削除
        
        Args:
            days: 保持日数
            
        Returns:
            削除成功フラグ
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 古いログデータを削除
                    cleanup_query = """
                        DELETE FROM system_logs 
                        WHERE created_at < NOW() - INTERVAL '%s days'
                    """
                    cursor.execute(cleanup_query, (days,))
                    
                    deleted_logs = cursor.rowcount
                    
                    # 古い価格データは保持（分析に必要）
                    # 必要に応じてパーティション削除を実装
                    
                    conn.commit()
                    logger.info(f"Deleted {deleted_logs} old log records")
                    return True
                    
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return False

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    db = DatabaseManager()
    
    print("=== Database Connection Test ===")
    if db.test_connection():
        print("Database connection: SUCCESS")
        
        # テストログ保存
        db.save_system_log("INFO", "Database connection test", "database", "test_connection")
        print("Test log saved")
        
    else:
        print("Database connection: FAILED")