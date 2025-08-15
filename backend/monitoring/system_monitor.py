"""
システム監視機能
リソース使用状況、MT5接続状態、データベース接続等を監視
"""
import psutil
import asyncio
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..websocket.websocket_manager import WebSocketManager
# from ..core.database import get_db

logger = logging.getLogger(__name__)

class SystemMonitor:
    """システム監視クラス"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.monitoring_active = False
        self.start_time = datetime.now()
        
        # アラート閾値設定
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'connection_errors': 5,
            'response_time_ms': 5000
        }
        
        # 監視履歴
        self.metrics_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
    async def start_monitoring(self):
        """監視開始"""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
            
        self.monitoring_active = True
        self.start_time = datetime.now()
        logger.info("System monitoring started")
        
        # バックグラウンドタスクとして監視実行
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._mt5_connection_monitor())
        asyncio.create_task(self._database_monitor())
        asyncio.create_task(self._performance_monitor())
        asyncio.create_task(self._heartbeat_monitor())
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring_active = False
        logger.info("System monitoring stopped")
    
    async def _monitoring_loop(self):
        """メイン監視ループ（システムリソース）"""
        while self.monitoring_active:
            try:
                # システムリソース取得
                system_stats = self._get_system_stats()
                
                # 履歴に追加
                self._add_to_history(system_stats)
                
                # WebSocketで送信
                await self.websocket_manager.broadcast({
                    'type': 'system_stats',
                    'data': system_stats
                })
                
                # アラートチェック
                await self._check_system_alerts(system_stats)
                
                # 30秒間隔
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"System monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _mt5_connection_monitor(self):
        """MT5接続監視"""
        last_error_count = 0
        
        while self.monitoring_active:
            try:
                # MT5接続状態チェック
                mt5_status = await self._check_mt5_connection()
                
                await self.websocket_manager.broadcast({
                    'type': 'mt5_status',
                    'data': mt5_status
                })
                
                # 接続エラー時のアラート
                if not mt5_status.get('connected', False):
                    await self._send_alert({
                        'level': 'error',
                        'type': 'mt5_disconnected',
                        'message': 'MT5との接続が切断されました',
                        'details': mt5_status.get('error', 'Unknown error')
                    })
                
                # エラー回数が増加している場合
                current_error_count = mt5_status.get('error_count', 0)
                if current_error_count > last_error_count:
                    await self._send_alert({
                        'level': 'warning',
                        'type': 'mt5_errors_increasing',
                        'message': f'MT5接続エラーが増加しています: {current_error_count}回',
                        'value': current_error_count
                    })
                
                last_error_count = current_error_count
                
                # 10秒間隔
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"MT5 monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _database_monitor(self):
        """データベース接続監視"""
        while self.monitoring_active:
            try:
                # データベース接続状態チェック
                db_status = await self._check_database_connection()
                
                await self.websocket_manager.broadcast({
                    'type': 'database_status',
                    'data': db_status
                })
                
                # 接続エラー時のアラート
                if not db_status.get('connected', False):
                    await self._send_alert({
                        'level': 'error',
                        'type': 'database_disconnected',
                        'message': 'データベースとの接続が切断されました',
                        'details': db_status.get('error', 'Unknown error')
                    })
                
                # レスポンス時間が遅い場合
                response_time = db_status.get('response_time_ms', 0)
                if response_time > self.alert_thresholds['response_time_ms']:
                    await self._send_alert({
                        'level': 'warning',
                        'type': 'database_slow_response',
                        'message': f'データベースのレスポンスが遅いです: {response_time:.0f}ms',
                        'value': response_time
                    })
                
                # 60秒間隔
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Database monitoring error: {e}")
                await asyncio.sleep(120)
    
    async def _performance_monitor(self):
        """パフォーマンス監視"""
        while self.monitoring_active:
            try:
                # パフォーマンス統計取得
                perf_stats = await self._get_performance_stats()
                
                await self.websocket_manager.broadcast({
                    'type': 'performance_stats',
                    'data': perf_stats
                })
                
                # 5分間隔
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _heartbeat_monitor(self):
        """ハートビート監視"""
        while self.monitoring_active:
            try:
                # WebSocketハートビート送信
                await self.websocket_manager.heartbeat_check()
                
                # 60秒間隔
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Heartbeat monitoring error: {e}")
                await asyncio.sleep(60)
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """
        システム統計取得
        
        Returns:
            Dict[str, Any]: システム統計データ
        """
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # ネットワーク統計
            network = psutil.net_io_counters()
            
            # プロセス統計
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # システム稼働時間
            uptime = datetime.now() - self.start_time
            
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': uptime.total_seconds(),
                'uptime_human': str(uptime),
                
                # CPU統計
                'cpu_percent': round(cpu_percent, 2),
                'cpu_count': cpu_count,
                
                # メモリ統計
                'memory_percent': round(memory_percent, 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                
                # ディスク統計
                'disk_percent': round(disk_percent, 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_used_gb': round(disk.used / (1024**3), 2),
                
                # ネットワーク統計
                'network_sent_mb': round(network.bytes_sent / (1024**2), 2),
                'network_recv_mb': round(network.bytes_recv / (1024**2), 2),
                'network_packets_sent': network.packets_sent,
                'network_packets_recv': network.packets_recv,
                
                # プロセス統計
                'process_memory_mb': round(process_memory.rss / (1024**2), 2),
                'process_memory_vms_mb': round(process_memory.vms / (1024**2), 2),
                
                # WebSocket接続数
                'websocket_connections': self.websocket_manager.get_connection_count()
            }
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def _check_mt5_connection(self) -> Dict[str, Any]:
        """
        MT5接続状態チェック
        
        Returns:
            Dict[str, Any]: MT5接続状態
        """
        try:
            # MT5初期化状態チェック
            if not mt5.initialize():
                last_error = mt5.last_error()
                return {
                    'connected': False,
                    'error': f'MT5 initialization failed: {last_error}',
                    'error_code': last_error[0] if last_error else None
                }
            
            # ターミナル情報取得
            terminal_info = mt5.terminal_info()
            account_info = mt5.account_info()
            
            if terminal_info is None or account_info is None:
                return {
                    'connected': False,
                    'error': 'Failed to get MT5 terminal or account info'
                }
            
            return {
                'connected': True,
                'terminal_name': terminal_info.name,
                'terminal_build': terminal_info.build,
                'terminal_path': terminal_info.path,
                'account_number': account_info.login,
                'account_name': account_info.name,
                'server': account_info.server,
                'currency': account_info.currency,
                'balance': float(account_info.balance),
                'equity': float(account_info.equity),
                'margin': float(account_info.margin),
                'margin_free': float(account_info.margin_free),
                'margin_level': float(account_info.margin_level) if account_info.margin_level else 0,
                'profit': float(account_info.profit),
                'company': account_info.company,
                'connected_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"MT5 connection check failed: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    async def _check_database_connection(self) -> Dict[str, Any]:
        """
        データベース接続状態チェック
        
        Returns:
            Dict[str, Any]: データベース接続状態
        """
        try:
            start_time = datetime.now()
            
            # データベース接続テスト
            db: Session = next(get_db())
            
            # 簡単なクエリ実行
            result = db.execute(text("SELECT 1 as test"))
            test_result = result.fetchone()
            
            # レスポンス時間計算
            response_time = (datetime.now() - start_time).total_milliseconds()
            
            # 接続プール統計取得（可能であれば）
            pool_stats = {}
            try:
                if hasattr(db.bind, 'pool'):
                    pool = db.bind.pool
                    pool_stats = {
                        'size': pool.size(),
                        'checked_in': pool.checkedin(),
                        'checked_out': pool.checkedout(),
                        'overflow': pool.overflow(),
                        'invalidated': pool.invalidated()
                    }
            except Exception:
                pass
            
            db.close()
            
            return {
                'connected': True,
                'response_time_ms': response_time,
                'test_query_result': test_result[0] if test_result else None,
                'pool_stats': pool_stats,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return {
                'connected': False,
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }
    
    async def _get_performance_stats(self) -> Dict[str, Any]:
        """
        パフォーマンス統計取得
        
        Returns:
            Dict[str, Any]: パフォーマンス統計
        """
        try:
            # 直近の統計から計算
            recent_stats = self.metrics_history[-10:] if len(self.metrics_history) >= 10 else self.metrics_history
            
            if not recent_stats:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'message': 'Not enough data for performance analysis'
                }
            
            # 平均値計算
            avg_cpu = sum(stat.get('cpu_percent', 0) for stat in recent_stats) / len(recent_stats)
            avg_memory = sum(stat.get('memory_percent', 0) for stat in recent_stats) / len(recent_stats)
            
            # 最大値計算
            max_cpu = max(stat.get('cpu_percent', 0) for stat in recent_stats)
            max_memory = max(stat.get('memory_percent', 0) for stat in recent_stats)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'period_minutes': 10,
                'sample_count': len(recent_stats),
                'cpu_avg': round(avg_cpu, 2),
                'cpu_max': round(max_cpu, 2),
                'memory_avg': round(avg_memory, 2),
                'memory_max': round(max_memory, 2),
                'websocket_connections': self.websocket_manager.get_connection_count()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def _check_system_alerts(self, stats: Dict[str, Any]):
        """
        システムアラートチェック
        
        Args:
            stats: システム統計データ
        """
        alerts = []
        
        # CPU使用率チェック
        cpu_percent = stats.get('cpu_percent', 0)
        if cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'level': 'warning' if cpu_percent < 95 else 'error',
                'type': 'high_cpu',
                'message': f"CPU使用率が高いです: {cpu_percent:.1f}%",
                'value': cpu_percent,
                'threshold': self.alert_thresholds['cpu_percent']
            })
        
        # メモリ使用率チェック
        memory_percent = stats.get('memory_percent', 0)
        if memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                'level': 'warning' if memory_percent < 95 else 'error',
                'type': 'high_memory',
                'message': f"メモリ使用率が高いです: {memory_percent:.1f}%",
                'value': memory_percent,
                'threshold': self.alert_thresholds['memory_percent']
            })
        
        # ディスク使用率チェック
        disk_percent = stats.get('disk_percent', 0)
        if disk_percent > self.alert_thresholds['disk_percent']:
            alerts.append({
                'level': 'error',
                'type': 'high_disk',
                'message': f"ディスク使用率が高いです: {disk_percent:.1f}%",
                'value': disk_percent,
                'threshold': self.alert_thresholds['disk_percent']
            })
        
        # アラートがあれば送信
        if alerts:
            await self._send_alert_batch(alerts)
    
    async def _send_alert(self, alert: Dict[str, Any]):
        """
        単一アラート送信
        
        Args:
            alert: アラートデータ
        """
        await self.websocket_manager.broadcast({
            'type': 'system_alert',
            'alert': {
                **alert,
                'timestamp': datetime.now().isoformat(),
                'id': f"{alert['type']}_{int(datetime.now().timestamp())}"
            }
        })
    
    async def _send_alert_batch(self, alerts: List[Dict[str, Any]]):
        """
        複数アラート一括送信
        
        Args:
            alerts: アラートデータリスト
        """
        timestamped_alerts = []
        for alert in alerts:
            timestamped_alerts.append({
                **alert,
                'timestamp': datetime.now().isoformat(),
                'id': f"{alert['type']}_{int(datetime.now().timestamp())}"
            })
        
        await self.websocket_manager.broadcast({
            'type': 'system_alerts',
            'alerts': timestamped_alerts
        })
    
    def _add_to_history(self, stats: Dict[str, Any]):
        """
        統計データを履歴に追加
        
        Args:
            stats: 統計データ
        """
        self.metrics_history.append(stats)
        
        # 履歴サイズ制限
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def get_metrics_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        統計履歴取得
        
        Args:
            limit: 取得件数制限
            
        Returns:
            List[Dict[str, Any]]: 統計履歴
        """
        if limit:
            return self.metrics_history[-limit:]
        return self.metrics_history.copy()
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        監視状態取得
        
        Returns:
            Dict[str, Any]: 監視状態
        """
        return {
            'monitoring_active': self.monitoring_active,
            'start_time': self.start_time.isoformat(),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'metrics_history_count': len(self.metrics_history),
            'alert_thresholds': self.alert_thresholds,
            'websocket_connections': self.websocket_manager.get_connection_count()
        }