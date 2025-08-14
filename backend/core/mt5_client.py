"""
MT5接続クライアント
"""
import MetaTrader5 as mt5
import json
import logging
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# 時間軸マッピング
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

# 対象通貨ペア
TARGET_SYMBOLS = [
    "USDJPY", "EURJPY", "GBPJPY", "AUDJPY", 
    "NZDJPY", "CADJPY", "CHFJPY"
]

class MT5Client:
    """MetaTrader5接続クライアント"""
    
    def __init__(self, config_path: str = "config/mt5_config.json"):
        self.config_path = config_path
        self.is_connected = False
        self.config = None
        self.max_retries = 3
        self.retry_delay = 1.0
        
    def load_config(self) -> bool:
        """設定ファイルを読み込み"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return True
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            return False
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in config file: {self.config_path}")
            return False
    
    def connect(self) -> bool:
        """MT5に接続"""
        if not self.load_config():
            return False
            
        try:
            # MT5を初期化
            if not mt5.initialize(
                path=self.config.get("path"),
                login=self.config.get("login"),
                password=self.config.get("password"),
                server=self.config.get("server"),
                timeout=self.config.get("timeout", 60000)
            ):
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
            
            # 接続確認
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("Failed to get account info")
                return False
                
            self.is_connected = True
            logger.info(f"Connected to MT5. Account: {account_info.login}")
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False
    
    def disconnect(self) -> None:
        """MT5から切断"""
        if self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            logger.info("Disconnected from MT5")
    
    def get_account_info(self) -> Optional[Dict]:
        """アカウント情報取得"""
        if not self.is_connected:
            return None
            
        account_info = mt5.account_info()
        if account_info is None:
            return None
            
        return {
            "login": account_info.login,
            "server": account_info.server,
            "name": account_info.name,
            "company": account_info.company,
            "currency": account_info.currency,
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin": account_info.margin,
            "margin_free": account_info.margin_free,
            "margin_level": account_info.margin_level
        }
    
    def get_symbols(self) -> List[str]:
        """利用可能な通貨ペア一覧取得"""
        if not self.is_connected:
            return []
            
        symbols = mt5.symbols_get()
        if symbols is None:
            return []
            
        return [symbol.name for symbol in symbols if symbol.visible]
    
    def get_rates(self, symbol: str, timeframe: str, count: int = 1000, 
                  start_pos: int = 0) -> Optional[pd.DataFrame]:
        """
        価格データ取得
        
        Args:
            symbol: 通貨ペア
            timeframe: 時間軸 (M1, M5, M15, M30, H1, H4, D1)
            count: 取得数
            start_pos: 開始位置（0=最新）
            
        Returns:
            価格データのDataFrame
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return None
            
        if timeframe not in TIMEFRAME_MAP:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None
            
        try:
            mt5_timeframe = TIMEFRAME_MAP[timeframe]
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, start_pos, count)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No rates data for {symbol} {timeframe}")
                return None
                
            # DataFrameに変換
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['symbol'] = symbol
            df['timeframe'] = timeframe
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting rates for {symbol} {timeframe}: {e}")
            return None
    
    def get_rates_range(self, symbol: str, timeframe: str, 
                       start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        指定期間の価格データ取得
        
        Args:
            symbol: 通貨ペア
            timeframe: 時間軸
            start_date: 開始日時
            end_date: 終了日時
            
        Returns:
            価格データのDataFrame
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return None
            
        if timeframe not in TIMEFRAME_MAP:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None
            
        try:
            mt5_timeframe = TIMEFRAME_MAP[timeframe]
            rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No rates data for {symbol} {timeframe} in range")
                return None
                
            # DataFrameに変換
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['symbol'] = symbol
            df['timeframe'] = timeframe
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting rates range for {symbol} {timeframe}: {e}")
            return None
    
    def get_tick(self, symbol: str) -> Optional[Dict]:
        """
        最新ティック取得
        
        Args:
            symbol: 通貨ペア
            
        Returns:
            ティックデータ辞書
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return None
            
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.warning(f"No tick data for {symbol}")
                return None
                
            return {
                "symbol": symbol,
                "time": datetime.fromtimestamp(tick.time),
                "bid": tick.bid,
                "ask": tick.ask,
                "last": tick.last,
                "volume": tick.volume,
                "spread": tick.ask - tick.bid
            }
            
        except Exception as e:
            logger.error(f"Error getting tick for {symbol}: {e}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        通貨ペア情報取得
        
        Args:
            symbol: 通貨ペア
            
        Returns:
            通貨ペア情報辞書
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return None
            
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                logger.warning(f"No symbol info for {symbol}")
                return None
                
            return {
                "name": info.name,
                "digits": info.digits,
                "spread": info.spread,
                "point": info.point,
                "min_lot": info.volume_min,
                "max_lot": info.volume_max,
                "lot_step": info.volume_step,
                "margin_initial": info.margin_initial,
                "margin_maintenance": info.margin_maintenance,
                "swap_long": info.swap_long,
                "swap_short": info.swap_short,
                "contract_size": info.trade_contract_size
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def reconnect(self) -> bool:
        """
        自動再接続
        
        Returns:
            接続成功フラグ
        """
        logger.info("Attempting to reconnect to MT5...")
        
        for attempt in range(self.max_retries):
            if self.is_connected:
                self.disconnect()
                
            time.sleep(self.retry_delay * (attempt + 1))
            
            if self.connect():
                logger.info(f"Reconnected successfully on attempt {attempt + 1}")
                return True
            else:
                logger.warning(f"Reconnection attempt {attempt + 1} failed")
                
        logger.error("Failed to reconnect after maximum retries")
        return False
    
    def ensure_connection(self) -> bool:
        """
        接続確認と再接続
        
        Returns:
            接続状態
        """
        if self.is_connected:
            # 接続テスト
            try:
                account_info = mt5.account_info()
                if account_info is not None:
                    return True
            except:
                pass
                
        # 再接続試行
        return self.reconnect()
    
    def get_multiple_rates(self, symbols: List[str], timeframe: str, 
                          count: int = 100) -> Dict[str, pd.DataFrame]:
        """
        複数通貨ペアの価格データを一括取得
        
        Args:
            symbols: 通貨ペアリスト
            timeframe: 時間軸
            count: 取得数
            
        Returns:
            通貨ペア別の価格データ辞書
        """
        results = {}
        
        for symbol in symbols:
            if not self.ensure_connection():
                logger.error("Connection lost and could not reconnect")
                break
                
            rates = self.get_rates(symbol, timeframe, count)
            if rates is not None:
                results[symbol] = rates
            else:
                logger.warning(f"Failed to get rates for {symbol}")
                
        return results
    
    def place_order(self, symbol: str, order_type: str, volume: float,
                   price: float = None, sl: float = None, tp: float = None,
                   comment: str = "", magic: int = 0) -> Optional[Any]:
        """
        注文実行
        
        Args:
            symbol: 通貨ペア
            order_type: 注文タイプ ('BUY', 'SELL')
            volume: ロット数
            price: 価格（成行の場合はNone）
            sl: ストップロス
            tp: テイクプロフィット
            comment: コメント
            magic: マジックナンバー
            
        Returns:
            注文結果
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return None
        
        try:
            # 注文タイプの変換
            if order_type.upper() == 'BUY':
                order_type_mt5 = mt5.ORDER_TYPE_BUY
                order_action = mt5.TRADE_ACTION_DEAL
            elif order_type.upper() == 'SELL':
                order_type_mt5 = mt5.ORDER_TYPE_SELL
                order_action = mt5.TRADE_ACTION_DEAL
            else:
                logger.error(f"Invalid order type: {order_type}")
                return None
            
            # 現在価格取得（価格指定がない場合）
            if price is None:
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    logger.error(f"Failed to get tick for {symbol}")
                    return None
                price = tick.ask if order_type.upper() == 'BUY' else tick.bid
            
            # 注文リクエスト作成
            request = {
                "action": order_action,
                "symbol": symbol,
                "volume": volume,
                "type": order_type_mt5,
                "price": price,
                "deviation": 20,
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # ストップロス・テイクプロフィット設定
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            # 注文送信
            result = mt5.order_send(request)
            
            if result is None:
                logger.error("order_send failed")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed: {result.retcode} - {result.comment}")
            else:
                logger.info(f"Order successful: {order_type} {volume} {symbol} at {price}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def close_position(self, position_id: int) -> Optional[Any]:
        """
        ポジションクローズ
        
        Args:
            position_id: ポジションID
            
        Returns:
            クローズ結果
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return None
        
        try:
            # ポジション情報取得
            positions = mt5.positions_get()
            position = None
            
            for pos in positions:
                if pos.ticket == position_id:
                    position = pos
                    break
            
            if position is None:
                logger.error(f"Position {position_id} not found")
                return None
            
            # クローズ注文の設定
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position_id,
                "price": price,
                "deviation": 20,
                "magic": position.magic,
                "comment": f"Close position {position_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # クローズ注文送信
            result = mt5.order_send(request)
            
            if result is None:
                logger.error("Close order_send failed")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Close failed: {result.retcode} - {result.comment}")
            else:
                logger.info(f"Position {position_id} closed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None
    
    def get_positions(self, symbol: str = None) -> List[Dict]:
        """
        現在のポジション取得
        
        Args:
            symbol: 通貨ペア（指定しない場合は全て）
            
        Returns:
            ポジション一覧
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return []
        
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            position_list = []
            for pos in positions:
                position_data = {
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "price_current": pos.price_current,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "swap": pos.swap,
                    "commission": pos.commission,
                    "time": datetime.fromtimestamp(pos.time),
                    "magic": pos.magic,
                    "comment": pos.comment
                }
                position_list.append(position_data)
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_orders(self, symbol: str = None) -> List[Dict]:
        """
        待機注文取得
        
        Args:
            symbol: 通貨ペア（指定しない場合は全て）
            
        Returns:
            注文一覧
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return []
        
        try:
            if symbol:
                orders = mt5.orders_get(symbol=symbol)
            else:
                orders = mt5.orders_get()
            
            if orders is None:
                return []
            
            order_list = []
            for order in orders:
                order_data = {
                    "ticket": order.ticket,
                    "symbol": order.symbol,
                    "type": self._convert_order_type(order.type),
                    "volume": order.volume_initial,
                    "price_open": order.price_open,
                    "sl": order.sl,
                    "tp": order.tp,
                    "time_setup": datetime.fromtimestamp(order.time_setup),
                    "magic": order.magic,
                    "comment": order.comment
                }
                order_list.append(order_data)
            
            return order_list
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def _convert_order_type(self, mt5_type: int) -> str:
        """MT5注文タイプを文字列に変換"""
        type_map = {
            mt5.ORDER_TYPE_BUY: "BUY",
            mt5.ORDER_TYPE_SELL: "SELL",
            mt5.ORDER_TYPE_BUY_LIMIT: "BUY_LIMIT",
            mt5.ORDER_TYPE_SELL_LIMIT: "SELL_LIMIT",
            mt5.ORDER_TYPE_BUY_STOP: "BUY_STOP",
            mt5.ORDER_TYPE_SELL_STOP: "SELL_STOP"
        }
        return type_map.get(mt5_type, "UNKNOWN")
    
    def modify_position(self, position_id: int, sl: float = None, 
                       tp: float = None) -> Optional[Any]:
        """
        ポジション修正（SL/TP変更）
        
        Args:
            position_id: ポジションID
            sl: 新しいストップロス
            tp: 新しいテイクプロフィット
            
        Returns:
            修正結果
        """
        if not self.is_connected:
            logger.error("MT5 not connected")
            return None
        
        try:
            # ポジション情報取得
            positions = mt5.positions_get()
            position = None
            
            for pos in positions:
                if pos.ticket == position_id:
                    position = pos
                    break
            
            if position is None:
                logger.error(f"Position {position_id} not found")
                return None
            
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": position_id,
                "magic": position.magic,
            }
            
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            # 修正注文送信
            result = mt5.order_send(request)
            
            if result is None:
                logger.error("Modify order_send failed")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Modify failed: {result.retcode} - {result.comment}")
            else:
                logger.info(f"Position {position_id} modified successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Error modifying position: {e}")
            return None
    
    def close_all_positions(self, symbol: str = None) -> int:
        """
        全ポジションクローズ
        
        Args:
            symbol: 通貨ペア（指定しない場合は全て）
            
        Returns:
            クローズされたポジション数
        """
        positions = self.get_positions(symbol)
        closed_count = 0
        
        for position in positions:
            result = self.close_position(position['ticket'])
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                closed_count += 1
        
        logger.info(f"Closed {closed_count} positions")
        return closed_count
    
    def test_connection(self) -> Dict[str, any]:
        """接続テスト"""
        result = {
            "success": False,
            "message": "",
            "account_info": None,
            "symbols_count": 0
        }
        
        try:
            if self.connect():
                account_info = self.get_account_info()
                symbols = self.get_symbols()
                
                result.update({
                    "success": True,
                    "message": "Connection successful",
                    "account_info": account_info,
                    "symbols_count": len(symbols)
                })
            else:
                result["message"] = "Connection failed"
                
        except Exception as e:
            result["message"] = f"Connection test error: {e}"
        
        finally:
            self.disconnect()
            
        return result

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    client = MT5Client()
    test_result = client.test_connection()
    
    print("=== MT5 Connection Test ===")
    print(f"Success: {test_result['success']}")
    print(f"Message: {test_result['message']}")
    
    if test_result["account_info"]:
        print(f"Account: {test_result['account_info']['login']}")
        print(f"Balance: {test_result['account_info']['balance']}")
        print(f"Currency: {test_result['account_info']['currency']}")
    
    print(f"Available Symbols: {test_result['symbols_count']}")