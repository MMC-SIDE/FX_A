"""
リスク管理API
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from backend.core.database import DatabaseManager
from backend.core.mt5_client import MT5Client
from backend.core.risk_manager import RiskManager
from backend.core.drawdown_monitor import DrawdownMonitor
from backend.models.risk_models import (
    RiskSettingsModel, RiskStatusResponse, DrawdownStatistics,
    AccountInfoModel, RiskAlertModel, EmergencyStopRequest,
    RiskLimitCheckResult, PositionSizingRequest, PositionSizingResponse,
    TradeRiskAnalysis, RiskReportRequest, RiskReportResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

# グローバル変数（実際の運用では適切なDIコンテナを使用）
risk_manager = None
drawdown_monitor = None
db_manager = None
mt5_client = None

def get_risk_dependencies():
    """リスク管理システムの依存関係を取得"""
    global risk_manager, drawdown_monitor, db_manager, mt5_client
    
    if not all([risk_manager, drawdown_monitor, db_manager, mt5_client]):
        # 初期化
        db_manager = DatabaseManager()
        mt5_client = MT5Client()
        risk_manager = RiskManager(db_manager, mt5_client)
        drawdown_monitor = DrawdownMonitor(db_manager)
    
    return risk_manager, drawdown_monitor, db_manager, mt5_client

@router.get("/settings", response_model=Dict[str, Any])
async def get_risk_settings():
    """
    リスク設定取得
    
    Returns:
        現在のリスク設定
    """
    try:
        manager, _, _, _ = get_risk_dependencies()
        
        return {
            "status": "success",
            "data": manager.settings,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting risk settings: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/settings")
async def update_risk_settings(settings: RiskSettingsModel):
    """
    リスク設定更新
    
    Args:
        settings: 更新するリスク設定
        
    Returns:
        更新結果
    """
    try:
        manager, _, _, _ = get_risk_dependencies()
        
        # 更新対象の設定を辞書形式に変換（None以外の値のみ）
        update_dict = {}
        for field, value in settings.dict().items():
            if value is not None:
                update_dict[field] = value
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No settings provided for update")
        
        # 設定更新
        success = manager.update_risk_settings(update_dict)
        
        if success:
            logger.info(f"Risk settings updated: {update_dict}")
            return {
                "status": "success",
                "message": "Risk settings updated successfully",
                "updated_settings": update_dict,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update risk settings")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating risk settings: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/status", response_model=Dict[str, Any])
async def get_risk_status():
    """
    リスク状況取得
    
    Returns:
        現在のリスク状況
    """
    try:
        manager, monitor, _, client = get_risk_dependencies()
        
        # アカウント情報更新
        if client.ensure_connection():
            account_info = client.get_account_info()
            if account_info:
                # ドローダウンモニター更新
                monitor.update(account_info['equity'])
        
        # リスク状態取得
        risk_status = manager.get_risk_status()
        
        return {
            "status": "success",
            "data": risk_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting risk status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/drawdown/statistics", response_model=Dict[str, Any])
async def get_drawdown_statistics(days: int = 30):
    """
    ドローダウン統計取得
    
    Args:
        days: 期間（日数）
        
    Returns:
        ドローダウン統計情報
    """
    try:
        _, monitor, _, _ = get_risk_dependencies()
        
        statistics = monitor.get_drawdown_statistics(days)
        
        return {
            "status": "success",
            "data": statistics,
            "period_days": days,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting drawdown statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/drawdown/chart")
async def get_drawdown_chart(days: int = 30):
    """
    ドローダウンチャートデータ取得
    
    Args:
        days: 期間（日数）
        
    Returns:
        チャートデータ
    """
    try:
        _, monitor, _, _ = get_risk_dependencies()
        
        chart_data = monitor.get_drawdown_chart_data(days)
        
        return {
            "status": "success",
            "data": chart_data,
            "period_days": days,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting drawdown chart data: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/emergency-stop")
async def trigger_emergency_stop(request: EmergencyStopRequest = EmergencyStopRequest()):
    """
    緊急停止トリガー
    
    Args:
        request: 緊急停止リクエスト
        
    Returns:
        緊急停止結果
    """
    try:
        manager, _, _, client = get_risk_dependencies()
        
        # 緊急停止トリガー
        manager.trigger_emergency_stop(request.reason)
        
        # 全ポジションクローズ（オプション）
        closed_positions = 0
        if request.close_all_positions:
            if client.ensure_connection():
                closed_positions = client.close_all_positions()
        
        logger.critical(f"Emergency stop triggered: {request.reason}")
        
        return {
            "status": "success",
            "message": "Emergency stop triggered",
            "reason": request.reason,
            "positions_closed": closed_positions,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/emergency-stop/reset")
async def reset_emergency_stop():
    """
    緊急停止解除
    
    Returns:
        解除結果
    """
    try:
        manager, _, _, _ = get_risk_dependencies()
        
        manager.reset_emergency_stop()
        
        logger.info("Emergency stop reset")
        
        return {
            "status": "success",
            "message": "Emergency stop reset",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/check-limits", response_model=Dict[str, Any])
async def check_risk_limits():
    """
    リスク制限チェック
    
    Returns:
        チェック結果
    """
    try:
        manager, _, _, _ = get_risk_dependencies()
        
        can_trade = manager.check_risk_limits()
        
        # 詳細なチェック結果を作成
        result = {
            "can_trade": can_trade,
            "failed_checks": [],
            "warnings": [],
            "risk_score": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 個別チェックの実行と結果記録
        if not manager._check_max_drawdown():
            result["failed_checks"].append("max_drawdown")
            result["risk_score"] += 30
            
        if not manager._check_max_positions():
            result["failed_checks"].append("max_positions")
            result["risk_score"] += 20
            
        if not manager._check_daily_trade_limit():
            result["failed_checks"].append("daily_trade_limit")
            result["risk_score"] += 15
            
        if not manager._check_consecutive_losses():
            result["failed_checks"].append("consecutive_losses")
            result["risk_score"] += 25
            
        if not manager._check_daily_loss_limit():
            result["failed_checks"].append("daily_loss_limit")
            result["risk_score"] += 35
        
        # リスクスコアを0-100の範囲に正規化
        result["risk_score"] = min(100, result["risk_score"])
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error checking risk limits: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/calculate-position-size", response_model=Dict[str, Any])
async def calculate_position_size(request: PositionSizingRequest):
    """
    ポジションサイズ計算
    
    Args:
        request: ポジションサイジングリクエスト
        
    Returns:
        計算結果
    """
    try:
        manager, _, _, client = get_risk_dependencies()
        
        # 現在価格取得（指定されていない場合）
        if request.entry_price is None:
            if client.ensure_connection():
                tick = client.get_tick(request.symbol)
                if tick:
                    request.entry_price = tick['ask'] if request.order_type == 'BUY' else tick['bid']
                else:
                    raise HTTPException(status_code=400, detail="Failed to get current price")
            else:
                raise HTTPException(status_code=503, detail="MT5 connection failed")
        
        # ロットサイズ計算
        lot_size = manager.calculate_lot_size(request.symbol, request.order_type)
        
        # SL/TP計算
        sl, tp = manager.calculate_sl_tp(request.symbol, request.order_type, request.entry_price)
        
        # リスク金額計算
        account_info = client.get_account_info()
        risk_amount = account_info['balance'] * manager.settings['max_risk_per_trade'] / 100
        risk_percentage = manager.settings['max_risk_per_trade']
        
        response = {
            "lot_size": lot_size,
            "risk_amount": risk_amount,
            "stop_loss": sl,
            "take_profit": tp,
            "risk_percentage": risk_percentage,
            "entry_price": request.entry_price,
            "calculated_at": datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "data": response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/account-info", response_model=Dict[str, Any])
async def get_account_info():
    """
    アカウント情報取得
    
    Returns:
        MT5アカウント情報
    """
    try:
        _, _, _, client = get_risk_dependencies()
        
        if not client.ensure_connection():
            raise HTTPException(status_code=503, detail="MT5 connection failed")
        
        account_info = client.get_account_info()
        
        if account_info is None:
            raise HTTPException(status_code=503, detail="Failed to get account info")
        
        return {
            "status": "success",
            "data": account_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/alerts")
async def get_risk_alerts(days: int = 7):
    """
    リスクアラート取得
    
    Args:
        days: 期間（日数）
        
    Returns:
        リスクアラート一覧
    """
    try:
        _, _, db_manager, _ = get_risk_dependencies()
        
        with db_manager.get_connection() as conn:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            query = """
                SELECT event_type, trigger_value, threshold_value, 
                       description, severity, created_at
                FROM risk_management_logs
                WHERE created_at >= %s AND created_at <= %s
                ORDER BY created_at DESC
                LIMIT 100
            """
            
            import pandas as pd
            result = pd.read_sql_query(query, conn, params=(start_date, end_date))
            
            alerts = []
            for _, row in result.iterrows():
                alert = {
                    "alert_type": row['event_type'],
                    "level": row['severity'].lower(),
                    "message": row['description'],
                    "current_value": float(row['trigger_value']),
                    "threshold_value": float(row['threshold_value']),
                    "timestamp": row['created_at'].isoformat(),
                    "action_required": row['severity'] in ['CRITICAL', 'ERROR']
                }
                alerts.append(alert)
        
        return {
            "status": "success",
            "data": alerts,
            "period_days": days,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting risk alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/reset-statistics")
async def reset_risk_statistics():
    """
    リスク統計リセット
    
    Returns:
        リセット結果
    """
    try:
        _, monitor, _, _ = get_risk_dependencies()
        
        monitor.reset_statistics()
        
        logger.info("Risk statistics reset")
        
        return {
            "status": "success",
            "message": "Risk statistics reset successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting risk statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health")
async def risk_health_check():
    """
    リスク管理システムヘルスチェック
    
    Returns:
        ヘルス状態
    """
    try:
        manager, monitor, db_manager, client = get_risk_dependencies()
        
        # 各コンポーネントの状態チェック
        health_status = {
            "risk_manager": manager is not None,
            "drawdown_monitor": monitor is not None,
            "database": db_manager.test_connection() if db_manager else False,
            "mt5_connection": client.ensure_connection() if client else False,
            "emergency_stop": manager.emergency_stop_triggered if manager else True
        }
        
        overall_healthy = all([
            health_status["risk_manager"],
            health_status["drawdown_monitor"],
            health_status["database"]
        ])
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "components": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Risk health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }