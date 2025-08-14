"""
アラート通知管理システム
各種アラートの管理、通知、履歴保存を行う
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import uuid

from ..websocket.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """アラートレベル"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertType(Enum):
    """アラートタイプ"""
    SYSTEM = "system"
    TRADING = "trading"
    RISK = "risk"
    PERFORMANCE = "performance"
    CONNECTION = "connection"

class Alert:
    """アラートデータクラス"""
    
    def __init__(
        self,
        level: AlertLevel,
        alert_type: AlertType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        value: Optional[float] = None,
        threshold: Optional[float] = None,
        source: Optional[str] = None
    ):
        self.id = str(uuid.uuid4())
        self.level = level
        self.alert_type = alert_type
        self.message = message
        self.details = details or {}
        self.value = value
        self.threshold = threshold
        self.source = source or "system"
        self.timestamp = datetime.now()
        self.acknowledged = False
        self.acknowledged_by = None
        self.acknowledged_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'level': self.level.value,
            'type': self.alert_type.value,
            'message': self.message,
            'details': self.details,
            'value': self.value,
            'threshold': self.threshold,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }
    
    def acknowledge(self, acknowledged_by: str = "system"):
        """アラート確認済みにマーク"""
        self.acknowledged = True
        self.acknowledged_by = acknowledged_by
        self.acknowledged_at = datetime.now()

