"""
監視機能APIエンドポイント
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime, timedelta

from ..websocket.websocket_manager import websocket_manager
from ..monitoring.system_monitor import SystemMonitor
from ..monitoring.trading_monitor import TradingMonitor
from ..monitoring.alert_manager import AlertManager, AlertLevel, AlertType, get_alert_manager
from ..monitoring.log_viewer import LogViewer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

# グローバル監視インスタンス（初期化時に設定）
system_monitor: Optional[SystemMonitor] = None
trading_monitor: Optional[TradingMonitor] = None
alert_manager: Optional[AlertManager] = None
log_viewer: Optional[LogViewer] = None

def initialize_monitoring():
    """監視システム初期化"""
    global system_monitor, trading_monitor, alert_manager, log_viewer
    
    try:
        # アラートマネージャー初期化
        alert_manager = AlertManager(websocket_manager)
        
        # システム監視初期化
        system_monitor = SystemMonitor(websocket_manager)
        
        # 取引監視初期化
        trading_monitor = TradingMonitor(websocket_manager)
        
        # ログビューア初期化
        log_viewer = LogViewer(websocket_manager)
        
        logger.info("Monitoring system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize monitoring system: {e}")
        raise

async def start_monitoring():
    """監視開始"""
    try:
        if system_monitor:
            await system_monitor.start_monitoring()
        
        if trading_monitor:
            await trading_monitor.start_monitoring()
        
        if log_viewer:
            await log_viewer.initialize()
        
        logger.info("Monitoring started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise

def stop_monitoring():
    """監視停止"""
    try:
        if system_monitor:
            system_monitor.stop_monitoring()
        
        if trading_monitor:
            trading_monitor.stop_monitoring()
        
        if log_viewer:
            log_viewer.stop_watching()
        
        logger.info("Monitoring stopped successfully")
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")

# ============= WebSocketエンドポイント =============

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """監視用WebSocketエンドポイント"""
    connection_id = await websocket_manager.connect(websocket, {
        'type': 'monitoring',
        'user_agent': websocket.headers.get('user-agent', 'unknown')
    })
    
    try:
        while True:
            # クライアントからのメッセージ受信
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # メッセージタイプ別処理
            message_type = message.get('type')
            
            if message_type == 'request_logs':
                if log_viewer:
                    await log_viewer.stream_logs(
                        log_type=message.get('log_type'),
                        lines=message.get('lines', 100),
                        level_filter=message.get('level_filter'),
                        search_term=message.get('search_term')
                    )
            
            elif message_type == 'search_logs':
                if log_viewer:
                    search_results = await log_viewer.search_logs(
                        search_term=message.get('search_term', ''),
                        log_type=message.get('log_type'),
                        level_filter=message.get('level_filter'),
                        max_results=message.get('max_results', 1000)
                    )
                    
                    await websocket_manager.send_to_connection(connection_id, {
                        'type': 'search_results',
                        'data': search_results
                    })
            
            elif message_type == 'acknowledge_alert':
                if alert_manager:
                    alert_id = message.get('alert_id')
                    if alert_id:
                        await alert_manager.acknowledge_alert(alert_id, 'websocket_user')
            
            elif message_type == 'dismiss_alert':
                if alert_manager:
                    alert_id = message.get('alert_id')
                    if alert_id:
                        await alert_manager.dismiss_alert(alert_id)
            
            elif message_type == 'clear_alerts':
                if alert_manager:
                    alert_type = message.get('alert_type')
                    if alert_type:
                        await alert_manager.clear_all_alerts(AlertType(alert_type))
                    else:
                        await alert_manager.clear_all_alerts()
            
            elif message_type == 'ping':
                # ピング応答
                await websocket_manager.send_to_connection(connection_id, {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected: {connection_id}")

# ============= REST APIエンドポイント =============

@router.get("/system-status")
async def get_system_status():
    """システム状況取得"""
    try:
        if not system_monitor:
            raise HTTPException(status_code=503, detail="System monitor not initialized")
        
        stats = system_monitor._get_system_stats()
        monitoring_status = system_monitor.get_monitoring_status()
        
        return {
            'current_stats': stats,
            'monitoring_status': monitoring_status,
            'websocket_connections': websocket_manager.get_connection_count()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trading-status")
async def get_trading_status():
    """取引状況取得"""
    try:
        if not trading_monitor:
            raise HTTPException(status_code=503, detail="Trading monitor not initialized")
        
        # 現在の取引統計取得
        today_stats = await trading_monitor._get_today_trading_stats()
        current_pnl = await trading_monitor._get_current_pnl()
        account_info = await trading_monitor._get_account_info()
        positions = await trading_monitor._get_current_positions()
        risk_metrics = await trading_monitor._calculate_risk_metrics()
        
        return {
            'today_stats': today_stats,
            'current_pnl': current_pnl,
            'account_info': account_info,
            'positions': positions,
            'risk_metrics': risk_metrics,
            'monitoring_status': trading_monitor.get_monitoring_status()
        }
        
    except Exception as e:
        logger.error(f"Failed to get trading status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_alerts(
    level: Optional[str] = Query(None, description="アラートレベル"),
    alert_type: Optional[str] = Query(None, description="アラートタイプ"),
    acknowledged: Optional[bool] = Query(None, description="確認済みフィルタ"),
    limit: int = Query(100, description="取得件数")
):
    """アラート取得"""
    try:
        if not alert_manager:
            raise HTTPException(status_code=503, detail="Alert manager not initialized")
        
        # フィルタ条件変換
        level_filter = AlertLevel(level) if level else None
        type_filter = AlertType(alert_type) if alert_type else None
        
        # アクティブアラート取得
        active_alerts = alert_manager.get_active_alerts(
            level=level_filter,
            alert_type=type_filter,
            acknowledged=acknowledged
        )
        
        # 統計情報取得
        stats = alert_manager.get_alert_stats()
        
        return {
            'alerts': active_alerts[:limit],
            'total_count': len(active_alerts),
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(100, description="取得件数"),
    level: Optional[str] = Query(None, description="アラートレベル"),
    alert_type: Optional[str] = Query(None, description="アラートタイプ"),
    start_time: Optional[str] = Query(None, description="開始時間"),
    end_time: Optional[str] = Query(None, description="終了時間")
):
    """アラート履歴取得"""
    try:
        if not alert_manager:
            raise HTTPException(status_code=503, detail="Alert manager not initialized")
        
        # パラメータ変換
        level_filter = AlertLevel(level) if level else None
        type_filter = AlertType(alert_type) if alert_type else None
        start_datetime = datetime.fromisoformat(start_time) if start_time else None
        end_datetime = datetime.fromisoformat(end_time) if end_time else None
        
        # 履歴取得
        history = alert_manager.get_alert_history(
            limit=limit,
            level=level_filter,
            alert_type=type_filter,
            start_time=start_datetime,
            end_time=end_datetime
        )
        
        return {
            'history': history,
            'total_count': len(history)
        }
        
    except Exception as e:
        logger.error(f"Failed to get alert history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """アラート確認"""
    try:
        if not alert_manager:
            raise HTTPException(status_code=503, detail="Alert manager not initialized")
        
        success = await alert_manager.acknowledge_alert(alert_id, 'api_user')
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {'message': 'Alert acknowledged successfully'}
        
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/alerts/{alert_id}")
async def dismiss_alert(alert_id: str):
    """アラート削除"""
    try:
        if not alert_manager:
            raise HTTPException(status_code=503, detail="Alert manager not initialized")
        
        success = await alert_manager.dismiss_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {'message': 'Alert dismissed successfully'}
        
    except Exception as e:
        logger.error(f"Failed to dismiss alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/{log_type}")
async def get_logs(
    log_type: str,
    lines: int = Query(100, description="取得行数"),
    level_filter: Optional[str] = Query(None, description="レベルフィルタ"),
    search_term: Optional[str] = Query(None, description="検索語句")
):
    """ログ取得"""
    try:
        if not log_viewer:
            raise HTTPException(status_code=503, detail="Log viewer not initialized")
        
        # ログ読み取り
        await log_viewer.stream_logs(
            log_type=log_type,
            lines=lines,
            level_filter=level_filter,
            search_term=search_term
        )
        
        # 注意: stream_logs は WebSocket 経由で送信するため、
        # REST API では直接結果を返すために別の方法を使用
        entries = await log_viewer._read_log_file(
            log_viewer.log_files_config.get(log_type, {}).get('path', ''),
            lines,
            level_filter,
            search_term
        )
        
        return {
            'log_type': log_type,
            'entries': [entry.to_dict() for entry in entries],
            'total_lines': len(entries)
        }
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/search")
async def search_logs(
    search_term: str = Query(..., description="検索語句"),
    log_type: Optional[str] = Query(None, description="ログタイプ"),
    level_filter: Optional[str] = Query(None, description="レベルフィルタ"),
    max_results: int = Query(1000, description="最大結果数")
):
    """ログ検索"""
    try:
        if not log_viewer:
            raise HTTPException(status_code=503, detail="Log viewer not initialized")
        
        # ログ検索
        results = await log_viewer.search_logs(
            search_term=search_term,
            log_type=log_type,
            level_filter=level_filter,
            max_results=max_results
        )
        
        return {
            'search_term': search_term,
            'results': results,
            'total_count': len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to search logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_monitoring_stats():
    """監視統計取得"""
    try:
        stats = {
            'timestamp': datetime.now().isoformat(),
            'websocket_connections': websocket_manager.get_connection_count()
        }
        
        if system_monitor:
            stats['system_monitor'] = system_monitor.get_monitoring_status()
        
        if trading_monitor:
            stats['trading_monitor'] = trading_monitor.get_monitoring_status()
        
        if alert_manager:
            stats['alert_manager'] = alert_manager.get_alert_stats()
        
        if log_viewer:
            stats['log_viewer'] = log_viewer.get_log_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get monitoring stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_monitoring_endpoint():
    """監視開始"""
    try:
        await start_monitoring()
        return {'message': 'Monitoring started successfully'}
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_monitoring_endpoint():
    """監視停止"""
    try:
        stop_monitoring()
        return {'message': 'Monitoring stopped successfully'}
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))