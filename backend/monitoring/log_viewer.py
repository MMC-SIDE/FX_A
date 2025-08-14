"""
ログビューア機能
ログファイルのリアルタイム監視と配信
"""
import asyncio
import os
import re
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from pathlib import Path
import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..websocket.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

class LogLevel:
    """ログレベル定数"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogEntry:
    """ログエントリクラス"""
    
    def __init__(self, raw_line: str, log_file: str):
        self.raw_line = raw_line.strip()
        self.log_file = log_file
        self.timestamp = None
        self.level = None
        self.logger_name = None
        self.message = None
        self.parsed = False
        
        self._parse_log_line()
    
    def _parse_log_line(self):
        """ログ行をパース"""
        try:
            # 一般的なログフォーマットパターン
            # 例: 2024-01-01 12:00:00,123 - logger_name - INFO - Message
            pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\.]?\d*)\s*-\s*([^-]+)\s*-\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*-\s*(.*)'
            
            match = re.match(pattern, self.raw_line)
            if match:
                timestamp_str, logger_name, level, message = match.groups()
                
                # タイムスタンプパース
                try:
                    # カンマかピリオドを含む場合の処理
                    if ',' in timestamp_str:
                        timestamp_str = timestamp_str.replace(',', '.')
                    
                    # マイクロ秒部分を処理
                    if '.' in timestamp_str:
                        base_time, microseconds = timestamp_str.split('.')
                        # マイクロ秒は6桁に調整
                        microseconds = microseconds.ljust(6, '0')[:6]
                        timestamp_str = f"{base_time}.{microseconds}"
                        self.timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        self.timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # パースに失敗した場合は現在時刻を使用
                    self.timestamp = datetime.now()
                
                self.level = level.strip()
                self.logger_name = logger_name.strip()
                self.message = message.strip()
                self.parsed = True
            else:
                # パースに失敗した場合はそのまま保存
                self.timestamp = datetime.now()
                self.level = "INFO"
                self.logger_name = "unknown"
                self.message = self.raw_line
                self.parsed = False
                
        except Exception as e:
            logger.error(f"Failed to parse log line: {e}")
            self.timestamp = datetime.now()
            self.level = "ERROR"
            self.logger_name = "parser"
            self.message = self.raw_line
            self.parsed = False
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'logger_name': self.logger_name,
            'message': self.message,
            'log_file': self.log_file,
            'raw_line': self.raw_line,
            'parsed': self.parsed
        }

class LogFileWatcher(FileSystemEventHandler):
    """ログファイル監視クラス"""
    
    def __init__(self, log_viewer: 'LogViewer'):
        self.log_viewer = log_viewer
    
    def on_modified(self, event):
        """ファイル変更イベント"""
        if not event.is_directory:
            file_path = event.src_path
            if file_path in self.log_viewer.watched_files:
                asyncio.create_task(self.log_viewer._handle_file_change(file_path))

class LogViewer:
    """ログビューアクラス"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.watched_files: Dict[str, Dict[str, Any]] = {}
        self.log_directories = [
            'logs',
            'logs/trading',
            'logs/system',
            'logs/error'
        ]
        
        # ログファイル設定
        self.log_files_config = {
            'trading': {
                'path': 'logs/trading.log',
                'description': '取引ログ',
                'auto_watch': True
            },
            'system': {
                'path': 'logs/system.log',
                'description': 'システムログ',
                'auto_watch': True
            },
            'error': {
                'path': 'logs/error.log',
                'description': 'エラーログ',
                'auto_watch': True
            },
            'mt5': {
                'path': 'logs/mt5.log',
                'description': 'MT5接続ログ',
                'auto_watch': True
            },
            'backtest': {
                'path': 'logs/backtest.log',
                'description': 'バックテストログ',
                'auto_watch': False
            }
        }
        
        # ファイル監視
        self.observer = Observer()
        self.file_watcher = LogFileWatcher(self)
        self.watching = False
        
        # ログバッファ
        self.log_buffer: Dict[str, List[LogEntry]] = {}
        self.max_buffer_size = 1000
        
        # フィルタ設定
        self.active_filters: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """ログビューア初期化"""
        try:
            # ログディレクトリ作成
            for log_dir in self.log_directories:
                Path(log_dir).mkdir(parents=True, exist_ok=True)
            
            # 設定されたログファイルを監視対象に追加
            for log_type, config in self.log_files_config.items():
                if config.get('auto_watch', False):
                    await self.add_watched_file(config['path'], log_type)
            
            # ファイル監視開始
            await self.start_watching()
            
            logger.info("Log viewer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize log viewer: {e}")
    
    async def start_watching(self):
        """ファイル監視開始"""
        try:
            if not self.watching:
                # 各ログディレクトリを監視
                for log_dir in self.log_directories:
                    if os.path.exists(log_dir):
                        self.observer.schedule(self.file_watcher, log_dir, recursive=True)
                
                self.observer.start()
                self.watching = True
                logger.info("Log file watching started")
                
        except Exception as e:
            logger.error(f"Failed to start log watching: {e}")
    
    def stop_watching(self):
        """ファイル監視停止"""
        try:
            if self.watching:
                self.observer.stop()
                self.observer.join()
                self.watching = False
                logger.info("Log file watching stopped")
                
        except Exception as e:
            logger.error(f"Failed to stop log watching: {e}")
    
    async def add_watched_file(self, file_path: str, log_type: str = None):
        """監視ファイル追加"""
        try:
            if not os.path.exists(file_path):
                # ファイルが存在しない場合は作成
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                Path(file_path).touch()
            
            # ファイル情報取得
            stat = os.stat(file_path)
            
            self.watched_files[file_path] = {
                'log_type': log_type or os.path.basename(file_path),
                'size': stat.st_size,
                'last_modified': stat.st_mtime,
                'position': stat.st_size,  # 現在の読み取り位置
                'description': self.log_files_config.get(log_type, {}).get('description', file_path)
            }
            
            # 初期ログ読み込み
            await self._read_initial_logs(file_path)
            
            logger.info(f"Added watched file: {file_path} ({log_type})")
            
        except Exception as e:
            logger.error(f"Failed to add watched file {file_path}: {e}")
    
    async def remove_watched_file(self, file_path: str):
        """監視ファイル削除"""
        try:
            if file_path in self.watched_files:
                del self.watched_files[file_path]
                logger.info(f"Removed watched file: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to remove watched file {file_path}: {e}")
    
    async def stream_logs(
        self,
        log_type: str = None,
        lines: int = 100,
        level_filter: str = None,
        search_term: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ):
        """
        ログストリーミング
        
        Args:
            log_type: ログタイプ
            lines: 取得行数
            level_filter: レベルフィルタ
            search_term: 検索語句
            start_time: 開始時間
            end_time: 終了時間
        """
        try:
            if log_type and log_type in self.log_files_config:
                file_path = self.log_files_config[log_type]['path']
                if not os.path.exists(file_path):
                    await self.websocket_manager.broadcast({
                        'type': 'log_error',
                        'data': {
                            'error': f"ログファイルが見つかりません: {file_path}",
                            'log_type': log_type
                        }
                    })
                    return
                
                # ログ読み取り
                log_entries = await self._read_log_file(
                    file_path, lines, level_filter, search_term, start_time, end_time
                )
                
                await self.websocket_manager.broadcast({
                    'type': 'log_data',
                    'data': {
                        'log_type': log_type,
                        'entries': [entry.to_dict() for entry in log_entries],
                        'total_lines': len(log_entries),
                        'file_path': file_path
                    }
                })
            else:
                # 全ログファイルから取得
                all_entries = []
                for file_path in self.watched_files.keys():
                    entries = await self._read_log_file(
                        file_path, lines, level_filter, search_term, start_time, end_time
                    )
                    all_entries.extend(entries)
                
                # タイムスタンプでソート
                all_entries.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)
                
                await self.websocket_manager.broadcast({
                    'type': 'log_data',
                    'data': {
                        'log_type': 'all',
                        'entries': [entry.to_dict() for entry in all_entries[:lines]],
                        'total_lines': len(all_entries),
                        'file_paths': list(self.watched_files.keys())
                    }
                })
                
        except Exception as e:
            logger.error(f"Failed to stream logs: {e}")
            await self.websocket_manager.broadcast({
                'type': 'log_error',
                'data': {'error': str(e)}
            })
    
    async def _read_log_file(
        self,
        file_path: str,
        lines: int = 100,
        level_filter: str = None,
        search_term: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[LogEntry]:
        """
        ログファイル読み取り
        
        Args:
            file_path: ファイルパス
            lines: 取得行数
            level_filter: レベルフィルタ
            search_term: 検索語句
            start_time: 開始時間
            end_time: 終了時間
            
        Returns:
            List[LogEntry]: ログエントリリスト
        """
        try:
            log_entries = []
            
            # バッファから取得できる場合
            if file_path in self.log_buffer:
                cached_entries = self.log_buffer[file_path]
                log_entries = self._filter_log_entries(
                    cached_entries, level_filter, search_term, start_time, end_time
                )
                
                if len(log_entries) >= lines:
                    return log_entries[-lines:]
            
            # ファイルから直接読み取り
            if os.path.exists(file_path):
                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_lines = await f.readlines()
                
                # 最新の行から処理
                recent_lines = file_lines[-lines*2:] if len(file_lines) > lines*2 else file_lines
                
                for line in recent_lines:
                    if line.strip():
                        entry = LogEntry(line, file_path)
                        log_entries.append(entry)
                
                # バッファ更新
                self.log_buffer[file_path] = log_entries[-self.max_buffer_size:]
                
                # フィルタ適用
                filtered_entries = self._filter_log_entries(
                    log_entries, level_filter, search_term, start_time, end_time
                )
                
                return filtered_entries[-lines:]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to read log file {file_path}: {e}")
            return []
    
    def _filter_log_entries(
        self,
        entries: List[LogEntry],
        level_filter: str = None,
        search_term: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[LogEntry]:
        """ログエントリフィルタ"""
        filtered_entries = []
        
        for entry in entries:
            # レベルフィルタ
            if level_filter and entry.level != level_filter:
                continue
            
            # 時間フィルタ
            if start_time and entry.timestamp and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp and entry.timestamp > end_time:
                continue
            
            # 検索語句フィルタ
            if search_term:
                search_text = f"{entry.message} {entry.logger_name}".lower()
                if search_term.lower() not in search_text:
                    continue
            
            filtered_entries.append(entry)
        
        return filtered_entries
    
    async def _handle_file_change(self, file_path: str):
        """ファイル変更処理"""
        try:
            if file_path not in self.watched_files:
                return
            
            file_info = self.watched_files[file_path]
            current_size = os.path.getsize(file_path)
            
            # ファイルサイズが増加した場合のみ処理
            if current_size > file_info['size']:
                # 新しい行を読み取り
                new_lines = await self._read_new_lines(file_path, file_info['position'])
                
                if new_lines:
                    # 新しいログエントリを作成
                    new_entries = []
                    for line in new_lines:
                        if line.strip():
                            entry = LogEntry(line, file_path)
                            new_entries.append(entry)
                    
                    # バッファ更新
                    if file_path not in self.log_buffer:
                        self.log_buffer[file_path] = []
                    
                    self.log_buffer[file_path].extend(new_entries)
                    
                    # バッファサイズ制限
                    if len(self.log_buffer[file_path]) > self.max_buffer_size:
                        self.log_buffer[file_path] = self.log_buffer[file_path][-self.max_buffer_size:]
                    
                    # リアルタイム通知
                    await self.websocket_manager.broadcast({
                        'type': 'log_update',
                        'data': {
                            'log_type': file_info['log_type'],
                            'new_entries': [entry.to_dict() for entry in new_entries],
                            'file_path': file_path
                        }
                    })
                
                # ファイル情報更新
                file_info['size'] = current_size
                file_info['position'] = current_size
                file_info['last_modified'] = os.path.getmtime(file_path)
                
        except Exception as e:
            logger.error(f"Failed to handle file change {file_path}: {e}")
    
    async def _read_new_lines(self, file_path: str, start_position: int) -> List[str]:
        """新しい行の読み取り"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                await f.seek(start_position)
                new_content = await f.read()
                return new_content.splitlines()
                
        except Exception as e:
            logger.error(f"Failed to read new lines from {file_path}: {e}")
            return []
    
    async def _read_initial_logs(self, file_path: str, lines: int = 100):
        """初期ログ読み込み"""
        try:
            initial_entries = await self._read_log_file(file_path, lines)
            self.log_buffer[file_path] = initial_entries
            logger.info(f"Loaded {len(initial_entries)} initial log entries from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to read initial logs from {file_path}: {e}")
    
    def get_watched_files(self) -> Dict[str, Dict[str, Any]]:
        """監視ファイル一覧取得"""
        return self.watched_files.copy()
    
    def get_log_stats(self) -> Dict[str, Any]:
        """ログ統計取得"""
        total_entries = sum(len(entries) for entries in self.log_buffer.values())
        
        return {
            'watched_files_count': len(self.watched_files),
            'total_buffered_entries': total_entries,
            'watching_active': self.watching,
            'buffer_size_limit': self.max_buffer_size,
            'log_files_config': self.log_files_config
        }
    
    async def search_logs(
        self,
        search_term: str,
        log_type: str = None,
        level_filter: str = None,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        ログ検索
        
        Args:
            search_term: 検索語句
            log_type: ログタイプ
            level_filter: レベルフィルタ
            max_results: 最大結果数
            
        Returns:
            List[Dict[str, Any]]: 検索結果
        """
        try:
            search_results = []
            
            # 検索対象ファイル決定
            if log_type and log_type in self.log_files_config:
                file_path = self.log_files_config[log_type]['path']
                target_files = [file_path] if file_path in self.watched_files else []
            else:
                target_files = list(self.watched_files.keys())
            
            # 各ファイルで検索
            for file_path in target_files:
                entries = await self._read_log_file(
                    file_path, max_results, level_filter, search_term
                )
                search_results.extend([entry.to_dict() for entry in entries])
            
            # タイムスタンプでソート
            search_results.sort(key=lambda x: x['timestamp'] or '', reverse=True)
            
            return search_results[:max_results]
            
        except Exception as e:
            logger.error(f"Failed to search logs: {e}")
            return []