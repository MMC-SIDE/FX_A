"""
時間帯分析機能
"""
import pandas as pd
import numpy as np
import pytz
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from backend.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class TimeframeAnalyzer:
    """時間帯分析エンジン"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.timezone_jst = pytz.timezone('Asia/Tokyo')
        self.timezone_utc = pytz.UTC
        
        # 市場セッション定義（JST基準）
        self.market_sessions = {
            'tokyo': {
                'name': '東京市場',
                'start': 9,
                'end': 15,
                'description': 'アジア市場の主要セッション'
            },
            'london': {
                'name': 'ロンドン市場',
                'start': 16,
                'end': 24,
                'description': 'ヨーロッパ市場の主要セッション'
            },
            'ny': {
                'name': 'ニューヨーク市場',
                'start': 21,
                'end': 6,  # 翌日6時まで
                'description': 'アメリカ市場の主要セッション'
            },
            'overlap_london_ny': {
                'name': 'ロンドン・NY重複',
                'start': 21,
                'end': 24,
                'description': '最も流動性の高い時間帯'
            }
        }
        
    def analyze_market_sessions(self,
                               symbol: str,
                               period_days: int = 365) -> Dict[str, Any]:
        """
        市場セッション別分析
        
        Args:
            symbol: 通貨ペア
            period_days: 分析期間（日数）
            
        Returns:
            セッション分析結果
        """
        try:
            logger.info(f"Starting market session analysis for {symbol} ({period_days} days)")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            # 取引データ取得
            trades = self._get_trades_data(symbol, start_date, end_date)
            
            if not trades:
                return self._empty_session_analysis(symbol, period_days)
            
            session_stats = {}
            
            # 各セッションの分析
            for session_name, session_config in self.market_sessions.items():
                session_trades = self._filter_trades_by_session(
                    trades, session_config, session_name
                )
                
                if session_trades:
                    stats = self._calculate_session_statistics(session_trades, session_config)
                    session_stats[session_name] = stats
                else:
                    session_stats[session_name] = self._empty_session_stats(session_config)
            
            # 最高パフォーマンスセッション特定
            best_session = self._find_best_session(session_stats)
            
            # セッション間比較分析
            comparison_analysis = self._compare_sessions(session_stats)
            
            return {
                'symbol': symbol,
                'period_days': period_days,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_trades': len(trades),
                'session_statistics': session_stats,
                'best_session': best_session,
                'comparison_analysis': comparison_analysis,
                'recommendations': self._generate_session_recommendations(session_stats)
            }
            
        except Exception as e:
            logger.error(f"Error in market session analysis: {e}")
            return self._empty_session_analysis(symbol, period_days)
    
    def analyze_hourly_performance(self,
                                  symbol: str,
                                  period_days: int = 365) -> Dict[str, Any]:
        """
        時間別パフォーマンス分析
        
        Args:
            symbol: 通貨ペア
            period_days: 分析期間（日数）
            
        Returns:
            時間別分析結果
        """
        try:
            logger.info(f"Starting hourly performance analysis for {symbol} ({period_days} days)")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            # 取引データ取得
            trades = self._get_trades_data(symbol, start_date, end_date)
            
            if not trades:
                return self._empty_hourly_analysis(symbol, period_days)
            
            hourly_stats = {}
            
            # 各時間の分析
            for hour in range(24):
                hour_trades = [
                    t for t in trades
                    if self._get_jst_hour(t['entry_time']) == hour
                ]
                
                if hour_trades:
                    stats = self._calculate_hourly_statistics(hour_trades, hour)
                    hourly_stats[f"{hour:02d}:00"] = stats
                else:
                    hourly_stats[f"{hour:02d}:00"] = self._empty_hourly_stats(hour)
            
            # 最高パフォーマンス時間帯特定
            best_hours = self._find_best_hours(hourly_stats)
            
            # 時間帯パターン分析
            pattern_analysis = self._analyze_hourly_patterns(hourly_stats)
            
            return {
                'symbol': symbol,
                'period_days': period_days,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_trades': len(trades),
                'hourly_statistics': hourly_stats,
                'best_hours': best_hours,
                'pattern_analysis': pattern_analysis,
                'recommendations': self._generate_hourly_recommendations(hourly_stats)
            }
            
        except Exception as e:
            logger.error(f"Error in hourly performance analysis: {e}")
            return self._empty_hourly_analysis(symbol, period_days)
    
    def analyze_weekday_performance(self,
                                   symbol: str,
                                   period_days: int = 365) -> Dict[str, Any]:
        """
        曜日別パフォーマンス分析
        
        Args:
            symbol: 通貨ペア
            period_days: 分析期間（日数）
            
        Returns:
            曜日別分析結果
        """
        try:
            logger.info(f"Starting weekday performance analysis for {symbol} ({period_days} days)")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            # 取引データ取得
            trades = self._get_trades_data(symbol, start_date, end_date)
            
            if not trades:
                return self._empty_weekday_analysis(symbol, period_days)
            
            weekday_names = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
            weekday_stats = {}
            
            # 各曜日の分析
            for weekday in range(7):
                weekday_trades = [
                    t for t in trades
                    if self._get_jst_weekday(t['entry_time']) == weekday
                ]
                
                if weekday_trades:
                    stats = self._calculate_weekday_statistics(weekday_trades, weekday)
                    weekday_stats[weekday_names[weekday]] = stats
                else:
                    weekday_stats[weekday_names[weekday]] = self._empty_weekday_stats(weekday)
            
            # 最高パフォーマンス曜日特定
            best_weekdays = self._find_best_weekdays(weekday_stats)
            
            # 週パターン分析
            weekly_pattern = self._analyze_weekly_patterns(weekday_stats)
            
            return {
                'symbol': symbol,
                'period_days': period_days,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_trades': len(trades),
                'weekday_statistics': weekday_stats,
                'best_weekdays': best_weekdays,
                'weekly_pattern': weekly_pattern,
                'recommendations': self._generate_weekday_recommendations(weekday_stats)
            }
            
        except Exception as e:
            logger.error(f"Error in weekday performance analysis: {e}")
            return self._empty_weekday_analysis(symbol, period_days)
    
    def analyze_combined_timeframe(self,
                                  symbol: str,
                                  period_days: int = 365) -> Dict[str, Any]:
        """
        総合時間帯分析（時間×曜日のマトリックス）
        
        Args:
            symbol: 通貨ペア
            period_days: 分析期間（日数）
            
        Returns:
            総合分析結果
        """
        try:
            logger.info(f"Starting combined timeframe analysis for {symbol} ({period_days} days)")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            # 取引データ取得
            trades = self._get_trades_data(symbol, start_date, end_date)
            
            if not trades:
                return self._empty_combined_analysis(symbol, period_days)
            
            weekday_names = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
            combined_stats = {}
            
            # 時間×曜日のマトリックス作成
            for weekday in range(7):
                combined_stats[weekday_names[weekday]] = {}
                
                for hour in range(24):
                    hour_weekday_trades = [
                        t for t in trades
                        if (self._get_jst_weekday(t['entry_time']) == weekday and
                            self._get_jst_hour(t['entry_time']) == hour)
                    ]
                    
                    if hour_weekday_trades:
                        stats = self._calculate_combined_statistics(hour_weekday_trades, hour, weekday)
                        combined_stats[weekday_names[weekday]][f"{hour:02d}:00"] = stats
                    else:
                        combined_stats[weekday_names[weekday]][f"{hour:02d}:00"] = self._empty_combined_stats(hour, weekday)
            
            # ベストパフォーマンス時間帯（曜日×時間）特定
            best_combinations = self._find_best_time_combinations(combined_stats)
            
            # ヒートマップデータ生成
            heatmap_data = self._generate_heatmap_data(combined_stats)
            
            return {
                'symbol': symbol,
                'period_days': period_days,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_trades': len(trades),
                'combined_statistics': combined_stats,
                'best_combinations': best_combinations,
                'heatmap_data': heatmap_data,
                'recommendations': self._generate_combined_recommendations(best_combinations)
            }
            
        except Exception as e:
            logger.error(f"Error in combined timeframe analysis: {e}")
            return self._empty_combined_analysis(symbol, period_days)
    
    def _get_trades_data(self,
                        symbol: str,
                        start_date: datetime,
                        end_date: datetime) -> List[Dict[str, Any]]:
        """取引データ取得"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT trade_id, symbol, order_type, entry_time, exit_time,
                           entry_price, exit_price, volume, profit_loss, 
                           magic_number, comment
                    FROM trades
                    WHERE symbol = %s AND entry_time >= %s AND entry_time <= %s
                    AND profit_loss IS NOT NULL AND is_closed = true
                    ORDER BY entry_time
                """
                
                result = pd.read_sql_query(
                    query, conn,
                    params=(symbol, start_date, end_date),
                    parse_dates=['entry_time', 'exit_time']
                )
                
                return result.to_dict('records')
                
        except Exception as e:
            logger.error(f"Error getting trades data: {e}")
            return []
    
    def _filter_trades_by_session(self,
                                 trades: List[Dict[str, Any]],
                                 session_config: Dict[str, Any],
                                 session_name: str) -> List[Dict[str, Any]]:
        """セッション時間でトレードをフィルタ"""
        try:
            filtered_trades = []
            
            for trade in trades:
                trade_hour = self._get_jst_hour(trade['entry_time'])
                
                if session_name == 'ny':
                    # ニューヨーク時間は日をまたぐ
                    if trade_hour >= 21 or trade_hour <= 6:
                        filtered_trades.append(trade)
                else:
                    # 通常のセッション
                    if session_config['start'] <= trade_hour < session_config['end']:
                        filtered_trades.append(trade)
            
            return filtered_trades
            
        except Exception as e:
            logger.error(f"Error filtering trades by session: {e}")
            return []
    
    def _get_jst_hour(self, dt: datetime) -> int:
        """JST時間での時を取得"""
        try:
            if dt.tzinfo is None:
                dt = self.timezone_utc.localize(dt)
            jst_time = dt.astimezone(self.timezone_jst)
            return jst_time.hour
        except Exception as e:
            logger.error(f"Error getting JST hour: {e}")
            return 0
    
    def _get_jst_weekday(self, dt: datetime) -> int:
        """JST時間での曜日を取得"""
        try:
            if dt.tzinfo is None:
                dt = self.timezone_utc.localize(dt)
            jst_time = dt.astimezone(self.timezone_jst)
            return jst_time.weekday()
        except Exception as e:
            logger.error(f"Error getting JST weekday: {e}")
            return 0
    
    def _calculate_session_statistics(self,
                                     trades: List[Dict[str, Any]],
                                     session_config: Dict[str, Any]) -> Dict[str, Any]:
        """セッション統計計算"""
        try:
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['profit_loss'] > 0])
            losing_trades = len([t for t in trades if t['profit_loss'] < 0])
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            profits = [t['profit_loss'] for t in trades if t['profit_loss'] > 0]
            losses = [t['profit_loss'] for t in trades if t['profit_loss'] < 0]
            
            total_profit = sum(profits) if profits else 0
            total_loss = abs(sum(losses)) if losses else 0
            net_profit = sum([t['profit_loss'] for t in trades])
            
            profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
            avg_profit_per_trade = net_profit / total_trades if total_trades > 0 else 0
            
            # 平均取引時間計算
            durations = []
            for trade in trades:
                if trade['exit_time']:
                    duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600
                    durations.append(duration)
            
            avg_duration = np.mean(durations) if durations else 0
            
            return {
                'session_name': session_config['name'],
                'time_range': f"{session_config['start']:02d}:00-{session_config['end']:02d}:00",
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_profit': round(total_profit, 2),
                'total_loss': round(total_loss, 2),
                'net_profit': round(net_profit, 2),
                'profit_factor': round(profit_factor, 4),
                'avg_profit_per_trade': round(avg_profit_per_trade, 2),
                'avg_duration_hours': round(avg_duration, 2),
                'largest_win': round(max(profits), 2) if profits else 0,
                'largest_loss': round(abs(min(losses)), 2) if losses else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating session statistics: {e}")
            return self._empty_session_stats({})
    
    def _calculate_hourly_statistics(self,
                                    trades: List[Dict[str, Any]],
                                    hour: int) -> Dict[str, Any]:
        """時間別統計計算"""
        try:
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['profit_loss'] > 0])
            losing_trades = len([t for t in trades if t['profit_loss'] < 0])
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            profits = [t['profit_loss'] for t in trades if t['profit_loss'] > 0]
            losses = [t['profit_loss'] for t in trades if t['profit_loss'] < 0]
            
            total_profit = sum(profits) if profits else 0
            total_loss = abs(sum(losses)) if losses else 0
            net_profit = sum([t['profit_loss'] for t in trades])
            
            profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
            avg_profit_per_trade = net_profit / total_trades if total_trades > 0 else 0
            
            return {
                'hour': hour,
                'time_label': f"{hour:02d}:00",
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_profit': round(total_profit, 2),
                'total_loss': round(total_loss, 2),
                'net_profit': round(net_profit, 2),
                'profit_factor': round(profit_factor, 4),
                'avg_profit_per_trade': round(avg_profit_per_trade, 2),
                'largest_win': round(max(profits), 2) if profits else 0,
                'largest_loss': round(abs(min(losses)), 2) if losses else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating hourly statistics: {e}")
            return self._empty_hourly_stats(hour)
    
    def _calculate_weekday_statistics(self,
                                     trades: List[Dict[str, Any]],
                                     weekday: int) -> Dict[str, Any]:
        """曜日別統計計算"""
        try:
            weekday_names = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
            
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['profit_loss'] > 0])
            losing_trades = len([t for t in trades if t['profit_loss'] < 0])
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            profits = [t['profit_loss'] for t in trades if t['profit_loss'] > 0]
            losses = [t['profit_loss'] for t in trades if t['profit_loss'] < 0]
            
            total_profit = sum(profits) if profits else 0
            total_loss = abs(sum(losses)) if losses else 0
            net_profit = sum([t['profit_loss'] for t in trades])
            
            profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
            avg_profit_per_trade = net_profit / total_trades if total_trades > 0 else 0
            
            return {
                'weekday': weekday,
                'weekday_name': weekday_names[weekday],
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_profit': round(total_profit, 2),
                'total_loss': round(total_loss, 2),
                'net_profit': round(net_profit, 2),
                'profit_factor': round(profit_factor, 4),
                'avg_profit_per_trade': round(avg_profit_per_trade, 2),
                'largest_win': round(max(profits), 2) if profits else 0,
                'largest_loss': round(abs(min(losses)), 2) if losses else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating weekday statistics: {e}")
            return self._empty_weekday_stats(weekday)
    
    def _calculate_combined_statistics(self,
                                      trades: List[Dict[str, Any]],
                                      hour: int,
                                      weekday: int) -> Dict[str, Any]:
        """時間×曜日組み合わせ統計計算"""
        try:
            if not trades:
                return self._empty_combined_stats(hour, weekday)
            
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['profit_loss'] > 0])
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            net_profit = sum([t['profit_loss'] for t in trades])
            avg_profit_per_trade = net_profit / total_trades if total_trades > 0 else 0
            
            return {
                'hour': hour,
                'weekday': weekday,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': round(win_rate, 2),
                'net_profit': round(net_profit, 2),
                'avg_profit_per_trade': round(avg_profit_per_trade, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating combined statistics: {e}")
            return self._empty_combined_stats(hour, weekday)
    
    def _find_best_session(self, session_stats: Dict[str, Any]) -> Dict[str, Any]:
        """最高パフォーマンスセッション特定"""
        try:
            best_session = None
            best_score = -float('inf')
            
            for session_name, stats in session_stats.items():
                if stats['total_trades'] >= 10:  # 最低取引数
                    # 複合スコア計算
                    score = (
                        stats['win_rate'] * 0.4 +
                        min(stats['profit_factor'] * 20, 100) * 0.4 +
                        max(stats['avg_profit_per_trade'] / 100, 0) * 0.2
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_session = {
                            'session_name': session_name,
                            'statistics': stats,
                            'score': round(score, 2)
                        }
            
            return best_session
            
        except Exception as e:
            logger.error(f"Error finding best session: {e}")
            return None
    
    def _find_best_hours(self, hourly_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """最高パフォーマンス時間帯特定"""
        try:
            hour_scores = []
            
            for hour_str, stats in hourly_stats.items():
                if stats['total_trades'] >= 5:  # 最低取引数
                    score = (
                        stats['win_rate'] * 0.4 +
                        min(stats['profit_factor'] * 20, 100) * 0.4 +
                        max(stats['avg_profit_per_trade'] / 100, 0) * 0.2
                    )
                    
                    hour_scores.append({
                        'hour': hour_str,
                        'statistics': stats,
                        'score': round(score, 2)
                    })
            
            # スコア順でソート
            hour_scores.sort(key=lambda x: x['score'], reverse=True)
            
            return hour_scores[:5]  # トップ5
            
        except Exception as e:
            logger.error(f"Error finding best hours: {e}")
            return []
    
    def _find_best_weekdays(self, weekday_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """最高パフォーマンス曜日特定"""
        try:
            weekday_scores = []
            
            for weekday_name, stats in weekday_stats.items():
                if stats['total_trades'] >= 10:  # 最低取引数
                    score = (
                        stats['win_rate'] * 0.4 +
                        min(stats['profit_factor'] * 20, 100) * 0.4 +
                        max(stats['avg_profit_per_trade'] / 100, 0) * 0.2
                    )
                    
                    weekday_scores.append({
                        'weekday': weekday_name,
                        'statistics': stats,
                        'score': round(score, 2)
                    })
            
            # スコア順でソート
            weekday_scores.sort(key=lambda x: x['score'], reverse=True)
            
            return weekday_scores[:3]  # トップ3
            
        except Exception as e:
            logger.error(f"Error finding best weekdays: {e}")
            return []
    
    def _find_best_time_combinations(self, combined_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """最高パフォーマンス時間×曜日組み合わせ特定"""
        try:
            combinations = []
            
            for weekday_name, hourly_data in combined_stats.items():
                for hour_str, stats in hourly_data.items():
                    if stats['total_trades'] >= 3:  # 最低取引数
                        score = (
                            stats['win_rate'] * 0.5 +
                            max(stats['avg_profit_per_trade'] / 100, 0) * 0.5
                        )
                        
                        combinations.append({
                            'weekday': weekday_name,
                            'hour': hour_str,
                            'statistics': stats,
                            'score': round(score, 2)
                        })
            
            # スコア順でソート
            combinations.sort(key=lambda x: x['score'], reverse=True)
            
            return combinations[:10]  # トップ10
            
        except Exception as e:
            logger.error(f"Error finding best time combinations: {e}")
            return []
    
    def _compare_sessions(self, session_stats: Dict[str, Any]) -> Dict[str, Any]:
        """セッション間比較分析"""
        try:
            comparison = {
                'win_rate_ranking': [],
                'profit_factor_ranking': [],
                'volume_ranking': []
            }
            
            # 勝率ランキング
            win_rate_ranking = [
                {'session': name, 'win_rate': stats['win_rate']}
                for name, stats in session_stats.items()
                if stats['total_trades'] > 0
            ]
            win_rate_ranking.sort(key=lambda x: x['win_rate'], reverse=True)
            comparison['win_rate_ranking'] = win_rate_ranking
            
            # プロフィットファクターランキング
            pf_ranking = [
                {'session': name, 'profit_factor': stats['profit_factor']}
                for name, stats in session_stats.items()
                if stats['total_trades'] > 0 and stats['profit_factor'] != float('inf')
            ]
            pf_ranking.sort(key=lambda x: x['profit_factor'], reverse=True)
            comparison['profit_factor_ranking'] = pf_ranking
            
            # 取引量ランキング
            volume_ranking = [
                {'session': name, 'total_trades': stats['total_trades']}
                for name, stats in session_stats.items()
            ]
            volume_ranking.sort(key=lambda x: x['total_trades'], reverse=True)
            comparison['volume_ranking'] = volume_ranking
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing sessions: {e}")
            return {}
    
    def _analyze_hourly_patterns(self, hourly_stats: Dict[str, Any]) -> Dict[str, Any]:
        """時間帯パターン分析"""
        try:
            patterns = {
                'peak_hours': [],
                'low_hours': [],
                'volatility_analysis': {}
            }
            
            # 取引量ベースでピーク・ロー時間を特定
            volume_data = [
                {'hour': hour, 'volume': stats['total_trades']}
                for hour, stats in hourly_stats.items()
            ]
            
            volume_data.sort(key=lambda x: x['volume'], reverse=True)
            
            patterns['peak_hours'] = volume_data[:3]  # 上位3時間
            patterns['low_hours'] = volume_data[-3:]  # 下位3時間
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing hourly patterns: {e}")
            return {}
    
    def _analyze_weekly_patterns(self, weekday_stats: Dict[str, Any]) -> Dict[str, Any]:
        """週パターン分析"""
        try:
            patterns = {
                'best_start_day': None,
                'best_end_day': None,
                'weekend_effect': {}
            }
            
            # 週明け・週末効果の分析
            weekday_performance = [
                {'day': day, 'win_rate': stats['win_rate'], 'total_trades': stats['total_trades']}
                for day, stats in weekday_stats.items()
                if stats['total_trades'] > 0
            ]
            
            if weekday_performance:
                best_performance = max(weekday_performance, key=lambda x: x['win_rate'])
                patterns['best_start_day'] = best_performance['day']
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing weekly patterns: {e}")
            return {}
    
    def _generate_heatmap_data(self, combined_stats: Dict[str, Any]) -> List[List[Any]]:
        """ヒートマップデータ生成"""
        try:
            # 曜日 x 時間のマトリックス
            weekdays = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
            hours = [f"{h:02d}:00" for h in range(24)]
            
            heatmap_data = []
            
            for weekday in weekdays:
                row = []
                for hour in hours:
                    if weekday in combined_stats and hour in combined_stats[weekday]:
                        stats = combined_stats[weekday][hour]
                        # 勝率をヒートマップ値として使用
                        value = stats['win_rate'] if stats['total_trades'] > 0 else 0
                    else:
                        value = 0
                    row.append(value)
                heatmap_data.append(row)
            
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Error generating heatmap data: {e}")
            return []
    
    def _generate_session_recommendations(self, session_stats: Dict[str, Any]) -> List[str]:
        """セッション推奨事項生成"""
        try:
            recommendations = []
            
            # 最高パフォーマンスセッション推奨
            best_session = self._find_best_session(session_stats)
            if best_session:
                recommendations.append(
                    f"{best_session['session_name']}が最も良好なパフォーマンスを示しています"
                    f"（勝率: {best_session['statistics']['win_rate']:.1f}%）"
                )
            
            # 低パフォーマンスセッション警告
            for session_name, stats in session_stats.items():
                if stats['total_trades'] >= 10 and stats['win_rate'] < 40:
                    recommendations.append(
                        f"{session_name}での取引は避けることを推奨します"
                        f"（勝率: {stats['win_rate']:.1f}%）"
                    )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating session recommendations: {e}")
            return []
    
    def _generate_hourly_recommendations(self, hourly_stats: Dict[str, Any]) -> List[str]:
        """時間別推奨事項生成"""
        try:
            recommendations = []
            
            best_hours = self._find_best_hours(hourly_stats)
            if best_hours:
                top_hour = best_hours[0]
                recommendations.append(
                    f"{top_hour['hour']}が最も良好なパフォーマンスを示しています"
                    f"（勝率: {top_hour['statistics']['win_rate']:.1f}%）"
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating hourly recommendations: {e}")
            return []
    
    def _generate_weekday_recommendations(self, weekday_stats: Dict[str, Any]) -> List[str]:
        """曜日別推奨事項生成"""
        try:
            recommendations = []
            
            best_weekdays = self._find_best_weekdays(weekday_stats)
            if best_weekdays:
                top_weekday = best_weekdays[0]
                recommendations.append(
                    f"{top_weekday['weekday']}が最も良好なパフォーマンスを示しています"
                    f"（勝率: {top_weekday['statistics']['win_rate']:.1f}%）"
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating weekday recommendations: {e}")
            return []
    
    def _generate_combined_recommendations(self, best_combinations: List[Dict[str, Any]]) -> List[str]:
        """総合推奨事項生成"""
        try:
            recommendations = []
            
            if best_combinations:
                top_combo = best_combinations[0]
                recommendations.append(
                    f"{top_combo['weekday']} {top_combo['hour']}が最も良好な時間帯です"
                    f"（勝率: {top_combo['statistics']['win_rate']:.1f}%）"
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating combined recommendations: {e}")
            return []
    
    # Empty statistics methods
    def _empty_session_analysis(self, symbol: str, period_days: int) -> Dict[str, Any]:
        """空のセッション分析結果"""
        return {
            'symbol': symbol,
            'period_days': period_days,
            'total_trades': 0,
            'session_statistics': {},
            'best_session': None,
            'recommendations': ['十分な取引データがありません']
        }
    
    def _empty_hourly_analysis(self, symbol: str, period_days: int) -> Dict[str, Any]:
        """空の時間別分析結果"""
        return {
            'symbol': symbol,
            'period_days': period_days,
            'total_trades': 0,
            'hourly_statistics': {},
            'best_hours': [],
            'recommendations': ['十分な取引データがありません']
        }
    
    def _empty_weekday_analysis(self, symbol: str, period_days: int) -> Dict[str, Any]:
        """空の曜日別分析結果"""
        return {
            'symbol': symbol,
            'period_days': period_days,
            'total_trades': 0,
            'weekday_statistics': {},
            'best_weekdays': [],
            'recommendations': ['十分な取引データがありません']
        }
    
    def _empty_combined_analysis(self, symbol: str, period_days: int) -> Dict[str, Any]:
        """空の総合分析結果"""
        return {
            'symbol': symbol,
            'period_days': period_days,
            'total_trades': 0,
            'combined_statistics': {},
            'best_combinations': [],
            'heatmap_data': [],
            'recommendations': ['十分な取引データがありません']
        }
    
    def _empty_session_stats(self, session_config: Dict[str, Any]) -> Dict[str, Any]:
        """空のセッション統計"""
        return {
            'session_name': session_config.get('name', ''),
            'time_range': '',
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'total_loss': 0,
            'net_profit': 0,
            'profit_factor': 0,
            'avg_profit_per_trade': 0,
            'avg_duration_hours': 0,
            'largest_win': 0,
            'largest_loss': 0
        }
    
    def _empty_hourly_stats(self, hour: int) -> Dict[str, Any]:
        """空の時間別統計"""
        return {
            'hour': hour,
            'time_label': f"{hour:02d}:00",
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'total_loss': 0,
            'net_profit': 0,
            'profit_factor': 0,
            'avg_profit_per_trade': 0,
            'largest_win': 0,
            'largest_loss': 0
        }
    
    def _empty_weekday_stats(self, weekday: int) -> Dict[str, Any]:
        """空の曜日別統計"""
        weekday_names = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
        return {
            'weekday': weekday,
            'weekday_name': weekday_names[weekday] if 0 <= weekday < 7 else '',
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'total_loss': 0,
            'net_profit': 0,
            'profit_factor': 0,
            'avg_profit_per_trade': 0,
            'largest_win': 0,
            'largest_loss': 0
        }
    
    def _empty_combined_stats(self, hour: int, weekday: int) -> Dict[str, Any]:
        """空の時間×曜日統計"""
        return {
            'hour': hour,
            'weekday': weekday,
            'total_trades': 0,
            'winning_trades': 0,
            'win_rate': 0,
            'net_profit': 0,
            'avg_profit_per_trade': 0
        }

if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.append('.')
    
    logging.basicConfig(level=logging.INFO)
    
    print("Timeframe analyzer test completed")