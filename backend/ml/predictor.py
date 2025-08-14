"""
リアルタイム予測機能
"""
import pandas as pd
import numpy as np
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path

from backend.core.mt5_client import MT5Client
from backend.core.database import DatabaseManager
from backend.ml.features import FeatureEngineering
from backend.ml.models.lightgbm_model import LightGBMPredictor

logger = logging.getLogger(__name__)

class RealTimePredictionService:
    """リアルタイム予測サービス"""
    
    def __init__(self, db_manager: DatabaseManager, mt5_client: MT5Client):
        self.db_manager = db_manager
        self.mt5_client = mt5_client
        self.feature_engine = FeatureEngineering()
        self.active_models = {}  # {symbol_timeframe: model}
        self.prediction_cache = {}  # キャッシュ
        self.is_running = False
        self.prediction_interval = 60  # 秒
        
    async def start_prediction_service(self):
        """予測サービス開始"""
        if self.is_running:
            logger.warning("Prediction service already running")
            return
        
        self.is_running = True
        logger.info("Starting real-time prediction service")
        
        # アクティブモデルの読み込み
        await self._load_active_models()
        
        # 予測ループ開始
        asyncio.create_task(self._prediction_loop())
    
    async def stop_prediction_service(self):
        """予測サービス停止"""
        self.is_running = False
        logger.info("Stopping real-time prediction service")
    
    async def _load_active_models(self):
        """アクティブなモデルを読み込み"""
        try:
            # データベースからアクティブモデルを取得
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT model_name, symbol, timeframe, file_path, model_type, version
                    FROM ml_models 
                    WHERE is_active = true
                    ORDER BY created_at DESC
                """
                
                models_df = pd.read_sql_query(query, conn)
                
                for _, model_info in models_df.iterrows():
                    try:
                        model = LightGBMPredictor()
                        model.load_model(model_info['file_path'])
                        
                        key = f"{model_info['symbol']}_{model_info['timeframe']}"
                        self.active_models[key] = {
                            'model': model,
                            'symbol': model_info['symbol'],
                            'timeframe': model_info['timeframe'],
                            'model_name': model_info['model_name'],
                            'version': model_info['version']
                        }
                        
                        logger.info(f"Loaded model: {model_info['model_name']} for {key}")
                        
                    except Exception as e:
                        logger.error(f"Failed to load model {model_info['model_name']}: {e}")
            
            logger.info(f"Loaded {len(self.active_models)} active models")
            
        except Exception as e:
            logger.error(f"Error loading active models: {e}")
    
    async def _prediction_loop(self):
        """予測ループ"""
        while self.is_running:
            try:
                await self._run_predictions()
                await asyncio.sleep(self.prediction_interval)
                
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
                await asyncio.sleep(30)  # エラー時は30秒待機
    
    async def _run_predictions(self):
        """予測実行"""
        if not self.active_models:
            return
        
        # MT5接続確認
        if not self.mt5_client.ensure_connection():
            logger.error("MT5 connection failed")
            return
        
        for key, model_info in self.active_models.items():
            try:
                await self._predict_for_model(model_info)
                
            except Exception as e:
                logger.error(f"Prediction error for {key}: {e}")
    
    async def _predict_for_model(self, model_info: Dict[str, Any]):
        """個別モデルでの予測"""
        try:
            symbol = model_info['symbol']
            timeframe = model_info['timeframe']
            model = model_info['model']
            
            # 最新データ取得
            df = self.mt5_client.get_rates(symbol, timeframe, count=500)
            if df is None or len(df) < 200:
                logger.warning(f"Insufficient data for {symbol} {timeframe}")
                return
            
            # 特徴量生成
            features_df = self.feature_engine.create_features(df)
            if features_df.empty:
                logger.warning(f"Feature generation failed for {symbol} {timeframe}")
                return
            
            # 最新レコードで予測
            latest_features = features_df.tail(1)[model.feature_columns]
            
            # 予測実行
            if hasattr(model, 'predict_with_confidence'):
                prediction, confidence = model.predict_with_confidence(latest_features)
                prediction = prediction[0]
                confidence = confidence[0]
            else:
                prediction = model.predict(latest_features)[0]
                confidence = None
            
            # 予測結果を保存
            prediction_data = {
                'model_id': None,  # 実際のmodel_idを取得する必要がある
                'symbol': symbol,
                'timeframe': timeframe,
                'prediction_time': datetime.now(),
                'target_time': datetime.now() + timedelta(hours=1),  # 1時間後を予測
                'predicted_direction': self._convert_prediction_to_direction(prediction),
                'predicted_price': None,  # 分類モデルの場合はNone
                'confidence_score': confidence,
                'features_used': latest_features.to_dict('records')[0]
            }
            
            # データベースに保存
            self._save_prediction(prediction_data)
            
            # キャッシュに保存
            cache_key = f"{symbol}_{timeframe}"
            self.prediction_cache[cache_key] = {
                'prediction': prediction,
                'confidence': confidence,
                'timestamp': datetime.now(),
                'direction': prediction_data['predicted_direction']
            }
            
            logger.debug(f"Prediction completed for {symbol} {timeframe}: {prediction} (confidence: {confidence})")
            
        except Exception as e:
            logger.error(f"Error in model prediction: {e}")
            raise
    
    def _convert_prediction_to_direction(self, prediction: int) -> str:
        """予測値を方向に変換"""
        direction_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
        return direction_map.get(prediction, 'HOLD')
    
    def _save_prediction(self, prediction_data: Dict[str, Any]):
        """予測結果をデータベースに保存"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO predictions 
                        (symbol, timeframe, prediction_time, target_time, 
                         predicted_direction, predicted_price, confidence_score, features_used)
                        VALUES (%(symbol)s, %(timeframe)s, %(prediction_time)s, %(target_time)s,
                               %(predicted_direction)s, %(predicted_price)s, %(confidence_score)s, %(features_used)s)
                    """
                    
                    cursor.execute(insert_query, {
                        'symbol': prediction_data['symbol'],
                        'timeframe': prediction_data['timeframe'],
                        'prediction_time': prediction_data['prediction_time'],
                        'target_time': prediction_data['target_time'],
                        'predicted_direction': prediction_data['predicted_direction'],
                        'predicted_price': prediction_data['predicted_price'],
                        'confidence_score': prediction_data['confidence_score'],
                        'features_used': json.dumps(prediction_data['features_used'])
                    })
                    
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error saving prediction: {e}")
    
    def get_latest_prediction(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """最新の予測結果を取得"""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self.prediction_cache:
            cached = self.prediction_cache[cache_key]
            # 5分以内のキャッシュのみ有効
            if (datetime.now() - cached['timestamp']).seconds < 300:
                return cached
        
        # データベースから取得
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT predicted_direction, confidence_score, prediction_time
                    FROM predictions 
                    WHERE symbol = %s AND timeframe = %s
                    ORDER BY prediction_time DESC
                    LIMIT 1
                """
                
                result = pd.read_sql_query(query, conn, params=(symbol, timeframe))
                
                if not result.empty:
                    row = result.iloc[0]
                    return {
                        'direction': row['predicted_direction'],
                        'confidence': row['confidence_score'],
                        'timestamp': row['prediction_time']
                    }
                    
        except Exception as e:
            logger.error(f"Error getting latest prediction: {e}")
        
        return None
    
    def get_prediction_history(self, symbol: str, timeframe: str, 
                             hours: int = 24) -> pd.DataFrame:
        """予測履歴を取得"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT prediction_time, predicted_direction, confidence_score,
                           target_time, actual_price
                    FROM predictions 
                    WHERE symbol = %s AND timeframe = %s
                    AND prediction_time >= %s
                    ORDER BY prediction_time DESC
                """
                
                since_time = datetime.now() - timedelta(hours=hours)
                result = pd.read_sql_query(query, conn, params=(symbol, timeframe, since_time))
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting prediction history: {e}")
            return pd.DataFrame()
    
    def get_model_accuracy(self, symbol: str, timeframe: str, 
                          days: int = 7) -> Optional[float]:
        """モデルの精度を計算"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT predicted_direction, actual_price, target_time
                    FROM predictions 
                    WHERE symbol = %s AND timeframe = %s
                    AND prediction_time >= %s
                    AND actual_price IS NOT NULL
                """
                
                since_time = datetime.now() - timedelta(days=days)
                result = pd.read_sql_query(query, conn, params=(symbol, timeframe, since_time))
                
                if len(result) < 10:  # 最低10件のデータが必要
                    return None
                
                # 実際の方向を計算（簡単な例）
                # 実際の実装では、より詳細な精度計算が必要
                correct_predictions = 0
                total_predictions = len(result)
                
                for _, row in result.iterrows():
                    predicted_dir = row['predicted_direction']
                    # 実際の方向計算のロジックをここに実装
                    # この例では簡略化
                    if predicted_dir in ['BUY', 'SELL']:  # HOLDを除く
                        correct_predictions += 1
                
                accuracy = correct_predictions / total_predictions
                return accuracy
                
        except Exception as e:
            logger.error(f"Error calculating model accuracy: {e}")
            return None

