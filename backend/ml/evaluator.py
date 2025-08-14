"""
モデル評価・検証機能
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Any, Optional
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score,
    mean_squared_error, mean_absolute_error, r2_score
)
from sklearn.model_selection import TimeSeriesSplit
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class ModelEvaluator:
    """モデル評価クラス"""
    
    def __init__(self):
        self.evaluation_results = {}
        
    def evaluate_classification_model(self, model, X_test: pd.DataFrame, 
                                    y_test: pd.Series, 
                                    model_name: str = "model") -> Dict[str, Any]:
        """
        分類モデルの評価
        
        Args:
            model: 学習済みモデル
            X_test: テスト特徴量
            y_test: テストラベル
            model_name: モデル名
            
        Returns:
            評価結果辞書
        """
        try:
            logger.info(f"Evaluating classification model: {model_name}")
            
            # 予測実行
            y_pred = model.predict(X_test)
            y_pred_proba = None
            
            # 確率予測があれば取得
            try:
                if hasattr(model, 'predict_with_confidence'):
                    _, y_pred_proba = model.predict_with_confidence(X_test)
                elif hasattr(model, 'predict_proba'):
                    y_pred_proba = model.predict_proba(X_test)
            except:
                pass
            
            # 基本メトリクス
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision_macro': precision_score(y_test, y_pred, average='macro', zero_division=0),
                'precision_weighted': precision_score(y_test, y_pred, average='weighted', zero_division=0),
                'recall_macro': recall_score(y_test, y_pred, average='macro', zero_division=0),
                'recall_weighted': recall_score(y_test, y_pred, average='weighted', zero_division=0),
                'f1_macro': f1_score(y_test, y_pred, average='macro', zero_division=0),
                'f1_weighted': f1_score(y_test, y_pred, average='weighted', zero_division=0)
            }
            
            # クラス別メトリクス
            class_report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
            
            # 混同行列
            cm = confusion_matrix(y_test, y_pred)
            
            # ROC-AUC（マルチクラスの場合）
            if y_pred_proba is not None and len(np.unique(y_test)) > 2:
                try:
                    metrics['roc_auc_ovr'] = roc_auc_score(y_test, y_pred_proba, 
                                                          multi_class='ovr', average='weighted')
                except:
                    pass
            
            # 評価結果
            evaluation_result = {
                'model_name': model_name,
                'evaluation_type': 'classification',
                'metrics': metrics,
                'class_report': class_report,
                'confusion_matrix': cm.tolist(),
                'predictions': y_pred.tolist(),
                'true_labels': y_test.tolist(),
                'prediction_probabilities': y_pred_proba.tolist() if y_pred_proba is not None else None,
                'evaluation_timestamp': datetime.now().isoformat()
            }
            
            self.evaluation_results[model_name] = evaluation_result
            
            logger.info(f"Classification evaluation completed for {model_name}")
            logger.info(f"Accuracy: {metrics['accuracy']:.4f}, F1 (weighted): {metrics['f1_weighted']:.4f}")
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"Error evaluating classification model: {e}")
            raise
    
    def evaluate_regression_model(self, model, X_test: pd.DataFrame, 
                                y_test: pd.Series, 
                                model_name: str = "model") -> Dict[str, Any]:
        """
        回帰モデルの評価
        
        Args:
            model: 学習済みモデル
            X_test: テスト特徴量
            y_test: テストラベル
            model_name: モデル名
            
        Returns:
            評価結果辞書
        """
        try:
            logger.info(f"Evaluating regression model: {model_name}")
            
            # 予測実行
            y_pred = model.predict(X_test)
            
            # 基本メトリクス
            metrics = {
                'mse': mean_squared_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'mae': mean_absolute_error(y_test, y_pred),
                'r2': r2_score(y_test, y_pred),
                'mape': np.mean(np.abs((y_test - y_pred) / y_test)) * 100,  # Mean Absolute Percentage Error
            }
            
            # 残差統計
            residuals = y_test - y_pred
            metrics.update({
                'residual_mean': np.mean(residuals),
                'residual_std': np.std(residuals),
                'residual_skew': pd.Series(residuals).skew(),
                'residual_kurt': pd.Series(residuals).kurtosis()
            })
            
            # 評価結果
            evaluation_result = {
                'model_name': model_name,
                'evaluation_type': 'regression',
                'metrics': metrics,
                'predictions': y_pred.tolist(),
                'true_values': y_test.tolist(),
                'residuals': residuals.tolist(),
                'evaluation_timestamp': datetime.now().isoformat()
            }
            
            self.evaluation_results[model_name] = evaluation_result
            
            logger.info(f"Regression evaluation completed for {model_name}")
            logger.info(f"RMSE: {metrics['rmse']:.4f}, R2: {metrics['r2']:.4f}")
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"Error evaluating regression model: {e}")
            raise
    
    def time_series_cross_validation(self, model, X: pd.DataFrame, y: pd.Series,
                                   n_splits: int = 5, test_size: Optional[int] = None) -> Dict[str, Any]:
        """
        時系列クロスバリデーション
        
        Args:
            model: モデルインスタンス
            X: 特徴量データ
            y: ラベルデータ
            n_splits: 分割数
            test_size: テストサイズ
            
        Returns:
            クロスバリデーション結果
        """
        try:
            logger.info("Starting time series cross validation...")
            
            # 時系列分割
            tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
            
            fold_results = []
            
            for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
                logger.info(f"Processing fold {fold + 1}/{n_splits}")
                
                # データ分割
                X_train_fold, X_test_fold = X.iloc[train_idx], X.iloc[test_idx]
                y_train_fold, y_test_fold = y.iloc[train_idx], y.iloc[test_idx]
                
                # モデル学習
                model_copy = self._copy_model(model)
                model_copy.train(X_train_fold, y_train_fold, validation_split=0.0)
                
                # 評価
                if hasattr(model_copy, 'task_type') and model_copy.task_type == 'regression':
                    fold_result = self.evaluate_regression_model(
                        model_copy, X_test_fold, y_test_fold, f"fold_{fold + 1}"
                    )
                else:
                    fold_result = self.evaluate_classification_model(
                        model_copy, X_test_fold, y_test_fold, f"fold_{fold + 1}"
                    )
                
                fold_result['fold'] = fold + 1
                fold_result['train_size'] = len(X_train_fold)
                fold_result['test_size'] = len(X_test_fold)
                fold_results.append(fold_result)
            
            # 結果集約
            cv_results = self._aggregate_cv_results(fold_results)
            
            logger.info("Time series cross validation completed")
            return cv_results
            
        except Exception as e:
            logger.error(f"Error in time series cross validation: {e}")
            raise
    
    def _copy_model(self, model):
        """モデルのコピー作成"""
        # モデルクラスに応じてコピーを作成
        if hasattr(model, '__class__'):
            model_class = model.__class__
            if hasattr(model, 'params'):
                return model_class(params=model.params.copy())
            else:
                return model_class()
        else:
            raise ValueError("Cannot copy model")
    
    def _aggregate_cv_results(self, fold_results: List[Dict]) -> Dict[str, Any]:
        """クロスバリデーション結果の集約"""
        if not fold_results:
            return {}
        
        # メトリクス名を取得
        metric_names = list(fold_results[0]['metrics'].keys())
        
        # 各メトリクスの統計
        aggregated_metrics = {}
        for metric in metric_names:
            values = [fold['metrics'][metric] for fold in fold_results]
            aggregated_metrics[metric] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'values': values
            }
        
        return {
            'n_folds': len(fold_results),
            'aggregated_metrics': aggregated_metrics,
            'fold_results': fold_results,
            'cv_timestamp': datetime.now().isoformat()
        }
    
    def trading_simulation_evaluation(self, model, price_data: pd.DataFrame,
                                    initial_balance: float = 100000,
                                    transaction_cost: float = 0.0001) -> Dict[str, Any]:
        """
        取引シミュレーション評価
        
        Args:
            model: 学習済みモデル
            price_data: 価格データ（OHLC）
            initial_balance: 初期残高
            transaction_cost: 取引コスト
            
        Returns:
            取引シミュレーション結果
        """
        try:
            logger.info("Starting trading simulation evaluation...")
            
            # 特徴量が含まれているかチェック
            if not hasattr(model, 'feature_columns') or model.feature_columns is None:
                raise ValueError("Model feature columns not found")
            
            # 予測実行
            predictions = model.predict(price_data[model.feature_columns])
            
            # 取引シミュレーション
            balance = initial_balance
            position = 0  # 0: no position, 1: long, -1: short
            trades = []
            equity_curve = [initial_balance]
            
            for i in range(1, len(price_data)):
                current_price = price_data['close'].iloc[i]
                signal = predictions[i]
                
                # シグナルに基づく取引判定
                if signal == 1 and position != 1:  # BUY signal
                    if position == -1:  # Close short position
                        profit = balance * (price_data['close'].iloc[i-1] - current_price) / price_data['close'].iloc[i-1]
                        balance += profit - (balance * transaction_cost)
                        trades.append({
                            'type': 'close_short',
                            'price': current_price,
                            'profit': profit,
                            'balance': balance,
                            'timestamp': price_data.index[i]
                        })
                    
                    # Open long position
                    position = 1
                    trades.append({
                        'type': 'open_long',
                        'price': current_price,
                        'balance': balance,
                        'timestamp': price_data.index[i]
                    })
                
                elif signal == 2 and position != -1:  # SELL signal
                    if position == 1:  # Close long position
                        profit = balance * (current_price - price_data['close'].iloc[i-1]) / price_data['close'].iloc[i-1]
                        balance += profit - (balance * transaction_cost)
                        trades.append({
                            'type': 'close_long',
                            'price': current_price,
                            'profit': profit,
                            'balance': balance,
                            'timestamp': price_data.index[i]
                        })
                    
                    # Open short position
                    position = -1
                    trades.append({
                        'type': 'open_short',
                        'price': current_price,
                        'balance': balance,
                        'timestamp': price_data.index[i]
                    })
                
                # Update equity curve
                if position == 1:
                    current_equity = balance + balance * (current_price - price_data['close'].iloc[i-1]) / price_data['close'].iloc[i-1]
                elif position == -1:
                    current_equity = balance + balance * (price_data['close'].iloc[i-1] - current_price) / price_data['close'].iloc[i-1]
                else:
                    current_equity = balance
                
                equity_curve.append(current_equity)
            
            # パフォーマンス計算
            total_return = (balance - initial_balance) / initial_balance
            profitable_trades = [t for t in trades if t.get('profit', 0) > 0]
            losing_trades = [t for t in trades if t.get('profit', 0) < 0]
            
            win_rate = len(profitable_trades) / max(len([t for t in trades if 'profit' in t]), 1)
            
            # ドローダウン計算
            equity_series = pd.Series(equity_curve)
            running_max = equity_series.expanding().max()
            drawdown = (equity_series - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # シャープレシオ計算
            returns = equity_series.pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            
            simulation_results = {
                'initial_balance': initial_balance,
                'final_balance': balance,
                'total_return': total_return,
                'total_trades': len([t for t in trades if 'profit' in t]),
                'winning_trades': len(profitable_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'equity_curve': equity_curve,
                'trades': trades,
                'predictions': predictions.tolist(),
                'simulation_timestamp': datetime.now().isoformat()
            }
            
            logger.info("Trading simulation evaluation completed")
            logger.info(f"Total return: {total_return:.2%}, Win rate: {win_rate:.2%}")
            
            return simulation_results
            
        except Exception as e:
            logger.error(f"Error in trading simulation evaluation: {e}")
            raise
    
    def plot_confusion_matrix(self, model_name: str, save_path: str = None):
        """混同行列のプロット"""
        if model_name not in self.evaluation_results:
            logger.error(f"No evaluation results found for {model_name}")
            return
        
        result = self.evaluation_results[model_name]
        if result['evaluation_type'] != 'classification':
            logger.error("Confusion matrix only available for classification models")
            return
        
        cm = np.array(result['confusion_matrix'])
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title(f'Confusion Matrix - {model_name}')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_equity_curve(self, simulation_results: Dict[str, Any], save_path: str = None):
        """エクイティカーブのプロット"""
        if 'equity_curve' not in simulation_results:
            logger.error("Equity curve data not found in simulation results")
            return
        
        plt.figure(figsize=(12, 6))
        plt.plot(simulation_results['equity_curve'])
        plt.title('Equity Curve')
        plt.xlabel('Time')
        plt.ylabel('Balance')
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def generate_evaluation_report(self, model_name: str) -> str:
        """評価レポートの生成"""
        if model_name not in self.evaluation_results:
            return f"No evaluation results found for {model_name}"
        
        result = self.evaluation_results[model_name]
        
        report = f"Model Evaluation Report: {model_name}\n"
        report += "="*50 + "\n\n"
        
        if result['evaluation_type'] == 'classification':
            metrics = result['metrics']
            report += f"Accuracy: {metrics['accuracy']:.4f}\n"
            report += f"Precision (weighted): {metrics['precision_weighted']:.4f}\n"
            report += f"Recall (weighted): {metrics['recall_weighted']:.4f}\n"
            report += f"F1-Score (weighted): {metrics['f1_weighted']:.4f}\n\n"
            
            report += "Class-wise Performance:\n"
            for class_name, class_metrics in result['class_report'].items():
                if isinstance(class_metrics, dict) and class_name not in ['accuracy', 'macro avg', 'weighted avg']:
                    report += f"  Class {class_name}:\n"
                    report += f"    Precision: {class_metrics.get('precision', 0):.4f}\n"
                    report += f"    Recall: {class_metrics.get('recall', 0):.4f}\n"
                    report += f"    F1-Score: {class_metrics.get('f1-score', 0):.4f}\n"
        
        elif result['evaluation_type'] == 'regression':
            metrics = result['metrics']
            report += f"RMSE: {metrics['rmse']:.4f}\n"
            report += f"MAE: {metrics['mae']:.4f}\n"
            report += f"R²: {metrics['r2']:.4f}\n"
            report += f"MAPE: {metrics['mape']:.2f}%\n"
        
        report += f"\nEvaluation completed at: {result['evaluation_timestamp']}\n"
        
        return report
    
    def compare_models(self, model_names: List[str]) -> pd.DataFrame:
        """複数モデルの比較"""
        comparison_data = []
        
        for model_name in model_names:
            if model_name in self.evaluation_results:
                result = self.evaluation_results[model_name]
                row = {'model_name': model_name}
                row.update(result['metrics'])
                comparison_data.append(row)
        
        return pd.DataFrame(comparison_data)

if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    # サンプル評価
    evaluator = ModelEvaluator()
    
    # サンプルデータ
    y_true = np.random.choice([0, 1, 2], 100)
    y_pred = np.random.choice([0, 1, 2], 100)
    
    print("Model evaluator test completed")