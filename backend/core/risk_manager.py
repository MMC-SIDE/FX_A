"""
リスク管理機能
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json

from core.database import DatabaseManager
from core.mt5_client import MT5Client

logger = logging.getLogger(__name__)

class RiskManager:
    """リスク管理クラス"""
    
    def __init__(self, db_manager: DatabaseManager, mt5_client: MT5Client):
        self.db_manager = db_manager
        self.mt5_client = mt5_client
        self.settings = self._load_risk_settings()
        self.emergency_stop_triggered = False
        
    def _load_risk_settings(self) -> Dict[str, Any]:
        """リスク設定を読み込み"""
        # デフォルト値を設定
        default_settings = {
            'max_risk_per_trade': 0.02,  # 2%
            'max_drawdown': 0.20,        # 20%
            'use_nanpin': True,
            'nanpin_max_count': 3,
            'nanpin_interval_pips': 10,
            'max_positions': 5,
            'max_daily_trades': 20,
            'stop_loss_pips': 50,
            'take_profit_pips': 100,
            'trailing_stop_pips': 30,
            'min_confidence_score': 0.7,
            'max_consecutive_losses': 5,
            'daily_loss_limit': 0.05    # 5%
        }
        
        try:
            # データベースから設定を読み込む
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT key, value, value_type FROM system_settings 
                    WHERE key LIKE 'trading.%' OR key LIKE 'risk.%'
                """
                
                result = pd.read_sql_query(query, conn)
                
                settings = {}
                for _, row in result.iterrows():
                    key = row['key'].split('.')[-1]  # 最後の部分のみ取得
                    value = row['value']
                    value_type = row['value_type']
                    
                    # 型変換
                    if value_type == 'float':
                        settings[key] = float(value)
                    elif value_type == 'integer':
                        settings[key] = int(value)
                    elif value_type == 'boolean':
                        settings[key] = value.lower() in ('true', '1', 'yes')
                    else:
                        settings[key] = value
                
                # デフォルト値で補完
                for key, default_value in default_settings.items():
                    if key not in settings:
                        settings[key] = default_value
                
                return settings
                
        except Exception as e:
            logger.error(f"Error loading risk settings: {e}")
            # エラー時はデフォルト設定を返す
            return default_settings
    
    def check_risk_limits(self) -> bool:
        """
        リスク制限チェック
        
        Returns:
            取引可能かどうか
        """
        try:
            # 緊急停止チェック
            if self.emergency_stop_triggered:
                logger.warning("Emergency stop is active")
                return False
            
            # 最大ドローダウンチェック
            if not self._check_max_drawdown():
                logger.warning("Maximum drawdown exceeded")
                return False
            
            # 最大ポジション数チェック
            if not self._check_max_positions():
                logger.warning("Maximum positions exceeded")
                return False
            
            # 日次取引数制限チェック
            if not self._check_daily_trade_limit():
                logger.warning("Daily trade limit exceeded")
                return False
            
            # 連続損失チェック
            if not self._check_consecutive_losses():
                logger.warning("Consecutive losses limit exceeded")
                return False
            
            # 日次損失制限チェック
            if not self._check_daily_loss_limit():
                logger.warning("Daily loss limit exceeded")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return False
    
    def _check_max_drawdown(self) -> bool:
        """最大ドローダウンチェック"""
        try:
            account_info = self.mt5_client.get_account_info()
            if account_info is None:
                return False
            
            current_equity = account_info['equity']
            initial_balance = account_info['balance']  # 実際の初期残高を取得する必要がある
            
            # ここでは簡易的に現在の残高を使用
            max_equity = self._get_max_equity_from_db() or current_equity
            
            if max_equity > 0:
                current_drawdown = (max_equity - current_equity) / max_equity
                max_allowed_drawdown = self.settings['max_drawdown']
                
                if current_drawdown > max_allowed_drawdown:
                    self._log_risk_event(
                        'drawdown_limit',
                        current_drawdown,
                        max_allowed_drawdown,
                        'Maximum drawdown exceeded'
                    )
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking max drawdown: {e}")
            return False
    
    def _check_max_positions(self) -> bool:
        """最大ポジション数チェック"""
        try:
            positions = self.mt5_client.get_positions()
            current_positions = len(positions)
            max_positions = self.settings['max_positions']
            
            if current_positions >= max_positions:
                self._log_risk_event(
                    'position_limit',
                    current_positions,
                    max_positions,
                    'Maximum positions exceeded'
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking max positions: {e}")
            return False
    
    def _check_daily_trade_limit(self) -> bool:
        """日次取引数制限チェック"""
        try:
            today = datetime.now().date()
            
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT COUNT(*) as trade_count
                    FROM trades 
                    WHERE DATE(entry_time) = %s
                """
                
                result = pd.read_sql_query(query, conn, params=(today,))
                
                if not result.empty:
                    daily_trades = result.iloc[0]['trade_count']
                    max_daily_trades = self.settings['max_daily_trades']
                    
                    if daily_trades >= max_daily_trades:
                        self._log_risk_event(
                            'daily_trade_limit',
                            daily_trades,
                            max_daily_trades,
                            'Daily trade limit exceeded'
                        )
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking daily trade limit: {e}")
            return False
    
    def _check_consecutive_losses(self) -> bool:
        """連続損失チェック"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT profit_loss
                    FROM trades 
                    WHERE is_closed = true
                    ORDER BY exit_time DESC
                    LIMIT %s
                """
                
                max_losses = self.settings['max_consecutive_losses']
                result = pd.read_sql_query(query, conn, params=(max_losses,))
                
                if len(result) >= max_losses:
                    # 全て損失かチェック
                    if all(result['profit_loss'] < 0):
                        self._log_risk_event(
                            'consecutive_losses',
                            max_losses,
                            max_losses,
                            'Maximum consecutive losses reached'
                        )
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking consecutive losses: {e}")
            return False
    
    def _check_daily_loss_limit(self) -> bool:
        """日次損失制限チェック"""
        try:
            today = datetime.now().date()
            
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT SUM(profit_loss) as daily_pnl
                    FROM trades 
                    WHERE DATE(entry_time) = %s AND is_closed = true
                """
                
                result = pd.read_sql_query(query, conn, params=(today,))
                
                if not result.empty and result.iloc[0]['daily_pnl'] is not None:
                    daily_pnl = result.iloc[0]['daily_pnl']
                    
                    # 残高を取得
                    account_info = self.mt5_client.get_account_info()
                    if account_info:
                        balance = account_info['balance']
                        loss_percentage = abs(daily_pnl) / balance if daily_pnl < 0 else 0
                        max_daily_loss = self.settings['daily_loss_limit']
                        
                        if loss_percentage > max_daily_loss:
                            self._log_risk_event(
                                'daily_loss_limit',
                                loss_percentage,
                                max_daily_loss,
                                'Daily loss limit exceeded'
                            )
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking daily loss limit: {e}")
            return False
    
    def calculate_lot_size(self, symbol: str, order_type: str) -> float:
        """
        ロットサイズ計算
        
        Args:
            symbol: 通貨ペア
            order_type: 注文タイプ
            
        Returns:
            ロットサイズ
        """
        try:
            # アカウント情報取得
            account_info = self.mt5_client.get_account_info()
            if account_info is None:
                logger.error("Failed to get account info")
                return 0.01  # 最小ロット
            
            balance = account_info['balance']
            risk_amount = balance * self.settings['max_risk_per_trade']
            
            # 通貨ペア情報取得
            symbol_info = self.mt5_client.get_symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Failed to get symbol info for {symbol}")
                return 0.01
            
            # ストップロス距離
            stop_loss_pips = self.settings['stop_loss_pips']
            stop_loss_distance = stop_loss_pips * symbol_info['point'] * 10
            
            # ロットサイズ計算
            if symbol.endswith('JPY'):
                # JPY通貨ペアの場合
                lot_size = risk_amount / (stop_loss_distance * 100000)  # 1ロット = 100,000通貨
            else:
                # その他通貨ペアの場合
                lot_size = risk_amount / (stop_loss_distance * 100000)
            
            # 最小/最大ロットサイズの制限
            min_lot = symbol_info['min_lot']
            max_lot = symbol_info['max_lot']
            lot_step = symbol_info['lot_step']
            
            # ロットステップに合わせて調整
            lot_size = round(lot_size / lot_step) * lot_step
            
            # 制限内に収める
            lot_size = max(min_lot, min(lot_size, max_lot))
            
            logger.info(f"Calculated lot size for {symbol}: {lot_size}")
            return lot_size
            
        except Exception as e:
            logger.error(f"Error calculating lot size: {e}")
            return 0.01
    
    def calculate_sl_tp(self, symbol: str, order_type: str, 
                       entry_price: float) -> Tuple[float, float]:
        """
        ストップロス・テイクプロフィット計算
        
        Args:
            symbol: 通貨ペア
            order_type: 注文タイプ
            entry_price: エントリー価格
            
        Returns:
            (ストップロス, テイクプロフィット)
        """
        try:
            # 通貨ペア情報取得
            symbol_info = self.mt5_client.get_symbol_info(symbol)
            if symbol_info is None:
                return None, None
            
            point = symbol_info['point']
            
            # Pips距離
            sl_pips = self.settings['stop_loss_pips']
            tp_pips = self.settings['take_profit_pips']
            
            if order_type.upper() == 'BUY':
                sl = entry_price - (sl_pips * point * 10)
                tp = entry_price + (tp_pips * point * 10)
            else:  # SELL
                sl = entry_price + (sl_pips * point * 10)
                tp = entry_price - (tp_pips * point * 10)
            
            # 価格の精度に合わせて丸める
            digits = symbol_info['digits']
            sl = round(sl, digits)
            tp = round(tp, digits)
            
            logger.info(f"Calculated SL/TP for {symbol} {order_type}: SL={sl}, TP={tp}")
            return sl, tp
            
        except Exception as e:
            logger.error(f"Error calculating SL/TP: {e}")
            return None, None
    
    def should_emergency_stop(self) -> bool:
        """緊急停止判定"""
        return self.emergency_stop_triggered
    
    def trigger_emergency_stop(self, reason: str = "Manual"):
        """緊急停止トリガー"""
        self.emergency_stop_triggered = True
        logger.critical(f"Emergency stop triggered: {reason}")
        
        self._log_risk_event(
            'emergency_stop',
            1,
            0,
            f'Emergency stop triggered: {reason}'
        )
    
    def reset_emergency_stop(self):
        """緊急停止解除"""
        self.emergency_stop_triggered = False
        logger.info("Emergency stop reset")
    
    def _get_max_equity_from_db(self) -> Optional[float]:
        """データベースから最大エクイティを取得"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT MAX(balance + profit) as max_equity
                    FROM trades
                    WHERE created_at >= %s
                """
                
                # 過去30日間
                since_date = datetime.now() - timedelta(days=30)
                result = pd.read_sql_query(query, conn, params=(since_date,))
                
                if not result.empty and result.iloc[0]['max_equity'] is not None:
                    return float(result.iloc[0]['max_equity'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting max equity: {e}")
            return None
    
    def _log_risk_event(self, event_type: str, trigger_value: float, 
                       threshold_value: float, description: str):
        """リスクイベントのログ記録"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO risk_management_logs 
                        (event_type, trigger_value, threshold_value, description, severity)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    
                    # 重要度判定
                    severity = "WARNING"
                    if event_type in ['emergency_stop', 'drawdown_limit']:
                        severity = "CRITICAL"
                    elif event_type in ['daily_loss_limit', 'consecutive_losses']:
                        severity = "ERROR"
                    
                    cursor.execute(insert_query, (
                        event_type, trigger_value, threshold_value, description, severity
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error logging risk event: {e}")
    
    def get_risk_status(self) -> Dict[str, Any]:
        """リスク状態取得"""
        try:
            account_info = self.mt5_client.get_account_info()
            positions = self.mt5_client.get_positions()
            
            # 現在のドローダウン計算
            current_drawdown = 0
            if account_info:
                current_equity = account_info['equity']
                max_equity = self._get_max_equity_from_db() or current_equity
                if max_equity > 0:
                    current_drawdown = (max_equity - current_equity) / max_equity
            
            # 日次損益計算
            today = datetime.now().date()
            daily_pnl = 0
            
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT COALESCE(SUM(profit_loss), 0) as daily_pnl
                    FROM trades 
                    WHERE DATE(entry_time) = %s AND is_closed = true
                """
                result = pd.read_sql_query(query, conn, params=(today,))
                if not result.empty:
                    daily_pnl = result.iloc[0]['daily_pnl']
            
            return {
                "emergency_stop": self.emergency_stop_triggered,
                "current_drawdown": current_drawdown,
                "max_allowed_drawdown": self.settings['max_drawdown'],
                "current_positions": len(positions),
                "max_positions": self.settings['max_positions'],
                "daily_pnl": daily_pnl,
                "risk_settings": self.settings
            }
            
        except Exception as e:
            logger.error(f"Error getting risk status: {e}")
            return {"error": str(e)}
    
    def update_risk_settings(self, new_settings: Dict[str, Any]) -> bool:
        """リスク設定更新"""
        try:
            for key, value in new_settings.items():
                if key in self.settings:
                    self.settings[key] = value
                    
                    # データベースにも保存
                    with self.db_manager.get_connection() as conn:
                        with conn.cursor() as cursor:
                            # 値の型を判定
                            if isinstance(value, bool):
                                value_type = 'boolean'
                                value_str = str(value).lower()
                            elif isinstance(value, int):
                                value_type = 'integer'
                                value_str = str(value)
                            elif isinstance(value, float):
                                value_type = 'float'
                                value_str = str(value)
                            else:
                                value_type = 'string'
                                value_str = str(value)
                            
                            # 設定更新
                            update_query = """
                                UPDATE system_settings 
                                SET value = %s, value_type = %s, updated_at = CURRENT_TIMESTAMP
                                WHERE key = %s
                            """
                            cursor.execute(update_query, (value_str, value_type, f"trading.{key}"))
                            
                            # 新規の場合は挿入
                            if cursor.rowcount == 0:
                                insert_query = """
                                    INSERT INTO system_settings (key, value, value_type, description)
                                    VALUES (%s, %s, %s, %s)
                                """
                                cursor.execute(insert_query, (
                                    f"trading.{key}", value_str, value_type, f"Trading setting: {key}"
                                ))
                            
                            conn.commit()
            
            logger.info("Risk settings updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating risk settings: {e}")
            return False

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    print("Risk manager test completed")