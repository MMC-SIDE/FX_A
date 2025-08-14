from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from contextlib import asynccontextmanager

from backend.api.market import router as market_router
from backend.api.websocket import router as websocket_router
from backend.api.ml import router as ml_router
from backend.api.trading import router as trading_router
from backend.api.risk import router as risk_router
from backend.api.backtest import router as backtest_router
from backend.api.analysis import router as analysis_router
from backend.api.monitoring import router as monitoring_router
from backend.core.mt5_client import MT5Client
from backend.core.database import DatabaseManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# アプリケーション初期化時の処理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時の処理
    logger.info("Starting FX Trading System API")
    
    # ログディレクトリ作成
    os.makedirs("logs", exist_ok=True)
    
    # データベース接続テスト
    db_manager = DatabaseManager()
    if not db_manager.test_connection():
        logger.error("Database connection failed")
    else:
        logger.info("Database connection successful")
    
    # MT5接続テスト（設定ファイルがある場合のみ）
    if os.path.exists("config/mt5_config.json"):
        mt5_client = MT5Client()
        test_result = mt5_client.test_connection()
        if test_result["success"]:
            logger.info("MT5 connection test successful")
        else:
            logger.warning(f"MT5 connection test failed: {test_result['message']}")
    else:
        logger.warning("MT5 config file not found. Please create config/mt5_config.json")
    
    yield
    
    # 終了時の処理
    logger.info("Shutting down FX Trading System API")

app = FastAPI(
    title="FX Trading System API",
    description="Automated FX Trading System with ML",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター追加
app.include_router(market_router)
app.include_router(websocket_router)
app.include_router(ml_router)
app.include_router(trading_router)
app.include_router(risk_router)
app.include_router(backtest_router)
app.include_router(analysis_router)
app.include_router(monitoring_router)

@app.get("/")
async def root():
    return {
        "message": "FX Trading System API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    try:
        # データベース接続確認
        db_manager = DatabaseManager()
        db_healthy = db_manager.test_connection()
        
        # MT5接続確認（設定ファイルがある場合のみ）
        mt5_healthy = False
        mt5_message = "Config not found"
        
        if os.path.exists("config/mt5_config.json"):
            mt5_client = MT5Client()
            test_result = mt5_client.test_connection()
            mt5_healthy = test_result["success"]
            mt5_message = test_result["message"]
        
        overall_status = "healthy" if db_healthy else "unhealthy"
        
        return {
            "status": overall_status,
            "database": {
                "status": "healthy" if db_healthy else "unhealthy"
            },
            "mt5": {
                "status": "healthy" if mt5_healthy else "unhealthy",
                "message": mt5_message
            }
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/status")
async def get_system_status():
    """システム状態取得"""
    try:
        # 各種状態を取得
        return {
            "api_status": "running",
            "timestamp": "2025-01-14T12:00:00Z",  # 実際の時刻に変更
            "uptime": "running",
            "services": {
                "market_data": "active",
                "websocket": "active",
                "database": "connected"
            }
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)