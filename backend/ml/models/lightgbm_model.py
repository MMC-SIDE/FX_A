"""
LightGBMモデル実装
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import logging
from typing import Dict, List, Tuple, Optional, Any
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class LightGBMPredictor:
    """LightGBM予測モデルクラス"""
    
    def __init__(self, params: Dict[str, Any] = None, task_type: str = "classification"):
        """
        初期化
        
        Args:
            params: LightGBMパラメータ
            task_type: "classification" or "regression"
        """
        self.task_type = task_type
        self.params = params or self._default_params()
        self.model = None
        self.feature_columns = None
        self.label_encoder = None
        self.feature_importance = None
        self.training_history = None
        self.validation_results = None
        
    def _default_params(self) -> Dict[str, Any]:
        """デフォルトパラメータ"""
        if self.task_type == "classification":
            return {
                'objective': 'multiclass',
                'num_class': 3,  # 0: HOLD, 1: BUY, 2: SELL
                'metric': 'multi_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'min_data_in_leaf': 20,
                'lambda_l1': 0.1,
                'lambda_l2': 0.1,
                'verbose': -1,
                'random_state': 42,
                'n_jobs': -1
            }
        else:  # regression
            return {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'min_data_in_leaf': 20,
                'lambda_l1': 0.1,
                'lambda_l2': 0.1,
                'verbose': -1,
                'random_state': 42,
                'n_jobs': -1
            }
    
    def prepare_labels(self, df: pd.DataFrame, 
                      target_column: str = 'close',
                      lookforward: int = 24,
                      method: str = 'threshold') -> pd.DataFrame:
        """
        ラベル作成
        
        Args:
            df: 価格データ
            target_column: 目標列名
            lookforward: 予測期間
            method: ラベル作成方法 ('threshold', 'quantile', 'return')
            
        Returns:
            ラベル付きDataFrame
        """
        try:
            df = df.copy()
            
            if method == 'threshold':
                return self._prepare_threshold_labels(df, target_column, lookforward)
            elif method == 'quantile':
                return self._prepare_quantile_labels(df, target_column, lookforward)
            elif method == 'return':
                return self._prepare_return_labels(df, target_column, lookforward)
            else:
                raise ValueError(f"Unknown method: {method}")
                
        except Exception as e:
            logger.error(f"Error preparing labels: {e}")
            raise
    
    def _prepare_threshold_labels(self, df: pd.DataFrame, 
                                target_column: str, lookforward: int) -> pd.DataFrame:
        """閾値ベースのラベル作成"""
        # 将来の価格変動率を計算
        df['future_return'] = df[target_column].shift(-lookforward) / df[target_column] - 1
        
        # ATRベースの閾値設定
        if 'atr' not in df.columns:
            import talib
            df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        df['threshold'] = df['atr'] / df[target_column] * 0.5  # ATRの50%をしきい値
        
        # ラベル生成
        conditions = [
            df['future_return'] > df['threshold'],   # BUY: 1
            df['future_return'] < -df['threshold'],  # SELL: 2
        ]
        choices = [1, 2]
        df['label'] = np.select(conditions, choices, default=0)  # HOLD: 0
        
        return df
    
    def _prepare_quantile_labels(self, df: pd.DataFrame, 
                               target_column: str, lookforward: int) -> pd.DataFrame:
        """分位数ベースのラベル作成"""
        # 将来の価格変動率を計算
        df['future_return'] = df[target_column].shift(-lookforward) / df[target_column] - 1
        
        # 分位数でラベル作成
        upper_threshold = df['future_return'].quantile(0.7)
        lower_threshold = df['future_return'].quantile(0.3)
        
        conditions = [
            df['future_return'] > upper_threshold,  # BUY: 1
            df['future_return'] < lower_threshold,  # SELL: 2
        ]
        choices = [1, 2]
        df['label'] = np.select(conditions, choices, default=0)  # HOLD: 0
        
        return df
    
    def _prepare_return_labels(self, df: pd.DataFrame, 
                             target_column: str, lookforward: int) -> pd.DataFrame:
        """リターン予測用ラベル作成（回帰）"""
        # 将来のリターンを直接予測
        df['target'] = df[target_column].shift(-lookforward) / df[target_column] - 1
        return df
    
    def train(self, X: pd.DataFrame, y: pd.Series, 
              validation_split: float = 0.2,
              early_stopping_rounds: int = 50,
              num_boost_round: int = 1000) -> Dict[str, Any]:
        """
        モデル学習
        
        Args:
            X: 特徴量データ
            y: ラベルデータ
            validation_split: 検証データ分割比率
            early_stopping_rounds: 早期停止ラウンド数
            num_boost_round: 最大ブースティングラウンド数
            
        Returns:
            学習結果メトリクス
        """
        try:
            logger.info("Starting model training...")
            
            # データの前処理
            X_clean, y_clean = self._preprocess_data(X, y)
            
            # 時系列分割
            split_idx = int(len(X_clean) * (1 - validation_split))
            X_train, X_val = X_clean[:split_idx], X_clean[split_idx:]
            y_train, y_val = y_clean[:split_idx], y_clean[split_idx:]
            
            logger.info(f"Training data shape: {X_train.shape}")
            logger.info(f"Validation data shape: {X_val.shape}")
            
            # LightGBMデータセット作成
            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            
            # モデル学習
            callbacks = [
                lgb.early_stopping(stopping_rounds=early_stopping_rounds),
                lgb.log_evaluation(period=100),
                lgb.record_evaluation(eval_result={})
            ]
            
            self.model = lgb.train(
                self.params,
                train_data,
                valid_sets=[train_data, val_data],
                valid_names=['train', 'eval'],
                num_boost_round=num_boost_round,
                callbacks=callbacks
            )
            
            self.feature_columns = X_train.columns.tolist()
            self.feature_importance = self._get_feature_importance()
            
            # 評価指標計算
            metrics = self._evaluate_model(X_val, y_val)
            self.validation_results = metrics
            
            logger.info("Model training completed successfully")
            logger.info(f"Validation metrics: {metrics}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in model training: {e}")
            raise
    
    def _preprocess_data(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """データの前処理"""
        # 欠損値の確認と処理
        if X.isnull().any().any():
            logger.warning("Found missing values in features, filling with 0")
            X = X.fillna(0)
        
        if y.isnull().any():
            logger.warning("Found missing values in labels, dropping rows")
            mask = ~y.isnull()
            X = X[mask]
            y = y[mask]
        
        # 無限大値の処理
        X = X.replace([np.inf, -np.inf], 0)
        
        # ラベルエンコーディング（分類問題の場合）
        if self.task_type == "classification":
            if self.label_encoder is None:
                self.label_encoder = LabelEncoder()
                y = self.label_encoder.fit_transform(y)
            else:
                y = self.label_encoder.transform(y)
        
        return X, y
    
    def _evaluate_model(self, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, float]:
        """モデル評価"""
        if self.task_type == "classification":
            y_pred = self.model.predict(X_val)
            y_pred_class = np.argmax(y_pred, axis=1)
            
            metrics = {
                'accuracy': accuracy_score(y_val, y_pred_class),
                'precision': precision_score(y_val, y_pred_class, average='weighted', zero_division=0),
                'recall': recall_score(y_val, y_pred_class, average='weighted', zero_division=0),
                'f1': f1_score(y_val, y_pred_class, average='weighted', zero_division=0)
            }
            
            # クラス別メトリクス
            report = classification_report(y_val, y_pred_class, output_dict=True, zero_division=0)
            for class_id, class_metrics in report.items():
                if isinstance(class_metrics, dict):
                    for metric_name, value in class_metrics.items():
                        metrics[f'{class_id}_{metric_name}'] = value
            
        else:  # regression
            y_pred = self.model.predict(X_val)
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            
            metrics = {
                'rmse': np.sqrt(mean_squared_error(y_val, y_pred)),
                'mae': mean_absolute_error(y_val, y_pred),
                'r2': r2_score(y_val, y_pred)
            }
        
        return metrics
    
    def _get_feature_importance(self) -> pd.DataFrame:
        """特徴量重要度の取得"""
        if self.model is None:
            return None
            
        importance_df = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importance(importance_type='gain'),
            'split': self.model.feature_importance(importance_type='split')
        })
        
        return importance_df.sort_values('importance', ascending=False)
    
    def predict(self, X: pd.DataFrame, return_proba: bool = False) -> np.ndarray:
        """
        予測実行
        
        Args:
            X: 特徴量データ
            return_proba: 確率を返すか
            
        Returns:
            予測結果
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        try:
            # 特徴量順序の確認
            if self.feature_columns:
                missing_features = set(self.feature_columns) - set(X.columns)
                if missing_features:
                    logger.warning(f"Missing features: {missing_features}")
                    for feature in missing_features:
                        X[feature] = 0
                
                X = X[self.feature_columns]
            
            # 前処理
            X = X.fillna(0).replace([np.inf, -np.inf], 0)
            
            # 予測実行
            predictions = self.model.predict(X)
            
            if self.task_type == "classification":
                if return_proba:
                    return predictions
                else:
                    predicted_classes = np.argmax(predictions, axis=1)
                    # ラベルエンコーダーがある場合は逆変換
                    if self.label_encoder:
                        predicted_classes = self.label_encoder.inverse_transform(predicted_classes)
                    return predicted_classes
            else:
                return predictions
                
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            raise
    
    def predict_with_confidence(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        信頼度付き予測
        
        Returns:
            (predicted_classes, confidence_scores)
        """
        if self.task_type != "classification":
            raise ValueError("Confidence prediction only available for classification")
        
        predictions = self.predict(X, return_proba=True)
        predicted_classes = np.argmax(predictions, axis=1)
        confidence_scores = np.max(predictions, axis=1)
        
        # ラベルエンコーダーがある場合は逆変換
        if self.label_encoder:
            predicted_classes = self.label_encoder.inverse_transform(predicted_classes)
        
        return predicted_classes, confidence_scores
    
    def hyperparameter_tuning(self, X: pd.DataFrame, y: pd.Series,
                            param_grid: Dict[str, List] = None,
                            cv_folds: int = 3) -> Dict[str, Any]:
        """
        ハイパーパラメータチューニング
        
        Args:
            X: 特徴量データ
            y: ラベルデータ
            param_grid: パラメータグリッド
            cv_folds: クロスバリデーション分割数
            
        Returns:
            最適パラメータ
        """
        try:
            logger.info("Starting hyperparameter tuning...")
            
            if param_grid is None:
                param_grid = {
                    'num_leaves': [31, 50, 100],
                    'learning_rate': [0.05, 0.1, 0.2],
                    'feature_fraction': [0.8, 0.9, 1.0],
                    'bagging_fraction': [0.8, 0.9, 1.0],
                    'min_data_in_leaf': [10, 20, 50]
                }
            
            # データの前処理
            X_clean, y_clean = self._preprocess_data(X, y)
            
            # 時系列クロスバリデーション
            tscv = TimeSeriesSplit(n_splits=cv_folds)
            
            # LightGBM推定器
            lgb_estimator = lgb.LGBMClassifier(**self.params) if self.task_type == "classification" else lgb.LGBMRegressor(**self.params)
            
            # グリッドサーチ
            grid_search = GridSearchCV(
                lgb_estimator,
                param_grid,
                cv=tscv,
                scoring='f1_weighted' if self.task_type == "classification" else 'neg_mean_squared_error',
                n_jobs=-1,
                verbose=1
            )
            
            grid_search.fit(X_clean, y_clean)
            
            # 最適パラメータでモデル更新
            self.params.update(grid_search.best_params_)
            
            logger.info(f"Best parameters: {grid_search.best_params_}")
            logger.info(f"Best score: {grid_search.best_score_}")
            
            return {
                'best_params': grid_search.best_params_,
                'best_score': grid_search.best_score_,
                'cv_results': grid_search.cv_results_
            }
            
        except Exception as e:
            logger.error(f"Error in hyperparameter tuning: {e}")
            raise
    
    def plot_feature_importance(self, top_n: int = 20, save_path: str = None):
        """特徴量重要度のプロット"""
        if self.feature_importance is None:
            logger.warning("Feature importance not available")
            return
        
        plt.figure(figsize=(10, 8))
        top_features = self.feature_importance.head(top_n)
        
        sns.barplot(data=top_features, x='importance', y='feature')
        plt.title(f'Top {top_n} Feature Importance')
        plt.xlabel('Importance')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def save_model(self, filepath: str, metadata: Dict[str, Any] = None):
        """
        モデル保存
        
        Args:
            filepath: 保存パス
            metadata: メタデータ
        """
        try:
            model_data = {
                'model': self.model,
                'feature_columns': self.feature_columns,
                'params': self.params,
                'task_type': self.task_type,
                'label_encoder': self.label_encoder,
                'feature_importance': self.feature_importance,
                'validation_results': self.validation_results,
                'metadata': metadata or {},
                'created_at': datetime.now().isoformat()
            }
            
            joblib.dump(model_data, filepath)
            logger.info(f"Model saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
    
    def load_model(self, filepath: str):
        """
        モデル読み込み
        
        Args:
            filepath: モデルファイルパス
        """
        try:
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.feature_columns = model_data['feature_columns']
            self.params = model_data['params']
            self.task_type = model_data.get('task_type', 'classification')
            self.label_encoder = model_data.get('label_encoder')
            self.feature_importance = model_data.get('feature_importance')
            self.validation_results = model_data.get('validation_results')
            
            logger.info(f"Model loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報の取得"""
        return {
            'task_type': self.task_type,
            'params': self.params,
            'feature_count': len(self.feature_columns) if self.feature_columns else 0,
            'feature_columns': self.feature_columns,
            'validation_results': self.validation_results,
            'model_trained': self.model is not None
        }

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    # サンプルデータ作成
    np.random.seed(42)
    n_samples = 1000
    n_features = 50
    
    X = pd.DataFrame(np.random.randn(n_samples, n_features), 
                     columns=[f'feature_{i}' for i in range(n_features)])
    y = pd.Series(np.random.choice([0, 1, 2], n_samples))
    
    # モデル学習テスト
    model = LightGBMPredictor(task_type="classification")
    metrics = model.train(X, y)
    
    print("Training completed")
    print(f"Metrics: {metrics}")
    
    # 予測テスト
    predictions = model.predict(X[:10])
    print(f"Predictions: {predictions}")
    
    # 信頼度付き予測テスト
    pred_classes, confidence = model.predict_with_confidence(X[:10])
    print(f"Predictions with confidence: {list(zip(pred_classes, confidence))}")