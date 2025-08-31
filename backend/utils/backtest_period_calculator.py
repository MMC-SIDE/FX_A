"""
バックテスト期間自動計算ユーティリティ
"""
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class BacktestPeriodCalculator:
    """バックテスト期間の自動計算クラス"""
    
    # 時間軸別の推奨期間（月数）とデータ制限
    TIMEFRAME_RECOMMENDATIONS = {
        'M1': {
            'recommended_months': 1,      # 1ヶ月
            'max_data_points': 1000,
            'min_months': 0.5,
            'max_months': 2,
            'reason': '短期トレード用'
        },
        'M5': {
            'recommended_months': 2,      # 2ヶ月
            'max_data_points': 1000,
            'min_months': 1,
            'max_months': 3,
            'reason': '短期トレード用'
        },
        'M15': {
            'recommended_months': 3,      # 3ヶ月
            'max_data_points': 1000,
            'min_months': 2,
            'max_months': 6,
            'reason': 'デイトレード用'
        },
        'M30': {
            'recommended_months': 4,      # 4ヶ月
            'max_data_points': 1000,
            'min_months': 3,
            'max_months': 8,
            'reason': 'デイトレード用'
        },
        'H1': {
            'recommended_months': 6,      # 6ヶ月
            'max_data_points': 5000,
            'min_months': 3,
            'max_months': 12,
            'reason': 'スイング・デイトレード用'
        },
        'H4': {
            'recommended_months': 12,     # 12ヶ月
            'max_data_points': 2000,
            'min_months': 6,
            'max_months': 24,
            'reason': 'スイング・ポジション用'
        },
        'D1': {
            'recommended_months': 24,     # 24ヶ月
            'max_data_points': 1000,
            'min_months': 12,
            'max_months': 60,
            'reason': '長期ポジション用'
        }
    }
    
    @classmethod
    def calculate_optimal_period(cls, timeframes: List[str]) -> Dict[str, any]:
        """
        複数時間軸に基づく最適期間の計算
        
        Args:
            timeframes: 時間軸のリスト
            
        Returns:
            最適化された期間情報
        """
        if not timeframes:
            # デフォルト設定
            return {
                'recommended_months': 12,
                'min_months': 6,
                'max_months': 24,
                'timeframe_details': {},
                'optimization_strategy': 'default'
            }
        
        # 各時間軸の推奨期間を取得
        timeframe_details = {}
        all_recommendations = []
        
        for tf in timeframes:
            if tf in cls.TIMEFRAME_RECOMMENDATIONS:
                details = cls.TIMEFRAME_RECOMMENDATIONS[tf].copy()
                timeframe_details[tf] = details
                all_recommendations.append(details['recommended_months'])
            else:
                # 未知の時間軸はH1として扱う
                logger.warning(f"Unknown timeframe: {tf}, treating as H1")
                details = cls.TIMEFRAME_RECOMMENDATIONS['H1'].copy()
                details['reason'] = f'未知時間軸（H1として処理）'
                timeframe_details[tf] = details
                all_recommendations.append(details['recommended_months'])
        
        # 最適化戦略の決定
        strategy, recommended_months = cls._determine_strategy(timeframes, all_recommendations)
        
        # 最小・最大期間の算出
        min_months = min([details['min_months'] for details in timeframe_details.values()])
        max_months = max([details['max_months'] for details in timeframe_details.values()])
        
        return {
            'recommended_months': recommended_months,
            'min_months': min_months,
            'max_months': max_months,
            'timeframe_details': timeframe_details,
            'optimization_strategy': strategy,
            'timeframes_count': len(timeframes)
        }
    
    @classmethod
    def _determine_strategy(cls, timeframes: List[str], recommendations: List[int]) -> Tuple[str, int]:
        """
        最適化戦略の決定
        
        Args:
            timeframes: 時間軸リスト
            recommendations: 各時間軸の推奨期間
            
        Returns:
            (戦略名, 推奨期間)
        """
        if len(timeframes) == 1:
            # 単一時間軸の場合
            return 'single_timeframe', recommendations[0]
        
        # 短期時間軸の存在チェック
        short_term_count = sum(1 for tf in timeframes if tf in ['M1', 'M5', 'M15', 'M30'])
        medium_term_count = sum(1 for tf in timeframes if tf in ['H1', 'H4'])
        long_term_count = sum(1 for tf in timeframes if tf in ['D1'])
        
        if short_term_count > 0 and medium_term_count == 0 and long_term_count == 0:
            # 短期のみ
            return 'short_term_focus', max(recommendations)
        elif short_term_count == 0 and medium_term_count > 0 and long_term_count == 0:
            # 中期のみ
            return 'medium_term_focus', max(recommendations)
        elif short_term_count == 0 and medium_term_count == 0 and long_term_count > 0:
            # 長期のみ
            return 'long_term_focus', max(recommendations)
        elif short_term_count > 0 and (medium_term_count > 0 or long_term_count > 0):
            # 短期と中長期の混合 - バランスを取る
            return 'mixed_focus', int(sum(recommendations) / len(recommendations))
        else:
            # 中長期の混合
            return 'balanced_approach', max(recommendations)
    
    @classmethod
    def get_period_explanation(cls, period_info: Dict[str, any]) -> str:
        """
        期間選択の説明文を生成
        
        Args:
            period_info: calculate_optimal_period()の戻り値
            
        Returns:
            説明文
        """
        strategy = period_info['optimization_strategy']
        recommended = period_info['recommended_months']
        timeframes = list(period_info['timeframe_details'].keys())
        
        explanations = {
            'single_timeframe': f"単一時間軸({timeframes[0]})に最適化された期間",
            'short_term_focus': "短期時間軸(M1-M30)に最適化された期間", 
            'medium_term_focus': "中期時間軸(H1-H4)に最適化された期間",
            'long_term_focus': "長期時間軸(D1)に最適化された期間",
            'mixed_focus': "短期・中長期時間軸のバランスを考慮した期間",
            'balanced_approach': "全時間軸のバランスを考慮した期間",
            'default': "デフォルト設定期間"
        }
        
        base_explanation = explanations.get(strategy, "最適化された期間")
        
        # 時間軸詳細の追加
        tf_details = []
        for tf, details in period_info['timeframe_details'].items():
            tf_details.append(f"{tf}: {details['reason']}")
        
        if tf_details:
            detail_str = " | ".join(tf_details)
            return f"{base_explanation}（{recommended}ヶ月推奨） - {detail_str}"
        else:
            return f"{base_explanation}（{recommended}ヶ月推奨）"
    
    @classmethod
    def validate_period(cls, timeframes: List[str], requested_months: int) -> Dict[str, any]:
        """
        リクエストされた期間の妥当性検証
        
        Args:
            timeframes: 時間軸リスト
            requested_months: リクエストされた期間（月数）
            
        Returns:
            検証結果
        """
        period_info = cls.calculate_optimal_period(timeframes)
        
        warnings = []
        recommendations = []
        
        if requested_months < period_info['min_months']:
            warnings.append(f"期間が短すぎます（最小推奨: {period_info['min_months']}ヶ月）")
            recommendations.append(f"最低{period_info['min_months']}ヶ月に設定することを推奨")
        
        if requested_months > period_info['max_months']:
            warnings.append(f"期間が長すぎます（最大推奨: {period_info['max_months']}ヶ月）")
            recommendations.append(f"最大{period_info['max_months']}ヶ月に設定することを推奨")
        
        # 各時間軸での実効期間の計算
        effective_periods = {}
        for tf in timeframes:
            if tf in cls.TIMEFRAME_RECOMMENDATIONS:
                tf_info = cls.TIMEFRAME_RECOMMENDATIONS[tf]
                max_points = tf_info['max_data_points']
                
                # 時間軸に応じた実効期間の計算（概算）
                if tf == 'M1':
                    effective_days = max_points * 1 / (60 * 24)  # 1分単位
                elif tf == 'M5':
                    effective_days = max_points * 5 / (60 * 24)  # 5分単位
                elif tf == 'M15':
                    effective_days = max_points * 15 / (60 * 24)  # 15分単位
                elif tf == 'M30':
                    effective_days = max_points * 30 / (60 * 24)  # 30分単位
                elif tf == 'H1':
                    effective_days = max_points / 24  # 1時間単位
                elif tf == 'H4':
                    effective_days = max_points * 4 / 24  # 4時間単位
                elif tf == 'D1':
                    effective_days = max_points  # 1日単位
                else:
                    effective_days = max_points / 24  # デフォルト
                
                effective_months = effective_days / 30
                effective_periods[tf] = {
                    'effective_months': round(effective_months, 1),
                    'max_data_points': max_points,
                    'limited': effective_months < requested_months
                }
                
                if effective_months < requested_months:
                    warnings.append(f"{tf}: データ制限により実際は約{effective_months:.1f}ヶ月分のみ")
        
        return {
            'is_valid': len(warnings) == 0,
            'warnings': warnings,
            'recommendations': recommendations,
            'effective_periods': effective_periods,
            'optimal_period_info': period_info
        }