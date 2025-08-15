"""
時間帯分析API
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
import time

from backend.core.database import DatabaseManager
from backend.analysis.timeframe_analyzer import TimeframeAnalyzer
from backend.analysis.economic_news_analyzer import EconomicNewsAnalyzer
from backend.analysis.optimal_time_finder import OptimalTimeFinder
from backend.models.analysis_models import (
    CurrencyPair, TimeframeAnalysisRequest, MarketSessionAnalysisResponse,
    HourlyAnalysisResponse, WeekdayAnalysisResponse, NewsImpactAnalysisRequest,
    NewsImpactAnalysisResponse, UpcomingEventsRequest, UpcomingEventsResponse,
    OptimalTimeFindingRequest, OptimalTimeFindingResponse,
    EntryExitAnalysisRequest, EntryExitAnalysisResponse,
    ComprehensiveAnalysisRequest, ComprehensiveAnalysisResponse,
    AnalysisApiResponse, AnalysisWarning, AnalysisError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

# グローバル変数（実際の運用では適切なDIコンテナを使用）
timeframe_analyzer = None
news_analyzer = None
optimal_time_finder = None
db_manager = None


def get_analysis_dependencies():
    """分析システムの依存関係を取得"""
    global timeframe_analyzer, news_analyzer, optimal_time_finder, db_manager
    
    if not all([timeframe_analyzer, db_manager]):
        # 初期化
        db_manager = DatabaseManager()
        timeframe_analyzer = TimeframeAnalyzer(db_manager)
        # news_analyzer = EconomicNewsAnalyzer(db_manager)  # 実装時に有効化
        # optimal_time_finder = OptimalTimeFinder(db_manager)  # 実装時に有効化
    
    return timeframe_analyzer, news_analyzer, optimal_time_finder, db_manager


# ============= 市場セッション分析 =============

@router.get("/market-sessions/{symbol}", response_model=AnalysisApiResponse)
async def get_market_session_analysis(
    symbol: CurrencyPair,
    period_days: int = Query(default=365, ge=30, le=1095, description="分析期間（日）")
):
    """
    市場セッション別パフォーマンス分析
    
    Args:
        symbol: 通貨ペア
        period_days: 分析期間（日）
        
    Returns:
        市場セッション分析結果
    """
    start_time = time.time()
    
    try:
        analyzer, _, _, _ = get_analysis_dependencies()
        
        logger.info(f"Starting market session analysis for {symbol.value}")
        
        # 分析実行
        result = analyzer.analyze_market_sessions(symbol.value, period_days)
        
        # レスポンス構築
        best_session_name = None
        if result.get('best_session'):
            best_session_name = result['best_session'].get('session_name')
        
        response_data = {
            'symbol': symbol.value,
            'period_days': period_days,
            'session_statistics': result['session_statistics'],
            'best_session': best_session_name,
            'best_session_details': result.get('best_session'),
            'recommendations': result.get('recommendations', [])
        }
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="success",
            message="Market session analysis completed successfully",
            data=response_data,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Market session analysis failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="error",
            message="Market session analysis failed",
            errors=[AnalysisError(
                error_code="ANALYSIS_ERROR",
                error_message=str(e)
            )],
            execution_time_ms=execution_time
        )


# ============= 時間別分析 =============

@router.get("/hourly/{symbol}")
async def get_hourly_analysis(
    symbol: CurrencyPair,
    period_days: int = Query(default=365, ge=30, le=1095, description="分析期間（日）"),
    include_heatmap: bool = Query(default=True, description="ヒートマップデータ含む")
):
    """
    時間別パフォーマンス分析
    
    Args:
        symbol: 通貨ペア
        period_days: 分析期間（日）
        include_heatmap: ヒートマップデータを含むか
        
    Returns:
        時間別分析結果
    """
    start_time = time.time()
    
    try:
        analyzer, _, _, _ = get_analysis_dependencies()
        
        logger.info(f"Starting hourly analysis for {symbol.value}")
        
        # 分析実行
        result = analyzer.analyze_hourly_performance(symbol.value, period_days)
        
        # ヒートマップデータ生成
        heatmap_data = None
        if include_heatmap:
            heatmap_data = _generate_heatmap_data(result['hourly_statistics'])
        
        # レスポンス構築
        response_data = {
            'symbol': symbol.value,
            'period_days': period_days,
            'hourly_statistics': result['hourly_statistics'],
            'best_hours': result.get('best_hours', []),
            'heatmap_data': heatmap_data,
            'recommendations': result.get('recommendations', [])
        }
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return {
            "status": "success",
            "message": "Hourly analysis completed successfully",
            "data": response_data,
            "execution_time_ms": execution_time,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Hourly analysis failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return {
            "status": "error",
            "message": "Hourly analysis failed",
            "errors": [{"error_code": "ANALYSIS_ERROR", "error_message": str(e)}],
            "execution_time_ms": execution_time,
            "timestamp": datetime.now().isoformat()
        }


def _generate_heatmap_data(hourly_stats: Dict[str, Any]) -> List[List[float]]:
    """ヒートマップデータ生成"""
    try:
        # 24時間 x 7日の配列を初期化
        heatmap = [[0.0 for _ in range(7)] for _ in range(24)]
        
        for hour_str, stats in hourly_stats.items():
            hour = int(hour_str.split(':')[0])
            win_rate = stats.get('win_rate', 0)
            
            # 各曜日に同じ値を設定（簡略化）
            for day in range(7):
                heatmap[hour][day] = win_rate
        
        return heatmap
        
    except Exception as e:
        logger.warning(f"Failed to generate heatmap data: {e}")
        return []


# ============= 曜日別分析 =============

@router.get("/weekday/{symbol}", response_model=AnalysisApiResponse)
async def get_weekday_analysis(
    symbol: CurrencyPair,
    period_days: int = Query(default=365, ge=30, le=1095, description="分析期間（日）"),
    include_weekend_effect: bool = Query(default=True, description="週末効果分析含む")
):
    """
    曜日別パフォーマンス分析
    
    Args:
        symbol: 通貨ペア
        period_days: 分析期間（日）
        include_weekend_effect: 週末効果分析を含むか
        
    Returns:
        曜日別分析結果
    """
    start_time = time.time()
    
    try:
        analyzer, _, _, _ = get_analysis_dependencies()
        
        logger.info(f"Starting weekday analysis for {symbol.value}")
        
        # 分析実行
        result = analyzer.analyze_weekday_performance(symbol.value, period_days)
        
        # 週末効果分析
        weekend_effect = None
        if include_weekend_effect:
            weekend_effect = _analyze_weekend_effect(result['weekday_statistics'])
        
        # レスポンス構築
        response_data = WeekdayAnalysisResponse(
            symbol=symbol,
            period_days=period_days,
            weekday_statistics=result['weekday_statistics'],
            best_weekdays=result.get('best_weekdays', []),
            weekend_effect=weekend_effect,
            recommendations=result.get('recommendations', [])
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="success",
            message="Weekday analysis completed successfully",
            data=response_data,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Weekday analysis failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="error",
            message="Weekday analysis failed",
            errors=[AnalysisError(
                error_code="ANALYSIS_ERROR",
                error_message=str(e)
            )],
            execution_time_ms=execution_time
        )


def _analyze_weekend_effect(weekday_stats: Dict[str, Any]) -> Dict[str, Any]:
    """週末効果分析"""
    try:
        weekdays = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日']
        weekend_days = ['土曜日', '日曜日']
        
        weekday_performance = []
        weekend_performance = []
        
        for day, stats in weekday_stats.items():
            if day in weekdays:
                weekday_performance.append(stats.get('win_rate', 0))
            elif day in weekend_days:
                weekend_performance.append(stats.get('win_rate', 0))
        
        avg_weekday_performance = sum(weekday_performance) / len(weekday_performance) if weekday_performance else 0
        avg_weekend_performance = sum(weekend_performance) / len(weekend_performance) if weekend_performance else 0
        
        weekend_effect_percent = avg_weekend_performance - avg_weekday_performance
        
        return {
            'avg_weekday_performance': round(avg_weekday_performance, 2),
            'avg_weekend_performance': round(avg_weekend_performance, 2),
            'weekend_effect_percent': round(weekend_effect_percent, 2),
            'is_weekend_beneficial': weekend_effect_percent > 0
        }
        
    except Exception as e:
        logger.warning(f"Failed to analyze weekend effect: {e}")
        return {}


# ============= 経済指標影響分析 =============

@router.post("/news-impact", response_model=AnalysisApiResponse)
async def analyze_news_impact(request: NewsImpactAnalysisRequest):
    """
    経済指標の価格影響分析
    
    Args:
        request: ニュース影響分析リクエスト
        
    Returns:
        ニュース影響分析結果
    """
    start_time = time.time()
    
    try:
        _, news_analyzer, _, _ = get_analysis_dependencies()
        
        logger.info(f"Starting news impact analysis for {request.symbol.value}")
        
        # 分析実行
        result = await news_analyzer.analyze_news_impact(
            symbol=request.symbol.value,
            impact_levels=[level.value for level in request.impact_levels],
            time_window_minutes=request.time_window_minutes,
            period_days=request.period_days
        )
        
        # レスポンス構築
        response_data = NewsImpactAnalysisResponse(
            symbol=request.symbol,
            analysis_period=result.get('analysis_period', {}),
            analyzed_events=result.get('analyzed_events', 0),
            results=result.get('results', []),
            summary=result.get('summary', {}),
            recommendations=result.get('recommendations', [])
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        # 警告チェック
        warnings = []
        if result.get('analyzed_events', 0) < 10:
            warnings.append(AnalysisWarning(
                warning_code="LOW_DATA",
                warning_message="分析に使用できる経済指標イベントが少ないです",
                severity="medium",
                recommendations=["分析期間を延長してください", "より多くの影響レベルを含めてください"]
            ))
        
        return AnalysisApiResponse(
            status="success",
            message="News impact analysis completed successfully",
            data=response_data,
            warnings=warnings,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"News impact analysis failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="error",
            message="News impact analysis failed",
            errors=[AnalysisError(
                error_code="ANALYSIS_ERROR",
                error_message=str(e)
            )],
            execution_time_ms=execution_time
        )


@router.post("/upcoming-events", response_model=AnalysisApiResponse)
async def get_upcoming_events(request: UpcomingEventsRequest):
    """
    今後の重要経済指標取得
    
    Args:
        request: 今後のイベント取得リクエスト
        
    Returns:
        今後のイベント情報
    """
    start_time = time.time()
    
    try:
        _, news_analyzer, _, _ = get_analysis_dependencies()
        
        logger.info(f"Getting upcoming events for {request.symbol.value}")
        
        # 今後のイベント取得
        events = await news_analyzer.get_upcoming_events(
            symbol=request.symbol.value,
            hours_ahead=request.hours_ahead,
            impact_levels=[level.value for level in request.impact_levels]
        )
        
        # 高インパクトイベント数
        high_impact_count = sum(1 for e in events if e.get('impact') == 'high')
        
        # 次の主要イベント
        next_major_event = None
        if events:
            next_major_event = min(events, key=lambda x: x['hours_until'])
        
        # 推奨事項生成
        recommendations = []
        if high_impact_count > 0:
            recommendations.append(f"今後{request.hours_ahead}時間以内に{high_impact_count}件の高インパクトイベントがあります")
        
        if next_major_event and next_major_event['hours_until'] < 2:
            recommendations.append("2時間以内に重要イベントが予定されています。取引に注意してください")
        
        # レスポンス構築
        response_data = UpcomingEventsResponse(
            symbol=request.symbol,
            hours_ahead=request.hours_ahead,
            events=events,
            high_impact_count=high_impact_count,
            next_major_event=next_major_event,
            recommendations=recommendations
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="success",
            message="Upcoming events retrieved successfully",
            data=response_data,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Getting upcoming events failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="error",
            message="Getting upcoming events failed",
            errors=[AnalysisError(
                error_code="ANALYSIS_ERROR",
                error_message=str(e)
            )],
            execution_time_ms=execution_time
        )


# ============= 最適時間帯検出 =============

@router.post("/optimal-hours", response_model=AnalysisApiResponse)
async def find_optimal_trading_hours(request: OptimalTimeFindingRequest):
    """
    最適取引時間帯の検出
    
    Args:
        request: 最適時間検出リクエスト
        
    Returns:
        最適時間検出結果
    """
    start_time = time.time()
    
    try:
        _, _, optimal_finder, _ = get_analysis_dependencies()
        
        logger.info(f"Finding optimal trading hours for {request.symbol.value}")
        
        # 最適時間検出実行
        result = await optimal_finder.find_optimal_trading_hours(
            symbol=request.symbol.value,
            min_trades=request.min_trades,
            min_win_rate=request.min_win_rate,
            min_profit_factor=request.min_profit_factor,
            exclude_news_hours=request.exclude_news_hours
        )
        
        # レスポンス構築
        response_data = OptimalTimeFindingResponse(
            symbol=request.symbol,
            analysis_criteria=result.get('analysis_criteria', {}),
            optimal_hours=result.get('optimal_hours', []),
            recommended_windows=result.get('recommended_windows', []),
            trading_schedule=result.get('trading_schedule', {}),
            market_session_analysis=result.get('market_session_analysis', {}),
            recommendations=result.get('recommendations', [])
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        # 警告チェック
        warnings = []
        if len(result.get('optimal_hours', [])) == 0:
            warnings.append(AnalysisWarning(
                warning_code="NO_OPTIMAL_HOURS",
                warning_message="指定条件を満たす最適時間帯が見つかりませんでした",
                severity="high",
                recommendations=["条件を緩和してください", "分析期間を延長してください"]
            ))
        
        return AnalysisApiResponse(
            status="success",
            message="Optimal trading hours analysis completed successfully",
            data=response_data,
            warnings=warnings,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Optimal hours analysis failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="error",
            message="Optimal hours analysis failed",
            errors=[AnalysisError(
                error_code="ANALYSIS_ERROR",
                error_message=str(e)
            )],
            execution_time_ms=execution_time
        )


# ============= エントリー・エグジット分析 =============

@router.post("/entry-exit", response_model=AnalysisApiResponse)
async def analyze_entry_exit_times(request: EntryExitAnalysisRequest):
    """
    最適エントリー・エグジット時間分析
    
    Args:
        request: エントリー・エグジット分析リクエスト
        
    Returns:
        エントリー・エグジット分析結果
    """
    start_time = time.time()
    
    try:
        _, _, optimal_finder, _ = get_analysis_dependencies()
        
        logger.info(f"Analyzing entry/exit times for {request.symbol.value}")
        
        # エントリー・エグジット分析実行
        result = await optimal_finder.find_optimal_entry_exit_times(
            symbol=request.symbol.value,
            position_type=request.position_type,
            min_holding_hours=request.min_holding_hours
        )
        
        # レスポンス構築
        response_data = EntryExitAnalysisResponse(
            symbol=request.symbol,
            position_type=request.position_type,
            optimal_entry_times=result.get('optimal_entry_times', []),
            optimal_exit_times=result.get('optimal_exit_times', []),
            optimal_pairs=result.get('optimal_pairs', []),
            recommendations=result.get('recommendations', [])
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="success",
            message="Entry/Exit analysis completed successfully",
            data=response_data,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Entry/Exit analysis failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="error",
            message="Entry/Exit analysis failed",
            errors=[AnalysisError(
                error_code="ANALYSIS_ERROR",
                error_message=str(e)
            )],
            execution_time_ms=execution_time
        )


# ============= 包括的分析 =============

@router.post("/comprehensive", response_model=AnalysisApiResponse)
async def run_comprehensive_analysis(request: ComprehensiveAnalysisRequest):
    """
    包括的時間帯分析の実行
    
    Args:
        request: 包括的分析リクエスト
        
    Returns:
        包括的分析結果
    """
    start_time = time.time()
    
    try:
        analyzer, news_analyzer, optimal_finder, _ = get_analysis_dependencies()
        
        logger.info(f"Starting comprehensive analysis for {len(request.symbols)} symbols")
        
        results = {}
        
        for symbol in request.symbols:
            symbol_results = {}
            
            # 市場セッション分析
            if request.include_market_sessions:
                try:
                    session_result = analyzer.analyze_market_sessions(symbol.value, request.period_days)
                    symbol_results['market_sessions'] = session_result
                except Exception as e:
                    logger.warning(f"Market session analysis failed for {symbol.value}: {e}")
            
            # 時間別分析
            if request.include_hourly_analysis:
                try:
                    hourly_result = analyzer.analyze_hourly_performance(symbol.value, request.period_days)
                    symbol_results['hourly'] = hourly_result
                except Exception as e:
                    logger.warning(f"Hourly analysis failed for {symbol.value}: {e}")
            
            # 曜日別分析
            if request.include_weekday_analysis:
                try:
                    weekday_result = analyzer.analyze_weekday_performance(symbol.value, request.period_days)
                    symbol_results['weekday'] = weekday_result
                except Exception as e:
                    logger.warning(f"Weekday analysis failed for {symbol.value}: {e}")
            
            # ニュース影響分析
            if request.include_news_impact:
                try:
                    news_result = await news_analyzer.analyze_news_impact(symbol.value)
                    symbol_results['news_impact'] = news_result
                except Exception as e:
                    logger.warning(f"News impact analysis failed for {symbol.value}: {e}")
            
            # 最適時間検出
            if request.include_optimal_times:
                try:
                    optimal_result = await optimal_finder.find_optimal_trading_hours(symbol.value)
                    symbol_results['optimal_times'] = optimal_result
                except Exception as e:
                    logger.warning(f"Optimal times analysis failed for {symbol.value}: {e}")
            
            results[symbol.value] = symbol_results
        
        # 全体サマリー生成
        summary = _generate_comprehensive_summary(results)
        
        # 通貨ペア横断分析
        cross_symbol_insights = _generate_cross_symbol_insights(results)
        
        # 総合推奨事項
        recommendations = _generate_comprehensive_recommendations(results, summary)
        
        # レスポンス構築
        response_data = ComprehensiveAnalysisResponse(
            symbols=request.symbols,
            period_days=request.period_days,
            summary=summary,
            cross_symbol_insights=cross_symbol_insights,
            recommendations=recommendations
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="success",
            message="Comprehensive analysis completed successfully",
            data=response_data,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="error",
            message="Comprehensive analysis failed",
            errors=[AnalysisError(
                error_code="ANALYSIS_ERROR",
                error_message=str(e)
            )],
            execution_time_ms=execution_time
        )


def _generate_comprehensive_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """包括的分析サマリー生成"""
    try:
        summary = {
            'analyzed_symbols': len(results),
            'successful_analyses': 0,
            'common_best_sessions': [],
            'overall_best_hours': [],
            'performance_metrics': {}
        }
        
        # 成功した分析数をカウント
        for symbol_results in results.values():
            if symbol_results:
                summary['successful_analyses'] += 1
        
        # 共通の最適セッション
        all_best_sessions = []
        for symbol_results in results.values():
            market_sessions = symbol_results.get('market_sessions', {})
            best_session = market_sessions.get('best_session')
            if best_session:
                all_best_sessions.append(best_session)
        
        if all_best_sessions:
            # 最も頻繁に現れるセッション
            session_counts = {}
            for session in all_best_sessions:
                session_counts[session] = session_counts.get(session, 0) + 1
            
            summary['common_best_sessions'] = sorted(
                session_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
        
        return summary
        
    except Exception as e:
        logger.warning(f"Failed to generate comprehensive summary: {e}")
        return {}


def _generate_cross_symbol_insights(results: Dict[str, Any]) -> List[str]:
    """通貨ペア横断分析インサイト生成"""
    insights = []
    
    try:
        # JPY通貨ペアの共通傾向
        jpy_pairs = [symbol for symbol in results.keys() if 'JPY' in symbol]
        if len(jpy_pairs) >= 2:
            insights.append(f"JPY通貨ペア（{len(jpy_pairs)}ペア）で共通傾向を分析しました")
        
        # 最適時間の重複
        all_optimal_hours = []
        for symbol_results in results.values():
            optimal_times = symbol_results.get('optimal_times', {})
            optimal_hours = optimal_times.get('optimal_hours', [])
            for hour_data in optimal_hours[:3]:  # トップ3のみ
                all_optimal_hours.append(hour_data.get('hour'))
        
        if all_optimal_hours:
            hour_counts = {}
            for hour in all_optimal_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            common_hours = [hour for hour, count in hour_counts.items() if count >= 2]
            if common_hours:
                insights.append(f"複数通貨ペアで共通する最適時間: {', '.join(common_hours)}")
        
        return insights
        
    except Exception as e:
        logger.warning(f"Failed to generate cross-symbol insights: {e}")
        return []


def _generate_comprehensive_recommendations(results: Dict[str, Any], summary: Dict[str, Any]) -> List[str]:
    """総合推奨事項生成"""
    recommendations = []
    
    try:
        analyzed_count = summary.get('analyzed_symbols', 0)
        successful_count = summary.get('successful_analyses', 0)
        
        if successful_count < analyzed_count:
            recommendations.append(
                f"{analyzed_count - successful_count}通貨ペアで分析に失敗しました。"
                "データ品質やパラメータを確認してください。"
            )
        
        # 共通セッションの推奨
        common_sessions = summary.get('common_best_sessions', [])
        if common_sessions:
            best_session = common_sessions[0][0]
            session_names = {
                'tokyo': '東京セッション',
                'london': 'ロンドンセッション',
                'ny': 'ニューヨークセッション',
                'london_ny_overlap': 'ロンドン・NY重複時間'
            }
            session_name = session_names.get(best_session, best_session)
            recommendations.append(f"複数通貨ペアで{session_name}が最適です。統一戦略を検討してください。")
        
        # 全体的な推奨
        if successful_count >= 3:
            recommendations.append("十分なデータが得られました。結果を基にトレーディング戦略を最適化してください。")
        
        return recommendations
        
    except Exception as e:
        logger.warning(f"Failed to generate comprehensive recommendations: {e}")
        return []


# ============= カレンダーデータ更新 =============

@router.post("/refresh-calendar")
async def refresh_economic_calendar(
    days_ahead: int = Query(default=7, ge=1, le=30, description="先読み日数")
):
    """
    経済指標カレンダーデータの更新
    
    Args:
        days_ahead: 先読み日数
        
    Returns:
        更新結果
    """
    start_time = time.time()
    
    try:
        _, news_analyzer, _, _ = get_analysis_dependencies()
        
        logger.info(f"Refreshing economic calendar data for {days_ahead} days ahead")
        
        # カレンダーデータ更新
        result = await news_analyzer.refresh_calendar_data(days_ahead)
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="success",
            message="Economic calendar data refreshed successfully",
            data=result,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Calendar refresh failed: {e}")
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalysisApiResponse(
            status="error",
            message="Calendar refresh failed",
            errors=[AnalysisError(
                error_code="REFRESH_ERROR",
                error_message=str(e)
            )],
            execution_time_ms=execution_time
        )


# ============= ヘルスチェック =============

@router.get("/test-hourly/{symbol}")
async def test_hourly_analysis_simple(symbol: str):
    """シンプルな時間別分析テスト"""
    try:
        analyzer, _, _, _ = get_analysis_dependencies()
        
        result = analyzer.analyze_hourly_performance(symbol, 180)
        
        return {
            "status": "success",
            "symbol": symbol,
            "total_trades": result.get('total_trades', 0),
            "best_hours": result.get('best_hours', [])[:3],  # トップ3のみ
            "recommendations": result.get('recommendations', [])
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/health")
async def analysis_health_check():
    """
    分析システムヘルスチェック
    
    Returns:
        ヘルス状態
    """
    try:
        analyzer, news_analyzer, optimal_finder, db_manager = get_analysis_dependencies()
        
        # 各コンポーネントの状態チェック
        health_status = {
            "timeframe_analyzer": analyzer is not None,
            "news_analyzer": news_analyzer is not None,
            "optimal_time_finder": optimal_finder is not None,
            "database": db_manager.test_connection() if db_manager else False
        }
        
        overall_healthy = all(health_status.values())
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "components": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analysis health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }