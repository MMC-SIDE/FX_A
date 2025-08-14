"""
モデル管理機能
"""
import pandas as pd
import numpy as np
import os
import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import shutil

from backend.core.database import DatabaseManager
from backend.ml.models.lightgbm_model import LightGBMPredictor
from backend.ml.features import FeatureEngineering
from backend.ml.evaluator import ModelEvaluator

logger = logging.getLogger(__name__)

class ModelManager:
    """モデル管理クラス"""
    
    def __init__(self, db_manager: DatabaseManager, models_dir: str = "models"):
        self.db_manager = db_manager
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.evaluator = ModelEvaluator()
        
    def save_model(self, model: LightGBMPredictor, 
                   model_name: str, symbol: str, timeframe: str, 
                   version: str, training_data_info: Dict[str, Any],
                   metrics: Dict[str, float],
                   metadata: Dict[str, Any] = None) -> str:
        """
        モデルを保存
        
        Args:
            model: 学習済みモデル
            model_name: モデル名
            symbol: 通貨ペア
            timeframe: 時間軸
            version: バージョン
            training_data_info: 学習データ情報
            metrics: 評価メトリクス
            metadata: メタデータ
            
        Returns:
            保存されたモデルのID
        """
        try:
            logger.info(f"Saving model: {model_name} for {symbol} {timeframe}")
            
            # ファイルパス生成
            filename = f"{symbol}_{timeframe}_{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
            file_path = self.models_dir / filename
            
            # モデル保存
            model_metadata = {
                'model_name': model_name,
                'symbol': symbol,
                'timeframe': timeframe,
                'version': version,
                'training_data_info': training_data_info,
                'metrics': metrics,
                'metadata': metadata or {}
            }
            
            model.save_model(str(file_path), model_metadata)
            
            # データベースに記録
            model_record = {
                'model_name': model_name,
                'model_type': 'lightgbm',
                'symbol': symbol,
                'timeframe': timeframe,
                'version': version,
                'file_path': str(file_path),
                'training_period_start': training_data_info.get('start_date'),
                'training_period_end': training_data_info.get('end_date'),
                'validation_score': metrics.get('f1_weighted', metrics.get('accuracy', 0)),
                'test_score': metrics.get('test_f1', metrics.get('test_accuracy')),
                'parameters': model.params,
                'feature_importance': model.feature_importance.to_dict('records') if model.feature_importance is not None else None,
                'feature_list': model.feature_columns,
                'metrics': metrics,
                'is_active': False,  # デフォルトは非アクティブ
                'notes': metadata.get('notes', ''),
                'created_by': metadata.get('created_by', 'system')
            }
            
            model_id = self._save_model_to_db(model_record)
            
            logger.info(f"Model saved successfully with ID: {model_id}")
            return model_id
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
    
    def _save_model_to_db(self, model_record: Dict[str, Any]) -> str:
        """モデル情報をデータベースに保存"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO ml_models 
                        (model_name, model_type, symbol, timeframe, version, file_path,
                         training_period_start, training_period_end, validation_score, test_score,
                         parameters, feature_importance, feature_list, metrics, is_active, notes, created_by)
                        VALUES (%(model_name)s, %(model_type)s, %(symbol)s, %(timeframe)s, %(version)s,
                               %(file_path)s, %(training_period_start)s, %(training_period_end)s,
                               %(validation_score)s, %(test_score)s, %(parameters)s, %(feature_importance)s,
                               %(feature_list)s, %(metrics)s, %(is_active)s, %(notes)s, %(created_by)s)
                        RETURNING id
                    """
                    
                    cursor.execute(insert_query, {
                        'model_name': model_record['model_name'],
                        'model_type': model_record['model_type'],
                        'symbol': model_record['symbol'],
                        'timeframe': model_record['timeframe'],
                        'version': model_record['version'],
                        'file_path': model_record['file_path'],
                        'training_period_start': model_record['training_period_start'],
                        'training_period_end': model_record['training_period_end'],
                        'validation_score': model_record['validation_score'],
                        'test_score': model_record['test_score'],
                        'parameters': json.dumps(model_record['parameters']),
                        'feature_importance': json.dumps(model_record['feature_importance']),
                        'feature_list': json.dumps(model_record['feature_list']),
                        'metrics': json.dumps(model_record['metrics']),
                        'is_active': model_record['is_active'],
                        'notes': model_record['notes'],
                        'created_by': model_record['created_by']
                    })
                    
                    model_id = cursor.fetchone()[0]
                    conn.commit()
                    
                    return model_id
                    
        except Exception as e:
            logger.error(f"Error saving model to database: {e}")
            raise
    
    def load_model(self, model_id: int) -> Optional[LightGBMPredictor]:
        """
        モデルを読み込み
        
        Args:
            model_id: モデルID
            
        Returns:
            読み込まれたモデル
        """
        try:
            # データベースからモデル情報を取得
            model_info = self.get_model_info(model_id)
            if model_info is None:
                logger.error(f"Model with ID {model_id} not found")
                return None
            
            # ファイルパスチェック
            file_path = model_info['file_path']
            if not os.path.exists(file_path):
                logger.error(f"Model file not found: {file_path}")
                return None
            
            # モデル読み込み
            model = LightGBMPredictor()
            model.load_model(file_path)
            
            logger.info(f"Model loaded successfully: {model_info['model_name']}")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model {model_id}: {e}")
            return None
    
    def load_latest_model(self, symbol: str, timeframe: str, 
                         model_type: str = 'lightgbm') -> Optional[LightGBMPredictor]:
        """
        最新のアクティブモデルを読み込み
        
        Args:
            symbol: 通貨ペア
            timeframe: 時間軸
            model_type: モデルタイプ
            
        Returns:
            読み込まれたモデル
        """
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT id FROM ml_models 
                    WHERE symbol = %s AND timeframe = %s AND model_type = %s AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                
                result = pd.read_sql_query(query, conn, params=(symbol, timeframe, model_type))
                
                if result.empty:
                    logger.warning(f"No active model found for {symbol} {timeframe}")
                    return None
                
                model_id = result.iloc[0]['id']
                return self.load_model(model_id)
                
        except Exception as e:
            logger.error(f"Error loading latest model: {e}")
            return None
    
    def get_model_info(self, model_id: int) -> Optional[Dict[str, Any]]:
        """モデル情報を取得"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT * FROM ml_models WHERE id = %s
                """
                
                result = pd.read_sql_query(query, conn, params=(model_id,))
                
                if result.empty:
                    return None
                
                model_info = result.iloc[0].to_dict()
                
                # JSON文字列をパース
                for json_field in ['parameters', 'feature_importance', 'feature_list', 'metrics']:
                    if model_info[json_field]:
                        try:
                            model_info[json_field] = json.loads(model_info[json_field])
                        except:
                            pass
                
                return model_info
                
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None
    
    def list_models(self, symbol: str = None, timeframe: str = None, 
                   is_active: bool = None, limit: int = 50) -> pd.DataFrame:
        """モデル一覧を取得"""
        try:
            with self.db_manager.get_connection() as conn:
                where_conditions = []
                params = []
                
                if symbol:
                    where_conditions.append("symbol = %s")
                    params.append(symbol)
                
                if timeframe:
                    where_conditions.append("timeframe = %s")
                    params.append(timeframe)
                
                if is_active is not None:
                    where_conditions.append("is_active = %s")
                    params.append(is_active)
                
                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                query = f"""
                    SELECT id, model_name, symbol, timeframe, version, validation_score,
                           is_active, created_at, created_by, notes
                    FROM ml_models
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params.append(limit)
                
                result = pd.read_sql_query(query, conn, params=params)
                return result
                
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return pd.DataFrame()
    
    def activate_model(self, model_id: int) -> bool:
        """モデルをアクティブ化"""
        try:
            model_info = self.get_model_info(model_id)
            if model_info is None:
                logger.error(f"Model {model_id} not found")
                return False
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 同じsymbol/timeframeの他のモデルを非アクティブ化
                    deactivate_query = """
                        UPDATE ml_models 
                        SET is_active = false 
                        WHERE symbol = %s AND timeframe = %s AND model_type = %s
                    """
                    cursor.execute(deactivate_query, (
                        model_info['symbol'], 
                        model_info['timeframe'], 
                        model_info['model_type']
                    ))
                    
                    # 指定モデルをアクティブ化
                    activate_query = """
                        UPDATE ml_models 
                        SET is_active = true, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                    cursor.execute(activate_query, (model_id,))
                    
                    conn.commit()
            
            logger.info(f"Model {model_id} activated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error activating model {model_id}: {e}")
            return False
    
    def deactivate_model(self, model_id: int) -> bool:
        """モデルを非アクティブ化"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        UPDATE ml_models 
                        SET is_active = false, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                    cursor.execute(query, (model_id,))
                    conn.commit()
            
            logger.info(f"Model {model_id} deactivated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating model {model_id}: {e}")
            return False
    
    def delete_model(self, model_id: int) -> bool:
        """モデルを削除"""
        try:
            # モデル情報取得
            model_info = self.get_model_info(model_id)
            if model_info is None:
                logger.error(f"Model {model_id} not found")
                return False
            
            # ファイル削除
            file_path = model_info['file_path']
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Model file deleted: {file_path}")
            
            # データベースから削除
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = "DELETE FROM ml_models WHERE id = %s"
                    cursor.execute(query, (model_id,))
                    conn.commit()
            
            logger.info(f"Model {model_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting model {model_id}: {e}")
            return False
    
    def backup_model(self, model_id: int, backup_dir: str = "model_backups") -> bool:
        """モデルをバックアップ"""
        try:
            model_info = self.get_model_info(model_id)
            if model_info is None:
                return False
            
            backup_path = Path(backup_dir)
            backup_path.mkdir(exist_ok=True)
            
            # ファイルをバックアップ
            source_file = model_info['file_path']
            backup_file = backup_path / f"backup_{model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
            
            shutil.copy2(source_file, backup_file)
            
            # メタデータも保存
            metadata_file = backup_file.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(model_info, f, indent=2, default=str)
            
            logger.info(f"Model {model_id} backed up to {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up model {model_id}: {e}")
            return False
    
    def compare_models(self, model_ids: List[int]) -> pd.DataFrame:
        """複数モデルの比較"""
        try:
            comparison_data = []
            
            for model_id in model_ids:
                model_info = self.get_model_info(model_id)
                if model_info:
                    metrics = model_info.get('metrics', {})
                    comparison_data.append({
                        'model_id': model_id,
                        'model_name': model_info['model_name'],
                        'symbol': model_info['symbol'],
                        'timeframe': model_info['timeframe'],
                        'version': model_info['version'],
                        'validation_score': model_info['validation_score'],
                        'accuracy': metrics.get('accuracy', 0),
                        'f1_score': metrics.get('f1_weighted', 0),
                        'precision': metrics.get('precision_weighted', 0),
                        'recall': metrics.get('recall_weighted', 0),
                        'is_active': model_info['is_active'],
                        'created_at': model_info['created_at']
                    })
            
            return pd.DataFrame(comparison_data)
            
        except Exception as e:
            logger.error(f"Error comparing models: {e}")
            return pd.DataFrame()
    
    def cleanup_old_models(self, keep_days: int = 30, keep_active: bool = True) -> int:
        """古いモデルをクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            with self.db_manager.get_connection() as conn:
                # 削除対象のモデルを取得
                where_clause = "created_at < %s"
                params = [cutoff_date]
                
                if keep_active:
                    where_clause += " AND is_active = false"
                
                query = f"SELECT id, file_path FROM ml_models WHERE {where_clause}"
                
                old_models = pd.read_sql_query(query, conn, params=params)
                
                deleted_count = 0
                for _, model in old_models.iterrows():
                    if self.delete_model(model['id']):
                        deleted_count += 1
                
                logger.info(f"Cleaned up {deleted_count} old models")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old models: {e}")
            return 0
    
    def get_model_performance_summary(self, days: int = 30) -> pd.DataFrame:
        """モデルパフォーマンス要約"""
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT m.id, m.model_name, m.symbol, m.timeframe,
                           m.validation_score, m.is_active,
                           COUNT(p.id) as prediction_count,
                           AVG(p.confidence_score) as avg_confidence
                    FROM ml_models m
                    LEFT JOIN predictions p ON m.symbol = p.symbol 
                                           AND m.timeframe = p.timeframe
                                           AND p.prediction_time >= %s
                    GROUP BY m.id, m.model_name, m.symbol, m.timeframe, 
                             m.validation_score, m.is_active
                    ORDER BY m.validation_score DESC
                """
                
                since_date = datetime.now() - timedelta(days=days)
                result = pd.read_sql_query(query, conn, params=(since_date,))
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting model performance summary: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    # サンプルテスト
    print("Model manager test completed")