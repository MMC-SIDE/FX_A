"""
時間帯分析機能のPydanticモデル
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class CurrencyPair(str, Enum):
    """通貨ペア"""
    USDJPY = "USDJPY"
    EURJPY = "EURJPY" 
    GBPJPY = "GBPJPY"
    AUDJPY = "AUDJPY"
    NZDJPY = "NZDJPY"
    CADJPY = "CADJPY"
    CHFJPY = "CHFJPY"
    EURUSD = "EURUSD"
    GBPUSD = "GBPUSD"


class MarketSession(str, Enum):
    """市場セッション"""
    TOKYO = "tokyo"
    LONDON = "london"
    NY = "ny"
    LONDON_NY_OVERLAP = "london_ny_overlap"
    QUIET = "quiet"


class ImpactLevel(str, Enum):
    """経済指標影響レベル"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Timeframe(str, Enum):
    """時間軸"""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


# ============= 基本統計モデル =============

class TradingStatistics(BaseModel):
    """取引統計"""
    total_trades: int = Field(..., ge=0, description="総取引数")
    winning_trades: int = Field(..., ge=0, description="勝利取引数")
    losing_trades: int = Field(..., ge=0, description="敗北取引数")
    win_rate: float = Field(..., ge=0, le=100, description="勝率（%）")
    total_profit: float = Field(..., description="総利益")
    total_loss: float = Field(..., description="総損失")
    net_profit: float = Field(..., description="純利益")
    profit_factor: float = Field(..., ge=0, description="プロフィットファクター")
    avg_profit_per_trade: float = Field(..., description="取引あたり平均利益")

    @validator('losing_trades')
    def validate_trades_sum(cls, v, values):
        if 'total_trades' in values and 'winning_trades' in values:
            expected = values['total_trades'] - values['winning_trades']
            if v != expected:
                raise ValueError('losing_trades must equal total_trades - winning_trades')
        return v


class SessionStatistics(TradingStatistics):
    """セッション統計（基本統計を継承）"""
    session_name: str = Field(..., description="セッション名")
    avg_volatility: Optional[float] = Field(None, description="平均ボラティリティ")
    max_drawdown: Optional[float] = Field(None, description="最大ドローダウン")


class HourlyStatistics(TradingStatistics):
    """時間別統計"""
    hour: str = Field(..., pattern=r"^([01]?[0-9]|2[0-3]):(00|30)$", description="時刻（HH:MM形式）")
    market_session: MarketSession = Field(..., description="市場セッション")
    avg_duration_minutes: Optional[float] = Field(None, description="平均取引時間（分）")
    news_events_count: Optional[int] = Field(None, ge=0, description="ニュースイベント数")


class WeekdayStatistics(TradingStatistics):
    """曜日別統計"""
    weekday: int = Field(..., ge=0, le=6, description="曜日（0=月曜、6=日曜）")
    weekday_name: str = Field(..., description="曜日名")
    is_weekend: bool = Field(False, description="週末フラグ")


# ============= 分析リクエスト/レスポンスモデル =============

class TimeframeAnalysisRequest(BaseModel):
    """時間帯分析リクエスト"""
    symbol: CurrencyPair = Field(..., description="通貨ペア")
    period_days: int = Field(default=365, ge=30, le=1095, description="分析期間（日）")
    include_weekends: bool = Field(default=False, description="週末含む")
    min_trades_per_hour: int = Field(default=5, ge=1, description="時間あたり最小取引数")


class MarketSessionAnalysisResponse(BaseModel):
    """市場セッション分析レスポンス"""
    symbol: CurrencyPair
    period_days: int
    session_statistics: Dict[str, SessionStatistics]
    best_session: Optional[str] = Field(None, description="最高パフォーマンスセッション")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")
    analysis_date: datetime = Field(default_factory=datetime.now, description="分析実行日時")


