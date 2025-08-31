"""
自動売買API
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from core.database import DatabaseManager
from core.mt5_client import MT5Client
from core.trading_engine import TradingEngine
from core.risk_manager import RiskManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])

# グローバル変数（実際の運用では適切なDIコンテナを使用）
trading_engine = None
db_manager = None
mt5_client = None

# リクエストモデル
class TradingStartRequest(BaseModel):
    symbol: str
    timeframe: str

class TradingStopRequest(BaseModel):
    close_positions: bool = False

class RiskSettingsUpdate(BaseModel):
    max_risk_per_trade: Optional[float] = None
    max_drawdown: Optional[float] = None
    use_nanpin: Optional[bool] = None
    nanpin_max_count: Optional[int] = None
    stop_loss_pips: Optional[int] = None
    take_profit_pips: Optional[int] = None

# 依存性注入
def get_trading_dependencies():
    """トレーディングシステムの依存関係を取得"""
    global trading_engine, db_manager, mt5_client
    
    if not all([trading_engine, db_manager, mt5_client]):
        # 初期化
        db_manager = DatabaseManager()
        mt5_client = MT5Client()
        trading_engine = TradingEngine(db_manager, mt5_client)
    
    return trading_engine, db_manager, mt5_client

@router.post("/start")
async def start_trading(request: TradingStartRequest):
    """
    自動売買開始
    
    Args:
        request: 取引開始リクエスト（通貨ペア・時間軸）
        
    Returns:
        開始結果
    """
    try:
        engine, _, _ = get_trading_dependencies()
        
        # 入力値検証
        valid_symbols = ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY"]
        valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
        
        if request.symbol not in valid_symbols:
            raise HTTPException(status_code=400, detail=f"Invalid symbol. Valid symbols: {valid_symbols}")
        
        if request.timeframe not in valid_timeframes:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe. Valid timeframes: {valid_timeframes}")
        
        # 取引開始
        success = await engine.start_trading(request.symbol, request.timeframe)
        
        if success:
            logger.info(f"Trading started for {request.symbol} {request.timeframe}")
            return {
                "status": "success",
                "message": f"Trading started for {request.symbol} {request.timeframe}",
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "started_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start trading")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting trading: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/stop")
async def stop_trading(request: TradingStopRequest = TradingStopRequest()):
    """
    自動売買停止
    
    Args:
        request: 停止リクエスト
        
    Returns:
        停止結果
    """
    try:
        engine, _, _ = get_trading_dependencies()
        
        # 取引停止
        success = await engine.stop_trading(close_positions=request.close_positions)
        
        if success:
            logger.info("Trading stopped")
            return {
                "status": "success",
                "message": "Trading stopped",
                "positions_closed": request.close_positions,
                "stopped_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to stop trading")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping trading: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/status")
async def get_trading_status():
    """
    取引状態取得
    
    Returns:
        現在の取引状態
    """
    try:
        engine, _, _ = get_trading_dependencies()
        
        status = engine.get_trading_status()
        
        return {
            "status": "success",
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/emergency-stop")
async def emergency_stop(reason: str = "Manual emergency stop"):
    """
    緊急停止
    
    Args:
        reason: 停止理由
        
    Returns:
        緊急停止結果
    """
    try:
        engine, _, _ = get_trading_dependencies()
        
        # 緊急停止トリガー
        engine.risk_manager.trigger_emergency_stop(reason)
        
        # 取引停止（全ポジションクローズ）
        await engine.stop_trading(close_positions=True)
        
        logger.critical(f"Emergency stop executed: {reason}")
        
        return {
            "status": "success",
            "message": "Emergency stop executed",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error executing emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/emergency-stop/reset")
async def reset_emergency_stop():
    """
    緊急停止解除
    
    Returns:
        解除結果
    """
    try:
        engine, _, _ = get_trading_dependencies()
        
        engine.risk_manager.reset_emergency_stop()
        
        logger.info("Emergency stop reset")
        
        return {
            "status": "success",
            "message": "Emergency stop reset",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/positions")
async def get_current_positions():
    """
    現在のポジション取得
    
    Returns:
        現在のポジション一覧
    """
    try:
        _, _, mt5_client = get_trading_dependencies()
        
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=503, detail="MT5 connection failed")
        
        positions = mt5_client.get_positions()
        
        return {
            "status": "success",
            "data": positions,
            "count": len(positions),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/trades")
async def get_trades(limit: int = 20, offset: int = 0):
    """
    取引履歴取得
    
    Args:
        limit: 取得件数（デフォルト20件）
        offset: オフセット
        
    Returns:
        取引履歴一覧
    """
    try:
        # 現在はモックデータを返す（実際の取引履歴機能は後で実装）
        return {
            "status": "success",
            "data": [],  # 空の配列を返す
            "count": 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/orders")
async def get_current_orders():
    """
    待機注文取得
    
    Returns:
        待機注文一覧
    """
    try:
        _, _, mt5_client = get_trading_dependencies()
        
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=503, detail="MT5 connection failed")
        
        orders = mt5_client.get_orders()
        
        return {
            "status": "success",
            "data": orders,
            "count": len(orders),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/risk-status")
async def get_risk_status():
    """
    リスク状態取得
    
    Returns:
        現在のリスク状態
    """
    try:
        engine, _, _ = get_trading_dependencies()
        
        risk_status = engine.risk_manager.get_risk_status()
        
        return {
            "status": "success",
            "data": risk_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting risk status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/risk-settings")
async def update_risk_settings(settings: RiskSettingsUpdate):
    """
    リスク設定更新
    
    Args:
        settings: 更新するリスク設定
        
    Returns:
        更新結果
    """
    try:
        engine, _, _ = get_trading_dependencies()
        
        # 更新対象の設定を辞書形式に変換
        update_dict = {}
        if settings.max_risk_per_trade is not None:
            update_dict['max_risk_per_trade'] = settings.max_risk_per_trade
        if settings.max_drawdown is not None:
            update_dict['max_drawdown'] = settings.max_drawdown
        if settings.use_nanpin is not None:
            update_dict['use_nanpin'] = settings.use_nanpin
        if settings.nanpin_max_count is not None:
            update_dict['nanpin_max_count'] = settings.nanpin_max_count
        if settings.stop_loss_pips is not None:
            update_dict['stop_loss_pips'] = settings.stop_loss_pips
        if settings.take_profit_pips is not None:
            update_dict['take_profit_pips'] = settings.take_profit_pips
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No settings provided for update")
        
        # 設定更新
        success = engine.risk_manager.update_risk_settings(update_dict)
        
        if success:
            logger.info(f"Risk settings updated: {update_dict}")
            return {
                "status": "success",
                "message": "Risk settings updated",
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

@router.get("/account-info")
async def get_account_info():
    """
    アカウント情報取得
    
    Returns:
        MT5アカウント情報
    """
    try:
        _, _, mt5_client = get_trading_dependencies()
        
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=503, detail="MT5 connection failed")
        
        account_info = mt5_client.get_account_info()
        
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

@router.post("/close-position/{position_id}")
async def close_position(position_id: int):
    """
    個別ポジションクローズ
    
    Args:
        position_id: ポジションID
        
    Returns:
        クローズ結果
    """
    try:
        _, _, mt5_client = get_trading_dependencies()
        
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=503, detail="MT5 connection failed")
        
        result = mt5_client.close_position(position_id)
        
        if result and hasattr(result, 'retcode') and result.retcode == 0:
            logger.info(f"Position {position_id} closed manually")
            return {
                "status": "success",
                "message": f"Position {position_id} closed",
                "position_id": position_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            error_msg = result.comment if result and hasattr(result, 'comment') else "Unknown error"
            raise HTTPException(status_code=400, detail=f"Failed to close position: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/close-all-positions")
async def close_all_positions():
    """
    全ポジションクローズ
    
    Returns:
        クローズ結果
    """
    try:
        _, _, mt5_client = get_trading_dependencies()
        
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=503, detail="MT5 connection failed")
        
        closed_count = mt5_client.close_all_positions()
        
        logger.info(f"Closed {closed_count} positions manually")
        
        return {
            "status": "success",
            "message": f"Closed {closed_count} positions",
            "closed_count": closed_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error closing all positions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/trades")
async def get_trades(
    limit: int = 20,
    offset: int = 0,
    symbol: str = None,
    start_date: str = None,
    end_date: str = None
):
    """
    取引履歴取得
    
    Args:
        limit: 取得件数
        offset: 開始位置
        symbol: 通貨ペア（オプション）
        start_date: 開始日（オプション）
        end_date: 終了日（オプション）
    
    Returns:
        取引履歴一覧
    """
    try:
        db_manager = DatabaseManager()
        
        # パラメータに基づいて取引履歴を取得
        if symbol or start_date or end_date:
            # フィルタリング付きクエリ（実装予定）
            trades = []  # プレースホルダー
        else:
            # 基本的なクエリ
            trades = []  # プレースホルダー
        
        return {
            "status": "success",
            "data": trades,
            "count": len(trades),
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/trades/{trade_id}")
async def get_trade_by_id(trade_id: str):
    """
    取引詳細取得
    
    Args:
        trade_id: 取引ID
    
    Returns:
        取引詳細
    """
    try:
        db_manager = DatabaseManager()
        
        # 取引詳細を取得（実装予定）
        trade = None  # プレースホルダー
        
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        return {
            "status": "success",
            "data": trade,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade {trade_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")