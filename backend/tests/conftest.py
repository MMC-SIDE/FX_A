"""
テスト設定とフィクスチャ
"""
import pytest
import asyncio
import os
import tempfile
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# テスト実行時にログディレクトリを作成
os.makedirs("logs", exist_ok=True)

# テスト用の設定でアプリをインポート
os.environ["TESTING"] = "1"
from backend.main import app
from backend.core.database import Base, get_db
from backend.core.mt5_client import MT5Client
from backend.models.backtest_models import Trade, Position, PriceData

# テスト用データベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """イベントループフィクスチャ"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def db_session():
    """テスト用データベースセッション"""
    # テーブル作成
    Base.metadata.create_all(bind=engine)
    
    # セッション作成
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        # テーブル削除
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    """FastAPIテストクライアント"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_mt5_client():
    """MT5クライアントのモック"""
    mock = Mock(spec=MT5Client)
    
    # 接続関連
    mock.connect.return_value = True
    mock.disconnect.return_value = True
    mock.is_connected.return_value = True
    
    # 価格データモック
    mock.get_rates.return_value = pd.DataFrame({
        'time': pd.date_range('2023-01-01', periods=100, freq='H'),
        'open': np.random.normal(130, 1, 100),
        'high': np.random.normal(130.5, 1, 100),
        'low': np.random.normal(129.5, 1, 100),
        'close': np.random.normal(130, 1, 100),
        'tick_volume': np.random.randint(100, 1000, 100)
    })
    
    # ティックデータモック
    mock_tick = Mock()
    mock_tick.ask = 130.25
    mock_tick.bid = 130.23
    mock_tick.time = 1640995200  # 2023-01-01 00:00:00
    mock.get_tick.return_value = mock_tick
    
    # 口座情報モック
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
    mock.get_account_info.return_value = mock_account
    
    # ポジション情報モック
    mock.get_positions.return_value = []
    
    # 注文関連モック
    mock.send_order.return_value = {
        'success': True,
        'order_id': 12345,
        'message': 'Order placed successfully'
    }
    
    mock.close_position.return_value = {
        'success': True,
        'message': 'Position closed successfully'
    }
    
    return mock

@pytest.fixture
def sample_price_data():
    """サンプル価格データ"""
    np.random.seed(42)  # 再現可能な結果のため
    
    dates = pd.date_range('2023-01-01', periods=1000, freq='H')
    
    # ランダムウォークで価格データ生成
    base_price = 130.0
    price_changes = np.random.normal(0, 0.01, 1000)
    prices = base_price + np.cumsum(price_changes)
    
    # OHLC生成
    opens = prices
    highs = opens + np.abs(np.random.normal(0, 0.005, 1000))
    lows = opens - np.abs(np.random.normal(0, 0.005, 1000))
    closes = opens + np.random.normal(0, 0.002, 1000)
    
    return pd.DataFrame({
        'time': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'tick_volume': np.random.randint(100, 1000, 1000)
    })

@pytest.fixture
def sample_trades(db_session):
    """サンプル取引データ"""
    trades = []
    
    for i in range(10):
        trade = Trade(
            symbol='USDJPY',
            order_type='BUY' if i % 2 == 0 else 'SELL',
            entry_time=pd.Timestamp('2023-01-01') + pd.Timedelta(hours=i),
            entry_price=130.0 + (i * 0.1),
            exit_time=pd.Timestamp('2023-01-01') + pd.Timedelta(hours=i+1),
            exit_price=130.0 + (i * 0.1) + (0.05 if i % 2 == 0 else -0.05),
            volume=0.1,
            profit_loss=500 if i % 2 == 0 else -300
        )
        trades.append(trade)
        db_session.add(trade)
    
    db_session.commit()
    return trades

@pytest.fixture
def sample_positions():
    """サンプルポジションデータ"""
    return [
        {
            'id': '1',
            'symbol': 'USDJPY',
            'type': 'BUY',
            'volume': 0.1,
            'open_price': 130.00,
            'current_price': 130.25,
            'profit': 250,
            'open_time': '2023-01-01T09:00:00Z'
        },
        {
            'id': '2',
            'symbol': 'EURJPY',
            'type': 'SELL',
            'volume': 0.05,
            'open_price': 145.50,
            'current_price': 145.30,
            'profit': 100,
            'open_time': '2023-01-01T10:00:00Z'
        }
    ]

@pytest.fixture
def mock_websocket_manager():
    """WebSocketマネージャーのモック"""
    mock = Mock()
    mock.connect.return_value = "test_connection_id"
    mock.disconnect.return_value = None
    mock.send_personal_message = MagicMock(return_value=True)
    mock.broadcast = MagicMock(return_value=5)
    mock.get_connection_count.return_value = 1
    return mock

@pytest.fixture
def mock_alert_manager():
    """アラートマネージャーのモック"""
    mock = Mock()
    mock.send_alert = MagicMock(return_value="alert_id_123")
    mock.acknowledge_alert = MagicMock(return_value=True)
    mock.dismiss_alert = MagicMock(return_value=True)
    mock.get_active_alerts.return_value = []
    mock.get_alert_stats.return_value = {
        'total_alerts': 0,
        'active_alerts_count': 0,
        'unacknowledged_count': 0
    }
    return mock

@pytest.fixture
def temp_log_file():
    """一時ログファイル"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        # サンプルログデータ書き込み
        log_lines = [
            "2023-01-01 12:00:00,123 - trading - INFO - Trade executed: USDJPY BUY 0.1",
            "2023-01-01 12:01:00,456 - system - WARNING - High CPU usage: 85%",
            "2023-01-01 12:02:00,789 - mt5 - ERROR - Connection lost to MT5 server",
            "2023-01-01 12:03:00,012 - trading - INFO - Position closed: USDJPY profit: 500",
        ]
        
        for line in log_lines:
            f.write(line + '\n')
        
        temp_file_path = f.name
    
    yield temp_file_path
    
    # クリーンアップ
    try:
        os.unlink(temp_file_path)
    except OSError:
        pass

