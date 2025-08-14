"""
リスク管理関連のPydanticモデル
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime

class RiskSettingsModel(BaseModel):
    """リスク設定モデル"""
    max_risk_per_trade: Optional[float] = Field(None, ge=0.1, le=100, description="1取引あたりの最大リスク(%)")
    max_drawdown: Optional[float] = Field(None, ge=1, le=100, description="最大ドローダウン(%)")
    use_nanpin: Optional[bool] = Field(None, description="ナンピン機能の使用")
    nanpin_max_count: Optional[int] = Field(None, ge=1, le=10, description="ナンピン最大回数")
    nanpin_interval_pips: Optional[int] = Field(None, ge=5, le=100, description="ナンピン間隔(pips)")
    stop_loss_pips: Optional[int] = Field(None, ge=5, le=500, description="ストップロス(pips)")
    take_profit_pips: Optional[int] = Field(None, ge=5, le=1000, description="テイクプロフィット(pips)")
    trailing_stop_pips: Optional[int] = Field(None, ge=5, le=200, description="トレーリングストップ(pips)")
    risk_reward_ratio: Optional[float] = Field(None, ge=0.5, le=10, description="リスクリワード比率")
    max_positions: Optional[int] = Field(None, ge=1, le=20, description="最大ポジション数")
    max_daily_trades: Optional[int] = Field(None, ge=1, le=100, description="日次最大取引数")
    min_confidence_score: Optional[float] = Field(None, ge=0.1, le=1.0, description="最小信頼度スコア")
    max_consecutive_losses: Optional[int] = Field(None, ge=1, le=20, description="最大連続損失回数")
    daily_loss_limit: Optional[float] = Field(None, ge=0.1, le=50, description="日次損失制限(%)")
    margin_level_limit: Optional[float] = Field(None, ge=100, le=1000, description="証拠金維持率制限(%)")

    @validator('risk_reward_ratio')
    def validate_risk_reward_ratio(cls, v):
        if v is not None and v < 1.0:
            # リスクリワード比率が1未満の場合は警告ログ出力
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Risk reward ratio is less than 1.0: {v}")
        return v

    @validator('max_risk_per_trade')
    def validate_max_risk_per_trade(cls, v):
        if v is not None and v > 10.0:
            # 10%を超える場合は警告
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"High risk per trade setting: {v}%")
        return v

class RiskStatusResponse(BaseModel):
    """リスク状態レスポンスモデル"""
    emergency_stop: bool
    current_drawdown: float
    max_allowed_drawdown: float
    current_positions: int
    max_positions: int
    daily_pnl: float
    consecutive_losses: int
    margin_level: Optional[float]
    risk_settings: Dict[str, Any]
    last_updated: datetime

class DrawdownStatistics(BaseModel):
    """ドローダウン統計モデル"""
    current_drawdown: float
    max_drawdown: float
    average_drawdown: float
    drawdown_frequency: int
    longest_drawdown_period: int
    recovery_factor: float
    current_peak_equity: float
    days_in_drawdown: int
    time_to_recovery: Optional[int]

class AccountInfoModel(BaseModel):
    """アカウント情報モデル"""
    login: int
    server: str
    name: str
    company: str
    currency: str
    balance: float
    equity: float
    margin: float
    margin_free: float
    margin_level: float

class RiskAlertModel(BaseModel):
    """リスクアラートモデル"""
    alert_type: str = Field(description="アラートタイプ (drawdown_warning, margin_low, consecutive_losses)")
    level: str = Field(description="レベル (warning, critical, emergency)")
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    action_required: bool = Field(default=False, description="アクション要求の有無")

class EmergencyStopRequest(BaseModel):
    """緊急停止リクエストモデル"""
    reason: str = Field(default="Manual emergency stop", description="停止理由")
    close_all_positions: bool = Field(default=True, description="全ポジションクローズの有無")

class RiskLimitCheckResult(BaseModel):
    """リスク制限チェック結果モデル"""
    can_trade: bool
    failed_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    risk_score: float = Field(description="リスクスコア (0-100)")
    
class PositionSizingRequest(BaseModel):
    """ポジションサイジングリクエストモデル"""
    symbol: str
    order_type: str = Field(pattern="^(BUY|SELL)$")
    entry_price: Optional[float] = None
    account_balance: Optional[float] = None

class PositionSizingResponse(BaseModel):
    """ポジションサイジングレスポンスモデル"""
    lot_size: float
    risk_amount: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_percentage: float
    calculated_at: datetime

class TradeRiskAnalysis(BaseModel):
    """取引リスク分析モデル"""
    symbol: str
    potential_loss: float
    potential_profit: float
    risk_reward_ratio: float
    win_probability: Optional[float]
    expected_value: Optional[float]
    recommendation: str = Field(description="推奨アクション (TAKE, AVOID, REDUCE_SIZE)")

class RiskMetrics(BaseModel):
    """リスクメトリクスモデル"""
    var_95: float = Field(description="95% Value at Risk")
    var_99: float = Field(description="99% Value at Risk")
    expected_shortfall: float = Field(description="期待ショートフォール")
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    max_drawdown_duration: int = Field(description="最大ドローダウン期間（日）")
    recovery_time: Optional[int] = Field(description="回復時間（日）")
    profit_factor: Optional[float]
    
class RiskReportRequest(BaseModel):
    """リスクレポートリクエストモデル"""
    start_date: datetime
    end_date: datetime
    include_positions: bool = Field(default=True)
    include_metrics: bool = Field(default=True)
    format: str = Field(default="json", pattern="^(json|pdf|csv)$")

class RiskReportResponse(BaseModel):
    """リスクレポートレスポンスモデル"""
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    max_drawdown: float
    risk_metrics: RiskMetrics
    drawdown_statistics: DrawdownStatistics
    risk_violations: list[RiskAlertModel]
    recommendations: list[str]
    generated_at: datetime