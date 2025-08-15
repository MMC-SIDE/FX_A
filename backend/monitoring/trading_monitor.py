"""
取引監視機能
取引状況、ポジション、リスク状況をリアルタイムで監視
"""
import asyncio
import MetaTrader5 as mt5
from datetime import datetime, timedelta, date
import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from ..websocket.websocket_manager import WebSocketManager
# from ..core.database import get_db
# from ..models.backtest_models import Trade, Position

logger = logging.getLogger(__name__)

class TradingMonitor:
    """取引監視クラス"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.monitoring_active = False
        
        # アラート閾値設定
        self.alert_thresholds = {
            'max_loss_per_trade': -10000,  # 1取引あたり最大損失（円）
            'max_daily_loss': -50000,      # 1日最大損失（円）
            'max_drawdown_percent': -20,   # 最大ドローダウン（%）
            'margin_level_warning': 200,   # 証拠金維持率警告レベル（%）
            'margin_level_danger': 100,    # 証拠金維持率危険レベル（%）
            'position_count_warning': 10   # ポジション数警告レベル
        }
        
        # 取引統計履歴
        self.trading_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # 前回の状態保存（変化検出用）
        self.last_positions_count = 0
        self.last_equity = 0.0
        self.last_margin_level = 0.0
        
    async def start_monitoring(self):
        """取引監視開始"""
        if self.monitoring_active:
            logger.warning("Trading monitoring is already active")
            return
            
        self.monitoring_active = True
        logger.info("Trading monitoring started")
        
        # バックグラウンドタスクとして実行
        asyncio.create_task(self._trading_status_monitor())
        asyncio.create_task(self._position_monitor())
        asyncio.create_task(self._risk_monitor())
        asyncio.create_task(self._performance_monitor())
    
    def stop_monitoring(self):
        """取引監視停止"""
        self.monitoring_active = False
        logger.info("Trading monitoring stopped")
    
    async def _trading_status_monitor(self):
        """取引状況監視"""
        while self.monitoring_active:
            try:
                # 今日の取引統計
                today_stats = await self._get_today_trading_stats()
                
                # リアルタイム損益
                current_pnl = await self._get_current_pnl()
                
                # 口座情報
                account_info = await self._get_account_info()
                
                # 取引統計送信
                trading_data = {
                    'today_stats': today_stats,
                    'current_pnl': current_pnl,
                    'account_info': account_info
                }
                
                # 履歴に追加
                self._add_to_history(trading_data)
                
                await self.websocket_manager.broadcast({
                    'type': 'trading_stats',
                    'data': trading_data
                })
                
                # 取引アラートチェック
                await self._check_trading_alerts(trading_data)
                
                # 5秒間隔
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Trading monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _position_monitor(self):
        """ポジション監視"""
        while self.monitoring_active:
            try:
                # 現在のポジション取得
                positions = await self._get_current_positions()
                
                # ポジション変化検出
                position_changes = self._detect_position_changes(positions)
                
                # ポジション状況送信
                await self.websocket_manager.broadcast({
                    'type': 'positions_update',
                    'data': {
                        'positions': positions,
                        'changes': position_changes,
                        'total_count': len(positions)
                    }
                })
                
                # ポジションアラートチェック
                await self._check_position_alerts(positions)
                
                # 前回の状態更新
                self.last_positions_count = len(positions)
                
                # 2秒間隔
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Position monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _risk_monitor(self):
        """リスク監視"""
        while self.monitoring_active:
            try:
                # リスク指標取得
                risk_metrics = await self._calculate_risk_metrics()
                
                # リスク状況送信
                await self.websocket_manager.broadcast({
                    'type': 'risk_metrics',
                    'data': risk_metrics
                })
                
                # リスクアラートチェック
                await self._check_risk_alerts(risk_metrics)
                
                # 30秒間隔
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Risk monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _performance_monitor(self):
        """パフォーマンス監視"""
        while self.monitoring_active:
            try:
                # パフォーマンス指標取得
                performance_metrics = await self._calculate_performance_metrics()
                
                # パフォーマンス状況送信
                await self.websocket_manager.broadcast({
                    'type': 'performance_metrics',
                    'data': performance_metrics
                })
                
                # 5分間隔
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _get_today_trading_stats(self) -> Dict[str, Any]:
        """
        本日の取引統計取得
        
        Returns:
            Dict[str, Any]: 本日の取引統計
        """
        try:
            db: Session = next(get_db())
            today = date.today()
            
            # 本日の完了取引取得
            trades = db.query(Trade).filter(
                Trade.entry_time >= today,
                Trade.exit_time.isnot(None),
                Trade.profit_loss.isnot(None)
            ).all()
            
            db.close()
            
            if not trades:
                return {
                    'date': today.isoformat(),
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'gross_profit': 0,
                    'gross_loss': 0,
                    'largest_win': 0,
                    'largest_loss': 0,
                    'average_win': 0,
                    'average_loss': 0,
                    'profit_factor': 0
                }
            
            # 統計計算
            winning_trades = [t for t in trades if t.profit_loss > 0]
            losing_trades = [t for t in trades if t.profit_loss < 0]
            
            total_pnl = sum(t.profit_loss for t in trades)
            gross_profit = sum(t.profit_loss for t in winning_trades)
            gross_loss = sum(t.profit_loss for t in losing_trades)
            
            return {
                'date': today.isoformat(),
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / len(trades)) * 100 if trades else 0,
                'total_pnl': total_pnl,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'largest_win': max((t.profit_loss for t in winning_trades), default=0),
                'largest_loss': min((t.profit_loss for t in losing_trades), default=0),
                'average_win': gross_profit / len(winning_trades) if winning_trades else 0,
                'average_loss': gross_loss / len(losing_trades) if losing_trades else 0,
                'profit_factor': abs(gross_profit / gross_loss) if gross_loss != 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get today's trading stats: {e}")
            return {
                'date': date.today().isoformat(),
                'error': str(e)
            }
    
    async def _get_current_pnl(self) -> Dict[str, Any]:
        """
        現在の損益取得
        
        Returns:
            Dict[str, Any]: 現在の損益情報
        """
        try:
            # MT5から現在のポジション取得
            positions = mt5.positions_get()
            if positions is None:
                return {
                    'total_profit': 0,
                    'unrealized_pnl': 0,
                    'position_count': 0
                }
            
            total_profit = sum(pos.profit for pos in positions)
            
            return {
                'total_profit': float(total_profit),
                'unrealized_pnl': float(total_profit),
                'position_count': len(positions),
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get current P&L: {e}")
            return {
                'total_profit': 0,
                'unrealized_pnl': 0,
                'position_count': 0,
                'error': str(e)
            }
    
    async def _get_account_info(self) -> Dict[str, Any]:
        """
        口座情報取得
        
        Returns:
            Dict[str, Any]: 口座情報
        """
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return {'error': 'Failed to get account info'}
            
            # エクイティの変化を検出
            current_equity = float(account_info.equity)
            equity_change = current_equity - self.last_equity if self.last_equity > 0 else 0
            
            # 証拠金維持率の変化を検出
            current_margin_level = float(account_info.margin_level) if account_info.margin_level else 0
            margin_level_change = current_margin_level - self.last_margin_level if self.last_margin_level > 0 else 0
            
            self.last_equity = current_equity
            self.last_margin_level = current_margin_level
            
            return {
                'login': account_info.login,
                'balance': float(account_info.balance),
                'equity': current_equity,
                'equity_change': equity_change,
                'margin': float(account_info.margin),
                'margin_free': float(account_info.margin_free),
                'margin_level': current_margin_level,
                'margin_level_change': margin_level_change,
                'profit': float(account_info.profit),
                'currency': account_info.currency,
                'server': account_info.server,
                'company': account_info.company,
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {'error': str(e)}
    
    async def _get_current_positions(self) -> List[Dict[str, Any]]:
        """
        現在のポジション取得
        
        Returns:
            List[Dict[str, Any]]: ポジションリスト
        """
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            position_list = []
            for pos in positions:
                # 現在価格取得
                symbol_info = mt5.symbol_info_tick(pos.symbol)
                current_price = symbol_info.bid if pos.type == mt5.ORDER_TYPE_BUY else symbol_info.ask
                
                position_list.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': float(pos.volume),
                    'open_price': float(pos.price_open),
                    'current_price': float(current_price),
                    'profit': float(pos.profit),
                    'swap': float(pos.swap),
                    'commission': float(pos.commission),
                    'open_time': datetime.fromtimestamp(pos.time).isoformat(),
                    'comment': pos.comment or '',
                    'magic': pos.magic,
                    'sl': float(pos.sl) if pos.sl else None,
                    'tp': float(pos.tp) if pos.tp else None
                })
            
            return position_list
            
        except Exception as e:
            logger.error(f"Failed to get current positions: {e}")
            return []
    
    def _detect_position_changes(self, current_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        ポジション変化検出
        
        Args:
            current_positions: 現在のポジションリスト
            
        Returns:
            Dict[str, Any]: 変化情報
        """
        current_count = len(current_positions)
        count_change = current_count - self.last_positions_count
        
        return {
            'count_change': count_change,
            'new_positions': count_change if count_change > 0 else 0,
            'closed_positions': abs(count_change) if count_change < 0 else 0,
            'detected_at': datetime.now().isoformat()
        }
    
    async def _calculate_risk_metrics(self) -> Dict[str, Any]:
        """
        リスク指標計算
        
        Returns:
            Dict[str, Any]: リスク指標
        """
        try:
            # 口座情報取得
            account_info = mt5.account_info()
            if not account_info:
                return {'error': 'Failed to get account info for risk calculation'}
            
            # 現在のポジション取得
            positions = mt5.positions_get()
            total_positions = len(positions) if positions else 0
            
            # 本日の損益取得
            today_stats = await self._get_today_trading_stats()
            today_pnl = today_stats.get('total_pnl', 0)
            
            # リスク指標計算
            balance = float(account_info.balance)
            equity = float(account_info.equity)
            margin_level = float(account_info.margin_level) if account_info.margin_level else 0
            
            # ドローダウン計算
            drawdown = ((balance - equity) / balance) * 100 if balance > 0 else 0
            
            # 1日のリスク率
            daily_risk_percent = (today_pnl / balance) * 100 if balance > 0 else 0
            
            return {
                'margin_level': margin_level,
                'margin_level_status': self._get_margin_level_status(margin_level),
                'current_drawdown_percent': drawdown,
                'daily_pnl': today_pnl,
                'daily_risk_percent': daily_risk_percent,
                'total_positions': total_positions,
                'balance': balance,
                'equity': equity,
                'margin_used': float(account_info.margin),
                'margin_free': float(account_info.margin_free),
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate risk metrics: {e}")
            return {'error': str(e)}
    
    def _get_margin_level_status(self, margin_level: float) -> str:
        """
        証拠金維持率ステータス取得
        
        Args:
            margin_level: 証拠金維持率
            
        Returns:
            str: ステータス（safe/warning/danger）
        """
        if margin_level >= self.alert_thresholds['margin_level_warning']:
            return 'safe'
        elif margin_level >= self.alert_thresholds['margin_level_danger']:
            return 'warning'
        else:
            return 'danger'
    
    async def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        パフォーマンス指標計算
        
        Returns:
            Dict[str, Any]: パフォーマンス指標
        """
        try:
            db: Session = next(get_db())
            
            # 過去30日の取引取得
            thirty_days_ago = datetime.now() - timedelta(days=30)
            trades = db.query(Trade).filter(
                Trade.entry_time >= thirty_days_ago,
                Trade.exit_time.isnot(None),
                Trade.profit_loss.isnot(None)
            ).all()
            
            db.close()
            
            if not trades:
                return {
                    'period': '30_days',
                    'total_trades': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'average_trade': 0
                }
            
            # パフォーマンス計算
            winning_trades = [t for t in trades if t.profit_loss > 0]
            losing_trades = [t for t in trades if t.profit_loss < 0]
            
            total_pnl = sum(t.profit_loss for t in trades)
            gross_profit = sum(t.profit_loss for t in winning_trades)
            gross_loss = sum(t.profit_loss for t in losing_trades)
            
            # 日別統計
            daily_stats = {}
            for trade in trades:
                trade_date = trade.entry_time.date()
                if trade_date not in daily_stats:
                    daily_stats[trade_date] = []
                daily_stats[trade_date].append(trade.profit_loss)
            
            daily_pnls = [sum(pnls) for pnls in daily_stats.values()]
            profitable_days = len([pnl for pnl in daily_pnls if pnl > 0])
            
            return {
                'period': '30_days',
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'win_rate': (len(winning_trades) / len(trades)) * 100,
                'total_pnl': total_pnl,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'profit_factor': abs(gross_profit / gross_loss) if gross_loss != 0 else 0,
                'average_trade': total_pnl / len(trades),
                'largest_win': max((t.profit_loss for t in winning_trades), default=0),
                'largest_loss': min((t.profit_loss for t in losing_trades), default=0),
                'trading_days': len(daily_stats),
                'profitable_days': profitable_days,
                'daily_win_rate': (profitable_days / len(daily_stats)) * 100 if daily_stats else 0,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
            return {'error': str(e)}
    
    async def _check_trading_alerts(self, trading_data: Dict[str, Any]):
        """
        取引アラートチェック
        
        Args:
            trading_data: 取引データ
        """
        alerts = []
        
        # 本日の損失チェック
        today_pnl = trading_data.get('today_stats', {}).get('total_pnl', 0)
        if today_pnl < self.alert_thresholds['max_daily_loss']:
            alerts.append({
                'level': 'error',
                'type': 'daily_loss_limit',
                'message': f"本日の損失が制限を超えました: {today_pnl:,.0f}円",
                'value': today_pnl,
                'threshold': self.alert_thresholds['max_daily_loss']
            })
        
        # 口座情報アラート
        account_info = trading_data.get('account_info', {})
        margin_level = account_info.get('margin_level', 0)
        
        if margin_level > 0 and margin_level < self.alert_thresholds['margin_level_danger']:
            alerts.append({
                'level': 'error',
                'type': 'margin_level_danger',
                'message': f"証拠金維持率が危険レベルです: {margin_level:.1f}%",
                'value': margin_level,
                'threshold': self.alert_thresholds['margin_level_danger']
            })
        elif margin_level > 0 and margin_level < self.alert_thresholds['margin_level_warning']:
            alerts.append({
                'level': 'warning',
                'type': 'margin_level_warning',
                'message': f"証拠金維持率が低下しています: {margin_level:.1f}%",
                'value': margin_level,
                'threshold': self.alert_thresholds['margin_level_warning']
            })
        
        if alerts:
            await self._send_trading_alerts(alerts)
    
    async def _check_position_alerts(self, positions: List[Dict[str, Any]]):
        """
        ポジションアラートチェック
        
        Args:
            positions: ポジションリスト
        """
        alerts = []
        
        # ポジション数チェック
        if len(positions) > self.alert_thresholds['position_count_warning']:
            alerts.append({
                'level': 'warning',
                'type': 'high_position_count',
                'message': f"ポジション数が多くなっています: {len(positions)}件",
                'value': len(positions),
                'threshold': self.alert_thresholds['position_count_warning']
            })
        
        # 大きな損失ポジションチェック
        for position in positions:
            profit = position.get('profit', 0)
            if profit < self.alert_thresholds['max_loss_per_trade']:
                alerts.append({
                    'level': 'warning',
                    'type': 'large_position_loss',
                    'message': f"大きな含み損: {profit:,.0f}円 ({position['symbol']})",
                    'value': profit,
                    'threshold': self.alert_thresholds['max_loss_per_trade'],
                    'position_ticket': position.get('ticket')
                })
        
        if alerts:
            await self._send_trading_alerts(alerts)
    
    async def _check_risk_alerts(self, risk_metrics: Dict[str, Any]):
        """
        リスクアラートチェック
        
        Args:
            risk_metrics: リスク指標
        """
        alerts = []
        
        # ドローダウンチェック
        drawdown = risk_metrics.get('current_drawdown_percent', 0)
        if drawdown < self.alert_thresholds['max_drawdown_percent']:
            alerts.append({
                'level': 'error',
                'type': 'high_drawdown',
                'message': f"ドローダウンが制限を超えました: {drawdown:.1f}%",
                'value': drawdown,
                'threshold': self.alert_thresholds['max_drawdown_percent']
            })
        
        if alerts:
            await self._send_trading_alerts(alerts)
    
    async def _send_trading_alerts(self, alerts: List[Dict[str, Any]]):
        """
        取引アラート送信
        
        Args:
            alerts: アラートリスト
        """
        timestamped_alerts = []
        for alert in alerts:
            timestamped_alerts.append({
                **alert,
                'timestamp': datetime.now().isoformat(),
                'id': f"{alert['type']}_{int(datetime.now().timestamp())}"
            })
        
        await self.websocket_manager.broadcast({
            'type': 'trading_alerts',
            'alerts': timestamped_alerts
        })
    
    def _add_to_history(self, trading_data: Dict[str, Any]):
        """
        取引データを履歴に追加
        
        Args:
            trading_data: 取引データ
        """
        timestamped_data = {
            **trading_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.trading_history.append(timestamped_data)
        
        # 履歴サイズ制限
        if len(self.trading_history) > self.max_history_size:
            self.trading_history = self.trading_history[-self.max_history_size:]
    
    def get_trading_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        取引履歴取得
        
        Args:
            limit: 取得件数制限
            
        Returns:
            List[Dict[str, Any]]: 取引履歴
        """
        if limit:
            return self.trading_history[-limit:]
        return self.trading_history.copy()
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        監視状態取得
        
        Returns:
            Dict[str, Any]: 監視状態
        """
        return {
            'monitoring_active': self.monitoring_active,
            'alert_thresholds': self.alert_thresholds,
            'trading_history_count': len(self.trading_history),
            'last_positions_count': self.last_positions_count,
            'last_equity': self.last_equity,
            'last_margin_level': self.last_margin_level
        }