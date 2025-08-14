"""
自動売買エンジン
"""
import pandas as pd
import numpy as np
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json

from backend.core.mt5_client import MT5Client
from backend.core.database import DatabaseManager
from backend.core.risk_manager import RiskManager
from backend.ml.features import FeatureEngineering
from backend.ml.model_manager import ModelManager
from backend.ml.models.lightgbm_model import LightGBMPredictor

logger = logging.getLogger(__name__)

class NanpinManager:
    """ナンピン管理クラス"""
    
    def __init__(self, mt5_client: MT5Client, max_count: int = 3, interval_pips: int = 10):
        self.mt5_client = mt5_client
        self.max_count = max_count
        self.interval_pips = interval_pips
    
    def check_nanpin_condition(self, symbol: str, position: Dict[str, Any]) -> bool:
        """
        ナンピン条件チェック
        
        Args:
            symbol: 通貨ペア
            position: ポジション情報
            
        Returns:
            ナンピン実行可能かどうか
        """
        try:
            if position['nanpin_count'] >= self.max_count:
                return False
            
            # 現在価格取得
            tick = self.mt5_client.get_tick(symbol)
            if tick is None:
                return False
            
            current_price = tick['ask'] if position['type'] == 'BUY' else tick['bid']
            
            # 通貨ペア情報取得（pip計算用）
            symbol_info = self.mt5_client.get_symbol_info(symbol)
            if symbol_info is None:
                return False
            
            # 価格差計算
            price_diff = abs(current_price - position['avg_price'])
            
            # JPY通貨ペアかどうかで計算方法を変える
            if symbol.endswith('JPY'):
                pip_value = 0.01  # JPY通貨ペア
            else:
                pip_value = 0.0001  # その他通貨ペア
            
            pip_diff = price_diff / pip_value
            
            # ナンピン実行条件チェック
            if position['type'] == 'BUY' and current_price < position['avg_price']:
                return pip_diff >= self.interval_pips
            elif position['type'] == 'SELL' and current_price > position['avg_price']:
                return pip_diff >= self.interval_pips
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking nanpin condition: {e}")
            return False
    
    def execute_nanpin(self, symbol: str, position: Dict[str, Any]) -> bool:
        """
        ナンピン実行
        
        Args:
            symbol: 通貨ペア
            position: ポジション情報
            
        Returns:
            実行成功かどうか
        """
        try:
            # 追加ロットサイズ（同じサイズ）
            additional_volume = position['volume']
            
            # 現在価格で追加注文
            result = self.mt5_client.place_order(
                symbol=symbol,
                order_type=position['type'],
                volume=additional_volume,
                comment=f"NANPIN_{position['nanpin_count'] + 1}",
                magic=position.get('magic', 0)
            )
            
            if result and hasattr(result, 'retcode') and result.retcode == 0:  # MT5成功コード
                # 現在価格取得
                tick = self.mt5_client.get_tick(symbol)
                current_price = tick['ask'] if position['type'] == 'BUY' else tick['bid']
                
                # ポジション情報更新（平均価格計算）
                total_volume = position['volume'] + additional_volume
                avg_price = (
                    (position['avg_price'] * position['volume'] + 
                     current_price * additional_volume) / total_volume
                )
                
                position['volume'] = total_volume
                position['avg_price'] = avg_price
                position['nanpin_count'] += 1
                
                logger.info(f"Nanpin executed for {symbol}: {position['nanpin_count']}/{self.max_count}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing nanpin: {e}")
            return False

