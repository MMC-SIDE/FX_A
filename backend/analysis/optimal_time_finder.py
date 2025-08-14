"""
最適時間帯検出機能
"""
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from backend.core.database import DatabaseManager
from backend.analysis.timeframe_analyzer import TimeframeAnalyzer
from backend.analysis.economic_news_analyzer import EconomicNewsAnalyzer

logger = logging.getLogger(__name__)


class OptimalTimeFinder:
    """
    最適取引時間帯検出クラス
    統計分析と経済指標を組み合わせて最適な取引タイミングを特定
    """
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or DatabaseManager().get_session()
        self.timeframe_analyzer = TimeframeAnalyzer(self.db)
        self.news_analyzer = EconomicNewsAnalyzer(self.db)
        
    async def find_optimal_trading_hours(self, 
                                       symbol: str,
                                       min_trades: int = 20,
                                       min_win_rate: float = 60.0,
                                       min_profit_factor: float = 1.2,
                                       exclude_news_hours: bool = True) -> Dict[str, Any]:
        """
        最適な取引時間帯の検出
        
        Args:
            symbol: 通貨ペア
            min_trades: 最小取引数
            min_win_rate: 最小勝率（%）
            min_profit_factor: 最小プロフィットファクター
            exclude_news_hours: ニュース時間を除外するか
            
        Returns:
            最適時間帯検出結果
        """
        try:
            # 時間別分析実行
            hourly_analysis = self.timeframe_analyzer.analyze_hourly_performance(symbol)
            
            # 経済指標の影響分析
            news_impact = None
            if exclude_news_hours:
                news_impact = await self.news_analyzer.analyze_news_impact(symbol)
            
            optimal_hours = []
            
            for hour_str, stats in hourly_analysis['hourly_statistics'].items():
                # 基本条件チェック
                if (stats['total_trades'] >= min_trades and
                    stats['win_rate'] >= min_win_rate and
                    stats['profit_factor'] >= min_profit_factor):
                    
                    hour = int(hour_str.split(':')[0])
                    
                    # ニュース影響のチェック
                    news_risk_score = 0
                    if exclude_news_hours and news_impact:
                        news_risk_score = self._calculate_news_risk_for_hour(hour, news_impact)
                    
                    # 時間帯スコア計算
                    score = self._calculate_hour_score(stats, news_risk_score)
                    
                    optimal_hours.append({
                        'hour': hour_str,
                        'statistics': stats,
                        'score': score,
                        'news_risk_score': news_risk_score,
                        'market_session': self._identify_market_session(hour)
                    })
            
            # スコア順でソート
            optimal_hours.sort(key=lambda x: x['score'], reverse=True)
            
            # 連続する時間帯をグループ化
            time_windows = self._group_consecutive_hours(optimal_hours)
            
            # 取引スケジュール生成
            trading_schedule = self._generate_trading_schedule(time_windows, exclude_news_hours)
            
            return {
                'symbol': symbol,
                'analysis_criteria': {
                    'min_trades': min_trades,
                    'min_win_rate': min_win_rate,
                    'min_profit_factor': min_profit_factor,
                    'exclude_news_hours': exclude_news_hours
                },
                'optimal_hours': optimal_hours[:10],  # トップ10
                'recommended_windows': time_windows[:5],  # トップ5窓
                'trading_schedule': trading_schedule,
                'market_session_analysis': self._analyze_session_performance(optimal_hours),
                'recommendations': self._generate_optimal_time_recommendations(optimal_hours, time_windows)
            }
            
        except Exception as e:
            logger.error(f"Error finding optimal trading hours: {e}")
            return {
                'symbol': symbol,
                'optimal_hours': [],
                'recommended_windows': [],
                'trading_schedule': {},
                'error': str(e)
            }
    
    def _calculate_news_risk_for_hour(self, hour: int, news_impact: Dict[str, Any]) -> float:
        """
        指定時間のニュースリスクスコア計算
        
        Args:
            hour: 時間（0-23）
            news_impact: ニュース影響分析結果
            
        Returns:
            リスクスコア（0-100）
        """
        risk_score = 0
        
        for event in news_impact.get('results', []):
            event_hour = datetime.fromisoformat(event['event']['time']).hour
            
            # イベント前後1時間をリスク時間とする
            if abs(event_hour - hour) <= 1 or abs(event_hour - hour) >= 23:
                volatility_increase = event['volatility_analysis']['volatility_increase_percent']
                impact_weight = {'high': 3, 'medium': 2, 'low': 1}.get(event['event']['impact'], 1)
                
                risk_score += volatility_increase * impact_weight * 0.01
        
        return min(risk_score, 100)  # 最大100に制限
    
    def _calculate_hour_score(self, stats: Dict[str, Any], news_risk_score: float = 0) -> float:
        """
        時間帯スコア計算
        
        Args:
            stats: 統計データ
            news_risk_score: ニュースリスクスコア
            
        Returns:
            総合スコア
        """
        # 基本パフォーマンススコア
        win_rate_score = stats['win_rate'] / 100 * 0.3
        profit_factor_score = min(stats['profit_factor'] / 2, 1.0) * 0.4
        avg_profit_score = max(stats['avg_profit_per_trade'] / 1000, 0) * 0.2
        
        # 取引量ボーナス
        trade_volume_bonus = min(stats['total_trades'] / 100, 1.0) * 0.1
        
        base_score = win_rate_score + profit_factor_score + avg_profit_score + trade_volume_bonus
        
        # ニュースリスクペナルティ
        risk_penalty = news_risk_score / 100 * 0.3
        
        final_score = max(0, base_score - risk_penalty)
        
        return round(final_score, 4)
    
    def _identify_market_session(self, hour: int) -> str:
        """
        時間から市場セッションを特定
        
        Args:
            hour: 時間（JST）
            
        Returns:
            市場セッション名
        """
        if 9 <= hour <= 15:
            return 'tokyo'
        elif 16 <= hour <= 20:
            return 'london'
        elif 21 <= hour <= 23:
            return 'london_ny_overlap'
        elif 0 <= hour <= 6:
            return 'ny'
        else:
            return 'quiet'
    
    def _group_consecutive_hours(self, optimal_hours: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        連続する時間帯のグループ化
        
        Args:
            optimal_hours: 最適時間リスト
            
        Returns:
            時間窓リスト
        """
        if not optimal_hours:
            return []
        
        windows = []
        current_window = [optimal_hours[0]]
        
        for i in range(1, len(optimal_hours)):
            current_hour = int(optimal_hours[i]['hour'].split(':')[0])
            prev_hour = int(optimal_hours[i-1]['hour'].split(':')[0])
            
            # 連続チェック（24時間回りも考慮）
            is_consecutive = (
                current_hour == (prev_hour + 1) % 24 or
                (prev_hour == 23 and current_hour == 0)
            )
            
            if is_consecutive:
                current_window.append(optimal_hours[i])
            else:
                if len(current_window) >= 1:  # 1時間以上の窓
                    windows.append(self._create_time_window(current_window))
                current_window = [optimal_hours[i]]
        
        # 最後の窓を追加
        if len(current_window) >= 1:
            windows.append(self._create_time_window(current_window))
        
        # 品質スコアでソート
        windows.sort(key=lambda x: x['quality_score'], reverse=True)
        
        return windows
    
    def _create_time_window(self, hours: List[Dict[str, Any]]) -> Dict[str, Any]:
        """時間窓オブジェクト作成"""
        start_hour = int(hours[0]['hour'].split(':')[0])
        end_hour = int(hours[-1]['hour'].split(':')[0])
        
        # 統計の平均計算
        total_trades = sum(h['statistics']['total_trades'] for h in hours)
        avg_win_rate = sum(h['statistics']['win_rate'] for h in hours) / len(hours)
        avg_profit_factor = sum(h['statistics']['profit_factor'] for h in hours) / len(hours)
        avg_score = sum(h['score'] for h in hours) / len(hours)
        
        # 窓の品質スコア
        quality_score = avg_score * (1 + len(hours) * 0.1)  # 連続時間にボーナス
        
        return {
            'start_hour': f"{start_hour:02d}:00",
            'end_hour': f"{(end_hour + 1) % 24:02d}:00",
            'duration_hours': len(hours),
            'hours': [h['hour'] for h in hours],
            'quality_score': round(quality_score, 4),
            'statistics': {
                'total_trades': total_trades,
                'avg_win_rate': round(avg_win_rate, 2),
                'avg_profit_factor': round(avg_profit_factor, 4),
                'avg_score': round(avg_score, 4)
            },
            'market_sessions': list(set(h['market_session'] for h in hours))
        }
    
    def _generate_trading_schedule(self, 
                                 time_windows: List[Dict[str, Any]], 
                                 exclude_news: bool = True) -> Dict[str, Any]:
        """
        取引スケジュール生成
        
        Args:
            time_windows: 時間窓リスト
            exclude_news: ニュース時間除外フラグ
            
        Returns:
            取引スケジュール
        """
        if not time_windows:
            return {
                'active_hours': [],
                'inactive_hours': list(range(24)),
                'recommended_sessions': [],
                'total_active_hours': 0
            }
        
        # 推奨時間の抽出
        active_hours = []
        for window in time_windows[:3]:  # トップ3窓
            for hour_str in window['hours']:
                hour = int(hour_str.split(':')[0])
                if hour not in active_hours:
                    active_hours.append(hour)
        
        active_hours.sort()
        inactive_hours = [h for h in range(24) if h not in active_hours]
        
        # セッション推奨
        recommended_sessions = []
        for window in time_windows[:3]:
            sessions = window['market_sessions']
            for session in sessions:
                if session not in [r['session'] for r in recommended_sessions]:
                    recommended_sessions.append({
                        'session': session,
                        'window': window,
                        'priority': 'high' if window['quality_score'] > 0.7 else 'medium'
                    })
        
        return {
            'active_hours': active_hours,
            'inactive_hours': inactive_hours,
            'recommended_sessions': recommended_sessions,
            'total_active_hours': len(active_hours),
            'schedule_efficiency': round(len(active_hours) / 24 * 100, 1),
            'daily_schedule': self._create_daily_schedule(active_hours)
        }
    
    def _create_daily_schedule(self, active_hours: List[int]) -> Dict[str, str]:
        """日別スケジュール作成"""
        schedule = {}
        
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        for day in weekdays:
            if day == 'friday':
                # 金曜日は早めに終了（週末リスク回避）
                day_hours = [h for h in active_hours if h < 20]
            else:
                day_hours = active_hours
            
            if day_hours:
                schedule[day] = f"{min(day_hours):02d}:00-{max(day_hours)+1:02d}:00"
            else:
                schedule[day] = "取引休止"
        
        # 週末は取引停止
        schedule['saturday'] = "市場休場"
        schedule['sunday'] = "市場休場"
        
        return schedule
    
    def _analyze_session_performance(self, optimal_hours: List[Dict[str, Any]]) -> Dict[str, Any]:
        """市場セッション別パフォーマンス分析"""
        session_stats = {}
        
        for hour_data in optimal_hours:
            session = hour_data['market_session']
            if session not in session_stats:
                session_stats[session] = {
                    'hours_count': 0,
                    'total_score': 0,
                    'total_trades': 0,
                    'avg_win_rate': 0,
                    'avg_profit_factor': 0
                }
            
            stats = session_stats[session]
            stats['hours_count'] += 1
            stats['total_score'] += hour_data['score']
            stats['total_trades'] += hour_data['statistics']['total_trades']
            stats['avg_win_rate'] += hour_data['statistics']['win_rate']
            stats['avg_profit_factor'] += hour_data['statistics']['profit_factor']
        
        # 平均計算
        for session, stats in session_stats.items():
            if stats['hours_count'] > 0:
                stats['avg_score'] = round(stats['total_score'] / stats['hours_count'], 4)
                stats['avg_win_rate'] = round(stats['avg_win_rate'] / stats['hours_count'], 2)
                stats['avg_profit_factor'] = round(stats['avg_profit_factor'] / stats['hours_count'], 4)
        
        # ランキング
        session_ranking = sorted(
            session_stats.items(),
            key=lambda x: x[1]['avg_score'],
            reverse=True
        )
        
        return {
            'session_statistics': session_stats,
            'best_session': session_ranking[0][0] if session_ranking else None,
            'session_ranking': [{'session': s[0], 'score': s[1]['avg_score']} for s in session_ranking]
        }
    
    def _generate_optimal_time_recommendations(self, 
                                             optimal_hours: List[Dict[str, Any]], 
                                             time_windows: List[Dict[str, Any]]) -> List[str]:
        """最適時間の推奨事項生成"""
        recommendations = []
        
        if not optimal_hours:
            recommendations.append("最適な取引時間帯が見つかりませんでした。条件を緩和するか、取引戦略を見直してください。")
            return recommendations
        
        # 最高スコア時間
        best_hour = optimal_hours[0]
        recommendations.append(
            f"最高パフォーマンス時間: {best_hour['hour']} "
            f"(勝率: {best_hour['statistics']['win_rate']}%, "
            f"PF: {best_hour['statistics']['profit_factor']})"
        )
        
        # 連続時間窓の推奨
        if time_windows:
            best_window = time_windows[0]
            recommendations.append(
                f"推奨取引時間帯: {best_window['start_hour']}-{best_window['end_hour']} "
                f"({best_window['duration_hours']}時間連続)"
            )
        
        # セッション別推奨
        session_performance = self._analyze_session_performance(optimal_hours)
        if session_performance['best_session']:
            session_names = {
                'tokyo': '東京セッション',
                'london': 'ロンドンセッション',
                'ny': 'ニューヨークセッション',
                'london_ny_overlap': 'ロンドン・NY重複',
                'quiet': '閑散時間'
            }
            best_session_name = session_names.get(session_performance['best_session'], session_performance['best_session'])
            recommendations.append(f"最適市場セッション: {best_session_name}")
        
        # リスク関連推奨
        high_risk_hours = [h for h in optimal_hours if h.get('news_risk_score', 0) > 50]
        if high_risk_hours:
            recommendations.append(
                f"ニュースリスクの高い時間帯 ({len(high_risk_hours)}時間) では "
                "ポジションサイズを50%に縮小することを推奨します。"
            )
        
        # 取引効率
        total_optimal_hours = len(optimal_hours)
        if total_optimal_hours < 4:
            recommendations.append("最適時間帯が少ないため、取引機会が限られる可能性があります。")
        elif total_optimal_hours > 12:
            recommendations.append("多くの時間帯が最適ですが、過度な取引に注意してください。")
        
        return recommendations
    
    async def find_optimal_entry_exit_times(self, 
                                          symbol: str,
                                          position_type: str = 'both',
                                          min_holding_hours: int = 1) -> Dict[str, Any]:
        """
        最適なエントリー・エグジット時間の特定
        
        Args:
            symbol: 通貨ペア
            position_type: ポジション種別（'buy', 'sell', 'both'）
            min_holding_hours: 最小保有時間
            
        Returns:
            最適エントリー・エグジット時間
        """
        try:
            # 時間別分析
            hourly_analysis = self.timeframe_analyzer.analyze_hourly_performance(symbol)
            
            entry_times = []
            exit_times = []
            
            for hour_str, stats in hourly_analysis['hourly_statistics'].items():
                hour = int(hour_str.split(':')[0])
                
                # エントリー時間の評価
                entry_score = self._calculate_entry_score(stats, hour)
                if entry_score > 0.6:
                    entry_times.append({
                        'hour': hour_str,
                        'score': entry_score,
                        'statistics': stats
                    })
                
                # エグジット時間の評価
                exit_score = self._calculate_exit_score(stats, hour)
                if exit_score > 0.6:
                    exit_times.append({
                        'hour': hour_str,
                        'score': exit_score,
                        'statistics': stats
                    })
            
            # スコア順ソート
            entry_times.sort(key=lambda x: x['score'], reverse=True)
            exit_times.sort(key=lambda x: x['score'], reverse=True)
            
            # 最適ペアの生成
            optimal_pairs = self._generate_entry_exit_pairs(
                entry_times, exit_times, min_holding_hours
            )
            
            return {
                'symbol': symbol,
                'position_type': position_type,
                'optimal_entry_times': entry_times[:5],
                'optimal_exit_times': exit_times[:5],
                'optimal_pairs': optimal_pairs[:3],
                'recommendations': self._generate_entry_exit_recommendations(optimal_pairs)
            }
            
        except Exception as e:
            logger.error(f"Error finding optimal entry/exit times: {e}")
            return {
                'symbol': symbol,
                'optimal_entry_times': [],
                'optimal_exit_times': [],
                'optimal_pairs': [],
                'error': str(e)
            }
    
    def _calculate_entry_score(self, stats: Dict[str, Any], hour: int) -> float:
        """エントリー時間スコア計算"""
        # 勝率重視
        win_rate_score = stats['win_rate'] / 100 * 0.4
        
        # 平均利益重視
        avg_profit_score = max(stats['avg_profit_per_trade'] / 1000, 0) * 0.3
        
        # 取引量
        volume_score = min(stats['total_trades'] / 50, 1.0) * 0.2
        
        # 時間帯ボーナス（ボラティリティが高い時間）
        time_bonus = 0.1 if hour in [9, 10, 16, 17, 21, 22] else 0
        
        return win_rate_score + avg_profit_score + volume_score + time_bonus
    
    def _calculate_exit_score(self, stats: Dict[str, Any], hour: int) -> float:
        """エグジット時間スコア計算"""
        # プロフィットファクター重視
        pf_score = min(stats['profit_factor'] / 2, 1.0) * 0.4
        
        # 勝率
        win_rate_score = stats['win_rate'] / 100 * 0.3
        
        # 損失の少なさ
        loss_score = 0.2 if stats.get('avg_loss', 0) < 500 else 0.1
        
        # 市場クローズ前ボーナス
        close_bonus = 0.1 if hour in [14, 15, 23, 0] else 0
        
        return pf_score + win_rate_score + loss_score + close_bonus
    
    def _generate_entry_exit_pairs(self, 
                                 entry_times: List[Dict[str, Any]], 
                                 exit_times: List[Dict[str, Any]], 
                                 min_holding_hours: int) -> List[Dict[str, Any]]:
        """エントリー・エグジットペア生成"""
        pairs = []
        
        for entry in entry_times[:5]:
            entry_hour = int(entry['hour'].split(':')[0])
            
            for exit in exit_times[:5]:
                exit_hour = int(exit['hour'].split(':')[0])
                
                # 保有時間計算（24時間回りを考慮）
                holding_hours = (exit_hour - entry_hour) % 24
                
                if holding_hours >= min_holding_hours and holding_hours <= 12:
                    combined_score = (entry['score'] + exit['score']) / 2
                    
                    pairs.append({
                        'entry_hour': entry['hour'],
                        'exit_hour': exit['hour'],
                        'holding_hours': holding_hours,
                        'entry_score': entry['score'],
                        'exit_score': exit['score'],
                        'combined_score': combined_score,
                        'entry_stats': entry['statistics'],
                        'exit_stats': exit['statistics']
                    })
        
        pairs.sort(key=lambda x: x['combined_score'], reverse=True)
        return pairs
    
    def _generate_entry_exit_recommendations(self, pairs: List[Dict[str, Any]]) -> List[str]:
        """エントリー・エグジット推奨事項生成"""
        recommendations = []
        
        if not pairs:
            recommendations.append("最適なエントリー・エグジットペアが見つかりませんでした。")
            return recommendations
        
        best_pair = pairs[0]
        recommendations.append(
            f"最適ペア: {best_pair['entry_hour']}エントリー → "
            f"{best_pair['exit_hour']}エグジット "
            f"(保有時間: {best_pair['holding_hours']}時間)"
        )
        
        avg_holding = sum(p['holding_hours'] for p in pairs) / len(pairs)
        recommendations.append(f"推奨平均保有時間: {avg_holding:.1f}時間")
        
        if best_pair['holding_hours'] < 4:
            recommendations.append("短時間取引が最適です。スキャルピング戦略を検討してください。")
        elif best_pair['holding_hours'] > 8:
            recommendations.append("長時間保有が最適です。スイング戦略を検討してください。")
        
        return recommendations