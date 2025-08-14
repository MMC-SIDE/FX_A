"""
Trading API統合テスト
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime

from backend.models.backtest_models import Trade, Position


class TestTradingAPI:
    """Trading APIの統合テストクラス"""

    def test_start_trading_success(self, client, mock_mt5_client, db_session):
        """取引開始API成功テスト"""
        # MT5クライアントの接続状態を設定
        mock_mt5_client.is_connected.return_value = True
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            response = client.post("/api/v1/trading/start", json={
                "symbol": "USDJPY",
                "timeframe": "H1"
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "message" in data

    def test_start_trading_mt5_not_connected(self, client, mock_mt5_client):
        """MT5未接続での取引開始テスト"""
        mock_mt5_client.is_connected.return_value = False
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            response = client.post("/api/v1/trading/start", json={
                "symbol": "USDJPY",
                "timeframe": "H1"
            })
        
        assert response.status_code == 400
        data = response.json()
        assert "not connected" in data["detail"]

    def test_start_trading_already_running(self, client, mock_mt5_client):
        """既に稼働中での取引開始テスト"""
        mock_mt5_client.is_connected.return_value = True
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            with patch('backend.api.trading.trading_engine') as mock_engine:
                mock_engine.is_running = True
                
                response = client.post("/api/v1/trading/start", json={
                    "symbol": "USDJPY",
                    "timeframe": "H1"
                })
        
        assert response.status_code == 400
        data = response.json()
        assert "already running" in data["detail"]

    def test_stop_trading_success(self, client):
        """取引停止API成功テスト"""
        with patch('backend.api.trading.trading_engine') as mock_engine:
            mock_engine.is_running = True
            mock_engine.stop_trading.return_value = None
            
            response = client.post("/api/v1/trading/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    def test_stop_trading_not_running(self, client):
        """未稼働時の取引停止テスト"""
        with patch('backend.api.trading.trading_engine') as mock_engine:
            mock_engine.is_running = False
            
            response = client.post("/api/v1/trading/stop")
        
        assert response.status_code == 400
        data = response.json()
        assert "not running" in data["detail"]

    def test_get_trading_status(self, client):
        """取引状態取得APIテスト"""
        mock_status = {
            "is_running": True,
            "symbol": "USDJPY",
            "timeframe": "H1",
            "last_signal": "BUY",
            "last_confidence": 0.85,
            "last_update": datetime.now().isoformat()
        }
        
        with patch('backend.api.trading.trading_engine') as mock_engine:
            mock_engine.get_status.return_value = mock_status
            
            response = client.get("/api/v1/trading/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_running"] is True
        assert data["symbol"] == "USDJPY"
        assert data["last_signal"] == "BUY"

    def test_get_positions_success(self, client, db_session, sample_trades):
        """ポジション取得API成功テスト"""
        # テストデータ作成（オープンポジション）
        open_trade = Trade(
            symbol="USDJPY",
            order_type="BUY",
            entry_time=datetime.now(),
            entry_price=130.00,
            volume=0.1,
            exit_time=None,  # まだ決済されていない
            exit_price=None,
            profit_loss=None
        )
        db_session.add(open_trade)
        db_session.commit()
        
        response = client.get("/api/v1/positions")
        
        assert response.status_code == 200
        positions = response.json()
        assert isinstance(positions, list)
        assert len(positions) >= 1

    def test_get_positions_empty(self, client, db_session):
        """ポジションなしでの取得テスト"""
        response = client.get("/api/v1/positions")
        
        assert response.status_code == 200
        positions = response.json()
        assert isinstance(positions, list)
        assert len(positions) == 0

    def test_close_position_success(self, client, db_session, mock_mt5_client):
        """ポジション決済API成功テスト"""
        # テストポジション作成
        test_trade = Trade(
            symbol="USDJPY",
            order_type="BUY",
            entry_time=datetime.now(),
            entry_price=130.00,
            volume=0.1
        )
        db_session.add(test_trade)
        db_session.commit()
        
        # MT5決済成功をモック
        mock_mt5_client.close_position.return_value = {
            "success": True,
            "message": "Position closed successfully"
        }
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            response = client.post(f"/api/v1/positions/{test_trade.id}/close")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_close_position_not_found(self, client):
        """存在しないポジション決済テスト"""
        response = client.post("/api/v1/positions/999999/close")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_close_position_mt5_failure(self, client, db_session, mock_mt5_client):
        """MT5決済失敗テスト"""
        # テストポジション作成
        test_trade = Trade(
            symbol="USDJPY",
            order_type="BUY",
            entry_time=datetime.now(),
            entry_price=130.00,
            volume=0.1
        )
        db_session.add(test_trade)
        db_session.commit()
        
        # MT5決済失敗をモック
        mock_mt5_client.close_position.return_value = {
            "success": False,
            "message": "Failed to close position"
        }
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            response = client.post(f"/api/v1/positions/{test_trade.id}/close")
        
        assert response.status_code == 400
        data = response.json()
        assert "Failed to close" in data["detail"]

    def test_get_trade_history(self, client, db_session, sample_trades):
        """取引履歴取得APIテスト"""
        response = client.get("/api/v1/trades")
        
        assert response.status_code == 200
        trades = response.json()
        assert isinstance(trades, list)
        assert len(trades) == len(sample_trades)

    def test_get_trade_history_with_filters(self, client, db_session, sample_trades):
        """フィルター付き取引履歴取得テスト"""
        # 特定のシンボルのみを取得
        response = client.get("/api/v1/trades?symbol=USDJPY")
        
        assert response.status_code == 200
        trades = response.json()
        assert isinstance(trades, list)
        # 全ての取引がUSDJPYであることを確認
        for trade in trades:
            assert trade["symbol"] == "USDJPY"

    def test_get_trade_history_with_pagination(self, client, db_session, sample_trades):
        """ページネーション付き取引履歴取得テスト"""
        response = client.get("/api/v1/trades?limit=5&offset=0")
        
        assert response.status_code == 200
        trades = response.json()
        assert isinstance(trades, list)
        assert len(trades) <= 5

    def test_update_trading_settings_success(self, client):
        """取引設定更新API成功テスト"""
        new_settings = {
            "symbol": "EURJPY",
            "timeframe": "M15",
            "min_confidence": 0.8,
            "max_spread": 2.5
        }
        
        with patch('backend.api.trading.trading_engine') as mock_engine:
            mock_engine.update_settings.return_value = None
            
            response = client.put("/api/v1/trading/settings", json=new_settings)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Settings updated successfully"

    def test_update_trading_settings_invalid_data(self, client):
        """無効な取引設定更新テスト"""
        invalid_settings = {
            "symbol": "",  # 空の通貨ペア
            "min_confidence": 1.5  # 無効な信頼度（1.0超過）
        }
        
        response = client.put("/api/v1/trading/settings", json=invalid_settings)
        
        assert response.status_code == 422  # Validation error

    def test_get_trading_performance(self, client, db_session, sample_trades):
        """取引パフォーマンス取得APIテスト"""
        with patch('backend.api.trading.trading_engine') as mock_engine:
            mock_performance = {
                "total_trades": 10,
                "winning_trades": 6,
                "total_profit": 2500,
                "win_rate": 60.0,
                "profit_factor": 1.5,
                "max_drawdown": 15.0
            }
            mock_engine.get_performance_metrics.return_value = mock_performance
            
            response = client.get("/api/v1/trading/performance")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 10
        assert data["win_rate"] == 60.0
        assert data["profit_factor"] == 1.5

    def test_emergency_stop_all_trading(self, client, mock_mt5_client):
        """緊急取引停止APIテスト"""
        # モックポジション
        mock_positions = [
            Mock(ticket=123456, symbol='USDJPY', volume=0.1),
            Mock(ticket=123457, symbol='EURJPY', volume=0.05)
        ]
        mock_mt5_client.get_positions.return_value = mock_positions
        mock_mt5_client.close_position.return_value = {
            "success": True,
            "message": "Position closed"
        }
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            with patch('backend.api.trading.trading_engine') as mock_engine:
                mock_engine.stop_trading.return_value = None
                
                response = client.post("/api/v1/trading/emergency-stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "emergency_stopped"
        assert data["closed_positions"] == 2

    def test_manual_trade_execution(self, client, mock_mt5_client):
        """手動取引実行APIテスト"""
        trade_request = {
            "symbol": "USDJPY",
            "type": "BUY",
            "volume": 0.1,
            "price": 130.25,
            "stop_loss": 129.75,
            "take_profit": 130.75
        }
        
        # MT5注文成功をモック
        mock_mt5_client.send_order.return_value = {
            "success": True,
            "order_id": 123456,
            "message": "Order executed successfully"
        }
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            response = client.post("/api/v1/trading/manual-trade", json=trade_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["order_id"] == 123456

    def test_manual_trade_execution_validation_error(self, client):
        """手動取引実行バリデーションエラーテスト"""
        invalid_request = {
            "symbol": "",  # 空のシンボル
            "type": "INVALID_TYPE",  # 無効なタイプ
            "volume": -0.1  # 負のボリューム
        }
        
        response = client.post("/api/v1/trading/manual-trade", json=invalid_request)
        
        assert response.status_code == 422  # Validation error

    def test_get_market_data_realtime(self, client, mock_mt5_client):
        """リアルタイム市場データ取得APIテスト"""
        # モックティック
        mock_tick = Mock()
        mock_tick.ask = 130.25
        mock_tick.bid = 130.23
        mock_tick.time = 1640995200
        mock_mt5_client.get_tick.return_value = mock_tick
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            response = client.get("/api/v1/trading/market-data/USDJPY")
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "USDJPY"
        assert data["ask"] == 130.25
        assert data["bid"] == 130.23

    def test_get_market_data_symbol_not_found(self, client, mock_mt5_client):
        """存在しないシンボルの市場データ取得テスト"""
        mock_mt5_client.get_tick.return_value = None
        
        with patch('backend.api.trading.get_mt5_client', return_value=mock_mt5_client):
            response = client.get("/api/v1/trading/market-data/INVALID")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]