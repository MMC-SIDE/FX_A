"""
バックテスト進捗追跡システム
"""
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading

@dataclass
class BacktestProgress:
    """バックテスト進捗情報"""
    test_id: str
    status: str  # 'running', 'completed', 'error'
    current_step: str
    progress_percent: float
    total_configurations: int
    completed_configurations: int
    current_symbol: str = ""
    current_timeframe: str = ""
    estimated_time_remaining: Optional[int] = None
    start_time: Optional[datetime] = None
    logs: list = None
    
    def __post_init__(self):
        if self.logs is None:
            self.logs = []

class ProgressTracker:
    """進捗追跡管理クラス"""
    
    def __init__(self):
        self._progress: Dict[str, BacktestProgress] = {}
        self._lock = threading.Lock()
    
    def start_backtest(self, test_id: str, total_configurations: int = 1) -> None:
        """バックテスト開始"""
        with self._lock:
            self._progress[test_id] = BacktestProgress(
                test_id=test_id,
                status='running',
                current_step='初期化中...',
                progress_percent=0.0,
                total_configurations=total_configurations,
                completed_configurations=0,
                start_time=datetime.now()
            )
    
    def update_progress(
        self, 
        test_id: str, 
        step: str, 
        progress: float, 
        symbol: str = "",
        timeframe: str = ""
    ) -> None:
        """進捗更新"""
        with self._lock:
            if test_id in self._progress:
                self._progress[test_id].current_step = step
                self._progress[test_id].progress_percent = min(100.0, max(0.0, progress))
                self._progress[test_id].current_symbol = symbol
                self._progress[test_id].current_timeframe = timeframe
                
                # ログ追加
                log_entry = f"{datetime.now().strftime('%H:%M:%S')} - {step}"
                if symbol and timeframe:
                    log_entry += f" ({symbol} {timeframe})"
                self._progress[test_id].logs.append(log_entry)
                
                # ログは最新20件のみ保持
                if len(self._progress[test_id].logs) > 20:
                    self._progress[test_id].logs = self._progress[test_id].logs[-20:]
    
    def complete_configuration(self, test_id: str) -> None:
        """設定完了"""
        with self._lock:
            if test_id in self._progress:
                self._progress[test_id].completed_configurations += 1
                progress = (self._progress[test_id].completed_configurations / 
                           self._progress[test_id].total_configurations) * 100
                self._progress[test_id].progress_percent = progress
    
    def complete_backtest(self, test_id: str, success: bool = True) -> None:
        """バックテスト完了"""
        with self._lock:
            if test_id in self._progress:
                self._progress[test_id].status = 'completed' if success else 'error'
                self._progress[test_id].progress_percent = 100.0
                self._progress[test_id].current_step = '完了' if success else 'エラー'
    
    def get_progress(self, test_id: str) -> Optional[Dict]:
        """進捗取得"""
        with self._lock:
            if test_id in self._progress:
                return asdict(self._progress[test_id])
            return None
    
    def cleanup_old_progress(self, hours: int = 24) -> None:
        """古い進捗データをクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        with self._lock:
            to_remove = []
            for test_id, progress in self._progress.items():
                if progress.start_time and progress.start_time < cutoff_time:
                    to_remove.append(test_id)
            
            for test_id in to_remove:
                del self._progress[test_id]

# グローバル進捗トラッカー
progress_tracker = ProgressTracker()