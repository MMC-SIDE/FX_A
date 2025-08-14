"""
WebSocketリアルタイム配信機能
"""
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import json
import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime

from backend.core.mt5_client import MT5Client, TARGET_SYMBOLS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    """WebSocket接続管理"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        self.mt5_client = MT5Client()
        self.is_broadcasting = False
        
    async def connect(self, websocket: WebSocket):
        """WebSocket接続"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # 最初の接続時にブロードキャスト開始
        if len(self.active_connections) == 1 and not self.is_broadcasting:
            asyncio.create_task(self.start_broadcasting())
    
    def disconnect(self, websocket: WebSocket):
        """WebSocket切断"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        
        # 接続がなくなったらブロードキャスト停止
        if len(self.active_connections) == 0:
            self.is_broadcasting = False
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """個別メッセージ送信"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str, symbol: str = None):
        """ブロードキャスト"""
        disconnected = []
        
        for websocket in self.active_connections:
            try:
                # 購読していない場合はスキップ
                if symbol and symbol not in self.subscriptions[websocket]:
                    continue
                    
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(websocket)
        
        # 切断されたWebSocketを削除
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def subscribe(self, websocket: WebSocket, symbol: str):
        """通貨ペア購読"""
        if symbol in TARGET_SYMBOLS:
            self.subscriptions[websocket].add(symbol)
            logger.info(f"Subscribed to {symbol}")
            return True
        return False
    
    def unsubscribe(self, websocket: WebSocket, symbol: str):
        """通貨ペア購読解除"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(symbol)
            logger.info(f"Unsubscribed from {symbol}")
            return True
        return False
    
    async def start_broadcasting(self):
        """リアルタイムデータ配信開始"""
        self.is_broadcasting = True
        logger.info("Starting real-time data broadcasting")
        
        while self.is_broadcasting and len(self.active_connections) > 0:
            try:
                if not self.mt5_client.ensure_connection():
                    logger.error("MT5 connection lost")
                    await asyncio.sleep(5)
                    continue
                
                # 購読されている通貨ペアのティックデータを取得
                subscribed_symbols = set()
                for symbols in self.subscriptions.values():
                    subscribed_symbols.update(symbols)
                
                for symbol in subscribed_symbols:
                    try:
                        tick = self.mt5_client.get_tick(symbol)
                        if tick:
                            # ティックデータをJSON形式で送信
                            tick_message = json.dumps({
                                "type": "tick",
                                "data": {
                                    "symbol": tick["symbol"],
                                    "time": tick["time"].isoformat(),
                                    "bid": tick["bid"],
                                    "ask": tick["ask"],
                                    "last": tick["last"],
                                    "volume": tick["volume"],
                                    "spread": tick["spread"]
                                }
                            })
                            
                            await self.broadcast(tick_message, symbol)
                            
                    except Exception as e:
                        logger.error(f"Error getting tick for {symbol}: {e}")
                
                # 100ms待機（高頻度更新）
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in broadcasting loop: {e}")
                await asyncio.sleep(1)
        
        logger.info("Real-time data broadcasting stopped")

# 接続マネージャーインスタンス
manager = ConnectionManager()

@router.websocket("/market")
async def websocket_market_data(websocket: WebSocket):
    """
    マーケットデータWebSocketエンドポイント
    
    メッセージ形式:
    - 購読: {"action": "subscribe", "symbol": "USDJPY"}
    - 購読解除: {"action": "unsubscribe", "symbol": "USDJPY"}
    - 複数購読: {"action": "subscribe", "symbols": ["USDJPY", "EURJPY"]}
    """
    await manager.connect(websocket)
    
    try:
        # 接続確認メッセージ
        await manager.send_personal_message(
            json.dumps({
                "type": "connection",
                "data": {
                    "status": "connected",
                    "available_symbols": TARGET_SYMBOLS,
                    "message": "WebSocket connected successfully"
                }
            }),
            websocket
        )
        
        while True:
            # クライアントからのメッセージを受信
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    # 単一シンボル購読
                    if "symbol" in message:
                        symbol = message["symbol"].upper()
                        if manager.subscribe(websocket, symbol):
                            response = {
                                "type": "subscription",
                                "data": {
                                    "action": "subscribed",
                                    "symbol": symbol,
                                    "status": "success"
                                }
                            }
                        else:
                            response = {
                                "type": "error",
                                "data": {
                                    "message": f"Invalid symbol: {symbol}",
                                    "available_symbols": TARGET_SYMBOLS
                                }
                            }
                    
                    # 複数シンボル購読
                    elif "symbols" in message:
                        symbols = [s.upper() for s in message["symbols"]]
                        subscribed = []
                        failed = []
                        
                        for symbol in symbols:
                            if manager.subscribe(websocket, symbol):
                                subscribed.append(symbol)
                            else:
                                failed.append(symbol)
                        
                        response = {
                            "type": "subscription",
                            "data": {
                                "action": "subscribed",
                                "subscribed_symbols": subscribed,
                                "failed_symbols": failed,
                                "status": "partial" if failed else "success"
                            }
                        }
                    
                    else:
                        response = {
                            "type": "error",
                            "data": {"message": "Missing symbol or symbols parameter"}
                        }
                
                elif action == "unsubscribe":
                    symbol = message.get("symbol", "").upper()
                    if manager.unsubscribe(websocket, symbol):
                        response = {
                            "type": "subscription",
                            "data": {
                                "action": "unsubscribed",
                                "symbol": symbol,
                                "status": "success"
                            }
                        }
                    else:
                        response = {
                            "type": "error",
                            "data": {"message": f"Failed to unsubscribe from {symbol}"}
                        }
                
                elif action == "get_subscriptions":
                    current_subscriptions = list(manager.subscriptions.get(websocket, set()))
                    response = {
                        "type": "subscriptions",
                        "data": {
                            "subscribed_symbols": current_subscriptions,
                            "available_symbols": TARGET_SYMBOLS
                        }
                    }
                
                else:
                    response = {
                        "type": "error",
                        "data": {"message": f"Unknown action: {action}"}
                    }
                
                await manager.send_personal_message(json.dumps(response), websocket)
                
            except json.JSONDecodeError:
                error_response = {
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }
                await manager.send_personal_message(json.dumps(error_response), websocket)
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                error_response = {
                    "type": "error",
                    "data": {"message": "Internal server error"}
                }
                await manager.send_personal_message(json.dumps(error_response), websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@router.websocket("/trading")
async def websocket_trading_updates(websocket: WebSocket):
    """
    取引更新WebSocketエンドポイント
    """
    await websocket.accept()
    
    try:
        # 接続確認メッセージ
        await websocket.send_text(json.dumps({
            "type": "connection",
            "data": {
                "status": "connected",
                "message": "Trading updates WebSocket connected"
            }
        }))
        
        # 取引更新のブロードキャスト（将来実装）
        while True:
            await asyncio.sleep(1)
            # ここで取引状態の更新をブロードキャスト
            # 現在はプレースホルダー
    
    except WebSocketDisconnect:
        logger.info("Trading WebSocket disconnected")
    except Exception as e:
        logger.error(f"Trading WebSocket error: {e}")