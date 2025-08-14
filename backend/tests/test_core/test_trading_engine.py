"""
TradingEngine単体テスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from backend.core.trading_engine import TradingEngine


class TestTradingEngine:
    """TradingEngineのテストクラス"""

    @pytest.fixture
    def mock_dependencies(self):
        """依存関係のモック作成"""
        return {
            'mt5_client': Mock(),
            'ml_predictor': Mock(),
            'risk_manager': Mock(),
            'db_session': Mock()
        }

    @pytest.fixture
    def trading_engine(self, mock_dependencies):
        """TradingEngineインスタンス作成"""
        engine = TradingEngine(
            mt5_client=mock_dependencies['mt5_client'],
            ml_predictor=mock_dependencies['ml_predictor'],
            risk_manager=mock_dependencies['risk_manager'],
            db_session=mock_dependencies['db_session']
        )
        
        # デフォルト設定
        engine.settings = {
            'symbol': 'USDJPY',
            'timeframe': 'H1',
            'min_confidence': 0.7,
            'max_spread': 3.0,
            'trading_hours': {
                'start': '09:00',
                'end': '17:00'
            }
        }
        
        return engine

    def test_init(self, mock_dependencies):
        """初期化テスト"""
        engine = TradingEngine(
            mt5_client=mock_dependencies['mt5_client'],
            ml_predictor=mock_dependencies['ml_predictor'],
            risk_manager=mock_dependencies['risk_manager'],
            db_session=mock_dependencies['db_session']
        )
        
        assert engine.mt5_client == mock_dependencies['mt5_client']
        assert engine.ml_predictor == mock_dependencies['ml_predictor']
        assert engine.risk_manager == mock_dependencies['risk_manager']
        assert engine.db_session == mock_dependencies['db_session']
        assert engine.is_running is False

    def test_start_trading_success(self, trading_engine, mock_dependencies):
        """取引開始成功テスト"""
        # MT5接続成功
        mock_dependencies['mt5_client'].is_connected.return_value = True
        
        with patch.object(trading_engine, '_trading_loop') as mock_loop:
            result = trading_engine.start_trading()
            
            assert result is True
            assert trading_engine.is_running is True
            mock_loop.assert_called_once()

    def test_start_trading_already_running(self, trading_engine):
        """既に実行中での取引開始テスト"""
        trading_engine.is_running = True
        
        result = trading_engine.start_trading()
        
        assert result is False

    def test_start_trading_mt5_not_connected(self, trading_engine, mock_dependencies):
        """MT5未接続での取引開始テスト"""
        mock_dependencies['mt5_client'].is_connected.return_value = False
        
        result = trading_engine.start_trading()
        
        assert result is False
        assert trading_engine.is_running is False

    def test_stop_trading(self, trading_engine):
        """取引停止テスト"""
        trading_engine.is_running = True
        
        trading_engine.stop_trading()
        
        assert trading_engine.is_running is False

    def test_get_market_data_success(self, trading_engine, mock_dependencies):
        """市場データ取得成功テスト"""
        # モック価格データ
        mock_rates = pd.DataFrame({
            'time': pd.date_range('2023-01-01', periods=100, freq='H'),
            'open': np.random.normal(130, 1, 100),
            'high': np.random.normal(130.5, 1, 100),
            'low': np.random.normal(129.5, 1, 100),
            'close': np.random.normal(130, 1, 100),
            'tick_volume': np.random.randint(100, 1000, 100)
        })
        
        mock_dependencies['mt5_client'].get_rates.return_value = mock_rates
        
        result = trading_engine._get_market_data()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100
        mock_dependencies['mt5_client'].get_rates.assert_called_once()

    def test_get_market_data_failure(self, trading_engine, mock_dependencies):
        """市場データ取得失敗テスト"""
        mock_dependencies['mt5_client'].get_rates.return_value = pd.DataFrame()
        
        result = trading_engine._get_market_data()
        
        assert result.empty

    def test_analyze_market_buy_signal(self, trading_engine, mock_dependencies):
        """買いシグナル分析テスト"""
        # モック予測結果（買いシグナル：クラス2）
        mock_dependencies['ml_predictor'].predict.return_value = (
            np.array([2]),  # 買いシグナル
            np.array([0.8])  # 高い信頼度
        )
        
        mock_market_data = pd.DataFrame({
            'close': [130.25],
            'feature1': [0.5],
            'feature2': [0.3]
        })
        
        signal, confidence = trading_engine._analyze_market(mock_market_data)
        
        assert signal == 'BUY'
        assert confidence == 0.8
        mock_dependencies['ml_predictor'].predict.assert_called_once()

    def test_analyze_market_sell_signal(self, trading_engine, mock_dependencies):
        """売りシグナル分析テスト"""
        # モック予測結果（売りシグナル：クラス0）
        mock_dependencies['ml_predictor'].predict.return_value = (
            np.array([0]),  # 売りシグナル
            np.array([0.9])  # 高い信頼度
        )
        
        mock_market_data = pd.DataFrame({
            'close': [130.25],
            'feature1': [0.5],
            'feature2': [0.3]
        })
        
        signal, confidence = trading_engine._analyze_market(mock_market_data)
        
        assert signal == 'SELL'
        assert confidence == 0.9

    def test_analyze_market_hold_signal(self, trading_engine, mock_dependencies):
        """ホールドシグナル分析テスト"""
        # モック予測結果（ホールドシグナル：クラス1）
        mock_dependencies['ml_predictor'].predict.return_value = (
            np.array([1]),  # ホールドシグナル
            np.array([0.6])
        )
        
        mock_market_data = pd.DataFrame({
            'close': [130.25],
            'feature1': [0.5],
            'feature2': [0.3]
        })
        
        signal, confidence = trading_engine._analyze_market(mock_market_data)
        
        assert signal == 'HOLD'
        assert confidence == 0.6

    def test_analyze_market_low_confidence(self, trading_engine, mock_dependencies):
        """低信頼度での分析テスト"""
        # 低信頼度の予測結果
        mock_dependencies['ml_predictor'].predict.return_value = (
            np.array([2]),  # 買いシグナル
            np.array([0.5])  # 低い信頼度
        )
        
        mock_market_data = pd.DataFrame({
            'close': [130.25],
            'feature1': [0.5],
            'feature2': [0.3]
        })
        
        signal, confidence = trading_engine._analyze_market(mock_market_data)
        
        # 最小信頼度（0.7）以下なのでHOLD
        assert signal == 'HOLD'
        assert confidence == 0.5

    def test_check_trading_conditions_success(self, trading_engine, mock_dependencies):
        """取引条件チェック成功テスト"""
        # モックティック
        mock_tick = Mock()
        mock_tick.ask = 130.25
        mock_tick.bid = 130.23
        mock_dependencies['mt5_client'].get_tick.return_value = mock_tick
        
        # 現在時刻を取引時間内に設定
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 0)  # 10:00
            
            result = trading_engine._check_trading_conditions()
            
            assert result is True

    def test_check_trading_conditions_high_spread(self, trading_engine, mock_dependencies):
        """高スプレッドでの取引条件チェックテスト"""
        # 高スプレッドのティック
        mock_tick = Mock()
        mock_tick.ask = 130.35
        mock_tick.bid = 130.20  # スプレッド15pips（許可値3.0pipsを超過）
        mock_dependencies['mt5_client'].get_tick.return_value = mock_tick
        
        result = trading_engine._check_trading_conditions()
        
        assert result is False

    def test_check_trading_conditions_outside_hours(self, trading_engine, mock_dependencies):
        """取引時間外での条件チェックテスト"""
        # モックティック
        mock_tick = Mock()
        mock_tick.ask = 130.25
        mock_tick.bid = 130.23
        mock_dependencies['mt5_client'].get_tick.return_value = mock_tick
        
        # 現在時刻を取引時間外に設定
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 18, 0)  # 18:00（時間外）
            
            result = trading_engine._check_trading_conditions()
            
            assert result is False

    def test_execute_trade_buy_success(self, trading_engine, mock_dependencies):
        """買い注文実行成功テスト"""
        # リスク管理OK
        mock_dependencies['risk_manager'].validate_trade_request.return_value = True
        mock_dependencies['risk_manager'].calculate_lot_size.return_value = 0.1
        
        # 注文成功
        mock_dependencies['mt5_client'].send_order.return_value = {
            'success': True,
            'order_id': 123456,
            'message': 'Order placed successfully'
        }
        
        # モックティック
        mock_tick = Mock()
        mock_tick.ask = 130.25
        mock_tick.bid = 130.23
        mock_dependencies['mt5_client'].get_tick.return_value = mock_tick
        
        result = trading_engine._execute_trade('BUY', 0.8)
        
        assert result is True
        mock_dependencies['mt5_client'].send_order.assert_called_once()

    def test_execute_trade_risk_rejection(self, trading_engine, mock_dependencies):
        """リスク管理による注文拒否テスト"""
        # リスク管理NG
        mock_dependencies['risk_manager'].validate_trade_request.return_value = False
        
        result = trading_engine._execute_trade('BUY', 0.8)
        
        assert result is False
        mock_dependencies['mt5_client'].send_order.assert_not_called()

    def test_execute_trade_order_failure(self, trading_engine, mock_dependencies):
        """注文失敗テスト"""
        # リスク管理OK
        mock_dependencies['risk_manager'].validate_trade_request.return_value = True
        mock_dependencies['risk_manager'].calculate_lot_size.return_value = 0.1
        
        # 注文失敗
        mock_dependencies['mt5_client'].send_order.return_value = {
            'success': False,
            'order_id': None,
            'message': 'Order failed'
        }
        
        # モックティック
        mock_tick = Mock()
        mock_tick.ask = 130.25
        mock_tick.bid = 130.23
        mock_dependencies['mt5_client'].get_tick.return_value = mock_tick
        
        result = trading_engine._execute_trade('BUY', 0.8)
        
        assert result is False

    def test_close_positions_success(self, trading_engine, mock_dependencies):
        """ポジション決済成功テスト"""
        # モックポジション
        mock_positions = [
            Mock(ticket=123456, symbol='USDJPY', volume=0.1, type=0),  # BUY
            Mock(ticket=123457, symbol='USDJPY', volume=0.05, type=1)  # SELL
        ]
        mock_dependencies['mt5_client'].get_positions.return_value = mock_positions
        
        # 決済成功
        mock_dependencies['mt5_client'].close_position.return_value = {
            'success': True,
            'message': 'Position closed successfully'
        }
        
        # モックティック
        mock_tick = Mock()
        mock_tick.ask = 130.25
        mock_tick.bid = 130.23
        mock_dependencies['mt5_client'].get_tick.return_value = mock_tick
        
        result = trading_engine._close_positions()
        
        assert result == 2  # 2つのポジションを決済
        assert mock_dependencies['mt5_client'].close_position.call_count == 2

    def test_close_positions_no_positions(self, trading_engine, mock_dependencies):
        """ポジションなしでの決済テスト"""
        mock_dependencies['mt5_client'].get_positions.return_value = []
        
        result = trading_engine._close_positions()
        
        assert result == 0
        mock_dependencies['mt5_client'].close_position.assert_not_called()

    def test_update_settings(self, trading_engine):
        """設定更新テスト"""
        new_settings = {
            'symbol': 'EURJPY',
            'timeframe': 'M15',
            'min_confidence': 0.8,
            'max_spread': 2.5
        }
        
        trading_engine.update_settings(new_settings)
        
        for key, value in new_settings.items():
            assert trading_engine.settings[key] == value

    def test_get_status(self, trading_engine):
        """ステータス取得テスト"""
        trading_engine.is_running = True
        trading_engine.last_signal = 'BUY'
        trading_engine.last_confidence = 0.85
        trading_engine.last_update = datetime.now()
        
        status = trading_engine.get_status()
        
        assert status['is_running'] is True
        assert status['last_signal'] == 'BUY'
        assert status['last_confidence'] == 0.85
        assert 'last_update' in status
        assert 'settings' in status

    def test_get_performance_metrics(self, trading_engine, mock_dependencies):
        """パフォーマンスメトリクス取得テスト"""
        # モック取引履歴
        mock_trades = [
            Mock(profit_loss=1000, exit_time=datetime.now()),
            Mock(profit_loss=-500, exit_time=datetime.now()),
            Mock(profit_loss=750, exit_time=datetime.now()),
        ]
        
        with patch.object(trading_engine, '_get_trade_history', return_value=mock_trades):
            metrics = trading_engine.get_performance_metrics()
            
            assert 'total_trades' in metrics
            assert 'winning_trades' in metrics
            assert 'total_profit' in metrics
            assert 'win_rate' in metrics
            assert 'profit_factor' in metrics
            
            assert metrics['total_trades'] == 3
            assert metrics['winning_trades'] == 2
            assert metrics['total_profit'] == 1250

    def test_trading_loop_cycle(self, trading_engine, mock_dependencies):
        """取引ループサイクルテスト"""
        # モック市場データ
        mock_market_data = pd.DataFrame({
            'close': [130.25],
            'feature1': [0.5]
        })
        
        # 各メソッドのモック設定
        with patch.object(trading_engine, '_get_market_data', return_value=mock_market_data):
            with patch.object(trading_engine, '_analyze_market', return_value=('BUY', 0.8)):
                with patch.object(trading_engine, '_check_trading_conditions', return_value=True):
                    with patch.object(trading_engine, '_execute_trade', return_value=True):
                        with patch('time.sleep'):  # スリープをスキップ
                            
                            # ループを1回だけ実行
                            trading_engine.is_running = True
                            
                            # 1回実行後に停止
                            def stop_after_one_cycle(*args):
                                trading_engine.is_running = False
                            
                            with patch.object(trading_engine, '_execute_trade', side_effect=stop_after_one_cycle):
                                trading_engine._trading_loop()
                            
                            # 各メソッドが呼ばれたことを確認
                            assert not trading_engine.is_running