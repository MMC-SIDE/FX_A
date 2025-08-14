"""
機械学習API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, UploadFile, File
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import asyncio
import json

from backend.core.database import DatabaseManager
from backend.core.mt5_client import MT5Client
from backend.ml.features import FeatureEngineering
from backend.ml.models.lightgbm_model import LightGBMPredictor
from backend.ml.model_manager import ModelManager
from backend.ml.evaluator import ModelEvaluator
from backend.ml.predictor import RealTimePredictionService, PredictionAPI

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ml", tags=["machine_learning"])

# グローバルインスタンス
db_manager = DatabaseManager()
mt5_client = MT5Client()
model_manager = ModelManager(db_manager)
evaluator = ModelEvaluator()
prediction_service = RealTimePredictionService(db_manager, mt5_client)
prediction_api = PredictionAPI(prediction_service)

@router.get("/models")
async def list_models(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100)
) -> Dict[str, Any]:
    """モデル一覧取得"""
    try:
        models_df = model_manager.list_models(symbol, timeframe, is_active, limit)
        
        return {
            "status": "success",
            "count": len(models_df),
            "models": models_df.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models/{model_id}")
async def get_model_info(model_id: int) -> Dict[str, Any]:
    """モデル情報取得"""
    try:
        model_info = model_manager.get_model_info(model_id)
        
        if model_info is None:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return {
            "status": "success",
            "model": model_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/models/{model_id}/activate")
async def activate_model(model_id: int) -> Dict[str, str]:
    """モデルアクティブ化"""
    try:
        success = model_manager.activate_model(model_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to activate model")
        
        return {"status": "success", "message": f"Model {model_id} activated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/models/{model_id}/deactivate")
async def deactivate_model(model_id: int) -> Dict[str, str]:
    """モデル非アクティブ化"""
    try:
        success = model_manager.deactivate_model(model_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to deactivate model")
        
        return {"status": "success", "message": f"Model {model_id} deactivated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/models/{model_id}")
async def delete_model(model_id: int) -> Dict[str, str]:
    """モデル削除"""
    try:
        success = model_manager.delete_model(model_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete model")
        
        return {"status": "success", "message": f"Model {model_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train")
async def train_model(
    background_tasks: BackgroundTasks,
    symbol: str,
    timeframe: str,
    model_name: str,
    version: str = "1.0.0",
    lookback_days: int = Query(365, ge=30, le=1095),
    validation_split: float = Query(0.2, ge=0.1, le=0.5)
) -> Dict[str, Any]:
    """モデル学習"""
    try:
        # バックグラウンドでモデル学習実行
        background_tasks.add_task(
            _train_model_background, 
            symbol, timeframe, model_name, version, 
            lookback_days, validation_split
        )
        
        return {
            "status": "training_started",
            "message": f"Training started for {model_name}",
            "symbol": symbol,
            "timeframe": timeframe
        }
        
    except Exception as e:
        logger.error(f"Error starting model training: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _train_model_background(symbol: str, timeframe: str, model_name: str, 
                                version: str, lookback_days: int, validation_split: float):
    """バックグラウンドでのモデル学習"""
    try:
        logger.info(f"Starting background training for {model_name}")
        
        # データ取得
        if not mt5_client.ensure_connection():
            raise Exception("MT5 connection failed")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        df = mt5_client.get_rates_range(symbol, timeframe, start_date, end_date)
        if df is None or len(df) < 1000:
            raise Exception("Insufficient data for training")
        
        # 特徴量生成
        feature_engine = FeatureEngineering()
        features_df = feature_engine.create_features(df)
        
        # モデル作成と学習
        model = LightGBMPredictor(task_type="classification")
        
        # ラベル作成
        labeled_df = model.prepare_labels(features_df, lookforward=24)
        
        # 特徴量とラベル分離
        feature_columns = feature_engine.get_feature_columns()
        X = labeled_df[feature_columns].dropna()
        y = labeled_df.loc[X.index, 'label']
        
        # 学習実行
        metrics = model.train(X, y, validation_split=validation_split)
        
        # モデル保存
        training_data_info = {
            'start_date': start_date.date(),
            'end_date': end_date.date(),
            'data_points': len(X),
            'feature_count': len(feature_columns)
        }
        
        model_id = model_manager.save_model(
            model, model_name, symbol, timeframe, version,
            training_data_info, metrics
        )
        
        logger.info(f"Model training completed: {model_id}")
        
    except Exception as e:
        logger.error(f"Error in background model training: {e}")

@router.get("/predictions/{symbol}/{timeframe}")
async def get_prediction(symbol: str, timeframe: str) -> Dict[str, Any]:
    """予測取得"""
    return await prediction_api.get_prediction(symbol, timeframe)

@router.get("/predictions/multiple/{timeframe}")
async def get_multiple_predictions(
    timeframe: str,
    symbols: str = Query(..., description="Comma-separated symbol list")
) -> Dict[str, Any]:
    """複数通貨ペアの予測取得"""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    return await prediction_api.get_multiple_predictions(symbol_list, timeframe)

@router.get("/predictions/{symbol}/{timeframe}/history")
async def get_prediction_history(
    symbol: str, 
    timeframe: str,
    hours: int = Query(24, ge=1, le=168)
) -> Dict[str, Any]:
    """予測履歴取得"""
    try:
        history_df = prediction_service.get_prediction_history(symbol, timeframe, hours)
        
        return {
            "status": "success",
            "symbol": symbol,
            "timeframe": timeframe,
            "hours": hours,
            "count": len(history_df),
            "predictions": history_df.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Error getting prediction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions/{symbol}/{timeframe}/accuracy")
async def get_prediction_accuracy(symbol: str, timeframe: str) -> Dict[str, Any]:
    """予測精度取得"""
    return await prediction_api.get_prediction_accuracy(symbol, timeframe)

@router.post("/predictions/start")
async def start_prediction_service(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """予測サービス開始"""
    try:
        background_tasks.add_task(prediction_service.start_prediction_service)
        return {"status": "success", "message": "Prediction service started"}
        
    except Exception as e:
        logger.error(f"Error starting prediction service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predictions/stop")
async def stop_prediction_service() -> Dict[str, str]:
    """予測サービス停止"""
    try:
        await prediction_service.stop_prediction_service()
        return {"status": "success", "message": "Prediction service stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping prediction service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions/status")
async def get_prediction_service_status() -> Dict[str, Any]:
    """予測サービス状態取得"""
    return {
        "status": "success",
        "is_running": prediction_service.is_running,
        "active_models": len(prediction_service.active_models),
        "prediction_interval": prediction_service.prediction_interval
    }

@router.post("/evaluate/{model_id}")
async def evaluate_model(
    model_id: int,
    background_tasks: BackgroundTasks,
    test_days: int = Query(30, ge=7, le=90)
) -> Dict[str, str]:
    """モデル評価"""
    try:
        background_tasks.add_task(_evaluate_model_background, model_id, test_days)
        
        return {
            "status": "evaluation_started",
            "message": f"Evaluation started for model {model_id}"
        }
        
    except Exception as e:
        logger.error(f"Error starting model evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _evaluate_model_background(model_id: int, test_days: int):
    """バックグラウンドでのモデル評価"""
    try:
        logger.info(f"Starting background evaluation for model {model_id}")
        
        # モデル読み込み
        model = model_manager.load_model(model_id)
        if model is None:
            raise Exception(f"Failed to load model {model_id}")
        
        model_info = model_manager.get_model_info(model_id)
        symbol = model_info['symbol']
        timeframe = model_info['timeframe']
        
        # テストデータ取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=test_days)
        
        df = mt5_client.get_rates_range(symbol, timeframe, start_date, end_date)
        if df is None or len(df) < 100:
            raise Exception("Insufficient test data")
        
        # 特徴量生成
        feature_engine = FeatureEngineering()
        features_df = feature_engine.create_features(df)
        
        # ラベル作成
        labeled_df = model.prepare_labels(features_df, lookforward=24)
        
        # 評価実行
        feature_columns = model.feature_columns
        X_test = labeled_df[feature_columns].dropna()
        y_test = labeled_df.loc[X_test.index, 'label']
        
        evaluation_result = evaluator.evaluate_classification_model(
            model, X_test, y_test, f"model_{model_id}"
        )
        
        logger.info(f"Model evaluation completed: {model_id}")
        
    except Exception as e:
        logger.error(f"Error in background model evaluation: {e}")

@router.get("/models/compare")
async def compare_models(model_ids: str = Query(..., description="Comma-separated model IDs")) -> Dict[str, Any]:
    """モデル比較"""
    try:
        ids = [int(id_str.strip()) for id_str in model_ids.split(",")]
        comparison_df = model_manager.compare_models(ids)
        
        return {
            "status": "success",
            "comparison": comparison_df.to_dict('records')
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model IDs format")
    except Exception as e:
        logger.error(f"Error comparing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/summary")
async def get_performance_summary(days: int = Query(30, ge=1, le=90)) -> Dict[str, Any]:
    """パフォーマンス要約取得"""
    try:
        summary_df = model_manager.get_model_performance_summary(days)
        
        return {
            "status": "success",
            "period_days": days,
            "summary": summary_df.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/models/cleanup")
async def cleanup_old_models(
    keep_days: int = Query(30, ge=7, le=365),
    keep_active: bool = Query(True)
) -> Dict[str, Any]:
    """古いモデルのクリーンアップ"""
    try:
        deleted_count = model_manager.cleanup_old_models(keep_days, keep_active)
        
        return {
            "status": "success",
            "message": f"Cleaned up {deleted_count} old models",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/features/importance/{model_id}")
async def get_feature_importance(model_id: int, top_n: int = Query(20, ge=5, le=50)) -> Dict[str, Any]:
    """特徴量重要度取得"""
    try:
        model_info = model_manager.get_model_info(model_id)
        if model_info is None:
            raise HTTPException(status_code=404, detail="Model not found")
        
        feature_importance = model_info.get('feature_importance', [])
        if not feature_importance:
            raise HTTPException(status_code=404, detail="Feature importance not available")
        
        # トップN個を取得
        top_features = feature_importance[:top_n]
        
        return {
            "status": "success",
            "model_id": model_id,
            "top_n": top_n,
            "feature_importance": top_features
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feature importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))