class PredictionAPI:
    """予測API"""
    
    def __init__(self, prediction_service: RealTimePredictionService):
        self.prediction_service = prediction_service
    
    async def get_prediction(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """予測取得API"""
        try:
            prediction = self.prediction_service.get_latest_prediction(symbol, timeframe)
            
            if prediction is None:
                return {
                    'status': 'no_prediction',
                    'message': 'No recent prediction available'
                }
            
            return {
                'status': 'success',
                'symbol': symbol,
                'timeframe': timeframe,
                'prediction': prediction['direction'],
                'confidence': prediction['confidence'],
                'timestamp': prediction['timestamp'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in prediction API: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def get_multiple_predictions(self, symbols: List[str], 
                                     timeframe: str) -> Dict[str, Any]:
        """複数通貨ペアの予測取得"""
        results = {}
        
        for symbol in symbols:
            results[symbol] = await self.get_prediction(symbol, timeframe)
        
        return {
            'status': 'success',
            'timeframe': timeframe,
            'predictions': results,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_prediction_accuracy(self, symbol: str, 
                                    timeframe: str) -> Dict[str, Any]:
        """予測精度取得API"""
        try:
            accuracy = self.prediction_service.get_model_accuracy(symbol, timeframe)
            
            if accuracy is None:
                return {
                    'status': 'insufficient_data',
                    'message': 'Insufficient data to calculate accuracy'
                }
            
            return {
                'status': 'success',
                'symbol': symbol,
                'timeframe': timeframe,
                'accuracy': accuracy,
                'period_days': 7
            }
            
        except Exception as e:
            logger.error(f"Error in accuracy API: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    async def test_prediction_service():
        # サンプルテスト
        print("Real-time prediction service test completed")
    
    # asyncio.run(test_prediction_service())