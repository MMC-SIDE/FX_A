"""
バックテスト関連のPydanticモデル
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

class TimeframeEnum(str, Enum):
    """時間軸列挙"""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"

class SymbolEnum(str, Enum):
    """通貨ペア列挙"""
    USDJPY = "USDJPY"
    EURJPY = "EURJPY"
    GBPJPY = "GBPJPY"
    AUDJPY = "AUDJPY"
    NZDJPY = "NZDJPY"
    CADJPY = "CADJPY"
    CHFJPY = "CHFJPY"

class OptimizationMethodEnum(str, Enum):
    """最適化手法列挙"""
    GRID = "grid"
    RANDOM = "random"
    BAYESIAN = "bayesian"

class OptimizationMetricEnum(str, Enum):
    """最適化指標列挙"""
    SHARPE_RATIO = "sharpe_ratio"
    PROFIT_FACTOR = "profit_factor"
    NET_PROFIT = "net_profit"
    WIN_RATE = "win_rate"
    CALMAR_RATIO = "calmar_ratio"
    SORTINO_RATIO = "sortino_ratio"

class ParameterRange(BaseModel):
    """パラメータ範囲定義"""
    min: Union[float, int]
    max: Union[float, int]
    step: Optional[Union[float, int]] = None

class BacktestRequest(BaseModel):
    """バックテストリクエスト"""
    symbol: SymbolEnum
    timeframe: TimeframeEnum
    start_date: datetime
    end_date: datetime
    initial_balance: float = Field(default=100000, gt=0, description="初期残高")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="戦略パラメータ")

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

    @validator('start_date', 'end_date')
    def dates_not_future(cls, v):
        # Convert both datetimes to naive for comparison
        now = datetime.now()
        if v.tzinfo is not None:
            # If v has timezone info, convert to naive
            v_naive = v.replace(tzinfo=None)
        else:
            v_naive = v
        
        if v_naive > now:
            raise ValueError('Date cannot be in the future')
        return v

class OptimizationRequest(BaseModel):
    """パラメータ最適化リクエスト"""
    symbol: SymbolEnum
    timeframe: TimeframeEnum
    start_date: datetime
    end_date: datetime
    parameter_ranges: Dict[str, Union[ParameterRange, List[Any], Any]]
    optimization_metric: OptimizationMetricEnum = OptimizationMetricEnum.SHARPE_RATIO
    optimization_method: OptimizationMethodEnum = OptimizationMethodEnum.RANDOM
    max_iterations: int = Field(default=100, gt=0, le=1000, description="最大反復回数")
    initial_balance: float = Field(default=100000, gt=0, description="初期残高")

class ComprehensiveBacktestRequest(BaseModel):
    """包括的バックテストリクエスト"""
    symbols: Optional[List[SymbolEnum]] = None
    timeframes: Optional[List[TimeframeEnum]] = None
    test_period_months: int = Field(default=12, gt=0, le=60, description="テスト期間（月）")
    parameter_ranges: Optional[Dict[str, Union[ParameterRange, List[Any], Any]]] = None
    optimization_metric: OptimizationMetricEnum = OptimizationMetricEnum.SHARPE_RATIO
    initial_balance: float = Field(default=100000, gt=0, description="初期残高")

class TradeResult(BaseModel):
    """取引結果"""
    entry_time: datetime
    exit_time: datetime
    type: str = Field(pattern="^(BUY|SELL)$")
    entry_price: float
    exit_price: float
    lot_size: float
    profit_loss: float
    duration_hours: float
    exit_reason: str
    nanpin_count: int = Field(default=0, ge=0)
    commission: float = Field(default=0, ge=0)

class EquityPoint(BaseModel):
    """エクイティカーブポイント"""
    timestamp: datetime
    equity: float
    balance: float
    unrealized_pnl: float = Field(default=0)
    position: Optional[str] = None
    price: Optional[float] = None

class BacktestStatistics(BaseModel):
    """バックテスト統計"""
    total_trades: int = Field(ge=0)
    winning_trades: int = Field(ge=0)
    losing_trades: int = Field(ge=0)
    win_rate: float = Field(ge=0, le=100, description="勝率（%）")
    total_profit: float = Field(ge=0)
    total_loss: float = Field(ge=0)
    net_profit: float
    profit_factor: float = Field(ge=0)
    avg_win: float = Field(ge=0)
    avg_loss: float = Field(ge=0)
    largest_win: float = Field(ge=0)
    largest_loss: float = Field(ge=0)
    consecutive_wins: int = Field(ge=0)
    consecutive_losses: int = Field(ge=0)
    max_drawdown: float = Field(ge=0)
    max_drawdown_percent: float = Field(ge=0, le=100)
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    final_balance: float = Field(gt=0)
    return_percent: float
    avg_duration_hours: float = Field(ge=0)
    total_commission: float = Field(ge=0)

class BacktestResult(BaseModel):
    """バックテスト結果"""
    test_id: str
    symbol: str
    timeframe: str
    period: Dict[str, str]  # start_date, end_date (ISO format)
    initial_balance: float
    parameters: Dict[str, Any]
    statistics: BacktestStatistics
    equity_curve: List[EquityPoint]
    trades: List[TradeResult]
    data_points: int = Field(ge=0)
    created_at: Optional[datetime] = None

class OptimizationResult(BaseModel):
    """最適化結果"""
    iteration: int
    parameters: Dict[str, Any]
    score: float
    statistics: BacktestStatistics
    test_id: str

class ParameterSensitivity(BaseModel):
    """パラメータ感度"""
    correlation: float = Field(ge=-1, le=1)
    sensitivity: float = Field(ge=0, le=1)
    direction: str = Field(pattern="^(positive|negative)$")

class ConvergenceAnalysis(BaseModel):
    """収束分析"""
    status: str = Field(pattern="^(converged|improving|insufficient_data|error)$")
    improvement_rate: float
    final_moving_average: float
    stability_score: float = Field(ge=0, le=1)

class OptimizationAnalysis(BaseModel):
    """最適化分析"""
    metric_statistics: Dict[str, float]
    convergence_analysis: ConvergenceAnalysis
    parameter_sensitivity: Dict[str, ParameterSensitivity]
    top_results: List[OptimizationResult]

class OptimizationResponse(BaseModel):
    """最適化レスポンス"""
    symbol: str
    timeframe: str
    period: Dict[str, str]
    optimization_method: str
    optimization_metric: str
    best_parameters: Optional[Dict[str, Any]]
    best_score: float
    best_test_id: Optional[str]
    total_iterations: int
    valid_results: int
    all_results: List[OptimizationResult]
    analysis: OptimizationAnalysis

class SymbolPerformance(BaseModel):
    """通貨ペア別パフォーマンス"""
    avg_score: float
    max_score: float
    count: int

class ComprehensiveAnalysis(BaseModel):
    """包括的分析結果"""
    overall_statistics: Dict[str, float]
    best_combination: Dict[str, Any]
    symbol_rankings: Dict[str, SymbolPerformance]
    timeframe_rankings: Dict[str, SymbolPerformance]
    top_10_combinations: List[tuple]

class ComprehensiveBacktestResponse(BaseModel):
    """包括的バックテストレスポンス"""
    individual_results: Dict[str, Dict[str, Any]]
    summary_statistics: Dict[str, Dict[str, Any]]
    overall_analysis: ComprehensiveAnalysis
    test_period: Dict[str, Any]
    optimization_settings: Dict[str, Any]

class BacktestListItem(BaseModel):
    """バックテストリスト項目"""
    test_id: str
    symbol: str
    timeframe: str
    created_at: datetime
    period: Dict[str, str]
    final_balance: float
    return_percent: float
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_percent: float
    sharpe_ratio: float

class BacktestListResponse(BaseModel):
    """バックテストリストレスポンス"""
    tests: List[BacktestListItem]
    total_count: int
    page: int
    page_size: int
    has_next: bool

class BacktestDeleteRequest(BaseModel):
    """バックテスト削除リクエスト"""
    test_ids: List[str] = Field(min_items=1, max_items=100)

class BacktestCompareRequest(BaseModel):
    """バックテスト比較リクエスト"""
    test_ids: List[str] = Field(min_items=2, max_items=10, description="比較するテストID")
    metrics: Optional[List[str]] = None

class ComparisonMetric(BaseModel):
    """比較指標"""
    metric_name: str
    values: Dict[str, float]  # test_id -> value
    best_test_id: str
    worst_test_id: str
    range_value: float

class BacktestCompareResponse(BaseModel):
    """バックテスト比較レスポンス"""
    test_ids: List[str]
    comparison_metrics: List[ComparisonMetric]
    summary: Dict[str, Any]
    recommendations: List[str]

class BacktestExportRequest(BaseModel):
    """バックテストエクスポートリクエスト"""
    test_id: str
    format: str = Field(default="csv", pattern="^(csv|excel|json|pdf)$")
    include_trades: bool = Field(default=True)
    include_equity_curve: bool = Field(default=True)
    include_statistics: bool = Field(default=True)

class BacktestValidationResult(BaseModel):
    """バックテスト検証結果"""
    is_valid: bool
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    data_quality_score: float = Field(ge=0, le=1)
    recommended_adjustments: List[str] = Field(default_factory=list)

class BacktestScheduleRequest(BaseModel):
    """バックテストスケジュールリクエスト"""
    symbol: SymbolEnum
    timeframe: TimeframeEnum
    schedule_type: str = Field(pattern="^(daily|weekly|monthly)$")
    auto_parameters: bool = Field(default=True, description="自動パラメータ最適化")
    notification_email: Optional[str] = None

class BacktestMetrics(BaseModel):
    """バックテスト指標集計"""
    total_tests: int
    avg_return_percent: float
    avg_win_rate: float
    avg_profit_factor: float
    avg_sharpe_ratio: float
    best_performing_symbol: str
    best_performing_timeframe: str
    total_profit: float
    total_trades: int