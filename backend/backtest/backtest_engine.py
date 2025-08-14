"""
バックテストエンジン
"""
import pandas as pd
import numpy as np
import uuid
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

from backend.core.database import DatabaseManager
from backend.core.mt5_client import MT5Client
from backend.ml.features import FeatureEngineering
from backend.ml.models.lightgbm_model import LightGBMPredictor
from backend.ml.model_manager import ModelManager

logger = logging.getLogger(__name__)

class BacktestEngine:
    """バックテストエンジン"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.feature_engine = FeatureEngineering()
        self.model_manager = ModelManager(db_manager)
        self.results = {}
        
    async def run_backtest(self,
                          symbol: str,
                          timeframe: str,
                          start_date: datetime,
                          end_date: datetime,
                          parameters: Dict[str, Any],
                          initial_balance: float = 100000) -> Dict[str, Any]:
        """
        バックテスト実行
        
        Args:
            symbol: 通貨ペア
            timeframe: 時間軸
            start_date: 開始日
            end_date: 終了日
            parameters: パラメータ
            initial_balance: 初期残高
            
        Returns:
            バックテスト結果
        """
        try:
            # テストID生成
            test_id = str(uuid.uuid4())
            
            logger.info(f"Starting backtest {test_id} for {symbol} {timeframe}")
            
            # データ取得
            historical_data = await self._get_historical_data(
                symbol, timeframe, start_date, end_date
            )
            
            if historical_data.empty:
                raise ValueError(f"No data available for {symbol} {timeframe}")
            
            # 特徴量作成
            features_data = self.feature_engine.create_features(historical_data)
            
            if features_data.empty:
                raise ValueError("Feature generation failed")
            
            # モデル学習（分割データで）
            model = await self._train_model_for_backtest(features_data, parameters)
            
            # バックテスト実行
            trades, equity_curve = await self._simulate_trading(
                historical_data, features_data, model, parameters, initial_balance
            )
            
            # 統計計算
            statistics = self._calculate_statistics(
                trades, equity_curve, initial_balance
            )
            
            # 結果保存
            await self._save_backtest_result(
                test_id, symbol, timeframe,
                start_date, end_date,
                initial_balance, statistics,
                parameters, equity_curve, trades
            )
            
            logger.info(f"Backtest {test_id} completed successfully")
            
            return {
                'test_id': test_id,
                'symbol': symbol,
                'timeframe': timeframe,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'initial_balance': initial_balance,
                'parameters': parameters,
                'statistics': statistics,
                'equity_curve': equity_curve,
                'trades': trades,
                'data_points': len(historical_data)
            }
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise
    
    async def _get_historical_data(self,
                                  symbol: str,
                                  timeframe: str,
                                  start_date: datetime,
                                  end_date: datetime) -> pd.DataFrame:
        """過去データ取得"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT time, open, high, low, close, tick_volume
                    FROM price_data
                    WHERE symbol = %s AND timeframe = %s 
                    AND time >= %s AND time <= %s
                    ORDER BY time
                """
                
                df = pd.read_sql_query(
                    query, conn, 
                    params=(symbol, timeframe, start_date, end_date),
                    parse_dates=['time']
                )
                
                if not df.empty:
                    df.set_index('time', inplace=True)
                    df.columns = ['open', 'high', 'low', 'close', 'volume']
                
                logger.info(f"Retrieved {len(df)} data points for {symbol} {timeframe}")
                return df
                
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    async def _train_model_for_backtest(self,
                                       features_data: pd.DataFrame,
                                       parameters: Dict[str, Any]) -> LightGBMPredictor:
        """バックテスト用モデル学習"""
        try:
            # データ分割（前半80%で学習、後半20%でテスト）
            split_point = int(len(features_data) * 0.8)
            train_data = features_data.iloc[:split_point]
            
            # ターゲット作成（価格変動に基づく）
            train_data = train_data.copy()
            train_data['target'] = self._create_target_labels(train_data)
            
            # 欠損値除去
            train_data = train_data.dropna()
            
            if len(train_data) < 100:
                raise ValueError("Insufficient training data")
            
            # 特徴量選択
            feature_columns = [col for col in train_data.columns 
                             if col not in ['target', 'open', 'high', 'low', 'close', 'volume']]
            
            X_train = train_data[feature_columns]
            y_train = train_data['target']
            
            # モデル学習
            model = LightGBMPredictor()
            
            # パラメータ設定
            model_params = {
                'n_estimators': parameters.get('n_estimators', 100),
                'max_depth': parameters.get('max_depth', 6),
                'learning_rate': parameters.get('learning_rate', 0.1),
                'min_samples_split': parameters.get('min_samples_split', 20),
                'min_samples_leaf': parameters.get('min_samples_leaf', 10)
            }
            
            model.train(X_train, y_train, model_params)
            model.feature_columns = feature_columns
            
            return model
            
        except Exception as e:
            logger.error(f"Error training model for backtest: {e}")
            raise
    
    def _create_target_labels(self, data: pd.DataFrame) -> pd.Series:
        """ターゲットラベル作成"""
        try:
            # 未来の価格変動を計算
            future_periods = 5  # 5期間後の価格を参照
            
            price_change = (
                data['close'].shift(-future_periods) - data['close']
            ) / data['close'] * 100
            
            # しきい値設定
            buy_threshold = 0.1   # 0.1%以上の上昇
            sell_threshold = -0.1  # 0.1%以上の下降
            
            # ラベル作成
            target = np.where(
                price_change > buy_threshold, 1,  # BUY
                np.where(price_change < sell_threshold, 2, 0)  # SELL or HOLD
            )
            
            return pd.Series(target, index=data.index)
            
        except Exception as e:
            logger.error(f"Error creating target labels: {e}")
            return pd.Series(0, index=data.index)
    
    async def _simulate_trading(self,
                               price_data: pd.DataFrame,
                               features_data: pd.DataFrame,
                               model: LightGBMPredictor,
                               parameters: Dict[str, Any],
                               initial_balance: float) -> Tuple[List[Dict], List[Dict]]:
        """取引シミュレーション"""
        try:
            balance = initial_balance
            equity = initial_balance
            position = None
            trades = []
            equity_curve = []
            
            # パラメータ取得
            risk_per_trade = parameters.get('risk_per_trade', 2.0) / 100
            stop_loss_pips = parameters.get('stop_loss_pips', 50)
            take_profit_pips = parameters.get('take_profit_pips', 100)
            min_confidence = parameters.get('min_confidence', 0.7)
            use_nanpin = parameters.get('use_nanpin', False)
            nanpin_max_count = parameters.get('nanpin_max_count', 3)
            nanpin_interval_pips = parameters.get('nanpin_interval_pips', 10)
            
            # 手数料設定
            commission_per_lot = parameters.get('commission_per_lot', 500)  # 円
            spread_pips = parameters.get('spread_pips', 1)
            
            # 対象期間（学習期間後からテスト）
            split_point = int(len(features_data) * 0.8)
            test_features = features_data.iloc[split_point:]
            test_prices = price_data.iloc[split_point:]
            
            logger.info(f"Simulating trading on {len(test_features)} data points")
            
            for i, (timestamp, feature_row) in enumerate(test_features.iterrows()):
                if timestamp not in test_prices.index:
                    continue
                    
                price_row = test_prices.loc[timestamp]
                current_price = price_row['close']
                
                # 最初の100データポイントはスキップ（安定性のため）
                if i < 100:
                    equity_curve.append({
                        'timestamp': timestamp.isoformat(),
                        'equity': equity,
                        'balance': balance,
                        'unrealized_pnl': 0,
                        'position': None
                    })
                    continue
                
                # 予測実行
                try:
                    # 特徴量準備
                    features_input = feature_row[model.feature_columns].to_frame().T
                    
                    if hasattr(model, 'predict_with_confidence'):
                        predictions, confidence = model.predict_with_confidence(features_input)
                        signal = ['HOLD', 'BUY', 'SELL'][predictions[0]]
                        conf_score = confidence[0]
                    else:
                        predictions = model.predict(features_input)
                        signal = ['HOLD', 'BUY', 'SELL'][predictions[0]]
                        conf_score = 0.7  # デフォルト信頼度
                        
                except Exception as e:
                    logger.warning(f"Prediction failed at {timestamp}: {e}")
                    signal = 'HOLD'
                    conf_score = 0.0
                
                # 信頼度チェック
                if conf_score < min_confidence:
                    signal = 'HOLD'
                
                # ポジション管理
                if position is None:  # ポジションなし
                    if signal in ['BUY', 'SELL']:
                        position = await self._open_backtest_position(
                            signal, current_price, timestamp,
                            balance, risk_per_trade, stop_loss_pips,
                            take_profit_pips, commission_per_lot, spread_pips
                        )
                        
                else:  # ポジションあり
                    # エグジット条件チェック
                    exit_info = await self._check_exit_conditions(
                        position, current_price, timestamp, signal, price_row
                    )
                    
                    if exit_info['should_exit']:
                        # ポジション決済
                        trade_result = await self._close_backtest_position(
                            position, exit_info['exit_price'],
                            timestamp, exit_info['reason'], commission_per_lot
                        )
                        
                        trades.append(trade_result)
                        balance += trade_result['profit_loss']
                        position = None
                        
                    # ナンピンチェック
                    elif use_nanpin and position['nanpin_count'] < nanpin_max_count:
                        nanpin_executed = await self._check_and_execute_nanpin(
                            position, current_price, timestamp,
                            nanpin_interval_pips, commission_per_lot, spread_pips
                        )
                        if nanpin_executed:
                            position = nanpin_executed
                
                # エクイティ計算
                unrealized_pnl = 0
                if position:
                    unrealized_pnl = self._calculate_unrealized_pnl(position, current_price)
                    equity = balance + unrealized_pnl
                else:
                    equity = balance
                
                # エクイティカーブ記録
                equity_curve.append({
                    'timestamp': timestamp.isoformat(),
                    'equity': equity,
                    'balance': balance,
                    'unrealized_pnl': unrealized_pnl,
                    'position': position['type'] if position else None,
                    'price': current_price
                })
            
            # 最終ポジション決済
            if position:
                final_trade = await self._close_backtest_position(
                    position, current_price, timestamp, 'END_OF_TEST', commission_per_lot
                )
                trades.append(final_trade)
                balance += final_trade['profit_loss']
            
            logger.info(f"Simulation completed: {len(trades)} trades, final balance: {balance:.2f}")
            
            return trades, equity_curve
            
        except Exception as e:
            logger.error(f"Error in trading simulation: {e}")
            return [], []
    
    async def _open_backtest_position(self,
                                     order_type: str,
                                     entry_price: float,
                                     entry_time: datetime,
                                     balance: float,
                                     risk_per_trade: float,
                                     stop_loss_pips: int,
                                     take_profit_pips: int,
                                     commission_per_lot: float,
                                     spread_pips: int) -> Dict[str, Any]:
        """バックテスト用ポジションオープン"""
        try:
            # リスク金額計算
            risk_amount = balance * risk_per_trade
            
            # ロットサイズ計算（簡易版）
            pip_value = 1000  # 0.1ロットで1pip = 1000円（USDJPY想定）
            lot_size = risk_amount / (stop_loss_pips * pip_value)
            lot_size = max(0.01, min(lot_size, 10.0))  # 制限
            lot_size = round(lot_size, 2)
            
            # エントリー価格調整（スプレッド考慮）
            if order_type == 'BUY':
                adjusted_entry_price = entry_price + (spread_pips * 0.01)
                stop_loss = entry_price - (stop_loss_pips * 0.01)
                take_profit = entry_price + (take_profit_pips * 0.01)
            else:  # SELL
                adjusted_entry_price = entry_price - (spread_pips * 0.01)
                stop_loss = entry_price + (stop_loss_pips * 0.01)
                take_profit = entry_price - (take_profit_pips * 0.01)
            
            position = {
                'type': order_type,
                'entry_price': adjusted_entry_price,
                'original_entry_price': entry_price,
                'entry_time': entry_time,
                'lot_size': lot_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'nanpin_count': 0,
                'total_volume': lot_size,
                'commission_paid': commission_per_lot * lot_size
            }
            
            return position
            
        except Exception as e:
            logger.error(f"Error opening backtest position: {e}")
            return None
    
    async def _check_exit_conditions(self,
                                    position: Dict[str, Any],
                                    current_price: float,
                                    current_time: datetime,
                                    signal: str,
                                    price_row: pd.Series) -> Dict[str, Any]:
        """エグジット条件チェック"""
        try:
            # ストップロス・テイクプロフィットチェック
            if position['type'] == 'BUY':
                if price_row['low'] <= position['stop_loss']:
                    return {
                        'should_exit': True,
                        'exit_price': position['stop_loss'],
                        'reason': 'STOP_LOSS'
                    }
                elif price_row['high'] >= position['take_profit']:
                    return {
                        'should_exit': True,
                        'exit_price': position['take_profit'],
                        'reason': 'TAKE_PROFIT'
                    }
            else:  # SELL
                if price_row['high'] >= position['stop_loss']:
                    return {
                        'should_exit': True,
                        'exit_price': position['stop_loss'],
                        'reason': 'STOP_LOSS'
                    }
                elif price_row['low'] <= position['take_profit']:
                    return {
                        'should_exit': True,
                        'exit_price': position['take_profit'],
                        'reason': 'TAKE_PROFIT'
                    }
            
            # 反対シグナルでのエグジット
            if (position['type'] == 'BUY' and signal == 'SELL') or \
               (position['type'] == 'SELL' and signal == 'BUY'):
                return {
                    'should_exit': True,
                    'exit_price': current_price,
                    'reason': 'SIGNAL_REVERSAL'
                }
            
            return {'should_exit': False}
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return {'should_exit': False}
    
    async def _close_backtest_position(self,
                                      position: Dict[str, Any],
                                      exit_price: float,
                                      exit_time: datetime,
                                      exit_reason: str,
                                      commission_per_lot: float) -> Dict[str, Any]:
        """バックテスト用ポジションクローズ"""
        try:
            # 損益計算
            if position['type'] == 'BUY':
                price_diff = exit_price - position['entry_price']
            else:  # SELL
                price_diff = position['entry_price'] - exit_price
            
            # 円建て損益（USDJPY想定）
            profit_loss = price_diff * 100 * position['total_volume'] * 1000
            
            # 手数料差し引き
            total_commission = position['commission_paid'] + (commission_per_lot * position['total_volume'])
            profit_loss -= total_commission
            
            # 取引期間
            duration = (exit_time - position['entry_time']).total_seconds() / 3600  # 時間
            
            trade_result = {
                'entry_time': position['entry_time'].isoformat(),
                'exit_time': exit_time.isoformat(),
                'type': position['type'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'lot_size': position['total_volume'],
                'profit_loss': round(profit_loss, 2),
                'duration_hours': round(duration, 2),
                'exit_reason': exit_reason,
                'nanpin_count': position['nanpin_count'],
                'commission': total_commission
            }
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error closing backtest position: {e}")
            return {}
    
    async def _check_and_execute_nanpin(self,
                                       position: Dict[str, Any],
                                       current_price: float,
                                       current_time: datetime,
                                       nanpin_interval_pips: int,
                                       commission_per_lot: float,
                                       spread_pips: int) -> Optional[Dict[str, Any]]:
        """ナンピンチェックと実行"""
        try:
            # 価格差計算
            price_diff = abs(current_price - position['entry_price'])
            pip_diff = price_diff / 0.01
            
            # ナンピン条件チェック
            should_nanpin = False
            if position['type'] == 'BUY' and current_price < position['entry_price']:
                should_nanpin = pip_diff >= nanpin_interval_pips
            elif position['type'] == 'SELL' and current_price > position['entry_price']:
                should_nanpin = pip_diff >= nanpin_interval_pips
            
            if should_nanpin:
                # ナンピン実行
                additional_lot = position['lot_size']  # 同じロットサイズ
                
                # エントリー価格調整
                if position['type'] == 'BUY':
                    adjusted_price = current_price + (spread_pips * 0.01)
                else:
                    adjusted_price = current_price - (spread_pips * 0.01)
                
                # 平均価格計算
                total_volume = position['total_volume'] + additional_lot
                avg_price = (
                    (position['entry_price'] * position['total_volume'] +
                     adjusted_price * additional_lot) / total_volume
                )
                
                # ポジション更新
                position['entry_price'] = avg_price
                position['total_volume'] = total_volume
                position['nanpin_count'] += 1
                position['commission_paid'] += commission_per_lot * additional_lot
                
                logger.debug(f"Nanpin executed: count={position['nanpin_count']}, new avg price={avg_price:.3f}")
                
                return position
            
            return None
            
        except Exception as e:
            logger.error(f"Error in nanpin execution: {e}")
            return None
    
    def _calculate_unrealized_pnl(self, position: Dict[str, Any], current_price: float) -> float:
        """含み損益計算"""
        try:
            if position['type'] == 'BUY':
                price_diff = current_price - position['entry_price']
            else:  # SELL
                price_diff = position['entry_price'] - current_price
            
            # 円建て損益
            unrealized_pnl = price_diff * 100 * position['total_volume'] * 1000
            
            return round(unrealized_pnl, 2)
            
        except Exception as e:
            logger.error(f"Error calculating unrealized PnL: {e}")
            return 0.0
    
    def _calculate_statistics(self,
                             trades: List[Dict],
                             equity_curve: List[Dict],
                             initial_balance: float) -> Dict[str, Any]:
        """統計指標計算"""
        try:
            if not trades:
                return self._empty_statistics(initial_balance)
            
            # 基本統計
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['profit_loss'] > 0])
            losing_trades = len([t for t in trades if t['profit_loss'] < 0])
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # 損益計算
            profits = [t['profit_loss'] for t in trades if t['profit_loss'] > 0]
            losses = [t['profit_loss'] for t in trades if t['profit_loss'] < 0]
            
            total_profit = sum(profits) if profits else 0
            total_loss = abs(sum(losses)) if losses else 0
            net_profit = sum([t['profit_loss'] for t in trades])
            
            # プロフィットファクター
            profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
            
            # 平均損益
            avg_win = np.mean(profits) if profits else 0
            avg_loss = abs(np.mean(losses)) if losses else 0
            
            # 最大値
            largest_win = max(profits) if profits else 0
            largest_loss = abs(min(losses)) if losses else 0
            
            # 連続勝ち・負け
            consecutive_wins, consecutive_losses = self._calculate_consecutive_results(trades)
            
            # エクイティカーブ分析
            equity_values = [point['equity'] for point in equity_curve]
            
            # 最大ドローダウン
            max_drawdown, max_drawdown_percent = self._calculate_max_drawdown(equity_values)
            
            # リターン計算
            returns = self._calculate_returns(equity_values)
            
            # シャープレシオ
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            
            # ソルティノレシオ
            sortino_ratio = self._calculate_sortino_ratio(returns)
            
            # カルマーレシオ
            annual_return_percent = (equity_values[-1] / initial_balance - 1) * 100
            calmar_ratio = (annual_return_percent / max_drawdown_percent) if max_drawdown_percent > 0 else 0
            
            # 取引期間統計
            durations = [t['duration_hours'] for t in trades]
            avg_duration = np.mean(durations) if durations else 0
            
            # 手数料合計
            total_commission = sum([t.get('commission', 0) for t in trades])
            
            statistics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_profit': round(total_profit, 2),
                'total_loss': round(total_loss, 2),
                'net_profit': round(net_profit, 2),
                'profit_factor': round(profit_factor, 4),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'largest_win': round(largest_win, 2),
                'largest_loss': round(largest_loss, 2),
                'consecutive_wins': consecutive_wins,
                'consecutive_losses': consecutive_losses,
                'max_drawdown': round(max_drawdown, 2),
                'max_drawdown_percent': round(max_drawdown_percent, 2),
                'sharpe_ratio': round(sharpe_ratio, 4),
                'sortino_ratio': round(sortino_ratio, 4),
                'calmar_ratio': round(calmar_ratio, 4),
                'final_balance': round(equity_values[-1], 2),
                'return_percent': round(annual_return_percent, 2),
                'avg_duration_hours': round(avg_duration, 2),
                'total_commission': round(total_commission, 2)
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return self._empty_statistics(initial_balance)
    
    def _empty_statistics(self, initial_balance: float) -> Dict[str, Any]:
        """空の統計結果"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'total_loss': 0,
            'net_profit': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'max_drawdown': 0,
            'max_drawdown_percent': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'calmar_ratio': 0,
            'final_balance': initial_balance,
            'return_percent': 0,
            'avg_duration_hours': 0,
            'total_commission': 0
        }
    
    def _calculate_consecutive_results(self, trades: List[Dict]) -> Tuple[int, int]:
        """連続勝ち・負け計算"""
        try:
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            current_consecutive_wins = 0
            current_consecutive_losses = 0
            
            for trade in trades:
                if trade['profit_loss'] > 0:
                    current_consecutive_wins += 1
                    current_consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_consecutive_wins)
                else:
                    current_consecutive_losses += 1
                    current_consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
            
            return max_consecutive_wins, max_consecutive_losses
            
        except Exception as e:
            logger.error(f"Error calculating consecutive results: {e}")
            return 0, 0
    
    def _calculate_max_drawdown(self, equity_values: List[float]) -> Tuple[float, float]:
        """最大ドローダウン計算"""
        try:
            peak = equity_values[0]
            max_drawdown = 0
            max_drawdown_percent = 0
            
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                
                drawdown = peak - equity
                drawdown_percent = (drawdown / peak * 100) if peak > 0 else 0
                
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_percent = drawdown_percent
            
            return max_drawdown, max_drawdown_percent
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0, 0
    
    def _calculate_returns(self, equity_values: List[float]) -> np.ndarray:
        """リターン計算"""
        try:
            equity_series = pd.Series(equity_values)
            returns = equity_series.pct_change().dropna()
            return returns.values
            
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return np.array([])
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.001) -> float:
        """シャープレシオ計算"""
        try:
            if len(returns) == 0:
                return 0
            
            excess_returns = returns - risk_free_rate / 252  # 日次リスクフリーレート
            
            if np.std(excess_returns) == 0:
                return 0
            
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            return sharpe
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0
    
    def _calculate_sortino_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.001) -> float:
        """ソルティノレシオ計算"""
        try:
            if len(returns) == 0:
                return 0
            
            excess_returns = returns - risk_free_rate / 252
            negative_returns = excess_returns[excess_returns < 0]
            
            if len(negative_returns) == 0:
                return float('inf')
            
            downside_deviation = np.std(negative_returns)
            
            if downside_deviation == 0:
                return 0
            
            sortino = np.mean(excess_returns) / downside_deviation * np.sqrt(252)
            return sortino
            
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0
    
    async def _save_backtest_result(self,
                                   test_id: str,
                                   symbol: str,
                                   timeframe: str,
                                   start_date: datetime,
                                   end_date: datetime,
                                   initial_balance: float,
                                   statistics: Dict[str, Any],
                                   parameters: Dict[str, Any],
                                   equity_curve: List[Dict],
                                   trades: List[Dict]):
        """バックテスト結果保存"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # メイン結果保存
                    insert_query = """
                        INSERT INTO backtest_results 
                        (test_id, symbol, timeframe, period_start, period_end,
                         initial_balance, final_balance, total_trades, winning_trades,
                         win_rate, profit_factor, max_drawdown, sharpe_ratio,
                         parameters, statistics, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_query, (
                        test_id, symbol, timeframe, start_date, end_date,
                        initial_balance, statistics['final_balance'],
                        statistics['total_trades'], statistics['winning_trades'],
                        statistics['win_rate'], statistics['profit_factor'],
                        statistics['max_drawdown_percent'], statistics['sharpe_ratio'],
                        str(parameters), str(statistics), datetime.now()
                    ))
                    
                    # エクイティカーブ保存（サンプリング）
                    equity_sample = equity_curve[::max(1, len(equity_curve) // 1000)]  # 最大1000ポイント
                    for point in equity_sample:
                        cursor.execute("""
                            INSERT INTO backtest_equity_curves 
                            (test_id, timestamp, equity, balance, unrealized_pnl)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            test_id, point['timestamp'], point['equity'],
                            point['balance'], point.get('unrealized_pnl', 0)
                        ))
                    
                    # 取引履歴保存（最初の100件）
                    for trade in trades[:100]:
                        cursor.execute("""
                            INSERT INTO backtest_trades 
                            (test_id, entry_time, exit_time, type, entry_price, exit_price,
                             lot_size, profit_loss, duration_hours, exit_reason)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            test_id, trade['entry_time'], trade['exit_time'],
                            trade['type'], trade['entry_price'], trade['exit_price'],
                            trade['lot_size'], trade['profit_loss'],
                            trade['duration_hours'], trade['exit_reason']
                        ))
                    
                    conn.commit()
                    logger.info(f"Backtest result saved: {test_id}")
                    
        except Exception as e:
            logger.error(f"Error saving backtest result: {e}")
            raise

if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.append('.')
    
    logging.basicConfig(level=logging.INFO)
    
    print("Backtest engine test completed")