"""
MT5Client単体テスト
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, Mock, MagicMock
import MetaTrader5 as mt5
from datetime import datetime

from backend.core.mt5_client import MT5Client


class TestMT5Client:
    """MT5Clientのテストクラス"""

    def test_init_with_config_file(self):
        """設定ファイルありの初期化テスト"""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open_with_config()):
                client = MT5Client("test_config.json")
                assert client.config_file == "test_config.json"
                assert client.login == 12345678
                assert client.password == "test_password"
                assert client.server == "XMTrading-Real 52"

    def test_init_without_config_file(self):
        """設定ファイルなしの初期化テスト"""
        with patch('os.path.exists', return_value=False):
            client = MT5Client("nonexistent_config.json")
            assert client.config_file == "nonexistent_config.json"
            assert client.login is None
            assert client.password is None
            assert client.server is None

    @patch('MetaTrader5.initialize')
    @patch('MetaTrader5.login')
    def test_connect_success(self, mock_login, mock_initialize):
        """MT5接続成功テスト"""
        # モック設定
        mock_initialize.return_value = True
        mock_login.return_value = True
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open_with_config()):
                client = MT5Client("test_config.json")
                result = client.connect()
                
                assert result is True
                assert client.connected is True
                mock_initialize.assert_called_once()
                mock_login.assert_called_once_with(12345678, password="test_password", server="XMTrading-Real 52")

    @patch('MetaTrader5.initialize')
    def test_connect_initialize_failure(self, mock_initialize):
        """MT5初期化失敗テスト"""
        mock_initialize.return_value = False
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open_with_config()):
                client = MT5Client("test_config.json")
                result = client.connect()
                
                assert result is False
                assert client.connected is False

    @patch('MetaTrader5.initialize')
    @patch('MetaTrader5.login')
    def test_connect_login_failure(self, mock_login, mock_initialize):
        """MT5ログイン失敗テスト"""
        mock_initialize.return_value = True
        mock_login.return_value = False
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open_with_config()):
                client = MT5Client("test_config.json")
                result = client.connect()
                
                assert result is False
                assert client.connected is False

    def test_connect_without_config(self):
        """設定ファイルなしでの接続テスト"""
        with patch('os.path.exists', return_value=False):
            client = MT5Client("nonexistent_config.json")
            result = client.connect()
            
            assert result is False
            assert client.connected is False

    @patch('MetaTrader5.shutdown')
    def test_disconnect(self, mock_shutdown):
        """切断テスト"""
        client = MT5Client()
        client.connected = True
        
        client.disconnect()
        
        assert client.connected is False
        mock_shutdown.assert_called_once()

    def test_is_connected_true(self):
        """接続状態確認テスト（接続中）"""
        client = MT5Client()
        client.connected = True
        
        assert client.is_connected() is True

    def test_is_connected_false(self):
        """接続状態確認テスト（未接続）"""
        client = MT5Client()
        client.connected = False
        
        assert client.is_connected() is False

    @patch('MetaTrader5.copy_rates_from_pos')
    def test_get_rates_success(self, mock_copy_rates):
        """価格データ取得成功テスト"""
        # モックデータ作成
        mock_rates = np.array([
            (1640995200, 130.00, 130.50, 129.50, 130.25, 1000, 5, 1000),
            (1640998800, 130.25, 130.75, 130.00, 130.50, 1200, 5, 1200),
        ], dtype=[
            ('time', 'i8'), ('open', 'f8'), ('high', 'f8'), 
            ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'),
            ('spread', 'i4'), ('real_volume', 'i8')
        ])
        
        mock_copy_rates.return_value = mock_rates
        
        client = MT5Client()
        client.connected = True
        
        result = client.get_rates("USDJPY", mt5.TIMEFRAME_H1, 2)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ['time', 'open', 'high', 'low', 'close', 'tick_volume']
        assert result.iloc[0]['close'] == 130.25
        assert result.iloc[1]['close'] == 130.50
        
        mock_copy_rates.assert_called_once_with("USDJPY", mt5.TIMEFRAME_H1, 0, 2)

    @patch('MetaTrader5.copy_rates_from_pos')
    def test_get_rates_no_data(self, mock_copy_rates):
        """価格データ取得失敗テスト（データなし）"""
        mock_copy_rates.return_value = None
        
        client = MT5Client()
        client.connected = True
        
        result = client.get_rates("INVALID", mt5.TIMEFRAME_H1, 100)
        
        assert result.empty

    def test_get_rates_not_connected(self):
        """未接続時の価格データ取得テスト"""
        client = MT5Client()
        client.connected = False
        
        result = client.get_rates("USDJPY", mt5.TIMEFRAME_H1, 100)
        
        assert result.empty

    @patch('MetaTrader5.symbol_info_tick')
    def test_get_tick_success(self, mock_symbol_info_tick):
        """ティック取得成功テスト"""
        mock_tick = Mock()
        mock_tick.ask = 130.25
        mock_tick.bid = 130.23
        mock_tick.time = 1640995200
        mock_tick.flags = 6
        mock_tick.volume = 1
        
        mock_symbol_info_tick.return_value = mock_tick
        
        client = MT5Client()
        client.connected = True
        
        result = client.get_tick("USDJPY")
        
        assert result == mock_tick
        mock_symbol_info_tick.assert_called_once_with("USDJPY")

    @patch('MetaTrader5.symbol_info_tick')
    def test_get_tick_no_data(self, mock_symbol_info_tick):
        """ティック取得失敗テスト"""
        mock_symbol_info_tick.return_value = None
        
        client = MT5Client()
        client.connected = True
        
        result = client.get_tick("INVALID")
        
        assert result is None

    def test_get_tick_not_connected(self):
        """未接続時のティック取得テスト"""
        client = MT5Client()
        client.connected = False
        
        result = client.get_tick("USDJPY")
        
        assert result is None

    @patch('MetaTrader5.account_info')
    def test_get_account_info_success(self, mock_account_info):
        """口座情報取得成功テスト"""
        mock_account = Mock()
        mock_account.login = 12345678
        mock_account.balance = 100000.0
        mock_account.equity = 100000.0
        mock_account.margin = 0.0
        mock_account.margin_free = 100000.0
        mock_account.margin_level = 0.0
        mock_account.profit = 0.0
        mock_account.currency = "JPY"
        mock_account.server = "XMTrading-Real 52"
        mock_account.company = "XM"
        
        mock_account_info.return_value = mock_account
        
        client = MT5Client()
        client.connected = True
        
        result = client.get_account_info()
        
        assert result == mock_account
        mock_account_info.assert_called_once()

    def test_get_account_info_not_connected(self):
        """未接続時の口座情報取得テスト"""
        client = MT5Client()
        client.connected = False
        
        result = client.get_account_info()
        
        assert result is None

    @patch('MetaTrader5.positions_get')
    def test_get_positions_success(self, mock_positions_get):
        """ポジション取得成功テスト"""
        mock_position1 = Mock()
        mock_position1.ticket = 123456
        mock_position1.symbol = "USDJPY"
        mock_position1.type = 0  # BUY
        mock_position1.volume = 0.1
        mock_position1.price_open = 130.00
        mock_position1.price_current = 130.25
        mock_position1.profit = 250.0
        
        mock_position2 = Mock()
        mock_position2.ticket = 123457
        mock_position2.symbol = "EURJPY"
        mock_position2.type = 1  # SELL
        mock_position2.volume = 0.05
        mock_position2.price_open = 145.50
        mock_position2.price_current = 145.30
        mock_position2.profit = 100.0
        
        mock_positions_get.return_value = [mock_position1, mock_position2]
        
        client = MT5Client()
        client.connected = True
        
        result = client.get_positions()
        
        assert len(result) == 2
        assert result[0] == mock_position1
        assert result[1] == mock_position2
        mock_positions_get.assert_called_once()

    def test_get_positions_not_connected(self):
        """未接続時のポジション取得テスト"""
        client = MT5Client()
        client.connected = False
        
        result = client.get_positions()
        
        assert result == []

    @patch('MetaTrader5.order_send')
    def test_send_order_success(self, mock_order_send):
        """注文送信成功テスト"""
        mock_result = Mock()
        mock_result.retcode = mt5.TRADE_RETCODE_DONE
        mock_result.order = 123456
        mock_result.comment = "Request executed"
        
        mock_order_send.return_value = mock_result
        
        client = MT5Client()
        client.connected = True
        
        order_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "USDJPY",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 130.25,
            "sl": 129.75,
            "tp": 130.75,
            "deviation": 20,
            "magic": 12345,
            "comment": "Test order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = client.send_order(order_request)
        
        assert result["success"] is True
        assert result["order_id"] == 123456
        assert "successfully" in result["message"]
        mock_order_send.assert_called_once_with(order_request)

    @patch('MetaTrader5.order_send')
    def test_send_order_failure(self, mock_order_send):
        """注文送信失敗テスト"""
        mock_result = Mock()
        mock_result.retcode = mt5.TRADE_RETCODE_INVALID_PRICE
        mock_result.order = 0
        mock_result.comment = "Invalid price"
        
        mock_order_send.return_value = mock_result
        
        client = MT5Client()
        client.connected = True
        
        order_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "USDJPY",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,  # 無効な価格
        }
        
        result = client.send_order(order_request)
        
        assert result["success"] is False
        assert result["order_id"] is None
        assert "Invalid price" in result["message"]

    def test_send_order_not_connected(self):
        """未接続時の注文送信テスト"""
        client = MT5Client()
        client.connected = False
        
        order_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "USDJPY",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 130.25,
        }
        
        result = client.send_order(order_request)
        
        assert result["success"] is False
        assert "not connected" in result["message"]

    @patch('MetaTrader5.order_send')
    def test_close_position_success(self, mock_order_send):
        """ポジション決済成功テスト"""
        mock_result = Mock()
        mock_result.retcode = mt5.TRADE_RETCODE_DONE
        mock_result.order = 123457
        mock_result.comment = "Position closed"
        
        mock_order_send.return_value = mock_result
        
        client = MT5Client()
        client.connected = True
        
        result = client.close_position(123456, "USDJPY", 0.1, 130.50)
        
        assert result["success"] is True
        assert "successfully" in result["message"]
        mock_order_send.assert_called_once()

    def test_close_position_not_connected(self):
        """未接続時のポジション決済テスト"""
        client = MT5Client()
        client.connected = False
        
        result = client.close_position(123456, "USDJPY", 0.1, 130.50)
        
        assert result["success"] is False
        assert "not connected" in result["message"]

    def test_test_connection_success(self):
        """接続テスト成功"""
        with patch.object(MT5Client, 'connect', return_value=True):
            with patch.object(MT5Client, 'disconnect'):
                client = MT5Client()
                result = client.test_connection()
                
                assert result["success"] is True
                assert "successful" in result["message"]

    def test_test_connection_failure(self):
        """接続テスト失敗"""
        with patch.object(MT5Client, 'connect', return_value=False):
            client = MT5Client()
            result = client.test_connection()
            
            assert result["success"] is False
            assert "failed" in result["message"]


def mock_open_with_config():
    """設定ファイルのモック"""
    mock_config = '''
    {
        "login": 12345678,
        "password": "test_password",
        "server": "XMTrading-Real 52"
    }
    '''
    return Mock(return_value=Mock(read=Mock(return_value=mock_config)))