class AlertManager:
    """アラート管理クラス"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 5000
        
        # 重複チェック用（同じアラートの連続送信防止）
        self.recent_alerts: Dict[str, datetime] = {}
        self.duplicate_threshold_minutes = 5
        
        # 通知設定
        self.notification_settings = {
            'email_enabled': False,
            'email_smtp_server': 'smtp.gmail.com',
            'email_smtp_port': 587,
            'email_username': '',
            'email_password': '',
            'email_recipients': [],
            'webhook_enabled': False,
            'webhook_url': '',
            'desktop_notifications': True
        }
        
        # アラートハンドラー（カスタム処理用）
        self.alert_handlers: Dict[str, Callable] = {}
        
        # 統計情報
        self.stats = {
            'total_alerts': 0,
            'alerts_by_level': {level.value: 0 for level in AlertLevel},
            'alerts_by_type': {alert_type.value: 0 for alert_type in AlertType},
            'last_alert_time': None
        }
    
    async def send_alert(
        self,
        level: AlertLevel,
        alert_type: AlertType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        value: Optional[float] = None,
        threshold: Optional[float] = None,
        source: Optional[str] = None,
        suppress_duplicates: bool = True
    ) -> str:
        """
        アラート送信
        
        Args:
            level: アラートレベル
            alert_type: アラートタイプ
            message: アラートメッセージ
            details: 詳細情報
            value: 現在値
            threshold: 閾値
            source: 送信元
            suppress_duplicates: 重複抑制フラグ
            
        Returns:
            str: アラートID
        """
        try:
            # 重複チェック
            if suppress_duplicates and self._is_duplicate_alert(alert_type, message):
                logger.debug(f"Suppressing duplicate alert: {message}")
                return ""
            
            # アラート作成
            alert = Alert(
                level=level,
                alert_type=alert_type,
                message=message,
                details=details,
                value=value,
                threshold=threshold,
                source=source
            )
            
            # アクティブアラートに追加
            self.active_alerts[alert.id] = alert
            
            # 履歴に追加
            self.alert_history.append(alert)
            self._cleanup_history()
            
            # 統計更新
            self._update_stats(alert)
            
            # 重複チェック用に記録
            alert_key = f"{alert_type.value}:{message}"
            self.recent_alerts[alert_key] = datetime.now()
            
            # WebSocket通知
            await self._send_websocket_notification(alert)
            
            # その他の通知方法
            await self._send_notifications(alert)
            
            # カスタムハンドラー実行
            await self._execute_custom_handlers(alert)
            
            logger.info(f"Alert sent: {level.value} - {message}")
            return alert.id
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return ""
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "user") -> bool:
        """
        アラート確認
        
        Args:
            alert_id: アラートID
            acknowledged_by: 確認者
            
        Returns:
            bool: 確認成功フラグ
        """
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.acknowledge(acknowledged_by)
                
                # WebSocket通知
                await self.websocket_manager.broadcast({
                    'type': 'alert_acknowledged',
                    'data': {
                        'alert_id': alert_id,
                        'acknowledged_by': acknowledged_by,
                        'acknowledged_at': alert.acknowledged_at.isoformat()
                    }
                })
                
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    async def dismiss_alert(self, alert_id: str) -> bool:
        """
        アラート削除
        
        Args:
            alert_id: アラートID
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
                
                # WebSocket通知
                await self.websocket_manager.broadcast({
                    'type': 'alert_dismissed',
                    'data': {'alert_id': alert_id}
                })
                
                logger.info(f"Alert dismissed: {alert_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to dismiss alert: {e}")
            return False
    
    async def clear_all_alerts(self, alert_type: Optional[AlertType] = None) -> int:
        """
        全アラートクリア
        
        Args:
            alert_type: 特定のタイプのみクリア（Noneの場合は全て）
            
        Returns:
            int: クリアした件数
        """
        try:
            cleared_count = 0
            alerts_to_remove = []
            
            for alert_id, alert in self.active_alerts.items():
                if alert_type is None or alert.alert_type == alert_type:
                    alerts_to_remove.append(alert_id)
            
            for alert_id in alerts_to_remove:
                del self.active_alerts[alert_id]
                cleared_count += 1
            
            # WebSocket通知
            await self.websocket_manager.broadcast({
                'type': 'alerts_cleared',
                'data': {
                    'cleared_count': cleared_count,
                    'alert_type': alert_type.value if alert_type else 'all'
                }
            })
            
            logger.info(f"Cleared {cleared_count} alerts")
            return cleared_count
            
        except Exception as e:
            logger.error(f"Failed to clear alerts: {e}")
            return 0
    
    def get_active_alerts(
        self,
        level: Optional[AlertLevel] = None,
        alert_type: Optional[AlertType] = None,
        acknowledged: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        アクティブアラート取得
        
        Args:
            level: フィルタするレベル
            alert_type: フィルタするタイプ
            acknowledged: 確認済みフィルタ
            
        Returns:
            List[Dict[str, Any]]: アラートリスト
        """
        filtered_alerts = []
        
        for alert in self.active_alerts.values():
            # フィルタ条件チェック
            if level and alert.level != level:
                continue
            if alert_type and alert.alert_type != alert_type:
                continue
            if acknowledged is not None and alert.acknowledged != acknowledged:
                continue
            
            filtered_alerts.append(alert.to_dict())
        
        # タイムスタンプでソート（新しい順）
        filtered_alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        return filtered_alerts
    
    def get_alert_history(
        self,
        limit: int = 100,
        level: Optional[AlertLevel] = None,
        alert_type: Optional[AlertType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        アラート履歴取得
        
        Args:
            limit: 取得件数制限
            level: フィルタするレベル
            alert_type: フィルタするタイプ
            start_time: 開始時間
            end_time: 終了時間
            
        Returns:
            List[Dict[str, Any]]: アラート履歴
        """
        filtered_history = []
        
        for alert in reversed(self.alert_history):  # 新しい順
            # 時間範囲チェック
            if start_time and alert.timestamp < start_time:
                continue
            if end_time and alert.timestamp > end_time:
                continue
            
            # フィルタ条件チェック
            if level and alert.level != level:
                continue
            if alert_type and alert.alert_type != alert_type:
                continue
            
            filtered_history.append(alert.to_dict())
            
            # 件数制限
            if len(filtered_history) >= limit:
                break
        
        return filtered_history
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """
        アラート統計取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        return {
            **self.stats,
            'active_alerts_count': len(self.active_alerts),
            'unacknowledged_count': len([a for a in self.active_alerts.values() if not a.acknowledged]),
            'history_count': len(self.alert_history),
            'critical_alerts_count': len([a for a in self.active_alerts.values() if a.level == AlertLevel.CRITICAL]),
            'error_alerts_count': len([a for a in self.active_alerts.values() if a.level == AlertLevel.ERROR])
        }
    
    def register_alert_handler(self, name: str, handler: Callable[[Alert], None]):
        """
        カスタムアラートハンドラー登録
        
        Args:
            name: ハンドラー名
            handler: ハンドラー関数
        """
        self.alert_handlers[name] = handler
        logger.info(f"Alert handler registered: {name}")
    
    def update_notification_settings(self, settings: Dict[str, Any]):
        """
        通知設定更新
        
        Args:
            settings: 通知設定
        """
        self.notification_settings.update(settings)
        logger.info("Notification settings updated")
    
    async def _send_websocket_notification(self, alert: Alert):
        """WebSocket通知送信"""
        try:
            await self.websocket_manager.broadcast({
                'type': 'new_alert',
                'data': alert.to_dict()
            })
        except Exception as e:
            logger.error(f"Failed to send WebSocket alert notification: {e}")
    
    async def _send_notifications(self, alert: Alert):
        """各種通知送信"""
        try:
            # Eメール通知
            if self.notification_settings.get('email_enabled', False):
                await self._send_email_notification(alert)
            
            # Webhook通知
            if self.notification_settings.get('webhook_enabled', False):
                await self._send_webhook_notification(alert)
            
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")
    
    async def _send_email_notification(self, alert: Alert):
        """Eメール通知送信"""
        try:
            if not self.notification_settings.get('email_recipients'):
                return
            
            # メール内容作成
            subject = f"[FX Trading Alert] {alert.level.value.upper()}: {alert.message}"
            
            body = f"""
FX Trading System Alert

Level: {alert.level.value.upper()}
Type: {alert.alert_type.value}
Message: {alert.message}
Source: {alert.source}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

"""
            
            if alert.value is not None:
                body += f"Current Value: {alert.value}\n"
            if alert.threshold is not None:
                body += f"Threshold: {alert.threshold}\n"
            
            if alert.details:
                body += f"\nDetails:\n{json.dumps(alert.details, indent=2)}\n"
            
            # SMTP送信（非同期実行）
            asyncio.create_task(self._send_smtp_email(subject, body))
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_smtp_email(self, subject: str, body: str):
        """SMTP経由でメール送信"""
        try:
            settings = self.notification_settings
            
            msg = MIMEMultipart()
            msg['From'] = settings['email_username']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # SMTP送信
            server = smtplib.SMTP(settings['email_smtp_server'], settings['email_smtp_port'])
            server.starttls()
            server.login(settings['email_username'], settings['email_password'])
            
            for recipient in settings['email_recipients']:
                msg['To'] = recipient
                server.send_message(msg)
                del msg['To']
            
            server.quit()
            logger.info("Email notification sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send SMTP email: {e}")
    
    async def _send_webhook_notification(self, alert: Alert):
        """Webhook通知送信"""
        try:
            import aiohttp
            
            webhook_url = self.notification_settings.get('webhook_url')
            if not webhook_url:
                return
            
            payload = {
                'alert': alert.to_dict(),
                'system': 'fx_trading_system',
                'timestamp': datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Webhook notification sent successfully")
                    else:
                        logger.warning(f"Webhook notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
    
    async def _execute_custom_handlers(self, alert: Alert):
        """カスタムハンドラー実行"""
        try:
            for name, handler in self.alert_handlers.items():
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(alert)
                    else:
                        handler(alert)
                except Exception as e:
                    logger.error(f"Error in custom handler {name}: {e}")
        except Exception as e:
            logger.error(f"Failed to execute custom handlers: {e}")
    
    def _is_duplicate_alert(self, alert_type: AlertType, message: str) -> bool:
        """重複アラートチェック"""
        try:
            alert_key = f"{alert_type.value}:{message}"
            
            if alert_key in self.recent_alerts:
                last_time = self.recent_alerts[alert_key]
                time_diff = datetime.now() - last_time
                
                if time_diff.total_seconds() < (self.duplicate_threshold_minutes * 60):
                    return True
            
            # 古いエントリを削除
            cutoff_time = datetime.now() - timedelta(minutes=self.duplicate_threshold_minutes)
            keys_to_remove = [
                key for key, time in self.recent_alerts.items()
                if time < cutoff_time
            ]
            for key in keys_to_remove:
                del self.recent_alerts[key]
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check duplicate alert: {e}")
            return False
    
    def _update_stats(self, alert: Alert):
        """統計情報更新"""
        try:
            self.stats['total_alerts'] += 1
            self.stats['alerts_by_level'][alert.level.value] += 1
            self.stats['alerts_by_type'][alert.alert_type.value] += 1
            self.stats['last_alert_time'] = alert.timestamp.isoformat()
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
    
    def _cleanup_history(self):
        """履歴サイズ制限"""
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]

# グローバルインスタンス（使用時に初期化）
alert_manager: Optional[AlertManager] = None

def initialize_alert_manager(websocket_manager: WebSocketManager):
    """アラートマネージャー初期化"""
    global alert_manager
    alert_manager = AlertManager(websocket_manager)
    return alert_manager

def get_alert_manager() -> AlertManager:
    """アラートマネージャー取得"""
    if alert_manager is None:
        raise RuntimeError("Alert manager not initialized")
    return alert_manager