class HourlyAnalysisResponse(BaseModel):
    """時間別分析レスポンス"""
    symbol: CurrencyPair
    period_days: int
    hourly_statistics: Dict[str, HourlyStatistics]
    best_hours: List[str] = Field(default_factory=list, description="最高パフォーマンス時間")
    heatmap_data: Optional[List[List[float]]] = Field(None, description="ヒートマップデータ")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")
    analysis_date: datetime = Field(default_factory=datetime.now, description="分析実行日時")


class WeekdayAnalysisResponse(BaseModel):
    """曜日別分析レスポンス"""
    symbol: CurrencyPair
    period_days: int
    weekday_statistics: Dict[str, WeekdayStatistics]
    best_weekdays: List[str] = Field(default_factory=list, description="最高パフォーマンス曜日")
    weekend_effect: Optional[Dict[str, Any]] = Field(None, description="週末効果分析")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")
    analysis_date: datetime = Field(default_factory=datetime.now, description="分析実行日時")


# ============= 経済指標関連モデル =============

class EconomicEvent(BaseModel):
    """経済指標イベント"""
    name: str = Field(..., description="イベント名")
    time: datetime = Field(..., description="発表時刻")
    currency: str = Field(..., min_length=3, max_length=3, description="通貨コード")
    impact: ImpactLevel = Field(..., description="影響レベル")
    actual: Optional[float] = Field(None, description="実際値")
    forecast: Optional[float] = Field(None, description="予測値")
    previous: Optional[float] = Field(None, description="前回値")


class VolatilityAnalysis(BaseModel):
    """ボラティリティ分析"""
    before_volatility: float = Field(..., ge=0, description="イベント前ボラティリティ")
    after_volatility: float = Field(..., ge=0, description="イベント後ボラティリティ")
    volatility_increase_percent: float = Field(..., description="ボラティリティ増加率（%）")
    price_change: float = Field(..., description="価格変動幅")
    price_change_percent: float = Field(..., description="価格変動率（%）")
    max_range: float = Field(..., ge=0, description="最大変動幅")
    max_range_percent: float = Field(..., description="最大変動率（%）")
    data_points_before: int = Field(..., ge=0, description="イベント前データ数")
    data_points_after: int = Field(..., ge=0, description="イベント後データ数")


class NewsImpactAnalysisRequest(BaseModel):
    """ニュース影響分析リクエスト"""
    symbol: CurrencyPair = Field(..., description="通貨ペア")
    impact_levels: List[ImpactLevel] = Field(default=[ImpactLevel.HIGH, ImpactLevel.MEDIUM], description="対象影響レベル")
    time_window_minutes: int = Field(default=60, ge=30, le=240, description="分析時間窓（分）")
    period_days: int = Field(default=90, ge=30, le=365, description="分析期間（日）")


class NewsImpactAnalysisResponse(BaseModel):
    """ニュース影響分析レスポンス"""
    symbol: CurrencyPair
    analysis_period: Dict[str, str]
    analyzed_events: int = Field(..., ge=0, description="分析イベント数")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="分析結果")
    summary: Dict[str, Any] = Field(default_factory=dict, description="サマリー統計")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")
    analysis_date: datetime = Field(default_factory=datetime.now)


class UpcomingEventsRequest(BaseModel):
    """今後のイベント取得リクエスト"""
    symbol: CurrencyPair = Field(..., description="通貨ペア")
    hours_ahead: int = Field(default=24, ge=1, le=168, description="先読み時間（時間）")
    impact_levels: List[ImpactLevel] = Field(default=[ImpactLevel.HIGH, ImpactLevel.MEDIUM], description="対象影響レベル")


class UpcomingEventsResponse(BaseModel):
    """今後のイベントレスポンス"""
    symbol: CurrencyPair
    hours_ahead: int
    events: List[Dict[str, Any]] = Field(default_factory=list, description="今後のイベント")
    high_impact_count: int = Field(..., ge=0, description="高インパクトイベント数")
    next_major_event: Optional[Dict[str, Any]] = Field(None, description="次の主要イベント")
    recommendations: List[str] = Field(default_factory=list)


# ============= 最適時間帯検出モデル =============