class TradingEngine:
    """自動売買エンジン"""
    
    def __init__(self, db_manager: DatabaseManager, mt5_client: MT5Client):
        self.db_manager = db_manager
        self.mt5_client = mt5_client
        self.risk_manager = RiskManager(db_manager, mt5_client)
        self.model_manager = ModelManager(db_manager)
        self.feature_engine = FeatureEngineering()
        self.nanpin_manager = NanpinManager(mt5_client)
        
        # 取引状態
        self.is_active = False
        self.symbol = None
        self.timeframe = None
        self.model = None
        self.current_positions = {}  # {symbol: position_info}
        self.magic_number = 12345  # マジックナンバー
        
        # 設定
        self.check_interval = 60  # 秒
        self.min_confidence = 0.7
        
    async def start_trading(self, symbol: str, timeframe: str) -> bool:
        """
        自動売買開始
        
        Args:
            symbol: 通貨ペア
            timeframe: 時間軸
            
        Returns:
            開始成功かどうか
        """
        try:
            if self.is_active:
                logger.warning("Trading already active")
                return False
            
            # MT5接続確認
            if not self.mt5_client.ensure_connection():
                logger.error("MT5 connection failed")
                return False
            
            # モデル読み込み
            self.model = self.model_manager.load_latest_model(symbol, timeframe)
            if self.model is None:
                logger.error(f"No trained model found for {symbol} {timeframe}")
                return False
            
            self.symbol = symbol
            self.timeframe = timeframe
            self.is_active = True
            
            logger.info(f"Trading started for {symbol} {timeframe}")
            
            # 既存ポジションを読み込み
            await self._load_existing_positions()
            
            # メインループ開始
            asyncio.create_task(self._trading_loop())
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting trading: {e}")
            return False
    
    async def stop_trading(self, close_positions: bool = False) -> bool:
        """
        自動売買停止
        
        Args:
            close_positions: ポジションをクローズするかどうか
            
        Returns:
            停止成功かどうか
        """
        try:
            self.is_active = False
            
            if close_positions:
                await self._close_all_positions()
            
            logger.info("Trading stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping trading: {e}")
            return False
    
    async def _load_existing_positions(self):
        """既存ポジションの読み込み"""
        try:
            positions = self.mt5_client.get_positions(self.symbol)
            
            for pos in positions:
                if pos['magic'] == self.magic_number:
                    position_info = {
                        'ticket': pos['ticket'],
                        'type': pos['type'],
                        'volume': pos['volume'],
                        'avg_price': pos['price_open'],
                        'open_time': pos['time'],
                        'sl': pos['sl'],
                        'tp': pos['tp'],
                        'nanpin_count': 0,  # 既存ポジションのナンピン回数は0とする
                        'magic': pos['magic']
                    }
                    self.current_positions[self.symbol] = position_info
                    logger.info(f"Loaded existing position: {pos['ticket']}")
                    
        except Exception as e:
            logger.error(f"Error loading existing positions: {e}")
    
    async def _trading_loop(self):
        """メイントレーディングループ"""
        while self.is_active:
            try:
                # MT5接続確認
                if not self.mt5_client.ensure_connection():
                    logger.error("MT5 connection lost")
                    await asyncio.sleep(30)
                    continue
                
                # 最新データ取得
                latest_data = await self._get_latest_data()
                if latest_data is None or latest_data.empty:
                    logger.warning("No data available")
                    await asyncio.sleep(self.check_interval)
                    continue
                
                # シグナル生成
                signal, confidence = await self._generate_signal(latest_data)
                
                # リスクチェック
                if not self.risk_manager.check_risk_limits():
                    logger.warning("Risk limits exceeded, skipping trade")
                    await asyncio.sleep(self.check_interval)
                    continue
                
                # トレード実行
                await self._execute_trade_signal(signal, confidence)
                
                # ポジション管理
                await self._manage_positions()
                
                # 次の実行まで待機
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機
        
        logger.info("Trading loop stopped")
    
    async def _get_latest_data(self) -> Optional[pd.DataFrame]:
        """最新データ取得"""
        try:
            # MT5から最新データ取得（500本）
            df = self.mt5_client.get_rates(self.symbol, self.timeframe, count=500)
            
            if df is None or len(df) < 200:
                logger.warning(f"Insufficient data for {self.symbol} {self.timeframe}")
                return None
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting latest data: {e}")
            return None
    
    async def _generate_signal(self, data: pd.DataFrame) -> Tuple[str, float]:
        """
        シグナル生成
        
        Args:
            data: 価格データ
            
        Returns:
            (シグナル, 信頼度)
        """
        try:
            # 特徴量作成
            features_df = self.feature_engine.create_features(data)
            
            if features_df.empty or len(features_df) < 1:
                logger.warning("Feature generation failed")
                return 'HOLD', 0.0
            
            # 最新行のみ取得
            latest_features = features_df.tail(1)
            
            # 必要な特徴量があるかチェック
            required_features = self.model.feature_columns
            if not all(col in latest_features.columns for col in required_features):
                logger.warning("Missing required features")
                return 'HOLD', 0.0
            
            # 予測実行
            if hasattr(self.model, 'predict_with_confidence'):
                predictions, confidence = self.model.predict_with_confidence(
                    latest_features[required_features]
                )
                prediction = predictions[0]
                confidence_score = confidence[0]
            else:
                prediction = self.model.predict(latest_features[required_features])[0]
                confidence_score = 0.5  # デフォルト信頼度
            
            # シグナル変換
            signal_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
            signal = signal_map.get(prediction, 'HOLD')
            
            logger.info(f"Generated signal: {signal} (confidence: {confidence_score:.3f})")
            
            return signal, confidence_score
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return 'HOLD', 0.0
    
    async def _execute_trade_signal(self, signal: str, confidence: float):
        """
        トレードシグナル実行
        
        Args:
            signal: シグナル
            confidence: 信頼度
        """
        try:
            # 信頼度チェック
            if confidence < self.min_confidence:
                logger.info(f"Signal confidence too low: {confidence:.3f}")
                return
            
            current_position = self.current_positions.get(self.symbol)
            
            if signal == 'BUY':
                if not current_position or current_position['type'] == 'SELL':
                    await self._open_position('BUY')
            elif signal == 'SELL':
                if not current_position or current_position['type'] == 'BUY':
                    await self._open_position('SELL')
            # HOLDの場合は何もしない
            
        except Exception as e:
            logger.error(f"Error executing trade signal: {e}")
    
    async def _open_position(self, order_type: str):
        """
        ポジションオープン
        
        Args:
            order_type: 注文タイプ ('BUY' or 'SELL')
        """
        try:
            # 既存ポジションがあればクローズ
            if self.symbol in self.current_positions:
                await self._close_position(self.symbol)
            
            # ロットサイズ計算
            lot_size = self.risk_manager.calculate_lot_size(self.symbol, order_type)
            
            if lot_size <= 0:
                logger.error("Invalid lot size calculated")
                return
            
            # 価格取得
            tick = self.mt5_client.get_tick(self.symbol)
            if tick is None:
                logger.error("Failed to get current price")
                return
            
            price = tick['ask'] if order_type == 'BUY' else tick['bid']
            
            # ストップロス・テイクプロフィット計算
            sl, tp = self.risk_manager.calculate_sl_tp(self.symbol, order_type, price)
            
            # 注文実行
            result = self.mt5_client.place_order(
                symbol=self.symbol,
                order_type=order_type,
                volume=lot_size,
                price=price,
                sl=sl,
                tp=tp,
                comment=f"ML_AUTO_{self.timeframe}",
                magic=self.magic_number
            )
            
            if result and hasattr(result, 'retcode') and result.retcode == 0:
                # ポジション記録
                position_data = {
                    'ticket': result.order if hasattr(result, 'order') else None,
                    'type': order_type,
                    'volume': lot_size,
                    'avg_price': price,
                    'open_time': datetime.now(),
                    'sl': sl,
                    'tp': tp,
                    'nanpin_count': 0,
                    'magic': self.magic_number
                }
                self.current_positions[self.symbol] = position_data
                
                # データベースに保存
                await self._save_trade_to_db(position_data)
                
                logger.info(f"Position opened: {order_type} {lot_size} lots at {price}")
            else:
                error_msg = result.comment if result and hasattr(result, 'comment') else "Unknown error"
                logger.error(f"Order failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error opening position: {e}")
    
    async def _close_position(self, symbol: str):
        """
        ポジションクローズ
        
        Args:
            symbol: 通貨ペア
        """
        if symbol not in self.current_positions:
            return
        
        position = self.current_positions[symbol]
        
        try:
            # クローズ注文実行
            result = self.mt5_client.close_position(position['ticket'])
            
            if result and hasattr(result, 'retcode') and result.retcode == 0:
                # 損益計算
                tick = self.mt5_client.get_tick(symbol)
                close_price = tick['bid'] if position['type'] == 'BUY' else tick['ask']
                
                # ポジション削除
                del self.current_positions[symbol]
                
                # データベース更新
                await self._update_trade_in_db(position['ticket'], close_price, datetime.now())
                
                logger.info(f"Position closed: {symbol} at {close_price}")
            else:
                error_msg = result.comment if result and hasattr(result, 'comment') else "Unknown error"
                logger.error(f"Close failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def _close_all_positions(self):
        """全ポジションクローズ"""
        symbols_to_close = list(self.current_positions.keys())
        
        for symbol in symbols_to_close:
            await self._close_position(symbol)
    
    async def _manage_positions(self):
        """ポジション管理"""
        for symbol, position in self.current_positions.copy().items():
            try:
                # 緊急停止チェック
                if self.risk_manager.should_emergency_stop():
                    await self._close_position(symbol)
                    continue
                
                # ナンピンチェック
                if self.risk_manager.settings.get('use_nanpin', False):
                    if self.nanpin_manager.check_nanpin_condition(symbol, position):
                        if self.nanpin_manager.execute_nanpin(symbol, position):
                            # ポジション情報更新後にDB保存
                            await self._update_position_in_db(position)
                
                # トレーリングストップチェック
                await self._check_trailing_stop(symbol, position)
                
            except Exception as e:
                logger.error(f"Error managing position {symbol}: {e}")
    
    async def _check_trailing_stop(self, symbol: str, position: Dict[str, Any]):
        """トレーリングストップチェック"""
        try:
            if not position.get('sl'):
                return
            
            # 現在価格取得
            tick = self.mt5_client.get_tick(symbol)
            if tick is None:
                return
            
            current_price = tick['ask'] if position['type'] == 'BUY' else tick['bid']
            
            # 通貨ペア情報取得
            symbol_info = self.mt5_client.get_symbol_info(symbol)
            if symbol_info is None:
                return
            
            trailing_pips = self.risk_manager.settings.get('trailing_stop_pips', 30)
            point = symbol_info['point']
            
            # トレーリングストップ距離
            trailing_distance = trailing_pips * point * 10
            
            new_sl = None
            
            if position['type'] == 'BUY':
                # 買いポジションの場合
                potential_sl = current_price - trailing_distance
                if potential_sl > position['sl']:
                    new_sl = potential_sl
            else:
                # 売りポジションの場合
                potential_sl = current_price + trailing_distance
                if potential_sl < position['sl']:
                    new_sl = potential_sl
            
            # ストップロス更新
            if new_sl is not None:
                result = self.mt5_client.modify_position(position['ticket'], sl=new_sl)
                if result and hasattr(result, 'retcode') and result.retcode == 0:
                    position['sl'] = new_sl
                    logger.info(f"Trailing stop updated for {symbol}: {new_sl}")
                    
        except Exception as e:
            logger.error(f"Error checking trailing stop: {e}")
    
    async def _save_trade_to_db(self, position_data: Dict[str, Any]):
        """取引データをデータベースに保存"""
        try:
            trade_data = {
                'trade_id': position_data['ticket'],
                'symbol': self.symbol,
                'order_type': position_data['type'],
                'entry_time': position_data['open_time'],
                'entry_price': position_data['avg_price'],
                'volume': position_data['volume'],
                'magic_number': position_data['magic'],
                'comment': f"ML_AUTO_{self.timeframe}",
                'is_closed': False
            }
            
            success = self.db_manager.save_trade(trade_data)
            if success:
                logger.info(f"Trade saved to database: {position_data['ticket']}")
            else:
                logger.error("Failed to save trade to database")
                
        except Exception as e:
            logger.error(f"Error saving trade to database: {e}")
    
    async def _update_trade_in_db(self, ticket: int, close_price: float, close_time: datetime):
        """データベースの取引データを更新"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 取引データ取得して損益計算
                    select_query = """
                        SELECT entry_price, volume, order_type
                        FROM trades WHERE trade_id = %s
                    """
                    cursor.execute(select_query, (ticket,))
                    result = cursor.fetchone()
                    
                    if result:
                        entry_price, volume, order_type = result
                        
                        # 損益計算（簡易版）
                        if order_type == 'BUY':
                            profit_loss = (close_price - entry_price) * volume * 100000  # 仮の計算
                        else:
                            profit_loss = (entry_price - close_price) * volume * 100000
                        
                        # 更新
                        update_query = """
                            UPDATE trades 
                            SET exit_time = %s, exit_price = %s, profit_loss = %s, 
                                is_closed = true, updated_at = CURRENT_TIMESTAMP
                            WHERE trade_id = %s
                        """
                        cursor.execute(update_query, (close_time, close_price, profit_loss, ticket))
                        conn.commit()
                        
                        logger.info(f"Trade updated in database: {ticket}, P/L: {profit_loss}")
                    
        except Exception as e:
            logger.error(f"Error updating trade in database: {e}")
    
    async def _update_position_in_db(self, position: Dict[str, Any]):
        """ポジション情報をデータベースに更新"""
        try:
            # ナンピン後の平均価格などを更新
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    update_query = """
                        UPDATE trades 
                        SET entry_price = %s, volume = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE trade_id = %s
                    """
                    cursor.execute(update_query, (
                        position['avg_price'], 
                        position['volume'], 
                        position['ticket']
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error updating position in database: {e}")
    
    def get_trading_status(self) -> Dict[str, Any]:
        """取引状態取得"""
        try:
            return {
                "is_active": self.is_active,
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "model_loaded": self.model is not None,
                "current_positions": len(self.current_positions),
                "positions": self.current_positions,
                "risk_status": self.risk_manager.get_risk_status(),
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting trading status: {e}")
            return {"error": str(e)}

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    print("Trading engine test completed")