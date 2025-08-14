"""
RiskManager単体テスト
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from backend.core.risk_manager import RiskManager


class TestRiskManager:
    """RiskManagerのテストクラス"""

    @pytest.fixture
    def risk_manager(self, db_session):
        """RiskManagerインスタンス作成"""
        manager = RiskManager(db_session)
        
        # デフォルト設定
        manager.settings = {
            'max_risk_per_trade': 2.0,  # 2%
            'max_drawdown': 20.0,  # 20%
            'stop_loss_pips': 50,
            'take_profit_pips': 100,
            'max_positions': 3,
            'margin_level_threshold': 200.0,
            'equity_threshold': 80.0  # 80%
        }
        
        # デフォルト口座情報
        manager.account_info = {
            'balance': 100000.0,
            'equity': 100000.0,
            'margin': 0.0,
            'margin_free': 100000.0,
            'margin_level': 0.0,
            'profit': 0.0
        }
        
        return manager

    def test_calculate_lot_size_basic(self, risk_manager):
        """基本的なロットサイズ計算テスト"""
        # 2%リスク、50pips、pip値1000円で計算
        lot_size = risk_manager.calculate_lot_size("USDJPY", "BUY")
        
        # 期待値: (100000 * 0.02) / (50 * 1000) = 2000 / 50000 = 0.04
        expected_lot_size = 0.04
        assert abs(lot_size - expected_lot_size) < 0.01

    def test_calculate_lot_size_different_risk(self, risk_manager):
        """異なるリスク設定でのロットサイズ計算テスト"""
        risk_manager.settings['max_risk_per_trade'] = 1.0  # 1%
        
        lot_size = risk_manager.calculate_lot_size("USDJPY", "BUY")
        
        # 期待値: (100000 * 0.01) / (50 * 1000) = 1000 / 50000 = 0.02
        expected_lot_size = 0.02
        assert abs(lot_size - expected_lot_size) < 0.01

    def test_calculate_lot_size_different_stop_loss(self, risk_manager):
        """異なるストップロス設定でのロットサイズ計算テスト"""
        risk_manager.settings['stop_loss_pips'] = 100  # 100pips
        
        lot_size = risk_manager.calculate_lot_size("USDJPY", "BUY")
        
        # 期待値: (100000 * 0.02) / (100 * 1000) = 2000 / 100000 = 0.02
        expected_lot_size = 0.02
        assert abs(lot_size - expected_lot_size) < 0.01

    def test_calculate_lot_size_eur_pair(self, risk_manager):
        """EUR系通貨ペアでのロットサイズ計算テスト"""
        lot_size = risk_manager.calculate_lot_size("EURJPY", "BUY")
        
        # EUR系は異なるpip値を使用（JPY系と同じと仮定）
        expected_lot_size = 0.04
        assert abs(lot_size - expected_lot_size) < 0.01

    def test_calculate_lot_size_minimum_lot(self, risk_manager):
        """最小ロットサイズテスト"""
        risk_manager.settings['max_risk_per_trade'] = 0.001  # 0.001%
        
        lot_size = risk_manager.calculate_lot_size("USDJPY", "BUY")
        
        # 最小ロットサイズ（0.01）が適用されるべき
        assert lot_size >= 0.01

    def test_calculate_lot_size_maximum_lot(self, risk_manager):
        """最大ロットサイズテスト"""
        risk_manager.settings['max_risk_per_trade'] = 50.0  # 50%
        
        lot_size = risk_manager.calculate_lot_size("USDJPY", "BUY")
        
        # 計算上は大きな値になるが、実用的な範囲内であること
        assert lot_size > 0
        assert lot_size < 100  # 実用的な上限

    def test_check_risk_limits_success(self, risk_manager):
        """リスク制限チェック成功テスト"""
        # 正常な口座状態
        risk_manager.account_info = {
            'balance': 100000.0,
            'equity': 100000.0,
            'margin_level': 300.0
        }
        
        result = risk_manager.check_risk_limits()
        assert result is True

    def test_check_risk_limits_low_equity(self, risk_manager):
        """低エクイティでのリスク制限チェックテスト"""
        # エクイティが80%以下
        risk_manager.account_info = {
            'balance': 100000.0,
            'equity': 75000.0,  # 75%
            'margin_level': 300.0
        }
        
        result = risk_manager.check_risk_limits()
        assert result is False

    def test_check_risk_limits_low_margin_level(self, risk_manager):
        """低マージンレベルでのリスク制限チェックテスト"""
        # マージンレベルが200%以下
        risk_manager.account_info = {
            'balance': 100000.0,
            'equity': 100000.0,
            'margin_level': 150.0  # 150%
        }
        
        result = risk_manager.check_risk_limits()
        assert result is False

    def test_check_risk_limits_zero_margin_level(self, risk_manager):
        """マージンレベル0での制限チェックテスト"""
        # ポジションなしの場合（マージンレベル0）
        risk_manager.account_info = {
            'balance': 100000.0,
            'equity': 100000.0,
            'margin_level': 0.0
        }
        
        result = risk_manager.check_risk_limits()
        assert result is True

    def test_check_max_positions_limit(self, risk_manager, sample_trades):
        """最大ポジション数制限チェックテスト"""
        # モックポジションを作成
        mock_positions = [
            Mock(symbol="USDJPY", type=0),
            Mock(symbol="EURJPY", type=1),
            Mock(symbol="GBPJPY", type=0),
        ]
        
        with patch.object(risk_manager, '_get_current_positions', return_value=mock_positions):
            # 最大3ポジションで現在3ポジション保有
            result = risk_manager.check_max_positions_limit()
            assert result is False
            
            # 最大ポジション数を増やす
            risk_manager.settings['max_positions'] = 5
            result = risk_manager.check_max_positions_limit()
            assert result is True

    def test_calculate_drawdown_no_trades(self, risk_manager):
        """取引履歴なしでのドローダウン計算テスト"""
        with patch.object(risk_manager, '_get_trade_history', return_value=[]):
            drawdown = risk_manager.calculate_drawdown()
            assert drawdown == 0.0

    def test_calculate_drawdown_with_profits(self, risk_manager):
        """利益のみの取引でのドローダウン計算テスト"""
        mock_trades = [
            Mock(profit_loss=1000, exit_time=datetime.now() - timedelta(days=2)),
            Mock(profit_loss=500, exit_time=datetime.now() - timedelta(days=1)),
            Mock(profit_loss=750, exit_time=datetime.now()),
        ]
        
        with patch.object(risk_manager, '_get_trade_history', return_value=mock_trades):
            drawdown = risk_manager.calculate_drawdown()
            assert drawdown == 0.0  # 利益のみなのでドローダウンなし

    def test_calculate_drawdown_with_losses(self, risk_manager):
        """損失を含む取引でのドローダウン計算テスト"""
        mock_trades = [
            Mock(profit_loss=1000, exit_time=datetime.now() - timedelta(days=5)),
            Mock(profit_loss=-500, exit_time=datetime.now() - timedelta(days=4)),
            Mock(profit_loss=-300, exit_time=datetime.now() - timedelta(days=3)),
            Mock(profit_loss=800, exit_time=datetime.now() - timedelta(days=2)),
            Mock(profit_loss=-200, exit_time=datetime.now() - timedelta(days=1)),
        ]
        
        with patch.object(risk_manager, '_get_trade_history', return_value=mock_trades):
            drawdown = risk_manager.calculate_drawdown()
            # 最大ドローダウンが計算されること
            assert drawdown > 0
            assert drawdown <= 20.0  # 設定された最大ドローダウン以下

    def test_check_drawdown_limit_success(self, risk_manager):
        """ドローダウン制限チェック成功テスト"""
        with patch.object(risk_manager, 'calculate_drawdown', return_value=15.0):
            result = risk_manager.check_drawdown_limit()
            assert result is True

    def test_check_drawdown_limit_failure(self, risk_manager):
        """ドローダウン制限チェック失敗テスト"""
        with patch.object(risk_manager, 'calculate_drawdown', return_value=25.0):
            result = risk_manager.check_drawdown_limit()
            assert result is False

    def test_validate_trade_request_success(self, risk_manager):
        """取引リクエスト検証成功テスト"""
        trade_request = {
            'symbol': 'USDJPY',
            'type': 'BUY',
            'volume': 0.1,
            'price': 130.25,
            'stop_loss': 129.75,
            'take_profit': 130.75
        }
        
        with patch.object(risk_manager, 'check_risk_limits', return_value=True):
            with patch.object(risk_manager, 'check_max_positions_limit', return_value=True):
                with patch.object(risk_manager, 'check_drawdown_limit', return_value=True):
                    result = risk_manager.validate_trade_request(trade_request)
                    assert result is True

    def test_validate_trade_request_risk_limits_fail(self, risk_manager):
        """リスク制限による取引リクエスト検証失敗テスト"""
        trade_request = {
            'symbol': 'USDJPY',
            'type': 'BUY',
            'volume': 0.1,
            'price': 130.25
        }
        
        with patch.object(risk_manager, 'check_risk_limits', return_value=False):
            result = risk_manager.validate_trade_request(trade_request)
            assert result is False

    def test_validate_trade_request_max_positions_fail(self, risk_manager):
        """最大ポジション数による取引リクエスト検証失敗テスト"""
        trade_request = {
            'symbol': 'USDJPY',
            'type': 'BUY',
            'volume': 0.1,
            'price': 130.25
        }
        
        with patch.object(risk_manager, 'check_risk_limits', return_value=True):
            with patch.object(risk_manager, 'check_max_positions_limit', return_value=False):
                result = risk_manager.validate_trade_request(trade_request)
                assert result is False

    def test_update_account_info(self, risk_manager):
        """口座情報更新テスト"""
        new_account_info = {
            'balance': 105000.0,
            'equity': 106000.0,
            'margin': 5000.0,
            'margin_free': 101000.0,
            'margin_level': 2120.0,
            'profit': 1000.0
        }
        
        risk_manager.update_account_info(new_account_info)
        
        assert risk_manager.account_info == new_account_info

    def test_update_settings(self, risk_manager):
        """設定更新テスト"""
        new_settings = {
            'max_risk_per_trade': 1.5,
            'max_drawdown': 15.0,
            'stop_loss_pips': 40,
            'take_profit_pips': 80,
            'max_positions': 2
        }
        
        risk_manager.update_settings(new_settings)
        
        for key, value in new_settings.items():
            assert risk_manager.settings[key] == value

    def test_get_risk_metrics(self, risk_manager):
        """リスクメトリクス取得テスト"""
        with patch.object(risk_manager, 'calculate_drawdown', return_value=10.5):
            with patch.object(risk_manager, '_get_current_positions', return_value=[Mock(), Mock()]):
                metrics = risk_manager.get_risk_metrics()
                
                assert 'current_drawdown' in metrics
                assert 'max_drawdown_limit' in metrics
                assert 'current_positions' in metrics
                assert 'max_positions_limit' in metrics
                assert 'equity_ratio' in metrics
                assert 'margin_level' in metrics
                
                assert metrics['current_drawdown'] == 10.5
                assert metrics['current_positions'] == 2
                assert metrics['equity_ratio'] == 100.0  # 100000/100000

    def test_pip_value_calculation(self, risk_manager):
        """Pip値計算テスト"""
        # JPY系通貨ペア
        pip_value = risk_manager._get_pip_value("USDJPY")
        assert pip_value == 1000.0
        
        pip_value = risk_manager._get_pip_value("EURJPY")
        assert pip_value == 1000.0
        
        # その他の通貨ペア（デフォルト）
        pip_value = risk_manager._get_pip_value("EURUSD")
        assert pip_value == 1000.0  # デフォルト値