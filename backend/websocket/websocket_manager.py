"""
WebSocketマネージャー
リアルタイム通信を管理
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Optional, Any
import asyncio
import json
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket接続管理クラス"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, dict] = {}
        self.connection_ids: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, client_data: Optional[dict] = None) -> str:
        """
        WebSocket接続
        
        Args:
            websocket: WebSocketインスタンス
            client_data: クライアント情報
            
        Returns:
            str: 接続ID
        """
        await websocket.accept()
        
        # 接続IDを生成
        connection_id = str(uuid.uuid4())
        
        # 接続を登録
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {
            'id': connection_id,
            'client_data': client_data or {},
            'connected_at': datetime.now(),
            'last_heartbeat': datetime.now()
        }
        self.connection_ids[connection_id] = websocket
        
        logger.info(f"WebSocket connected: {connection_id} - {client_data}")
        
        # 接続時に初期データ送信
        await self.send_initial_data(websocket)
        
        return connection_id
    
    def disconnect(self, websocket: WebSocket):
        """
        WebSocket切断
        
        Args:
            websocket: WebSocketインスタンス
        """
        if websocket in self.active_connections:
            # 接続データ取得
            connection_data = self.connection_data.get(websocket, {})
            connection_id = connection_data.get('id', 'unknown')
            
            # 接続を削除
            self.active_connections.remove(websocket)
            if websocket in self.connection_data:
                del self.connection_data[websocket]
            if connection_id in self.connection_ids:
                del self.connection_ids[connection_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket) -> bool:
        """
        個別メッセージ送信
        
        Args:
            message: 送信メッセージ
            websocket: 送信先WebSocket
            
        Returns:
            bool: 送信成功フラグ
        """
        try:
            # タイムスタンプを追加
            message['timestamp'] = datetime.now().isoformat()
            
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)
            return False
    
    async def send_to_connection(self, connection_id: str, message: dict) -> bool:
        """
        接続IDを指定してメッセージ送信
        
        Args:
            connection_id: 接続ID
            message: 送信メッセージ
            
        Returns:
            bool: 送信成功フラグ
        """
        websocket = self.connection_ids.get(connection_id)
        if websocket:
            return await self.send_personal_message(message, websocket)
        return False
    
    async def broadcast(self, message: dict, exclude_connections: Optional[List[str]] = None) -> int:
        """
        全接続にブロードキャスト
        
        Args:
            message: ブロードキャストメッセージ
            exclude_connections: 除外する接続IDリスト
            
        Returns:
            int: 送信成功数
        """
        if not self.active_connections:
            return 0
        
        exclude_connections = exclude_connections or []
        success_count = 0
        failed_connections = []
        
        # タイムスタンプを追加
        message['timestamp'] = datetime.now().isoformat()
        message_json = json.dumps(message, ensure_ascii=False)
        
        for connection in self.active_connections.copy():
            try:
                # 除外チェック
                connection_data = self.connection_data.get(connection, {})
                connection_id = connection_data.get('id')
                
                if connection_id in exclude_connections:
                    continue
                
                await connection.send_text(message_json)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send broadcast to connection: {e}")
                failed_connections.append(connection)
        
        # 失敗した接続を削除
        for connection in failed_connections:
            self.disconnect(connection)
        
        return success_count
    
    async def broadcast_to_group(self, message: dict, group_filter: dict) -> int:
        """
        条件に一致する接続グループにブロードキャスト
        
        Args:
            message: ブロードキャストメッセージ
            group_filter: グループフィルター条件
            
        Returns:
            int: 送信成功数
        """
        success_count = 0
        failed_connections = []
        
        # タイムスタンプを追加
        message['timestamp'] = datetime.now().isoformat()
        message_json = json.dumps(message, ensure_ascii=False)
        
        for connection in self.active_connections.copy():
            try:
                # フィルター条件チェック
                connection_data = self.connection_data.get(connection, {})
                client_data = connection_data.get('client_data', {})
                
                # フィルター条件に一致するかチェック
                match = True
                for key, value in group_filter.items():
                    if client_data.get(key) != value:
                        match = False
                        break
                
                if match:
                    await connection.send_text(message_json)
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to send group broadcast: {e}")
                failed_connections.append(connection)
        
        # 失敗した接続を削除
        for connection in failed_connections:
            self.disconnect(connection)
        
        return success_count
    
    async def send_initial_data(self, websocket: WebSocket):
        """
        初期データ送信
        
        Args:
            websocket: WebSocketインスタンス
        """
        try:
            # システム状況
            system_status = await self._get_system_status()
            await self.send_personal_message({
                'type': 'system_status',
                'data': system_status
            }, websocket)
            
            # 取引状況
            trading_status = await self._get_trading_status()
            await self.send_personal_message({
                'type': 'trading_status',
                'data': trading_status
            }, websocket)
            
            # 接続確認メッセージ
            await self.send_personal_message({
                'type': 'connection_established',
                'data': {
                    'status': 'connected',
                    'server_time': datetime.now().isoformat()
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"Failed to send initial data: {e}")
    
    async def _get_system_status(self) -> dict:
        """
        システム状況取得
        
        Returns:
            dict: システム状況データ
        """
        try:
            # システム統計を取得（monitoring moduleに依存）
            return {
                'status': 'running',
                'uptime': '0:00:00',  # 実装要
                'version': '1.0.0',
                'connections': len(self.active_connections)
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _get_trading_status(self) -> dict:
        """
        取引状況取得
        
        Returns:
            dict: 取引状況データ
        """
        try:
            # 取引状況を取得（trading moduleに依存）
            return {
                'is_active': False,  # 実装要
                'current_positions': 0,  # 実装要
                'today_trades': 0,  # 実装要
                'today_pnl': 0.0  # 実装要
            }
        except Exception as e:
            logger.error(f"Failed to get trading status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_connection_count(self) -> int:
        """
        アクティブ接続数取得
        
        Returns:
            int: アクティブ接続数
        """
        return len(self.active_connections)
    
    def get_connection_info(self) -> List[dict]:
        """
        接続情報一覧取得
        
        Returns:
            List[dict]: 接続情報リスト
        """
        connection_info = []
        
        for websocket, data in self.connection_data.items():
            connection_info.append({
                'id': data.get('id'),
                'client_data': data.get('client_data', {}),
                'connected_at': data.get('connected_at').isoformat() if data.get('connected_at') else None,
                'last_heartbeat': data.get('last_heartbeat').isoformat() if data.get('last_heartbeat') else None
            })
        
        return connection_info
    
    async def heartbeat_check(self):
        """
        ハートビートチェック（定期実行）
        """
        try:
            # 生存確認メッセージ送信
            heartbeat_message = {
                'type': 'heartbeat',
                'data': {
                    'server_time': datetime.now().isoformat(),
                    'active_connections': len(self.active_connections)
                }
            }
            
            await self.broadcast(heartbeat_message)
            
        except Exception as e:
            logger.error(f"Heartbeat check failed: {e}")

# WebSocketマネージャーのシングルトンインスタンス
websocket_manager = WebSocketManager()