class OptimalHour(BaseModel):
    """最適時間"""
    hour: str = Field(..., description="時刻")
    statistics: TradingStatistics
    score: float = Field(..., ge=0, le=1, description="総合スコア")
    news_risk_score: float = Field(default=0, ge=0, le=100, description="ニュースリスクスコア")
    market_session: MarketSession = Field(..., description="市場セッション")


class TimeWindow(BaseModel):
    """時間窓"""
    start_hour: str = Field(..., description="開始時刻")
    end_hour: str = Field(..., description="終了時刻")
    duration_hours: int = Field(..., ge=1, le=24, description="継続時間")
    hours: List[str] = Field(..., description="含まれる時間リスト")
    quality_score: float = Field(..., ge=0, description="品質スコア")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="統計データ")
    market_sessions: List[MarketSession] = Field(default_factory=list, description="含まれる市場セッション")


class TradingSchedule(BaseModel):
    """取引スケジュール"""
    active_hours: List[int] = Field(default_factory=list, description="取引有効時間")
    inactive_hours: List[int] = Field(default_factory=list, description="取引無効時間")
    recommended_sessions: List[Dict[str, Any]] = Field(default_factory=list, description="推奨セッション")
    total_active_hours: int = Field(..., ge=0, le=24, description="総取引時間")
    schedule_efficiency: float = Field(..., ge=0, le=100, description="スケジュール効率（%）")
    daily_schedule: Dict[str, str] = Field(default_factory=dict, description="日別スケジュール")


class OptimalTimeFindingRequest(BaseModel):
    """最適時間検出リクエスト"""
    symbol: CurrencyPair = Field(..., description="通貨ペア")
    min_trades: int = Field(default=20, ge=5, description="最小取引数")
    min_win_rate: float = Field(default=60.0, ge=30.0, le=100.0, description="最小勝率（%）")
    min_profit_factor: float = Field(default=1.2, ge=1.0, description="最小プロフィットファクター")
    exclude_news_hours: bool = Field(default=True, description="ニュース時間除外")
    analysis_period_days: int = Field(default=365, ge=90, le=1095, description="分析期間（日）")


class OptimalTimeFindingResponse(BaseModel):
    """最適時間検出レスポンス"""
    symbol: CurrencyPair
    analysis_criteria: Dict[str, Any]
    optimal_hours: List[OptimalHour] = Field(default_factory=list, description="最適時間リスト")
    recommended_windows: List[TimeWindow] = Field(default_factory=list, description="推奨時間窓")
    trading_schedule: TradingSchedule
    market_session_analysis: Dict[str, Any] = Field(default_factory=dict, description="セッション分析")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")
    analysis_date: datetime = Field(default_factory=datetime.now)


# ============= エントリー・エグジット分析モデル =============

class EntryExitPair(BaseModel):
    """エントリー・エグジットペア"""
    entry_hour: str = Field(..., description="エントリー時刻")
    exit_hour: str = Field(..., description="エグジット時刻")
    holding_hours: int = Field(..., ge=1, le=24, description="保有時間")
    entry_score: float = Field(..., ge=0, le=1, description="エントリースコア")
    exit_score: float = Field(..., ge=0, le=1, description="エグジットスコア")
    combined_score: float = Field(..., ge=0, le=1, description="総合スコア")
    entry_stats: TradingStatistics
    exit_stats: TradingStatistics


class EntryExitAnalysisRequest(BaseModel):
    """エントリー・エグジット分析リクエスト"""
    symbol: CurrencyPair = Field(..., description="通貨ペア")
    position_type: str = Field(default="both", pattern="^(buy|sell|both)$", description="ポジション種別")
    min_holding_hours: int = Field(default=1, ge=1, le=24, description="最小保有時間")
    max_holding_hours: int = Field(default=12, ge=1, le=24, description="最大保有時間")
    analysis_period_days: int = Field(default=365, ge=90, le=1095, description="分析期間（日）")

    @validator('max_holding_hours')
    def validate_holding_hours(cls, v, values):
        if 'min_holding_hours' in values and v < values['min_holding_hours']:
            raise ValueError('max_holding_hours must be >= min_holding_hours')
        return v


