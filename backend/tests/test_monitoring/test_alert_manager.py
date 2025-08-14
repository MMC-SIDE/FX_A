"""
AlertManager単体テスト
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import asyncio

from backend.monitoring.alert_manager import AlertManager, Alert, AlertLevel, AlertType


class TestAlertManager:
    """AlertManagerのテストクラス"""

    @pytest.fixture
    def mock_websocket_manager(self):
        """WebSocketマネージャーのモック"""
        mock = Mock()
        mock.broadcast = AsyncMock(return_value=2)
        return mock

    @pytest.fixture
    def alert_manager(self, mock_websocket_manager):
        """AlertManagerインスタンス作成"""
        return AlertManager(mock_websocket_manager)

    def test_alert_creation(self):
        """アラート作成テスト"""
        alert = Alert(AlertLevel.ERROR, AlertType.SYSTEM, "Test error message")
        
        assert alert.level == AlertLevel.ERROR
        assert alert.alert_type == AlertType.SYSTEM
        assert alert.message == "Test error message"
        assert alert.id is not None
        assert isinstance(alert.created_at, datetime)
        assert alert.acknowledged is False
        assert alert.acknowledged_by is None
        assert alert.acknowledged_at is None

    @pytest.mark.asyncio
    async def test_send_alert_basic(self, alert_manager, mock_websocket_manager):
        """基本的なアラート送信テスト"""
        alert_id = await alert_manager.send_alert(
            AlertLevel.WARNING,
            AlertType.TRADING,
            "Test warning message"
        )
        
        assert alert_id is not None
        assert len(alert_manager.active_alerts) == 1
        mock_websocket_manager.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_with_data(self, alert_manager):
        """データ付きアラート送信テスト"""
        additional_data = {"cpu_usage": 95.5, "memory_usage": 89.2}
        
        alert_id = await alert_manager.send_alert(
            AlertLevel.CRITICAL,
            AlertType.SYSTEM,
            "High resource usage",
            data=additional_data
        )
        
        alert = alert_manager.active_alerts[alert_id]
        assert alert.data == additional_data

    @pytest.mark.asyncio
    async def test_duplicate_alert_suppression(self, alert_manager):
        """重複アラート抑制テスト"""
        # 同じメッセージで2回送信
        alert_id1 = await alert_manager.send_alert(
            AlertLevel.ERROR,
            AlertType.TRADING,
            "Connection lost"
        )
        
        alert_id2 = await alert_manager.send_alert(
            AlertLevel.ERROR,
            AlertType.TRADING,
            "Connection lost"
        )
        
        # 重複のため同じIDが返される
        assert alert_id1 == alert_id2
        assert len(alert_manager.active_alerts) == 1

    @pytest.mark.asyncio
    async def test_acknowledge_alert_success(self, alert_manager):
        """アラート確認成功テスト"""
        # アラート送信
        alert_id = await alert_manager.send_alert(
            AlertLevel.WARNING,
            AlertType.SYSTEM,
            "Test acknowledgement"
        )
        
        # アラート確認
        success = await alert_manager.acknowledge_alert(alert_id, "test_user")
        
        assert success is True
        alert = alert_manager.active_alerts[alert_id]
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "test_user"
        assert alert.acknowledged_at is not None

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, alert_manager):
        """存在しないアラート確認テスト"""
        success = await alert_manager.acknowledge_alert("nonexistent_id", "test_user")
        assert success is False

    @pytest.mark.asyncio
    async def test_dismiss_alert_success(self, alert_manager):
        """アラート削除成功テスト"""
        # アラート送信
        alert_id = await alert_manager.send_alert(
            AlertLevel.INFO,
            AlertType.TRADING,
            "Test dismissal"
        )
        
        # アラート削除
        success = await alert_manager.dismiss_alert(alert_id)
        
        assert success is True
        assert alert_id not in alert_manager.active_alerts

    @pytest.mark.asyncio
    async def test_dismiss_alert_not_found(self, alert_manager):
        """存在しないアラート削除テスト"""
        success = await alert_manager.dismiss_alert("nonexistent_id")
        assert success is False

    def test_get_active_alerts_all(self, alert_manager):
        """全アクティブアラート取得テスト"""
        # 複数のアラート作成
        alert1 = Alert(AlertLevel.INFO, AlertType.SYSTEM, "Info message")
        alert2 = Alert(AlertLevel.WARNING, AlertType.TRADING, "Warning message")
        alert3 = Alert(AlertLevel.ERROR, AlertType.RISK, "Error message")
        
        alert_manager.active_alerts[alert1.id] = alert1
        alert_manager.active_alerts[alert2.id] = alert2
        alert_manager.active_alerts[alert3.id] = alert3
        
        alerts = alert_manager.get_active_alerts()
        assert len(alerts) == 3

    def test_get_active_alerts_by_level(self, alert_manager):
        """レベル別アクティブアラート取得テスト"""
        # 異なるレベルのアラート作成
        alert1 = Alert(AlertLevel.INFO, AlertType.SYSTEM, "Info message")
        alert2 = Alert(AlertLevel.WARNING, AlertType.TRADING, "Warning message")
        alert3 = Alert(AlertLevel.ERROR, AlertType.RISK, "Error message")
        
        alert_manager.active_alerts[alert1.id] = alert1
        alert_manager.active_alerts[alert2.id] = alert2
        alert_manager.active_alerts[alert3.id] = alert3
        
        # ERRORレベルのみ取得
        error_alerts = alert_manager.get_active_alerts(level=AlertLevel.ERROR)
        assert len(error_alerts) == 1
        assert error_alerts[0].level == AlertLevel.ERROR

    def test_get_active_alerts_by_type(self, alert_manager):
        """タイプ別アクティブアラート取得テスト"""
        # 異なるタイプのアラート作成
        alert1 = Alert(AlertLevel.WARNING, AlertType.SYSTEM, "System warning")
        alert2 = Alert(AlertLevel.WARNING, AlertType.TRADING, "Trading warning")
        alert3 = Alert(AlertLevel.WARNING, AlertType.RISK, "Risk warning")
        
        alert_manager.active_alerts[alert1.id] = alert1
        alert_manager.active_alerts[alert2.id] = alert2
        alert_manager.active_alerts[alert3.id] = alert3
        
        # SYSTEMタイプのみ取得
        system_alerts = alert_manager.get_active_alerts(alert_type=AlertType.SYSTEM)
        assert len(system_alerts) == 1
        assert system_alerts[0].alert_type == AlertType.SYSTEM

    def test_get_active_alerts_acknowledged_filter(self, alert_manager):
        """確認済みフィルターでのアクティブアラート取得テスト"""
        # 確認済みと未確認のアラート作成
        alert1 = Alert(AlertLevel.WARNING, AlertType.SYSTEM, "Unacknowledged alert")
        alert2 = Alert(AlertLevel.WARNING, AlertType.TRADING, "Acknowledged alert")
        alert2.acknowledged = True
        alert2.acknowledged_by = "test_user"
        alert2.acknowledged_at = datetime.now()
        
        alert_manager.active_alerts[alert1.id] = alert1
        alert_manager.active_alerts[alert2.id] = alert2
        
        # 未確認のみ取得
        unack_alerts = alert_manager.get_active_alerts(acknowledged=False)
        assert len(unack_alerts) == 1
        assert unack_alerts[0].acknowledged is False
        
        # 確認済みのみ取得
        ack_alerts = alert_manager.get_active_alerts(acknowledged=True)
        assert len(ack_alerts) == 1
        assert ack_alerts[0].acknowledged is True

    def test_get_alert_stats(self, alert_manager):
        """アラート統計取得テスト"""
        # 複数のアラート作成
        alert1 = Alert(AlertLevel.INFO, AlertType.SYSTEM, "Info alert")
        alert2 = Alert(AlertLevel.WARNING, AlertType.TRADING, "Warning alert")
        alert3 = Alert(AlertLevel.ERROR, AlertType.RISK, "Error alert")
        alert3.acknowledged = True
        
        alert_manager.active_alerts[alert1.id] = alert1
        alert_manager.active_alerts[alert2.id] = alert2
        alert_manager.active_alerts[alert3.id] = alert3
        
        stats = alert_manager.get_alert_stats()
        
        assert stats['total_alerts'] == 3
        assert stats['active_alerts_count'] == 3
        assert stats['unacknowledged_count'] == 2
        assert stats['by_level']['INFO'] == 1
        assert stats['by_level']['WARNING'] == 1
        assert stats['by_level']['ERROR'] == 1

    def test_get_alert_history_empty(self, alert_manager):
        """空のアラート履歴取得テスト"""
        history = alert_manager.get_alert_history()
        assert len(history) == 0

    def test_get_alert_history_with_data(self, alert_manager):
        """データありのアラート履歴取得テスト"""
        # 履歴用のアラート作成
        alert1 = Alert(AlertLevel.INFO, AlertType.SYSTEM, "Historical alert 1")
        alert1.created_at = datetime.now() - timedelta(hours=2)
        
        alert2 = Alert(AlertLevel.WARNING, AlertType.TRADING, "Historical alert 2")
        alert2.created_at = datetime.now() - timedelta(hours=1)
        
        alert_manager.alert_history.extend([alert1, alert2])
        
        history = alert_manager.get_alert_history()
        assert len(history) == 2
        
        # 時間順にソートされていることを確認
        assert history[0].created_at > history[1].created_at

    def test_get_alert_history_with_limit(self, alert_manager):
        """制限付きアラート履歴取得テスト"""
        # 複数の履歴アラート作成
        for i in range(10):
            alert = Alert(AlertLevel.INFO, AlertType.SYSTEM, f"Alert {i}")
            alert.created_at = datetime.now() - timedelta(hours=i)
            alert_manager.alert_history.append(alert)
        
        # 制限付きで取得
        history = alert_manager.get_alert_history(limit=5)
        assert len(history) == 5

    def test_get_alert_history_with_filters(self, alert_manager):
        """フィルター付きアラート履歴取得テスト"""
        # 異なるレベルの履歴アラート作成
        alert1 = Alert(AlertLevel.ERROR, AlertType.SYSTEM, "Error alert")
        alert2 = Alert(AlertLevel.WARNING, AlertType.TRADING, "Warning alert")
        
        alert_manager.alert_history.extend([alert1, alert2])
        
        # ERRORレベルのみ取得
        error_history = alert_manager.get_alert_history(level=AlertLevel.ERROR)
        assert len(error_history) == 1
        assert error_history[0].level == AlertLevel.ERROR

    @pytest.mark.asyncio
    async def test_clear_all_alerts(self, alert_manager):
        """全アラートクリアテスト"""
        # 複数のアラート作成
        await alert_manager.send_alert(AlertLevel.INFO, AlertType.SYSTEM, "Alert 1")
        await alert_manager.send_alert(AlertLevel.WARNING, AlertType.TRADING, "Alert 2")
        await alert_manager.send_alert(AlertLevel.ERROR, AlertType.RISK, "Alert 3")
        
        assert len(alert_manager.active_alerts) == 3
        
        # 全クリア
        await alert_manager.clear_all_alerts()
        
        assert len(alert_manager.active_alerts) == 0

    @pytest.mark.asyncio
    async def test_clear_alerts_by_type(self, alert_manager):
        """タイプ別アラートクリアテスト"""
        # 異なるタイプのアラート作成
        await alert_manager.send_alert(AlertLevel.WARNING, AlertType.SYSTEM, "System alert")
        await alert_manager.send_alert(AlertLevel.WARNING, AlertType.TRADING, "Trading alert")
        await alert_manager.send_alert(AlertLevel.WARNING, AlertType.RISK, "Risk alert")
        
        assert len(alert_manager.active_alerts) == 3
        
        # SYSTEMタイプのみクリア
        await alert_manager.clear_all_alerts(AlertType.SYSTEM)
        
        assert len(alert_manager.active_alerts) == 2
        remaining_types = [alert.alert_type for alert in alert_manager.active_alerts.values()]
        assert AlertType.SYSTEM not in remaining_types

    @pytest.mark.asyncio
    async def test_cleanup_old_alerts(self, alert_manager):
        """古いアラートクリーンアップテスト"""
        # 古いアラート作成
        old_alert = Alert(AlertLevel.INFO, AlertType.SYSTEM, "Old alert")
        old_alert.created_at = datetime.now() - timedelta(days=2)
        alert_manager.active_alerts[old_alert.id] = old_alert
        
        # 新しいアラート作成
        await alert_manager.send_alert(AlertLevel.INFO, AlertType.SYSTEM, "New alert")
        
        assert len(alert_manager.active_alerts) == 2
        
        # クリーンアップ実行（1日以上古いアラートを削除）
        await alert_manager.cleanup_old_alerts(max_age_hours=24)
        
        assert len(alert_manager.active_alerts) == 1
        # 新しいアラートのみ残っている
        remaining_alert = next(iter(alert_manager.active_alerts.values()))
        assert remaining_alert.message == "New alert"

    def test_alert_to_dict(self):
        """アラート辞書変換テスト"""
        alert = Alert(AlertLevel.WARNING, AlertType.TRADING, "Test message")
        alert.acknowledged = True
        alert.acknowledged_by = "test_user"
        alert.acknowledged_at = datetime.now()
        alert.data = {"key": "value"}
        
        alert_dict = alert.to_dict()
        
        assert alert_dict['id'] == alert.id
        assert alert_dict['level'] == "WARNING"
        assert alert_dict['alert_type'] == "TRADING"
        assert alert_dict['message'] == "Test message"
        assert alert_dict['acknowledged'] is True
        assert alert_dict['acknowledged_by'] == "test_user"
        assert alert_dict['data'] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_email_notification(self, alert_manager):
        """メール通知テスト"""
        # メール設定を有効にする
        alert_manager.email_notifications = True
        alert_manager.smtp_config = {
            'host': 'localhost',
            'port': 587,
            'username': 'test@example.com',
            'password': 'password',
            'recipients': ['admin@example.com']
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            await alert_manager.send_alert(
                AlertLevel.CRITICAL,
                AlertType.SYSTEM,
                "Critical system error"
            )
            
            # メール送信が試行されたことを確認
            mock_smtp.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_notification(self, alert_manager):
        """Webhook通知テスト"""
        # Webhook設定を有効にする
        alert_manager.webhook_notifications = True
        alert_manager.webhook_config = {
            'url': 'https://example.com/webhook',
            'headers': {'Content-Type': 'application/json'}
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            
            await alert_manager.send_alert(
                AlertLevel.ERROR,
                AlertType.TRADING,
                "Trading error occurred"
            )
            
            # Webhook送信が試行されたことを確認
            mock_post.assert_called_once()