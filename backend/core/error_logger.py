"""
統一ログ管理システム
全システムのログを一元管理し、構造化ログとして記録
"""
import logging
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from contextlib import contextmanager
from enum import Enum


class LogLevel(Enum):
    """ログレベル定義"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DateTimeEncoder(json.JSONEncoder):
    """JSON変換でdatetimeオブジェクトを適切に処理するカスタムエンコーダー"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# ログディレクトリの作成
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class ErrorLogger:
    """エラーログの管理"""
    
    def __init__(self):
        self.setup_loggers()
    
    def setup_loggers(self):
        """ロガーの設定"""
        # エラーログファイル
        error_handler = logging.FileHandler(LOG_DIR / "error.log", encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # バックテストログファイル
        backtest_handler = logging.FileHandler(LOG_DIR / "backtest.log", encoding='utf-8')
        backtest_handler.setLevel(logging.INFO)
        backtest_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # エラーロガー
        self.error_logger = logging.getLogger("error_logger")
        self.error_logger.setLevel(logging.ERROR)
        self.error_logger.addHandler(error_handler)
        
        # バックテストロガー
        self.backtest_logger = logging.getLogger("backtest_logger")
        self.backtest_logger.setLevel(logging.INFO)
        self.backtest_logger.addHandler(backtest_handler)
        
        # コンソール出力（開発時用）
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.error_logger.addHandler(console_handler)
        self.backtest_logger.addHandler(console_handler)
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """エラーをログに記録"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        # JSONログファイルに保存
        self._write_json_log("error", error_data)
        
        # テキストログにも記録
        self.error_logger.error(f"{error_data['error_type']}: {error_data['error_message']}")
        if context:
            self.error_logger.error(f"Context: {json.dumps(context, ensure_ascii=False, indent=2)}")
    
    def log_backtest_start(self, test_id: str, params: Dict[str, Any]):
        """バックテスト開始ログ"""
        # パラメータを JSON シリアライズ可能な形式に変換
        serializable_params = {}
        for key, value in params.items():
            if isinstance(value, datetime):
                serializable_params[key] = value.isoformat()
            else:
                serializable_params[key] = value
                
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "backtest_start",
            "test_id": test_id,
            "parameters": serializable_params
        }
        
        self._write_json_log("backtest", log_data)
        self.backtest_logger.info(f"Backtest started: {test_id}")
    
    def log_backtest_complete(self, test_id: str, result: Dict[str, Any]):
        """バックテスト完了ログ"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "backtest_complete",
            "test_id": test_id,
            "result_summary": {
                "total_trades": result.get("statistics", {}).get("total_trades", 0),
                "net_profit": result.get("statistics", {}).get("net_profit", 0),
                "profit_factor": result.get("statistics", {}).get("profit_factor", 0),
                "win_rate": result.get("statistics", {}).get("win_rate", 0)
            }
        }
        
        self._write_json_log("backtest", log_data)
        self.backtest_logger.info(f"Backtest completed: {test_id}")
    
    def log_backtest_error(self, test_id: str, error: Exception, params: Optional[Dict[str, Any]] = None):
        """バックテストエラーログ"""
        # パラメータを JSON シリアライズ可能な形式に変換
        serializable_params = None
        if params:
            serializable_params = {}
            for key, value in params.items():
                if isinstance(value, datetime):
                    serializable_params[key] = value.isoformat()
                else:
                    serializable_params[key] = value
                    
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "backtest_error",
            "test_id": test_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "parameters": serializable_params
        }
        
        self._write_json_log("backtest_error", error_data)
        self.error_logger.error(f"Backtest error [{test_id}]: {error}")
    
    def _write_json_log(self, log_type: str, data: Dict[str, Any]):
        """JSONログファイルに書き込み"""
        log_file = LOG_DIR / f"{log_type}.json"
        
        # 既存のログを読み込み
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # 新しいログを追加
        logs.append(data)
        
        # 最新1000件を保持
        logs = logs[-1000:]
        
        # ファイルに保存
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
    
    def get_recent_logs(self, log_type: str, limit: int = 50) -> list:
        """最近のログを取得"""
        log_file = LOG_DIR / f"{log_type}.json"
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            return logs[-limit:]
        except:
            return []
    
    @contextmanager
    def log_operation(self, operation_name: str, context: Optional[Dict[str, Any]] = None):
        """操作のログ記録コンテキストマネージャ"""
        try:
            self.backtest_logger.info(f"Starting {operation_name}")
            yield
            self.backtest_logger.info(f"Completed {operation_name}")
        except Exception as e:
            self.log_error(e, {
                "operation": operation_name,
                **(context or {})
            })
            raise


# シングルトンインスタンス
error_logger = ErrorLogger()

# 便利な関数
def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """エラーをログに記録"""
    error_logger.log_error(error, context)

def log_backtest_start(test_id: str, params: Dict[str, Any]):
    """バックテスト開始ログ"""
    error_logger.log_backtest_start(test_id, params)

def log_backtest_complete(test_id: str, result: Dict[str, Any]):
    """バックテスト完了ログ"""
    error_logger.log_backtest_complete(test_id, result)

def log_backtest_error(test_id: str, error: Exception, params: Optional[Dict[str, Any]] = None):
    """バックテストエラーログ"""
    error_logger.log_backtest_error(test_id, error, params)

def get_recent_error_logs(limit: int = 50) -> list:
    """最近のエラーログを取得"""
    return error_logger.get_recent_logs("error", limit)

def get_recent_backtest_logs(limit: int = 50) -> list:
    """最近のバックテストログを取得"""
    return error_logger.get_recent_logs("backtest", limit)