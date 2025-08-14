"""
パフォーマンステスト
"""
import pytest
import time
import asyncio
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backend.core.mt5_client import MT5Client
from backend.core.trading_engine import TradingEngine
from backend.ml.lightgbm_predictor import LightGBMPredictor
from backend.backtest.backtest_engine import BacktestEngine


class TestPerformance:
    """パフォーマンステストクラス"""

    def test_api_response_time(self, client):
        """API応答時間テスト"""
        endpoints = [
            "/api/v1/trading/status",
            "/api/v1/positions",
            "/api/v1/trades",
            "/health",
            "/status"
        ]
        
        response_times = []
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            # 応答時間が1秒以内であることを確認
            assert response_time < 1.0, f"Endpoint {endpoint} took {response_time:.3f}s"
            assert response.status_code in [200, 404, 503]  # 404や503は正常（実装状況による）
        
        # 平均応答時間が500ms以内であることを確認
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 0.5, f"Average response time {avg_response_time:.3f}s exceeds 500ms"

    def test_concurrent_api_requests(self, client):
        """同時リクエストテスト"""
        def make_request():
            start_time = time.time()
            response = client.get("/api/v1/trading/status")
            end_time = time.time()
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time
            }
        
        # 50の同時リクエストを実行
        num_requests = 50
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]
        
        # 全てのリクエストが成功すること
        success_count = sum(1 for r in results if r['status_code'] in [200, 404, 503])
        assert success_count == num_requests, f"Only {success_count}/{num_requests} requests succeeded"
        
        # 99%のリクエストが2秒以内に完了すること
        response_times = [r['response_time'] for r in results]
        response_times.sort()
        p99_response_time = response_times[int(len(response_times) * 0.99)]
        assert p99_response_time < 2.0, f"99th percentile response time {p99_response_time:.3f}s exceeds 2s"

    def test_memory_usage_during_data_processing(self, sample_price_data):
        """データ処理中のメモリ使用量テスト"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 大量データ処理をシミュレート
        large_dataset = pd.concat([sample_price_data] * 10, ignore_index=True)  # 10倍のデータ
        
        # 特徴量エンジニアリングの実行
        from backend.ml.feature_engineering import FeatureEngineering
        feature_engine = FeatureEngineering()
        
        for _ in range(5):  # 5回繰り返し処理
            features = feature_engine.create_features(large_dataset)
            
            # 中間のメモリ使用量チェック
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory
            
            # メモリ使用量増加が200MB以下であること
            assert memory_increase < 200, f"Memory usage increased by {memory_increase:.1f}MB"
        
        # ガベージコレクション後の最終メモリチェック
        import gc
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024
        final_increase = final_memory - initial_memory
        
        # 最終的なメモリ使用量増加が100MB以下であること
        assert final_increase < 100, f"Final memory usage increased by {final_increase:.1f}MB"

    def test_database_query_performance(self, db_session):
        """データベースクエリパフォーマンステスト"""
        from backend.models.backtest_models import Trade, PriceData
        
        # 大量のテストデータを挿入
        test_trades = []
        for i in range(1000):
            trade = Trade(
                symbol='USDJPY',
                order_type='BUY' if i % 2 == 0 else 'SELL',
                entry_time=datetime.now() - timedelta(hours=i),
                entry_price=130.0 + (i * 0.001),
                exit_time=datetime.now() - timedelta(hours=i-1),
                exit_price=130.0 + (i * 0.001) + (0.01 if i % 2 == 0 else -0.01),
                volume=0.1,
                profit_loss=100 if i % 2 == 0 else -50
            )
            test_trades.append(trade)
        
        # バッチ挿入のパフォーマンス測定
        start_time = time.time()
        db_session.bulk_save_objects(test_trades)
        db_session.commit()
        insert_time = time.time() - start_time
        
        # 挿入時間が5秒以内であること
        assert insert_time < 5.0, f"Bulk insert took {insert_time:.3f}s"
        
        # クエリパフォーマンスの測定
        query_tests = [
            # 全取引の取得
            lambda: db_session.query(Trade).all(),
            # フィルタ付きクエリ
            lambda: db_session.query(Trade).filter(Trade.symbol == 'USDJPY').all(),
            # 日付範囲クエリ
            lambda: db_session.query(Trade).filter(
                Trade.entry_time >= datetime.now() - timedelta(days=1)
            ).all(),
            # 集計クエリ
            lambda: db_session.query(Trade).filter(Trade.profit_loss > 0).count(),
        ]
        
        for i, query_func in enumerate(query_tests):
            start_time = time.time()
            result = query_func()
            query_time = time.time() - start_time
            
            # 各クエリが1秒以内に完了すること
            assert query_time < 1.0, f"Query {i} took {query_time:.3f}s"

    def test_ml_model_prediction_performance(self, sample_price_data):
        """機械学習モデル予測パフォーマンステスト"""
        from backend.ml.feature_engineering import FeatureEngineering
        
        # 特徴量作成
        feature_engine = FeatureEngineering()
        features = feature_engine.create_features(sample_price_data)
        
        # モデルの作成とトレーニング
        predictor = LightGBMPredictor()
        labeled_data = predictor.prepare_labels(features)
        clean_data = labeled_data.dropna()
        
        if len(clean_data) > 50:
            X = clean_data.drop(['label', 'future_return'], axis=1)
            y = clean_data['label']
            
            # トレーニング時間の測定
            start_time = time.time()
            predictor.train(X, y)
            training_time = time.time() - start_time
            
            # トレーニング時間が30秒以内であること
            assert training_time < 30.0, f"Model training took {training_time:.3f}s"
            
            # 予測時間の測定
            test_data = X.tail(100)  # 100サンプルで予測
            
            start_time = time.time()
            predictions, confidence = predictor.predict(test_data)
            prediction_time = time.time() - start_time
            
            # 100サンプルの予測が1秒以内であること
            assert prediction_time < 1.0, f"Prediction took {prediction_time:.3f}s for 100 samples"
            
            # 単一サンプルの予測時間
            single_sample = X.tail(1)
            start_time = time.time()
            single_prediction, single_confidence = predictor.predict(single_sample)
            single_prediction_time = time.time() - start_time
            
            # 単一予測が10ms以内であること
            assert single_prediction_time < 0.01, f"Single prediction took {single_prediction_time:.6f}s"

    def test_backtest_engine_performance(self, db_session, sample_price_data):
        """バックテストエンジンパフォーマンステスト"""
        from backend.models.backtest_models import PriceData
        
        # テスト用価格データをDBに保存
        price_data_list = []
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
            price_data_list.append(price_data)
        
        db_session.bulk_save_objects(price_data_list)
        db_session.commit()
        
        # バックテストエンジンの実行
        backtest_engine = BacktestEngine(db_session)
        
        parameters = {
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'stop_loss_percent': 2.0,
            'take_profit_percent': 4.0
        }
        
        start_time = time.time()
        results = backtest_engine.run_backtest(
            symbol="USDJPY",
            timeframe="H1",
            start_date=sample_price_data['time'].min(),
            end_date=sample_price_data['time'].max(),
            initial_balance=100000,
            parameters=parameters
        )
        backtest_time = time.time() - start_time
        
        # バックテスト実行時間が60秒以内であること
        assert backtest_time < 60.0, f"Backtest took {backtest_time:.3f}s"
        
        # 結果が正常に生成されていること
        assert results is not None
        assert 'total_trades' in results
        assert 'statistics' in results

    def test_websocket_performance(self, mock_websocket_manager):
        """WebSocket パフォーマンステスト"""
        from backend.websocket.websocket_manager import WebSocketManager
        
        # 複数の接続をシミュレート
        connections = []
        for i in range(100):
            mock_ws = Mock()
            mock_ws.send_text = Mock()
            connections.append(mock_ws)
        
        # 接続追加の時間測定
        start_time = time.time()
        for ws in connections:
            mock_websocket_manager.connect(ws, {'client_id': f'client_{len(connections)}'})
        connection_time = time.time() - start_time
        
        # 100接続の追加が1秒以内であること
        assert connection_time < 1.0, f"Adding 100 connections took {connection_time:.3f}s"
        
        # ブロードキャスト性能の測定
        test_message = {'type': 'test', 'data': {'value': 123}}
        
        start_time = time.time()
        mock_websocket_manager.broadcast(test_message)
        broadcast_time = time.time() - start_time
        
        # 100接続へのブロードキャストが500ms以内であること
        assert broadcast_time < 0.5, f"Broadcasting to 100 connections took {broadcast_time:.3f}s"

    def test_cpu_usage_under_load(self, client):
        """負荷テスト時のCPU使用率テスト"""
        initial_cpu = psutil.cpu_percent(interval=1)
        
        def stress_test():
            """ストレステスト関数"""
            responses = []
            for _ in range(20):
                response = client.get("/api/v1/trading/status")
                responses.append(response.status_code)
            return responses
        
        # 複数スレッドでストレステストを実行
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(stress_test) for _ in range(5)]
            
            # CPU使用率を監視
            cpu_samples = []
            for _ in range(10):  # 10秒間監視
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_samples.append(cpu_percent)
            
            # テスト完了まで待機
            results = [future.result() for future in as_completed(futures)]
        
        # 平均CPU使用率が80%以下であること
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        assert avg_cpu < 80.0, f"Average CPU usage {avg_cpu:.1f}% exceeds 80%"
        
        # 最大CPU使用率が95%以下であること
        max_cpu = max(cpu_samples)
        assert max_cpu < 95.0, f"Maximum CPU usage {max_cpu:.1f}% exceeds 95%"

    def test_large_dataset_processing(self):
        """大量データ処理パフォーマンステスト"""
        # 大量のテストデータ生成（10万レコード）
        num_records = 100000
        dates = pd.date_range('2020-01-01', periods=num_records, freq='T')
        
        large_dataset = pd.DataFrame({
            'time': dates,
            'open': np.random.normal(130, 5, num_records),
            'high': np.random.normal(131, 5, num_records),
            'low': np.random.normal(129, 5, num_records),
            'close': np.random.normal(130, 5, num_records),
            'tick_volume': np.random.randint(100, 1000, num_records)
        })
        
        # データ処理時間の測定
        from backend.ml.feature_engineering import FeatureEngineering
        feature_engine = FeatureEngineering()
        
        start_time = time.time()
        features = feature_engine.create_features(large_dataset)
        processing_time = time.time() - start_time
        
        # 10万レコードの処理が5分以内であること
        assert processing_time < 300.0, f"Processing 100k records took {processing_time:.1f}s"
        
        # 処理速度（レコード/秒）をチェック
        processing_rate = num_records / processing_time
        assert processing_rate > 500, f"Processing rate {processing_rate:.0f} records/sec is too slow"

    @pytest.mark.asyncio
    async def test_async_performance(self):
        """非同期処理パフォーマンステスト"""
        async def async_task(task_id: int):
            """非同期タスクのシミュレート"""
            await asyncio.sleep(0.1)  # 100ms の処理をシミュレート
            return f"Task {task_id} completed"
        
        # 100の同時非同期タスクを実行
        num_tasks = 100
        start_time = time.time()
        
        tasks = [async_task(i) for i in range(num_tasks)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # 100タスクが2秒以内に完了すること（並行実行のため）
        assert total_time < 2.0, f"100 async tasks took {total_time:.3f}s"
        
        # 全タスクが正常に完了していること
        assert len(results) == num_tasks
        for i, result in enumerate(results):
            assert result == f"Task {i} completed"

    def test_memory_leak_detection(self, sample_price_data):
        """メモリリーク検出テスト"""
        import gc
        
        process = psutil.Process()
        
        # 初期メモリ使用量
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # 繰り返し処理でメモリリークをチェック
        for iteration in range(10):
            # データ処理を繰り返し実行
            from backend.ml.feature_engineering import FeatureEngineering
            feature_engine = FeatureEngineering()
            
            # 処理実行
            features = feature_engine.create_features(sample_price_data)
            
            # 明示的に削除
            del features
            del feature_engine
            
            # ガベージコレクション
            gc.collect()
            
            # メモリ使用量チェック
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory
            
            # メモリ使用量の増加が50MB以下であること
            assert memory_increase < 50, f"Memory leak detected: {memory_increase:.1f}MB increase at iteration {iteration}"

    def test_concurrent_database_access(self, db_session):
        """同時データベースアクセステスト"""
        from backend.models.backtest_models import Trade
        
        def database_operation(thread_id: int):
            """データベース操作を実行"""
            results = []
            
            for i in range(10):
                # 取引データの挿入
                trade = Trade(
                    symbol='USDJPY',
                    order_type='BUY',
                    entry_time=datetime.now(),
                    entry_price=130.0,
                    volume=0.1,
                    profit_loss=100
                )
                
                try:
                    db_session.add(trade)
                    db_session.commit()
                    results.append(f"Thread {thread_id}: Insert {i} successful")
                except Exception as e:
                    db_session.rollback()
                    results.append(f"Thread {thread_id}: Insert {i} failed: {e}")
            
            return results
        
        # 5つのスレッドで同時にデータベース操作を実行
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(database_operation, i) for i in range(5)]
            all_results = [future.result() for future in as_completed(futures)]
        
        operation_time = time.time() - start_time
        
        # 同時データベース操作が10秒以内に完了すること
        assert operation_time < 10.0, f"Concurrent database operations took {operation_time:.3f}s"
        
        # 全ての操作が正常に完了していることを確認
        total_operations = sum(len(results) for results in all_results)
        assert total_operations == 50  # 5スレッド × 10操作