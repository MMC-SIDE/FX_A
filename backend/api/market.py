"""
マーケットデータAPI
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import asyncio

from backend.core.mt5_client import MT5Client, TARGET_SYMBOLS, TIMEFRAME_MAP
from backend.core.database import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/market", tags=["market"])

# グローバルインスタンス
mt5_client = MT5Client()
db_manager = DatabaseManager()

class MarketDataService:
    """マーケットデータサービス"""
    
    def __init__(self):
        self.mt5_client = MT5Client()
        self.db_manager = DatabaseManager()
        self.is_collecting = False
        
    async def start_data_collection(self):
        """データ収集開始"""
        if self.is_collecting:
            logger.warning("Data collection already running")
            return
            
        self.is_collecting = True
        logger.info("Starting market data collection")
        
        # バックグラウンドでデータ収集実行
        asyncio.create_task(self._collect_data_loop())
    
    async def stop_data_collection(self):
        """データ収集停止"""
        self.is_collecting = False
        logger.info("Stopping market data collection")
    
    async def _collect_data_loop(self):
        """データ収集ループ"""
        while self.is_collecting:
            try:
                if not self.mt5_client.ensure_connection():
                    logger.error("Failed to connect to MT5")
                    await asyncio.sleep(30)
                    continue
                
                # 各通貨ペアの最新データを取得
                for symbol in TARGET_SYMBOLS:
                    for timeframe in ["M1", "M5", "M15", "M30", "H1"]:
                        try:
                            # 最新10本のデータを取得
                            df = self.mt5_client.get_rates(symbol, timeframe, 10)
                            if df is not None and not df.empty:
                                # データベースに保存
                                success = self.db_manager.save_price_data(df)
                                if success:
                                    logger.debug(f"Saved {len(df)} records for {symbol} {timeframe}")
                                else:
                                    logger.warning(f"Failed to save data for {symbol} {timeframe}")
                                    
                        except Exception as e:
                            logger.error(f"Error collecting data for {symbol} {timeframe}: {e}")
                
                # 1分待機
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in data collection loop: {e}")
                await asyncio.sleep(30)

# サービスインスタンス
market_service = MarketDataService()

@router.get("/symbols")
async def get_symbols() -> Dict[str, Any]:
    """
    利用可能な通貨ペア一覧取得
    """
    try:
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=500, detail="Failed to connect to MT5")
        
        all_symbols = mt5_client.get_symbols()
        target_symbols = [s for s in all_symbols if s in TARGET_SYMBOLS]
        
        return {
            "symbols": target_symbols,
            "total_count": len(target_symbols),
            "available_timeframes": list(TIMEFRAME_MAP.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols/{symbol}/info")
async def get_symbol_info(symbol: str) -> Dict[str, Any]:
    """
    通貨ペア情報取得
    """
    try:
        if symbol not in TARGET_SYMBOLS:
            raise HTTPException(status_code=404, detail="Symbol not found")
            
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=500, detail="Failed to connect to MT5")
        
        info = mt5_client.get_symbol_info(symbol)
        if info is None:
            raise HTTPException(status_code=404, detail="Symbol info not available")
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting symbol info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols/{symbol}/tick")
async def get_current_tick(symbol: str) -> Dict[str, Any]:
    """
    最新ティック取得
    """
    try:
        if symbol not in TARGET_SYMBOLS:
            raise HTTPException(status_code=404, detail="Symbol not found")
            
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=500, detail="Failed to connect to MT5")
        
        tick = mt5_client.get_tick(symbol)
        if tick is None:
            raise HTTPException(status_code=404, detail="Tick data not available")
        
        return tick
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tick: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols/{symbol}/rates/{timeframe}")
async def get_rates(
    symbol: str,
    timeframe: str,
    count: int = Query(100, ge=1, le=5000),
    source: str = Query("mt5", regex="^(mt5|database)$")
) -> Dict[str, Any]:
    """
    価格データ取得
    
    Args:
        symbol: 通貨ペア
        timeframe: 時間軸
        count: 取得件数
        source: データソース (mt5/database)
    """
    try:
        if symbol not in TARGET_SYMBOLS:
            raise HTTPException(status_code=404, detail="Symbol not found")
        
        if timeframe not in TIMEFRAME_MAP:
            raise HTTPException(status_code=400, detail="Invalid timeframe")
        
        if source == "mt5":
            # MT5から直接取得
            if not mt5_client.ensure_connection():
                raise HTTPException(status_code=500, detail="Failed to connect to MT5")
            
            df = mt5_client.get_rates(symbol, timeframe, count)
            if df is None or df.empty:
                raise HTTPException(status_code=404, detail="No data available")
            
        else:
            # データベースから取得
            df = db_manager.get_latest_price_data(symbol, timeframe, count)
            if df is None or df.empty:
                raise HTTPException(status_code=404, detail="No data in database")
        
        # DataFrameを辞書に変換
        rates = df.to_dict('records')
        
        # 時間をISO文字列に変換
        for rate in rates:
            if 'time' in rate:
                rate['time'] = rate['time'].isoformat()
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(rates),
            "source": source,
            "data": rates
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols/{symbol}/rates/{timeframe}/range")
async def get_rates_range(
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """
    指定期間の価格データ取得
    """
    try:
        if symbol not in TARGET_SYMBOLS:
            raise HTTPException(status_code=404, detail="Symbol not found")
        
        if timeframe not in TIMEFRAME_MAP:
            raise HTTPException(status_code=400, detail="Invalid timeframe")
        
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Invalid date range")
        
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=500, detail="Failed to connect to MT5")
        
        df = mt5_client.get_rates_range(symbol, timeframe, start_date, end_date)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")
        
        # DataFrameを辞書に変換
        rates = df.to_dict('records')
        
        # 時間をISO文字列に変換
        for rate in rates:
            if 'time' in rate:
                rate['time'] = rate['time'].isoformat()
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "count": len(rates),
            "data": rates
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rates range: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/multiple-rates/{timeframe}")
async def get_multiple_rates(
    timeframe: str,
    symbols: str = Query(..., description="Comma-separated symbol list"),
    count: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    複数通貨ペアの価格データ一括取得
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        invalid_symbols = [s for s in symbol_list if s not in TARGET_SYMBOLS]
        
        if invalid_symbols:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid symbols: {invalid_symbols}"
            )
        
        if timeframe not in TIMEFRAME_MAP:
            raise HTTPException(status_code=400, detail="Invalid timeframe")
        
        if not mt5_client.ensure_connection():
            raise HTTPException(status_code=500, detail="Failed to connect to MT5")
        
        results = mt5_client.get_multiple_rates(symbol_list, timeframe, count)
        
        # DataFrameを辞書に変換
        formatted_results = {}
        for symbol, df in results.items():
            if df is not None and not df.empty:
                rates = df.to_dict('records')
                # 時間をISO文字列に変換
                for rate in rates:
                    if 'time' in rate:
                        rate['time'] = rate['time'].isoformat()
                formatted_results[symbol] = rates
        
        return {
            "timeframe": timeframe,
            "requested_symbols": symbol_list,
            "successful_symbols": list(formatted_results.keys()),
            "data": formatted_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting multiple rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data-collection/start")
async def start_data_collection(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    データ収集開始
    """
    try:
        background_tasks.add_task(market_service.start_data_collection)
        return {"message": "Data collection started"}
        
    except Exception as e:
        logger.error(f"Error starting data collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data-collection/stop")
async def stop_data_collection() -> Dict[str, str]:
    """
    データ収集停止
    """
    try:
        await market_service.stop_data_collection()
        return {"message": "Data collection stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping data collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-collection/status")
async def get_data_collection_status() -> Dict[str, Any]:
    """
    データ収集状態取得
    """
    return {
        "is_collecting": market_service.is_collecting,
        "mt5_connected": mt5_client.is_connected
    }