class EntryExitAnalysisResponse(BaseModel):
    """エントリー・エグジット分析レスポンス"""
    symbol: CurrencyPair
    position_type: str
    optimal_entry_times: List[Dict[str, Any]] = Field(default_factory=list, description="最適エントリー時間")
    optimal_exit_times: List[Dict[str, Any]] = Field(default_factory=list, description="最適エグジット時間")
    optimal_pairs: List[EntryExitPair] = Field(default_factory=list, description="最適ペア")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")
    analysis_date: datetime = Field(default_factory=datetime.now)


# ============= 一括分析モデル =============

class ComprehensiveAnalysisRequest(BaseModel):
    """包括的分析リクエスト"""
    symbols: List[CurrencyPair] = Field(default=[CurrencyPair.USDJPY], description="対象通貨ペア")
    period_days: int = Field(default=365, ge=90, le=1095, description="分析期間（日）")
    include_market_sessions: bool = Field(default=True, description="市場セッション分析含む")
    include_hourly_analysis: bool = Field(default=True, description="時間別分析含む")
    include_weekday_analysis: bool = Field(default=True, description="曜日別分析含む")
    include_news_impact: bool = Field(default=True, description="ニュース影響分析含む")
    include_optimal_times: bool = Field(default=True, description="最適時間検出含む")


class ComprehensiveAnalysisResponse(BaseModel):
    """包括的分析レスポンス"""
    symbols: List[CurrencyPair]
    period_days: int
    market_session_results: Dict[str, MarketSessionAnalysisResponse] = Field(default_factory=dict)
    hourly_results: Dict[str, HourlyAnalysisResponse] = Field(default_factory=dict)
    weekday_results: Dict[str, WeekdayAnalysisResponse] = Field(default_factory=dict)
    news_impact_results: Dict[str, NewsImpactAnalysisResponse] = Field(default_factory=dict)
    optimal_time_results: Dict[str, OptimalTimeFindingResponse] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict, description="全体サマリー")
    cross_symbol_insights: List[str] = Field(default_factory=list, description="通貨ペア横断分析")
    recommendations: List[str] = Field(default_factory=list, description="総合推奨事項")
    analysis_date: datetime = Field(default_factory=datetime.now)


# ============= エラーレスポンスモデル =============

class AnalysisError(BaseModel):
    """分析エラー"""
    error_code: str = Field(..., description="エラーコード")
    error_message: str = Field(..., description="エラーメッセージ")
    details: Optional[Dict[str, Any]] = Field(None, description="詳細情報")
    timestamp: datetime = Field(default_factory=datetime.now, description="エラー発生時刻")


class AnalysisWarning(BaseModel):
    """分析警告"""
    warning_code: str = Field(..., description="警告コード")
    warning_message: str = Field(..., description="警告メッセージ")
    severity: str = Field(default="medium", pattern="^(low|medium|high)$", description="重要度")
    recommendations: List[str] = Field(default_factory=list, description="推奨対応")


# ============= API共通レスポンスモデル =============

class AnalysisApiResponse(BaseModel):
    """分析API共通レスポンス"""
    status: str = Field(default="success", pattern="^(success|warning|error)$", description="ステータス")
    message: str = Field(default="Analysis completed successfully", description="メッセージ")
    data: Optional[Union[
        MarketSessionAnalysisResponse,
        HourlyAnalysisResponse,
        WeekdayAnalysisResponse,
        NewsImpactAnalysisResponse,
        OptimalTimeFindingResponse,
        EntryExitAnalysisResponse,
        ComprehensiveAnalysisResponse
    ]] = Field(None, description="レスポンスデータ")
    warnings: List[AnalysisWarning] = Field(default_factory=list, description="警告リスト")
    errors: List[AnalysisError] = Field(default_factory=list, description="エラーリスト")
    execution_time_ms: Optional[int] = Field(None, ge=0, description="実行時間（ミリ秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="レスポンス時刻")