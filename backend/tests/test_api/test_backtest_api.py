"""
Backtest API統合テスト
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime, timedelta

from backend.models.backtest_models import PriceData, BacktestResult


class TestBacktestAPI:
    """Backtest APIの統合テストクラス"""

    def test_run_backtest_success(self, client, db_session, sample_price_data):
        """バックテスト実行API成功テスト"""
        # テスト用価格データをDBに保存
        for _, row in sample_price_data.iterrows():
            price_data = PriceData(
                symbol="USDJPY",
                timeframe="H1",
                time=row['time'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                tick_volume=row['tick_volume']
            )
            db_session.add(price_data)
        db_session.commit()
        
        backtest_request = {
            "symbol": "USDJPY",
            "timeframe": "H1",
            "start_date": "2023-01-01",
            "end_date": "2023-01-05",
            "initial_balance": 100000,
            "parameters": {
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "stop_loss_percent": 2.0,
                "take_profit_percent": 4.0,
                "max_positions": 1
            }
        }
        
        with patch('backend.api.backtest.run_backtest_task') as mock_task:
            mock_result = {
                "test_id": "test_123",
                "status": "running",
                "message": "Backtest started successfully"
            }
            mock_task.delay.return_value.id = "test_123"
            
            response = client.post("/api/v1/backtest/run", json=backtest_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "test_id" in data
        assert data["status"] == "running"

    def test_run_backtest_invalid_dates(self, client):
        """無効な日付でのバックテスト実行テスト"""
        backtest_request = {
            "symbol": "USDJPY",
            "timeframe": "H1",
            "start_date": "2023-01-05",  # 終了日より後
            "end_date": "2023-01-01",
            "initial_balance": 100000,
            "parameters": {
                "rsi_period": 14
            }
        }
        
        response = client.post("/api/v1/backtest/run", json=backtest_request)
        
        assert response.status_code == 400
        data = response.json()
        assert "start_date must be before end_date" in data["detail"]

    def test_run_backtest_invalid_balance(self, client):
        """無効な初期残高でのバックテスト実行テスト"""
        backtest_request = {
            "symbol": "USDJPY",
            "timeframe": "H1",
            "start_date": "2023-01-01",
            "end_date": "2023-01-05",
            "initial_balance": -1000,  # 負の残高
            "parameters": {
                "rsi_period": 14
            }
        }
        
        response = client.post("/api/v1/backtest/run", json=backtest_request)
        
        assert response.status_code == 422  # Validation error

    def test_run_backtest_missing_data(self, client, db_session):
        """データ不足でのバックテスト実行テスト"""
        backtest_request = {
            "symbol": "NONEXISTENT",
            "timeframe": "H1",
            "start_date": "2023-01-01",
            "end_date": "2023-01-05",
            "initial_balance": 100000,
            "parameters": {
                "rsi_period": 14
            }
        }
        
        response = client.post("/api/v1/backtest/run", json=backtest_request)
        
        assert response.status_code == 400
        data = response.json()
        assert "Insufficient price data" in data["detail"]

    def test_get_backtest_result_success(self, client, db_session):
        """バックテスト結果取得API成功テスト"""
        # テスト用バックテスト結果作成
        test_result = BacktestResult(
            test_id="test_123",
            symbol="USDJPY",
            timeframe="H1",
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 5),
            total_trades=25,
            winning_trades=15,
            profit_factor=1.5,
            max_drawdown=12.5,
            parameters={"rsi_period": 14, "stop_loss_percent": 2.0}
        )
        db_session.add(test_result)
        db_session.commit()
        
        response = client.get("/api/v1/backtest/results/test_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["test_id"] == "test_123"
        assert data["symbol"] == "USDJPY"
        assert data["total_trades"] == 25
        assert data["profit_factor"] == 1.5

    def test_get_backtest_result_not_found(self, client):
        """存在しないバックテスト結果取得テスト"""
        response = client.get("/api/v1/backtest/results/nonexistent_id")
        
        assert response.status_code == 404
        data = response.json()
        assert "Backtest result not found" in data["detail"]

    def test_get_backtest_status_running(self, client):
        """実行中バックテストのステータス取得テスト"""
        with patch('backend.api.backtest.get_task_status') as mock_status:
            mock_status.return_value = {
                "status": "PROGRESS",
                "progress": 45,
                "message": "Processing trades..."
            }
            
            response = client.get("/api/v1/backtest/status/test_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PROGRESS"
        assert data["progress"] == 45

    def test_get_backtest_status_completed(self, client):
        """完了バックテストのステータス取得テスト"""
        with patch('backend.api.backtest.get_task_status') as mock_status:
            mock_status.return_value = {
                "status": "SUCCESS",
                "progress": 100,
                "message": "Backtest completed successfully"
            }
            
            response = client.get("/api/v1/backtest/status/test_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["progress"] == 100

    def test_get_backtest_status_failed(self, client):
        """失敗バックテストのステータス取得テスト"""
        with patch('backend.api.backtest.get_task_status') as mock_status:
            mock_status.return_value = {
                "status": "FAILURE",
                "error": "Insufficient data for analysis"
            }
            
            response = client.get("/api/v1/backtest/status/test_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILURE"
        assert "error" in data

    def test_cancel_backtest_success(self, client):
        """バックテストキャンセルAPI成功テスト"""
        with patch('backend.api.backtest.cancel_backtest_task') as mock_cancel:
            mock_cancel.return_value = True
            
            response = client.delete("/api/v1/backtest/test_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Backtest cancelled successfully"

    def test_cancel_backtest_not_found(self, client):
        """存在しないバックテストキャンセルテスト"""
        with patch('backend.api.backtest.cancel_backtest_task') as mock_cancel:
            mock_cancel.return_value = False
            
            response = client.delete("/api/v1/backtest/nonexistent_id")
        
        assert response.status_code == 404
        data = response.json()
        assert "Backtest not found" in data["detail"]

    def test_list_backtest_results(self, client, db_session):
        """バックテスト結果一覧取得APIテスト"""
        # 複数のテスト結果作成
        for i in range(5):
            test_result = BacktestResult(
                test_id=f"test_{i}",
                symbol="USDJPY",
                timeframe="H1",
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 5),
                total_trades=10 + i,
                winning_trades=5 + i,
                profit_factor=1.0 + (i * 0.1),
                max_drawdown=10.0 + i,
                parameters={"rsi_period": 14}
            )
            db_session.add(test_result)
        db_session.commit()
        
        response = client.get("/api/v1/backtest/results")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 5
        assert data["total_count"] == 5

    def test_list_backtest_results_with_filters(self, client, db_session):
        """フィルター付きバックテスト結果一覧取得テスト"""
        # 異なる通貨ペアの結果作成
        symbols = ["USDJPY", "EURJPY", "GBPJPY"]
        for i, symbol in enumerate(symbols):
            test_result = BacktestResult(
                test_id=f"test_{symbol}",
                symbol=symbol,
                timeframe="H1",
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 5),
                total_trades=10,
                winning_trades=5,
                profit_factor=1.5,
                max_drawdown=10.0,
                parameters={"rsi_period": 14}
            )
            db_session.add(test_result)
        db_session.commit()
        
        # USDJPYのみをフィルター
        response = client.get("/api/v1/backtest/results?symbol=USDJPY")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["symbol"] == "USDJPY"

    def test_list_backtest_results_with_pagination(self, client, db_session):
        """ページネーション付きバックテスト結果一覧取得テスト"""
        # 10個のテスト結果作成
        for i in range(10):
            test_result = BacktestResult(
                test_id=f"test_{i}",
                symbol="USDJPY",
                timeframe="H1",
                period_start=datetime(2023, 1, 1),
                period_end=datetime(2023, 1, 5),
                total_trades=10,
                winning_trades=5,
                profit_factor=1.5,
                max_drawdown=10.0,
                parameters={"rsi_period": 14}
            )
            db_session.add(test_result)
        db_session.commit()
        
        # 最初の5件を取得
        response = client.get("/api/v1/backtest/results?limit=5&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 5
        assert data["total_count"] == 10

    def test_get_backtest_trades(self, client, db_session):
        """バックテスト取引履歴取得APIテスト"""
        # テスト用取引履歴作成
        test_trades = []
        for i in range(3):
            trade = {
                "test_id": "test_123",
                "entry_time": datetime.now() - timedelta(hours=i),
                "exit_time": datetime.now() - timedelta(hours=i-1),
                "symbol": "USDJPY",
                "type": "BUY" if i % 2 == 0 else "SELL",
                "volume": 0.1,
                "entry_price": 130.0 + (i * 0.1),
                "exit_price": 130.0 + (i * 0.1) + 0.05,
                "profit_loss": 500 if i % 2 == 0 else -300
            }
            test_trades.append(trade)
        
        with patch('backend.api.backtest.get_backtest_trades') as mock_trades:
            mock_trades.return_value = test_trades
            
            response = client.get("/api/v1/backtest/test_123/trades")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) == 3
        assert data["total_count"] == 3

    def test_compare_backtest_results(self, client, db_session):
        """バックテスト結果比較APIテスト"""
        # 2つのテスト結果作成
        result1 = BacktestResult(
            test_id="test_1",
            symbol="USDJPY",
            timeframe="H1",
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            total_trades=50,
            winning_trades=30,
            profit_factor=1.8,
            max_drawdown=15.0,
            parameters={"rsi_period": 14}
        )
        
        result2 = BacktestResult(
            test_id="test_2",
            symbol="USDJPY",
            timeframe="H1",
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            total_trades=45,
            winning_trades=32,
            profit_factor=2.1,
            max_drawdown=12.0,
            parameters={"rsi_period": 21}
        )
        
        db_session.add(result1)
        db_session.add(result2)
        db_session.commit()
        
        response = client.post("/api/v1/backtest/compare", json={
            "test_ids": ["test_1", "test_2"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert "comparison" in data
        assert data["comparison"]["better_profit_factor"] == "test_2"

    def test_export_backtest_results(self, client, db_session):
        """バックテスト結果エクスポートAPIテスト"""
        # テスト結果作成
        test_result = BacktestResult(
            test_id="test_export",
            symbol="USDJPY",
            timeframe="H1",
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            total_trades=25,
            winning_trades=15,
            profit_factor=1.5,
            max_drawdown=12.5,
            parameters={"rsi_period": 14}
        )
        db_session.add(test_result)
        db_session.commit()
        
        response = client.get("/api/v1/backtest/test_export/export?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

    def test_optimization_run_success(self, client, db_session, sample_price_data):
        """パラメータ最適化実行APIテスト"""
        # テスト用価格データをDBに保存
        for _, row in sample_price_data.head(100).iterrows():
            price_data = PriceData(
                symbol="USDJPY",
                timeframe="H1",
                time=row['time'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                tick_volume=row['tick_volume']
            )
            db_session.add(price_data)
        db_session.commit()
        
        optimization_request = {
            "symbol": "USDJPY",
            "timeframe": "H1",
            "start_date": "2023-01-01",
            "end_date": "2023-01-05",
            "initial_balance": 100000,
            "optimization_params": {
                "rsi_period": {"min": 10, "max": 20, "step": 2},
                "stop_loss_percent": {"min": 1.0, "max": 3.0, "step": 0.5}
            },
            "optimization_target": "profit_factor"
        }
        
        with patch('backend.api.backtest.run_optimization_task') as mock_task:
            mock_task.delay.return_value.id = "opt_123"
            
            response = client.post("/api/v1/backtest/optimize", json=optimization_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "optimization_id" in data
        assert data["status"] == "running"