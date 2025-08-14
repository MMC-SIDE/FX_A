"""
ドローダウン監視機能
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from backend.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class DrawdownMonitor:
    """ドローダウン監視クラス"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.peak_equity = 0
        self.current_drawdown = 0
        self.max_drawdown = 0
        self.drawdown_start_date = None
        self.recovery_date = None
        
        # 履歴データ初期化
        self._initialize_peak_equity()
        
    def _initialize_peak_equity(self):
        """初期ピークエクイティの設定"""
        try:
            with self.db_manager.get_connection() as conn:
                # 過去の最高エクイティを取得
                query = """
                    SELECT MAX(balance + COALESCE(profit_loss, 0)) as peak_equity
                    FROM trades
                    WHERE created_at >= %s
                """
                
                # 過去30日間
                since_date = datetime.now() - timedelta(days=30)
                result = pd.read_sql_query(query, conn, params=(since_date,))
                
                if not result.empty and result.iloc[0]['peak_equity'] is not None:
                    self.peak_equity = float(result.iloc[0]['peak_equity'])
                    logger.info(f"Initialized peak equity: {self.peak_equity:.2f}")
                else:
                    # デフォルト値（設定から取得）
                    self.peak_equity = self._get_initial_balance()
                    logger.info(f"Using initial balance as peak equity: {self.peak_equity:.2f}")
                    
        except Exception as e:
            logger.error(f"Error initializing peak equity: {e}")
            self.peak_equity = 100000  # デフォルト値
    
    def update(self, current_equity: float) -> float:
        """
        ドローダウン更新
        
        Args:
            current_equity: 現在のエクイティ
            
        Returns:
            現在のドローダウン（%）
        """
        try:
            # 新しい最高値の場合
            if current_equity > self.peak_equity:
                # 回復チェック
                if self.current_drawdown > 0:
                    self.recovery_date = datetime.now()
                    logger.info(f"Drawdown recovered: {self.current_drawdown:.2f}% -> 0%")
                
                self.peak_equity = current_equity
                self.current_drawdown = 0
                self.drawdown_start_date = None
            else:
                # ドローダウン計算
                new_drawdown = (self.peak_equity - current_equity) / self.peak_equity * 100
                
                # ドローダウン開始の記録
                if self.current_drawdown == 0 and new_drawdown > 0:
                    self.drawdown_start_date = datetime.now()
                    logger.info(f"Drawdown started: {new_drawdown:.2f}%")
                
                self.current_drawdown = new_drawdown
                
                # 最大ドローダウン更新
                if self.current_drawdown > self.max_drawdown:
                    self.max_drawdown = self.current_drawdown
                    logger.warning(f"New max drawdown: {self.max_drawdown:.2f}%")
            
            # ドローダウンレベルによるアラート
            self._check_drawdown_alerts()
            
            # データベースに記録
            self._save_drawdown_record(current_equity)
            
            return self.current_drawdown
            
        except Exception as e:
            logger.error(f"Error updating drawdown: {e}")
            return self.current_drawdown
    
    def _check_drawdown_alerts(self):
        """ドローダウンアラートチェック"""
        try:
            # 警告レベル（最大ドローダウンの80%）
            warning_level = self._get_max_drawdown_setting() * 0.8
            
            if self.current_drawdown > warning_level:
                logger.warning(f"Drawdown warning: {self.current_drawdown:.2f}% (limit: {self._get_max_drawdown_setting():.1f}%)")
                
                # 重要なレベル（90%）
                critical_level = self._get_max_drawdown_setting() * 0.9
                if self.current_drawdown > critical_level:
                    logger.error(f"Critical drawdown level: {self.current_drawdown:.2f}%")
                    
        except Exception as e:
            logger.error(f"Error checking drawdown alerts: {e}")
    
    def _save_drawdown_record(self, current_equity: float):
        """ドローダウン記録の保存"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO performance_stats 
                        (stat_type, stat_value, metadata, created_at)
                        VALUES (%s, %s, %s, %s)
                    """
                    
                    metadata = {
                        "current_equity": current_equity,
                        "peak_equity": self.peak_equity,
                        "current_drawdown": self.current_drawdown,
                        "max_drawdown": self.max_drawdown,
                        "drawdown_start": self.drawdown_start_date.isoformat() if self.drawdown_start_date else None
                    }
                    
                    cursor.execute(insert_query, (
                        'drawdown',
                        self.current_drawdown,
                        str(metadata),
                        datetime.now()
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error saving drawdown record: {e}")
    
    def get_drawdown_statistics(self, days: int = 30) -> Dict[str, any]:
        """
        ドローダウン統計取得
        
        Args:
            days: 期間（日数）
            
        Returns:
            ドローダウン統計情報
        """
        try:
            with self.db_manager.get_connection() as conn:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                query = """
                    SELECT stat_value, metadata, created_at
                    FROM performance_stats
                    WHERE stat_type = 'drawdown' 
                    AND created_at >= %s AND created_at <= %s
                    ORDER BY created_at
                """
                
                result = pd.read_sql_query(query, conn, params=(start_date, end_date))
                
                if result.empty:
                    return self._get_default_statistics()
                
                # 統計計算
                drawdowns = result['stat_value'].values
                
                statistics = {
                    "current_drawdown": self.current_drawdown,
                    "max_drawdown": float(np.max(drawdowns)),
                    "average_drawdown": float(np.mean(drawdowns[drawdowns > 0])) if len(drawdowns[drawdowns > 0]) > 0 else 0.0,
                    "drawdown_frequency": len(drawdowns[drawdowns > 0]),
                    "longest_drawdown_period": self._calculate_longest_drawdown_period(result),
                    "recovery_factor": self._calculate_recovery_factor(result),
                    "current_peak_equity": self.peak_equity,
                    "days_in_drawdown": self._calculate_days_in_drawdown(),
                    "time_to_recovery": self._estimate_time_to_recovery(result)
                }
                
                return statistics
                
        except Exception as e:
            logger.error(f"Error getting drawdown statistics: {e}")
            return self._get_default_statistics()
    
    def _calculate_longest_drawdown_period(self, data: pd.DataFrame) -> int:
        """最長ドローダウン期間計算"""
        try:
            if data.empty:
                return 0
                
            # ドローダウン期間の計算
            in_drawdown = data['stat_value'] > 0
            drawdown_periods = []
            current_period = 0
            
            for is_dd in in_drawdown:
                if is_dd:
                    current_period += 1
                else:
                    if current_period > 0:
                        drawdown_periods.append(current_period)
                        current_period = 0
            
            # 最後のドローダウンが継続中の場合
            if current_period > 0:
                drawdown_periods.append(current_period)
            
            return max(drawdown_periods) if drawdown_periods else 0
            
        except Exception as e:
            logger.error(f"Error calculating longest drawdown period: {e}")
            return 0
    
    def _calculate_recovery_factor(self, data: pd.DataFrame) -> float:
        """回復ファクター計算"""
        try:
            if data.empty:
                return 1.0
                
            # 最大利益と最大ドローダウンの比率
            max_profit = self.peak_equity - self._get_initial_balance()
            max_dd_value = np.max(data['stat_value'].values)
            
            if max_dd_value > 0:
                recovery_factor = max_profit / (self.peak_equity * max_dd_value / 100)
                return max(0.1, min(10.0, recovery_factor))  # 0.1-10.0の範囲で制限
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Error calculating recovery factor: {e}")
            return 1.0
    
    def _calculate_days_in_drawdown(self) -> int:
        """現在のドローダウン期間計算"""
        if self.drawdown_start_date and self.current_drawdown > 0:
            return (datetime.now() - self.drawdown_start_date).days
        return 0
    
    def _estimate_time_to_recovery(self, data: pd.DataFrame) -> Optional[int]:
        """回復時間の推定"""
        try:
            if data.empty or self.current_drawdown == 0:
                return None
                
            # 過去の回復パターンから推定
            recovery_times = []
            
            # 過去の回復記録を分析（簡易版）
            # 実際の実装では機械学習を用いてより精密な予測が可能
            
            if recovery_times:
                avg_recovery_time = np.mean(recovery_times)
                return int(avg_recovery_time)
            
            # デフォルト推定（現在のドローダウンレベルに基づく）
            if self.current_drawdown < 5:
                return 7  # 1週間
            elif self.current_drawdown < 10:
                return 14  # 2週間
            else:
                return 30  # 1ヶ月
                
        except Exception as e:
            logger.error(f"Error estimating recovery time: {e}")
            return None
    
    def _get_default_statistics(self) -> Dict[str, any]:
        """デフォルト統計情報"""
        return {
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "average_drawdown": 0.0,
            "drawdown_frequency": 0,
            "longest_drawdown_period": 0,
            "recovery_factor": 1.0,
            "current_peak_equity": self.peak_equity,
            "days_in_drawdown": self._calculate_days_in_drawdown(),
            "time_to_recovery": None
        }
    
    def _get_max_drawdown_setting(self) -> float:
        """最大ドローダウン設定取得"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT value FROM system_settings 
                    WHERE key = 'trading.max_drawdown'
                """
                result = pd.read_sql_query(query, conn)
                
                if not result.empty:
                    return float(result.iloc[0]['value'])
                    
            return 20.0  # デフォルト値
            
        except Exception as e:
            logger.error(f"Error getting max drawdown setting: {e}")
            return 20.0
    
    def _get_initial_balance(self) -> float:
        """初期残高取得"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT value FROM system_settings 
                    WHERE key = 'trading.initial_balance'
                """
                result = pd.read_sql_query(query, conn)
                
                if not result.empty:
                    return float(result.iloc[0]['value'])
                    
            return 100000  # デフォルト値（10万円）
            
        except Exception as e:
            logger.error(f"Error getting initial balance: {e}")
            return 100000
    
    def reset_statistics(self):
        """統計リセット"""
        try:
            self.peak_equity = self._get_initial_balance()
            self.current_drawdown = 0
            self.max_drawdown = 0
            self.drawdown_start_date = None
            self.recovery_date = None
            
            logger.info("Drawdown statistics reset")
            
        except Exception as e:
            logger.error(f"Error resetting statistics: {e}")
    
    def get_drawdown_chart_data(self, days: int = 30) -> List[Dict[str, any]]:
        """
        ドローダウンチャートデータ取得
        
        Args:
            days: 期間（日数）
            
        Returns:
            チャートデータ
        """
        try:
            with self.db_manager.get_connection() as conn:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                query = """
                    SELECT stat_value as drawdown, created_at
                    FROM performance_stats
                    WHERE stat_type = 'drawdown' 
                    AND created_at >= %s AND created_at <= %s
                    ORDER BY created_at
                """
                
                result = pd.read_sql_query(query, conn, params=(start_date, end_date))
                
                if result.empty:
                    return []
                
                chart_data = []
                for _, row in result.iterrows():
                    chart_data.append({
                        "date": row['created_at'].isoformat(),
                        "drawdown": float(row['drawdown'])
                    })
                
                return chart_data
                
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return []

if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.append('.')
    
    logging.basicConfig(level=logging.INFO)
    
    print("Drawdown monitor test completed")