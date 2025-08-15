"""
取引制御用のPydanticモデル
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


# ============= Enums =============

class OrderType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradingStatus(str, Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


class PositionType(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


# ============= Request Models =============

class TradingStartRequest(BaseModel):
    """取引開始リクエスト"""
    symbol: str = Field(..., description="通貨ペア", example="USDJPY")
    timeframe: str = Field(..., description="時間軸", example="H1")


class TradingStopRequest(BaseModel):
    """取引停止リクエスト"""
    close_positions: bool = Field(default=False, description="ポジションをクローズするか")


class TradingSettings(BaseModel):
    """取引設定"""
    max_risk_per_trade: float = Field(default=20.0, ge=1.0, le=100.0, description="1取引あたり最大リスク(%)")
    max_drawdown: float = Field(default=20.0, ge=1.0, le=50.0, description="最大ドローダウン(%)")
    use_nanpin: bool = Field(default=True, description="ナンピン使用")
    nanpin_max_count: int = Field(default=3, ge=1, le=10, description="ナンピン最大回数")
    nanpin_interval_pips: int = Field(default=10, ge=5, le=100, description="ナンピン間隔(pips)")
    trailing_stop_pips: int = Field(default=30, ge=10, le=200, description="トレーリングストップ(pips)")
    min_confidence: float = Field(default=0.7, ge=0.1, le=1.0, description="最小信頼度")
    check_interval_seconds: int = Field(default=60, ge=10, le=300, description="チェック間隔(秒)")
    trading_hours: Dict[str, str] = Field(
        default={"start": "09:00", "end": "17:00"},
        description="取引時間帯"
    )


class RiskSettingsUpdate(BaseModel):
    """リスク設定更新"""
    max_risk_per_trade: Optional[float] = Field(None, ge=1.0, le=100.0)
    max_drawdown: Optional[float] = Field(None, ge=1.0, le=50.0)
    use_nanpin: Optional[bool] = None
    nanpin_max_count: Optional[int] = Field(None, ge=1, le=10)
    stop_loss_pips: Optional[int] = Field(None, ge=5, le=500)
    take_profit_pips: Optional[int] = Field(None, ge=5, le=1000)


class PositionCloseRequest(BaseModel):
    """ポジションクローズリクエスト"""
    ticket: int = Field(..., description="ポジションチケット番号")
    volume: Optional[float] = Field(None, description="部分決済ボリューム")


class OrderPlaceRequest(BaseModel):
    """注文発注リクエスト"""
    symbol: str = Field(..., description="通貨ペア")
    order_type: OrderType = Field(..., description="注文タイプ")
    volume: float = Field(..., gt=0, description="ロット数")
    price: Optional[float] = Field(None, description="指値価格")
    sl: Optional[float] = Field(None, description="ストップロス")
    tp: Optional[float] = Field(None, description="テイクプロフィット")
    comment: Optional[str] = Field(None, description="コメント")


# ============= Response Models =============

class PositionResponse(BaseModel):
    """ポジション情報"""
    ticket: int = Field(..., description="チケット番号")
    symbol: str = Field(..., description="通貨ペア")
    type: str = Field(..., description="ポジションタイプ")
    volume: float = Field(..., description="ロット数")
    price_open: float = Field(..., description="オープン価格")
    price_current: float = Field(..., description="現在価格")
    profit: float = Field(..., description="損益")
    swap: float = Field(..., description="スワップ")
    time: datetime = Field(..., description="オープン時刻")
    comment: Optional[str] = Field(None, description="コメント")
    magic: int = Field(..., description="マジックナンバー")


class TradeHistoryResponse(BaseModel):
    """取引履歴"""
    trade_id: int = Field(..., description="取引ID")
    symbol: str = Field(..., description="通貨ペア")
    order_type: str = Field(..., description="注文タイプ")
    entry_time: datetime = Field(..., description="エントリー時刻")
    exit_time: Optional[datetime] = Field(None, description="エグジット時刻")
    entry_price: float = Field(..., description="エントリー価格")
    exit_price: Optional[float] = Field(None, description="エグジット価格")
    volume: float = Field(..., description="ロット数")
    profit_loss: Optional[float] = Field(None, description="損益")
    comment: Optional[str] = Field(None, description="コメント")


class TradingStatusResponse(BaseModel):
    """取引状態レスポンス"""
    is_active: bool = Field(..., description="取引が有効かどうか")
    symbol: Optional[str] = Field(None, description="監視中の通貨ペア")
    timeframe: Optional[str] = Field(None, description="時間軸")
    model_loaded: bool = Field(..., description="モデルが読み込まれているか")
    current_positions: int = Field(..., description="現在のポジション数")
    positions: Dict[str, Any] = Field(default_factory=dict, description="ポジション詳細")
    risk_status: Dict[str, Any] = Field(default_factory=dict, description="リスク状態")
    last_update: str = Field(..., description="最終更新時刻")


class AccountInfoResponse(BaseModel):
    """アカウント情報レスポンス"""
    login: int = Field(..., description="ログイン番号")
    balance: float = Field(..., description="残高")
    equity: float = Field(..., description="有効証拠金")
    margin: float = Field(..., description="必要証拠金")
    free_margin: float = Field(..., description="余剰証拠金")
    margin_level: float = Field(..., description="証拠金維持率")
    profit: float = Field(..., description="損益")
    currency: str = Field(..., description="通貨")
    server: str = Field(..., description="サーバー名")


class TradingStatistics(BaseModel):
    """取引統計"""
    total_trades: int = Field(..., description="総取引数")
    winning_trades: int = Field(..., description="勝利取引数")
    win_rate: float = Field(..., description="勝率(%)")
    total_profit: float = Field(..., description="総損益")
    average_profit: float = Field(..., description="平均損益")
    max_drawdown: float = Field(..., description="最大ドローダウン")
    profit_factor: float = Field(..., description="プロフィットファクター")


class RiskStatusResponse(BaseModel):
    """リスク状態レスポンス"""
    current_drawdown: float = Field(..., description="現在のドローダウン(%)")
    max_risk_per_trade: float = Field(..., description="1取引あたり最大リスク(%)")
    emergency_stop_active: bool = Field(..., description="緊急停止が有効か")
    risk_warnings: List[str] = Field(default_factory=list, description="リスク警告")
    position_count: int = Field(..., description="現在のポジション数")
    total_exposure: float = Field(..., description="総エクスポージャー")


# ============= API Response Models =============

class TradingApiError(BaseModel):
    """APIエラー"""
    error_code: str = Field(..., description="エラーコード")
    error_message: str = Field(..., description="エラーメッセージ")


class TradingApiWarning(BaseModel):
    """API警告"""
    warning_code: str = Field(..., description="警告コード")
    warning_message: str = Field(..., description="警告メッセージ")
    severity: str = Field(..., description="重要度")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")


class TradingApiResponse(BaseModel):
    """統一APIレスポンス"""
    status: str = Field(..., description="ステータス", example="success")
    message: str = Field(..., description="メッセージ")
    data: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="データ")
    errors: Optional[List[TradingApiError]] = Field(None, description="エラー一覧")
    warnings: Optional[List[TradingApiWarning]] = Field(None, description="警告一覧")
    execution_time_ms: Optional[int] = Field(None, description="実行時間(ミリ秒)")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="タイムスタンプ")


# ============= WebSocket Models =============

class TradingUpdate(BaseModel):
    """取引更新通知"""
    type: str = Field(..., description="更新タイプ")
    symbol: str = Field(..., description="通貨ペア")
    data: Dict[str, Any] = Field(..., description="更新データ")
    timestamp: datetime = Field(default_factory=datetime.now, description="タイムスタンプ")


class PositionUpdate(BaseModel):
    """ポジション更新通知"""
    action: str = Field(..., description="アクション", example="opened")
    position: PositionResponse = Field(..., description="ポジション情報")
    timestamp: datetime = Field(default_factory=datetime.now, description="タイムスタンプ")


class PriceUpdate(BaseModel):
    """価格更新通知"""
    symbol: str = Field(..., description="通貨ペア")
    bid: float = Field(..., description="ビッド価格")
    ask: float = Field(..., description="アスク価格")
    timestamp: datetime = Field(default_factory=datetime.now, description="タイムスタンプ")


class SignalUpdate(BaseModel):
    """シグナル更新通知"""
    symbol: str = Field(..., description="通貨ペア")
    signal: str = Field(..., description="シグナル")
    confidence: float = Field(..., description="信頼度")
    timestamp: datetime = Field(default_factory=datetime.now, description="タイムスタンプ")


# ============= Configuration Models =============

class TradingConfig(BaseModel):
    """取引設定"""
    symbols: List[str] = Field(default_factory=list, description="監視通貨ペア")
    default_timeframe: str = Field(default="H1", description="デフォルト時間軸")
    risk_settings: TradingSettings = Field(default_factory=TradingSettings, description="リスク設定")
    notification_settings: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email_alerts": True,
            "webhook_notifications": True,
            "emergency_stop_alerts": True
        },
        description="通知設定"
    )


class BacktestTradingConfig(BaseModel):
    """バックテスト用取引設定"""
    initial_balance: float = Field(default=100000.0, description="初期残高")
    commission_per_lot: float = Field(default=500.0, description="手数料/ロット")
    spread_pips: float = Field(default=1.5, description="スプレッド(pips)")
    slippage_pips: float = Field(default=0.5, description="スリッページ(pips)")
    margin_requirement: float = Field(default=0.01, description="証拠金率")


# ============= Validation Models =============

class TradingValidation(BaseModel):
    """取引検証"""
    is_valid: bool = Field(..., description="検証結果")
    errors: List[str] = Field(default_factory=list, description="エラーメッセージ")
    warnings: List[str] = Field(default_factory=list, description="警告メッセージ")


class SymbolValidation(BaseModel):
    """通貨ペア検証"""
    symbol: str = Field(..., description="通貨ペア")
    is_tradeable: bool = Field(..., description="取引可能か")
    market_hours: Dict[str, str] = Field(default_factory=dict, description="市場時間")
    contract_size: float = Field(..., description="契約サイズ")
    min_lot: float = Field(..., description="最小ロット")
    max_lot: float = Field(..., description="最大ロット")
    lot_step: float = Field(..., description="ロット刻み")


# ============= Monitoring Models =============

class TradingMetrics(BaseModel):
    """取引メトリクス"""
    timestamp: datetime = Field(default_factory=datetime.now, description="タイムスタンプ")
    active_positions: int = Field(..., description="アクティブポジション数")
    total_profit: float = Field(..., description="総損益")
    daily_profit: float = Field(..., description="日次損益")
    drawdown: float = Field(..., description="ドローダウン(%)")
    margin_level: float = Field(..., description="証拠金維持率(%)")
    signals_generated: int = Field(..., description="生成シグナル数")
    trades_executed: int = Field(..., description="実行取引数")


class SystemHealthMetrics(BaseModel):
    """システムヘルスメトリクス"""
    timestamp: datetime = Field(default_factory=datetime.now, description="タイムスタンプ")
    mt5_connection: bool = Field(..., description="MT5接続状態")
    database_connection: bool = Field(..., description="DB接続状態")
    model_loaded: bool = Field(..., description="モデル読み込み状態")
    trading_engine_active: bool = Field(..., description="取引エンジン状態")
    last_signal_time: Optional[datetime] = Field(None, description="最終シグナル時刻")
    last_trade_time: Optional[datetime] = Field(None, description="最終取引時刻")
    error_count: int = Field(default=0, description="エラー数")
    warning_count: int = Field(default=0, description="警告数")