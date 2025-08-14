"""
経済指標ニュース分析機能
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import asyncio
import aiohttp
from sqlalchemy.orm import Session

from backend.core.database import DatabaseManager
from backend.models.database_models import EconomicCalendar, PriceData

logger = logging.getLogger(__name__)


class EconomicNewsAnalyzer:
    """
    経済指標ニュース分析クラス
    経済指標発表前後の価格変動を分析
    """
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or DatabaseManager().get_session()
        self.api_config = self._load_api_config()
        
    def _load_api_config(self) -> Dict[str, str]:
        """外部API設定読み込み"""
        # 実際の実装では設定ファイルから読み込み
        return {
            "forex_factory_url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            "investing_com_url": "https://api.investing.com/api/financialdata/",
            "timeout": 30
        }
    
    async def fetch_economic_calendar(self, 
                                    start_date: datetime,
                                    end_date: datetime,
                                    currencies: List[str] = None) -> List[Dict[str, Any]]:
        """
        経済指標カレンダー取得
        
        Args:
            start_date: 開始日
            end_date: 終了日
            currencies: 対象通貨リスト
            
        Returns:
            経済指標データリスト
        """
        try:
            if currencies is None:
                currencies = ['USD', 'JPY', 'EUR', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF']
            
            # 外部APIからデータ取得
            events = await self._fetch_from_external_api(start_date, end_date, currencies)
            
            # データベースに保存
            saved_count = await self._save_economic_events(events)
            
            logger.info(f"Fetched {len(events)} economic events, saved {saved_count} new events")
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to fetch economic calendar: {e}")
            return []
    
    async def _fetch_from_external_api(self, 
                                     start_date: datetime, 
                                     end_date: datetime,
                                     currencies: List[str]) -> List[Dict[str, Any]]:
        """
        外部APIからデータ取得（サンプル実装）
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.api_config["timeout"])) as session:
                # ForexFactory APIからデータ取得（サンプル）
                async with session.get(self.api_config["forex_factory_url"]) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_forex_factory_data(data, start_date, end_date, currencies)
                    else:
                        logger.warning(f"External API returned status {response.status}")
                        return self._generate_sample_economic_data(start_date, end_date, currencies)
                        
        except Exception as e:
            logger.warning(f"External API call failed: {e}, using sample data")
            return self._generate_sample_economic_data(start_date, end_date, currencies)
    
    def _parse_forex_factory_data(self, 
                                data: Any, 
                                start_date: datetime, 
                                end_date: datetime,
                                currencies: List[str]) -> List[Dict[str, Any]]:
        """ForexFactoryデータのパース"""
        events = []
        
        try:
            # データ構造は実際のAPIに依存
            for item in data:
                event_time = datetime.fromisoformat(item.get('date', ''))
                
                if start_date <= event_time <= end_date:
                    currency = item.get('currency', '')
                    if currency in currencies:
                        events.append({
                            'time': event_time,
                            'currency': currency,
                            'name': item.get('title', ''),
                            'impact': item.get('impact', 'medium'),
                            'actual': item.get('actual'),
                            'forecast': item.get('forecast'),
                            'previous': item.get('previous')
                        })
            
            return events
            
        except Exception as e:
            logger.error(f"Error parsing ForexFactory data: {e}")
            return []
    
    def _generate_sample_economic_data(self, 
                                     start_date: datetime, 
                                     end_date: datetime,
                                     currencies: List[str]) -> List[Dict[str, Any]]:
        """サンプル経済指標データ生成"""
        events = []
        
        sample_events = [
            {
                'name': 'Non-Farm Payrolls',
                'currency': 'USD',
                'impact': 'high',
                'typical_day': 5,  # 金曜日
                'time_hour': 22,   # JST 22:30
                'time_minute': 30
            },
            {
                'name': 'GDP Growth Rate',
                'currency': 'JPY',
                'impact': 'high',
                'typical_day': 1,  # 月曜日
                'time_hour': 8,
                'time_minute': 50
            },
            {
                'name': 'Consumer Price Index',
                'currency': 'EUR',
                'impact': 'medium',
                'typical_day': 3,  # 水曜日
                'time_hour': 18,
                'time_minute': 0
            },
            {
                'name': 'Interest Rate Decision',
                'currency': 'GBP',
                'impact': 'high',
                'typical_day': 4,  # 木曜日
                'time_hour': 21,
                'time_minute': 0
            }
        ]
        
        current_date = start_date
        while current_date <= end_date:
            for event_template in sample_events:
                if (current_date.weekday() == event_template['typical_day'] and 
                    event_template['currency'] in currencies):
                    
                    event_time = current_date.replace(
                        hour=event_template['time_hour'],
                        minute=event_template['time_minute'],
                        second=0,
                        microsecond=0
                    )
                    
                    events.append({
                        'time': event_time,
                        'currency': event_template['currency'],
                        'name': event_template['name'],
                        'impact': event_template['impact'],
                        'actual': 2.1,
                        'forecast': 2.0,
                        'previous': 1.9
                    })
            
            current_date += timedelta(days=1)
        
        return events
    
    async def _save_economic_events(self, events: List[Dict[str, Any]]) -> int:
        """経済指標イベントをデータベースに保存"""
        saved_count = 0
        
        try:
            for event in events:
                # 既存データチェック
                existing = self.db.query(EconomicCalendar).filter(
                    EconomicCalendar.event_time == event['time'],
                    EconomicCalendar.event_name == event['name'],
                    EconomicCalendar.currency == event['currency']
                ).first()
                
                if not existing:
                    calendar_entry = EconomicCalendar(
                        event_time=event['time'],
                        currency=event['currency'],
                        event_name=event['name'],
                        impact=event['impact'],
                        actual_value=event.get('actual'),
                        forecast_value=event.get('forecast'),
                        previous_value=event.get('previous')
                    )
                    self.db.add(calendar_entry)
                    saved_count += 1
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error saving economic events: {e}")
            self.db.rollback()
        
        return saved_count
    
    async def analyze_news_impact(self, 
                                symbol: str,
                                impact_levels: List[str] = None,
                                time_window_minutes: int = 60,
                                period_days: int = 90) -> Dict[str, Any]:
        """
        経済指標の影響分析
        
        Args:
            symbol: 通貨ペア
            impact_levels: 影響レベル（high, medium, low）
            time_window_minutes: 分析時間窓（分）
            period_days: 分析期間（日）
            
        Returns:
            影響分析結果
        """
        try:
            if impact_levels is None:
                impact_levels = ['high', 'medium']
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            # 対象経済指標取得
            target_currencies = self._extract_currencies_from_symbol(symbol)
            
            events = self.db.query(EconomicCalendar).filter(
                EconomicCalendar.impact.in_(impact_levels),
                EconomicCalendar.currency.in_(target_currencies),
                EconomicCalendar.event_time.between(start_date, end_date)
            ).all()
            
            analysis_results = []
            
            for event in events:
                volatility_analysis = await self._analyze_event_volatility(
                    symbol, event, time_window_minutes
                )
                
                if volatility_analysis:
                    analysis_results.append({
                        'event': {
                            'name': event.event_name,
                            'time': event.event_time.isoformat(),
                            'currency': event.currency,
                            'impact': event.impact,
                            'actual': event.actual_value,
                            'forecast': event.forecast_value,
                            'previous': event.previous_value
                        },
                        'volatility_analysis': volatility_analysis
                    })
            
            summary = self._summarize_news_impact(analysis_results)
            
            return {
                'symbol': symbol,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'analyzed_events': len(analysis_results),
                'results': analysis_results,
                'summary': summary,
                'recommendations': self._generate_news_impact_recommendations(summary)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing news impact: {e}")
            return {
                'symbol': symbol,
                'analyzed_events': 0,
                'results': [],
                'summary': {},
                'error': str(e)
            }
    
    def _extract_currencies_from_symbol(self, symbol: str) -> List[str]:
        """通貨ペアから通貨を抽出"""
        if len(symbol) >= 6:
            return [symbol[:3], symbol[3:6]]
        return ['USD', 'JPY']  # デフォルト
    
    async def _analyze_event_volatility(self, 
                                      symbol: str, 
                                      event: EconomicCalendar, 
                                      time_window_minutes: int) -> Optional[Dict[str, Any]]:
        """
        イベント前後のボラティリティ分析
        
        Args:
            symbol: 通貨ペア
            event: 経済指標イベント
            time_window_minutes: 分析時間窓
            
        Returns:
            ボラティリティ分析結果
        """
        try:
            event_time = event.event_time
            before_time = event_time - timedelta(minutes=time_window_minutes)
            after_time = event_time + timedelta(minutes=time_window_minutes)
            
            # 価格データ取得
            price_data = self.db.query(PriceData).filter(
                PriceData.symbol == symbol,
                PriceData.time.between(before_time, after_time),
                PriceData.timeframe == 'M1'
            ).order_by(PriceData.time).all()
            
            if len(price_data) < 60:  # 最低1時間分のデータが必要
                return None
            
            # データをDataFrameに変換
            df = pd.DataFrame([{
                'time': p.time,
                'close': float(p.close),
                'high': float(p.high),
                'low': float(p.low),
                'open': float(p.open)
            } for p in price_data])
            
            # イベント時刻のインデックス取得
            event_mask = df['time'] <= event_time
            if not event_mask.any():
                return None
            
            event_idx = event_mask.sum() - 1
            
            # 前後のデータ分割
            half_window = time_window_minutes // 2
            before_data = df.iloc[max(0, event_idx - half_window):event_idx]
            after_data = df.iloc[event_idx:min(len(df), event_idx + half_window)]
            
            if len(before_data) < 10 or len(after_data) < 10:
                return None
            
            # ボラティリティ計算
            before_volatility = before_data['close'].std()
            after_volatility = after_data['close'].std()
            
            # 価格変動計算
            price_before = before_data['close'].iloc[-1] if len(before_data) > 0 else 0
            price_after = after_data['close'].iloc[-1] if len(after_data) > 0 else 0
            
            # 最大変動幅
            max_high = after_data['high'].max()
            min_low = after_data['low'].min()
            max_range = max_high - min_low
            
            # パーセンテージ計算
            price_change = abs(price_after - price_before) if price_before > 0 else 0
            price_change_percent = (price_change / price_before * 100) if price_before > 0 else 0
            max_range_percent = (max_range / price_before * 100) if price_before > 0 else 0
            
            # ボラティリティ増加率
            volatility_increase = ((after_volatility / before_volatility - 1) * 100) if before_volatility > 0 else 0
            
            return {
                'before_volatility': round(before_volatility, 6),
                'after_volatility': round(after_volatility, 6),
                'volatility_increase_percent': round(volatility_increase, 2),
                'price_change': round(price_change, 5),
                'price_change_percent': round(price_change_percent, 4),
                'max_range': round(max_range, 5),
                'max_range_percent': round(max_range_percent, 4),
                'data_points_before': len(before_data),
                'data_points_after': len(after_data)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing event volatility: {e}")
            return None
    
    def _summarize_news_impact(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ニュース影響分析のサマリー生成"""
        if not analysis_results:
            return {
                'total_events': 0,
                'avg_volatility_increase': 0,
                'avg_price_change_percent': 0,
                'high_impact_events': 0,
                'max_volatility_increase': 0
            }
        
        volatility_increases = []
        price_changes = []
        high_impact_count = 0
        
        for result in analysis_results:
            vol_analysis = result['volatility_analysis']
            volatility_increases.append(vol_analysis['volatility_increase_percent'])
            price_changes.append(vol_analysis['price_change_percent'])
            
            if result['event']['impact'] == 'high':
                high_impact_count += 1
        
        return {
            'total_events': len(analysis_results),
            'avg_volatility_increase': round(sum(volatility_increases) / len(volatility_increases), 2),
            'avg_price_change_percent': round(sum(price_changes) / len(price_changes), 4),
            'max_volatility_increase': round(max(volatility_increases), 2),
            'max_price_change_percent': round(max(price_changes), 4),
            'high_impact_events': high_impact_count,
            'events_with_significant_impact': len([v for v in volatility_increases if v > 50])
        }
    
    def _generate_news_impact_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """ニュース影響分析の推奨事項生成"""
        recommendations = []
        
        if summary.get('total_events', 0) == 0:
            recommendations.append("十分な経済指標データがありません。データ収集期間を延長してください。")
            return recommendations
        
        avg_volatility = summary.get('avg_volatility_increase', 0)
        
        if avg_volatility > 100:
            recommendations.append("経済指標発表時のボラティリティが非常に高いです。発表前後1時間は取引を避けることを推奨します。")
        elif avg_volatility > 50:
            recommendations.append("経済指標発表時のボラティリティが高めです。ポジションサイズを通常の50%に縮小することを推奨します。")
        elif avg_volatility > 20:
            recommendations.append("経済指標発表時に適度なボラティリティが発生します。ストップロスを通常より厳しく設定してください。")
        else:
            recommendations.append("経済指標の影響は比較的軽微です。通常の取引戦略を継続できます。")
        
        high_impact_ratio = summary.get('high_impact_events', 0) / summary.get('total_events', 1)
        if high_impact_ratio > 0.3:
            recommendations.append("高インパクト指標の割合が高いです。発表スケジュールを事前にチェックし、取引計画を調整してください。")
        
        max_volatility = summary.get('max_volatility_increase', 0)
        if max_volatility > 300:
            recommendations.append("極めて高いボラティリティ増加が観測されています。リスク管理を最優先にしてください。")
        
        return recommendations
    
    async def get_upcoming_events(self, 
                                symbol: str, 
                                hours_ahead: int = 24,
                                impact_levels: List[str] = None) -> List[Dict[str, Any]]:
        """
        今後の重要経済指標取得
        
        Args:
            symbol: 通貨ペア
            hours_ahead: 先読み時間（時間）
            impact_levels: 対象影響レベル
            
        Returns:
            今後の経済指標リスト
        """
        try:
            if impact_levels is None:
                impact_levels = ['high', 'medium']
            
            target_currencies = self._extract_currencies_from_symbol(symbol)
            now = datetime.now()
            end_time = now + timedelta(hours=hours_ahead)
            
            events = self.db.query(EconomicCalendar).filter(
                EconomicCalendar.currency.in_(target_currencies),
                EconomicCalendar.impact.in_(impact_levels),
                EconomicCalendar.event_time.between(now, end_time)
            ).order_by(EconomicCalendar.event_time).all()
            
            upcoming_events = []
            for event in events:
                time_until = event.event_time - now
                hours_until = time_until.total_seconds() / 3600
                
                upcoming_events.append({
                    'event_name': event.event_name,
                    'currency': event.currency,
                    'impact': event.impact,
                    'event_time': event.event_time.isoformat(),
                    'hours_until': round(hours_until, 1),
                    'forecast': event.forecast_value,
                    'previous': event.previous_value
                })
            
            return upcoming_events
            
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []
    
    async def refresh_calendar_data(self, days_ahead: int = 7) -> Dict[str, Any]:
        """
        カレンダーデータの更新
        
        Args:
            days_ahead: 先読み日数
            
        Returns:
            更新結果
        """
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days_ahead)
            
            events = await self.fetch_economic_calendar(start_date, end_date)
            
            return {
                'status': 'success',
                'fetched_events': len(events),
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error refreshing calendar data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'updated_at': datetime.now().isoformat()
            }