@pytest.fixture
def backtest_request_data():
    """バックテストリクエストデータ"""
    return {
        "symbol": "USDJPY",
        "timeframe": "H1",
        "start_date": "2023-01-01",
        "end_date": "2023-01-31",
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

@pytest.fixture
def mock_lightgbm_model():
    """LightGBMモデルのモック"""
    mock_model = Mock()
    
    # 予測結果モック
    mock_model.predict.return_value = (
        np.array([0, 1, 2, 1, 0]),  # predictions
        np.array([0.8, 0.7, 0.9, 0.6, 0.75])  # confidence
    )
    
    # 学習結果モック
    mock_model.train.return_value = {
        'accuracy': 0.85,
        'f1': 0.82,
        'precision': 0.88,
        'recall': 0.79
    }
    
    # 特徴量重要度モック
    mock_model.feature_importance_.return_value = {
        'rsi': 0.25,
        'macd': 0.20,
        'bollinger': 0.15,
        'volume': 0.10,
        'price_change': 0.30
    }
    
    return mock_model

# テスト用のヘルパー関数

def create_test_price_data(db_session, symbol="USDJPY", count=100):
    """テスト用価格データをDBに作成"""
    price_data_list = []
    
    for i in range(count):
        price_data = PriceData(
            symbol=symbol,
            timeframe="H1",
            time=pd.Timestamp('2023-01-01') + pd.Timedelta(hours=i),
            open=130.0 + (i * 0.01),
            high=130.5 + (i * 0.01),
            low=129.5 + (i * 0.01),
            close=130.0 + (i * 0.01) + np.random.normal(0, 0.1),
            tick_volume=np.random.randint(100, 1000)
        )
        price_data_list.append(price_data)
        db_session.add(price_data)
    
    db_session.commit()
    return price_data_list

def assert_response_success(response, expected_keys=None):
    """レスポンス成功アサーション"""
    assert response.status_code == 200
    data = response.json()
    
    if expected_keys:
        for key in expected_keys:
            assert key in data
    
    return data

def assert_response_error(response, expected_status=400):
    """レスポンスエラーアサーション"""
    assert response.status_code == expected_status
    data = response.json()
    assert 'detail' in data or 'error' in data
    return data

# テスト用定数
TEST_SYMBOLS = ['USDJPY', 'EURJPY', 'GBPJPY']
TEST_TIMEFRAMES = ['M1', 'M5', 'H1', 'H4', 'D1']
TEST_ORDER_TYPES = ['BUY', 'SELL']