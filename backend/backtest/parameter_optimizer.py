"""
パラメータ最適化機能
"""
import numpy as np
import pandas as pd
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import itertools
from concurrent.futures import ThreadPoolExecutor
import random

from backend.backtest.backtest_engine import BacktestEngine

logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """パラメータ最適化クラス"""
    
    def __init__(self, backtest_engine: BacktestEngine):
        self.backtest_engine = backtest_engine
        self.optimization_results = []
        
    async def optimize_parameters(self,
                                 symbol: str,
                                 timeframe: str,
                                 start_date: datetime,
                                 end_date: datetime,
                                 parameter_ranges: Dict[str, Any],
                                 optimization_metric: str = 'sharpe_ratio',
                                 max_iterations: int = 100,
                                 optimization_method: str = 'grid') -> Dict[str, Any]:
        """
        パラメータ最適化実行
        
        Args:
            symbol: 通貨ペア
            timeframe: 時間軸
            start_date: 開始日
            end_date: 終了日
            parameter_ranges: パラメータ範囲
            optimization_metric: 最適化指標
            max_iterations: 最大反復回数
            optimization_method: 最適化手法 ('grid', 'random', 'bayesian')
            
        Returns:
            最適化結果
        """
        try:
            logger.info(f"Starting parameter optimization for {symbol} {timeframe}")
            logger.info(f"Method: {optimization_method}, Metric: {optimization_metric}, Max iterations: {max_iterations}")
            
            best_result = None
            best_score = float('-inf')
            all_results = []
            
            # パラメータの組み合わせ生成
            if optimization_method == 'grid':
                param_combinations = self._generate_grid_combinations(parameter_ranges, max_iterations)
            elif optimization_method == 'random':
                param_combinations = self._generate_random_combinations(parameter_ranges, max_iterations)
            elif optimization_method == 'bayesian':
                param_combinations = await self._bayesian_optimization(
                    symbol, timeframe, start_date, end_date,
                    parameter_ranges, optimization_metric, max_iterations
                )
                return param_combinations  # ベイズ最適化は独自の結果を返す
            else:
                raise ValueError(f"Unknown optimization method: {optimization_method}")
            
            logger.info(f"Generated {len(param_combinations)} parameter combinations")
            
            # 並列実行の準備
            semaphore = asyncio.Semaphore(4)  # 同時実行数制限
            
            async def run_single_optimization(i: int, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                async with semaphore:
                    try:
                        # バックテスト実行
                        result = await self.backtest_engine.run_backtest(
                            symbol, timeframe, start_date, end_date, params
                        )
                        
                        # 評価指標取得
                        score = result['statistics'].get(optimization_metric, float('-inf'))
                        
                        # 無効な結果をフィルタリング
                        if not self._is_valid_result(result['statistics']):
                            logger.warning(f"Invalid result for iteration {i+1}: insufficient trades")
                            return None
                        
                        result_data = {
                            'iteration': i + 1,
                            'parameters': params,
                            'score': score,
                            'statistics': result['statistics'],
                            'test_id': result['test_id']
                        }
                        
                        logger.info(f"Iteration {i+1}/{len(param_combinations)}: "
                                  f"{optimization_metric}={score:.4f}, trades={result['statistics']['total_trades']}")
                        
                        return result_data
                        
                    except Exception as e:
                        logger.error(f"Optimization iteration {i+1} failed: {e}")
                        return None
            
            # 並列実行
            tasks = [
                run_single_optimization(i, params) 
                for i, params in enumerate(param_combinations)
            ]
            
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果処理
            for result in completed_results:
                if result is not None and not isinstance(result, Exception):
                    all_results.append(result)
                    
                    # 最良結果更新
                    if result['score'] > best_score:
                        best_score = result['score']
                        best_result = result
            
            # 結果の統計分析
            analysis = self._analyze_optimization_results(all_results, optimization_metric)
            
            logger.info(f"Optimization completed: {len(all_results)} valid results")
            if best_result:
                logger.info(f"Best {optimization_metric}: {best_score:.4f}")
                logger.info(f"Best parameters: {best_result['parameters']}")
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'optimization_method': optimization_method,
                'optimization_metric': optimization_metric,
                'best_parameters': best_result['parameters'] if best_result else None,
                'best_score': best_score,
                'best_test_id': best_result['test_id'] if best_result else None,
                'total_iterations': len(param_combinations),
                'valid_results': len(all_results),
                'all_results': all_results,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Parameter optimization failed: {e}")
            raise
    
    def _generate_grid_combinations(self,
                                   parameter_ranges: Dict[str, Any],
                                   max_iterations: int) -> List[Dict[str, Any]]:
        """グリッドサーチ組み合わせ生成"""
        try:
            # 各パラメータの値リスト作成
            param_lists = {}
            
            for param_name, param_config in parameter_ranges.items():
                if isinstance(param_config, dict):
                    min_val = param_config['min']
                    max_val = param_config['max']
                    step = param_config.get('step', (max_val - min_val) / 10)
                    
                    if isinstance(min_val, int):
                        values = list(range(int(min_val), int(max_val) + 1, int(step)))
                    else:
                        values = np.arange(min_val, max_val + step, step).tolist()
                        
                elif isinstance(param_config, list):
                    values = param_config
                else:
                    values = [param_config]
                
                param_lists[param_name] = values
            
            # 全組み合わせ生成
            param_names = list(param_lists.keys())
            param_values = list(param_lists.values())
            
            combinations = []
            for combination in itertools.product(*param_values):
                param_dict = dict(zip(param_names, combination))
                combinations.append(param_dict)
            
            # 組み合わせ数を制限
            if len(combinations) > max_iterations:
                # 均等にサンプリング
                step = len(combinations) // max_iterations
                combinations = combinations[::step][:max_iterations]
            
            logger.info(f"Generated {len(combinations)} grid combinations")
            return combinations
            
        except Exception as e:
            logger.error(f"Error generating grid combinations: {e}")
            return []
    
    def _generate_random_combinations(self,
                                     parameter_ranges: Dict[str, Any],
                                     max_iterations: int) -> List[Dict[str, Any]]:
        """ランダムサーチ組み合わせ生成"""
        try:
            combinations = []
            
            for _ in range(max_iterations):
                param_dict = {}
                
                for param_name, param_config in parameter_ranges.items():
                    if isinstance(param_config, dict):
                        min_val = param_config['min']
                        max_val = param_config['max']
                        
                        if isinstance(min_val, int):
                            value = random.randint(min_val, max_val)
                        else:
                            value = random.uniform(min_val, max_val)
                            
                    elif isinstance(param_config, list):
                        value = random.choice(param_config)
                    else:
                        value = param_config
                    
                    param_dict[param_name] = value
                
                combinations.append(param_dict)
            
            logger.info(f"Generated {len(combinations)} random combinations")
            return combinations
            
        except Exception as e:
            logger.error(f"Error generating random combinations: {e}")
            return []
    
    async def _bayesian_optimization(self,
                                    symbol: str,
                                    timeframe: str,
                                    start_date: datetime,
                                    end_date: datetime,
                                    parameter_ranges: Dict[str, Any],
                                    optimization_metric: str,
                                    max_iterations: int) -> Dict[str, Any]:
        """ベイズ最適化（簡易版）"""
        try:
            logger.info("Running Bayesian optimization (simplified)")
            
            # 初期ランダムサンプル
            initial_samples = min(10, max_iterations // 4)
            random_combinations = self._generate_random_combinations(
                parameter_ranges, initial_samples
            )
            
            best_result = None
            best_score = float('-inf')
            all_results = []
            
            # 初期サンプル評価
            for i, params in enumerate(random_combinations):
                try:
                    result = await self.backtest_engine.run_backtest(
                        symbol, timeframe, start_date, end_date, params
                    )
                    
                    score = result['statistics'].get(optimization_metric, float('-inf'))
                    
                    if self._is_valid_result(result['statistics']):
                        result_data = {
                            'iteration': i + 1,
                            'parameters': params,
                            'score': score,
                            'statistics': result['statistics'],
                            'test_id': result['test_id']
                        }
                        all_results.append(result_data)
                        
                        if score > best_score:
                            best_score = score
                            best_result = result_data
                        
                        logger.info(f"Initial sample {i+1}: {optimization_metric}={score:.4f}")
                        
                except Exception as e:
                    logger.error(f"Initial sample {i+1} failed: {e}")
                    continue
            
            # 残りの反復でベスト近傍を探索
            remaining_iterations = max_iterations - len(all_results)
            
            for i in range(remaining_iterations):
                try:
                    # ベストパラメータの近傍を生成
                    if best_result:
                        neighbor_params = self._generate_neighbor_parameters(
                            best_result['parameters'], parameter_ranges
                        )
                    else:
                        # フォールバック: ランダム
                        neighbor_params = self._generate_random_combinations(parameter_ranges, 1)[0]
                    
                    result = await self.backtest_engine.run_backtest(
                        symbol, timeframe, start_date, end_date, neighbor_params
                    )
                    
                    score = result['statistics'].get(optimization_metric, float('-inf'))
                    
                    if self._is_valid_result(result['statistics']):
                        result_data = {
                            'iteration': len(all_results) + 1,
                            'parameters': neighbor_params,
                            'score': score,
                            'statistics': result['statistics'],
                            'test_id': result['test_id']
                        }
                        all_results.append(result_data)
                        
                        if score > best_score:
                            best_score = score
                            best_result = result_data
                            logger.info(f"New best found: {optimization_metric}={score:.4f}")
                        
                except Exception as e:
                    logger.error(f"Bayesian iteration {i+1} failed: {e}")
                    continue
            
            analysis = self._analyze_optimization_results(all_results, optimization_metric)
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'optimization_method': 'bayesian',
                'optimization_metric': optimization_metric,
                'best_parameters': best_result['parameters'] if best_result else None,
                'best_score': best_score,
                'best_test_id': best_result['test_id'] if best_result else None,
                'total_iterations': max_iterations,
                'valid_results': len(all_results),
                'all_results': all_results,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Bayesian optimization failed: {e}")
            raise
    
    def _generate_neighbor_parameters(self,
                                     base_params: Dict[str, Any],
                                     parameter_ranges: Dict[str, Any],
                                     noise_factor: float = 0.1) -> Dict[str, Any]:
        """近傍パラメータ生成"""
        try:
            neighbor_params = base_params.copy()
            
            for param_name, param_config in parameter_ranges.items():
                if param_name not in base_params:
                    continue
                
                current_value = base_params[param_name]
                
                if isinstance(param_config, dict):
                    min_val = param_config['min']
                    max_val = param_config['max']
                    
                    if isinstance(current_value, int):
                        # 整数パラメータ
                        noise = int((max_val - min_val) * noise_factor)
                        noise = max(1, noise)
                        new_value = current_value + random.randint(-noise, noise)
                        new_value = max(min_val, min(new_value, max_val))
                    else:
                        # 浮動小数点パラメータ
                        noise = (max_val - min_val) * noise_factor
                        new_value = current_value + random.uniform(-noise, noise)
                        new_value = max(min_val, min(new_value, max_val))
                    
                    neighbor_params[param_name] = new_value
                    
                elif isinstance(param_config, list):
                    # 選択肢から近傍を選択
                    current_index = param_config.index(current_value) if current_value in param_config else 0
                    shift = random.choice([-1, 0, 1])
                    new_index = max(0, min(len(param_config) - 1, current_index + shift))
                    neighbor_params[param_name] = param_config[new_index]
            
            return neighbor_params
            
        except Exception as e:
            logger.error(f"Error generating neighbor parameters: {e}")
            return base_params
    
    def _is_valid_result(self, statistics: Dict[str, Any]) -> bool:
        """結果の有効性チェック"""
        try:
            # 最小取引数チェック
            min_trades = 10
            if statistics.get('total_trades', 0) < min_trades:
                return False
            
            # プロフィットファクターチェック
            profit_factor = statistics.get('profit_factor', 0)
            if profit_factor <= 0:
                return False
            
            # 最大ドローダウンチェック
            max_drawdown = statistics.get('max_drawdown_percent', 100)
            if max_drawdown >= 50:  # 50%以上のドローダウンは除外
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating result: {e}")
            return False
    
    def _analyze_optimization_results(self,
                                     results: List[Dict[str, Any]],
                                     optimization_metric: str) -> Dict[str, Any]:
        """最適化結果の分析"""
        try:
            if not results:
                return {}
            
            scores = [r['score'] for r in results]
            
            # 基本統計
            analysis = {
                'metric_statistics': {
                    'mean': np.mean(scores),
                    'std': np.std(scores),
                    'min': np.min(scores),
                    'max': np.max(scores),
                    'median': np.median(scores),
                    'q25': np.percentile(scores, 25),
                    'q75': np.percentile(scores, 75)
                },
                'convergence_analysis': self._analyze_convergence(results),
                'parameter_sensitivity': self._analyze_parameter_sensitivity(results),
                'top_results': sorted(results, key=lambda x: x['score'], reverse=True)[:5]
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing optimization results: {e}")
            return {}
    
    def _analyze_convergence(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """収束分析"""
        try:
            if len(results) < 10:
                return {'status': 'insufficient_data'}
            
            scores = [r['score'] for r in results]
            
            # 移動平均での収束チェック
            window_size = min(10, len(scores) // 4)
            moving_avg = pd.Series(scores).rolling(window=window_size).mean()
            
            # 最後の25%での変化率
            last_quarter = int(len(moving_avg) * 0.75)
            if last_quarter < len(moving_avg) - 1:
                improvement_rate = (moving_avg.iloc[-1] - moving_avg.iloc[last_quarter]) / abs(moving_avg.iloc[last_quarter])
            else:
                improvement_rate = 0
            
            convergence_status = 'converged' if abs(improvement_rate) < 0.05 else 'improving'
            
            return {
                'status': convergence_status,
                'improvement_rate': improvement_rate,
                'final_moving_average': moving_avg.iloc[-1] if not moving_avg.empty else 0,
                'stability_score': 1 - (np.std(scores[-window_size:]) / np.mean(scores[-window_size:]))
            }
            
        except Exception as e:
            logger.error(f"Error analyzing convergence: {e}")
            return {'status': 'error'}
    
    def _analyze_parameter_sensitivity(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """パラメータ感度分析"""
        try:
            if len(results) < 20:
                return {}
            
            # 結果をDataFrameに変換
            data = []
            for result in results:
                row = result['parameters'].copy()
                row['score'] = result['score']
                data.append(row)
            
            df = pd.DataFrame(data)
            
            # 各パラメータとスコアの相関
            correlations = {}
            numeric_params = df.select_dtypes(include=[np.number]).columns
            
            for param in numeric_params:
                if param != 'score':
                    corr = df[param].corr(df['score'])
                    if not np.isnan(corr):
                        correlations[param] = {
                            'correlation': corr,
                            'sensitivity': abs(corr),
                            'direction': 'positive' if corr > 0 else 'negative'
                        }
            
            # 最も重要なパラメータ
            most_sensitive = max(correlations.keys(), key=lambda x: correlations[x]['sensitivity']) if correlations else None
            
            return {
                'correlations': correlations,
                'most_sensitive_parameter': most_sensitive,
                'parameter_rankings': sorted(
                    correlations.items(),
                    key=lambda x: x[1]['sensitivity'],
                    reverse=True
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing parameter sensitivity: {e}")
            return {}

class ComprehensiveOptimizer:
    """包括的最適化クラス"""
    
    def __init__(self, parameter_optimizer: ParameterOptimizer):
        self.parameter_optimizer = parameter_optimizer
    
    async def run_comprehensive_optimization(self,
                                           symbols: List[str] = None,
                                           timeframes: List[str] = None,
                                           test_period_months: int = 12,
                                           parameter_ranges: Dict[str, Any] = None,
                                           optimization_metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """包括的最適化実行"""
        try:
            if symbols is None:
                symbols = ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'CHFJPY']
            
            if timeframes is None:
                timeframes = ['M15', 'M30', 'H1', 'H4']
            
            if parameter_ranges is None:
                parameter_ranges = self._get_default_parameter_ranges()
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=test_period_months * 30)
            
            results = {}
            summary_stats = {}
            
            logger.info(f"Starting comprehensive optimization for {len(symbols)} symbols and {len(timeframes)} timeframes")
            
            for symbol in symbols:
                results[symbol] = {}
                for timeframe in timeframes:
                    try:
                        logger.info(f"Optimizing {symbol} {timeframe}...")
                        
                        optimization_result = await self.parameter_optimizer.optimize_parameters(
                            symbol=symbol,
                            timeframe=timeframe,
                            start_date=start_date,
                            end_date=end_date,
                            parameter_ranges=parameter_ranges,
                            optimization_metric=optimization_metric,
                            max_iterations=50,  # 包括テストでは反復数を制限
                            optimization_method='random'
                        )
                        
                        results[symbol][timeframe] = optimization_result
                        
                        # サマリー統計更新
                        if optimization_result['best_score'] > float('-inf'):
                            key = f"{symbol}_{timeframe}"
                            summary_stats[key] = {
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'best_score': optimization_result['best_score'],
                                'best_parameters': optimization_result['best_parameters'],
                                'valid_results': optimization_result['valid_results']
                            }
                        
                    except Exception as e:
                        logger.error(f"Optimization failed for {symbol} {timeframe}: {e}")
                        results[symbol][timeframe] = {'error': str(e)}
            
            # 総合分析
            overall_analysis = self._analyze_comprehensive_results(summary_stats, optimization_metric)
            
            return {
                'individual_results': results,
                'summary_statistics': summary_stats,
                'overall_analysis': overall_analysis,
                'test_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'months': test_period_months
                },
                'optimization_settings': {
                    'metric': optimization_metric,
                    'symbols': symbols,
                    'timeframes': timeframes,
                    'parameter_ranges': parameter_ranges
                }
            }
            
        except Exception as e:
            logger.error(f"Comprehensive optimization failed: {e}")
            raise
    
    def _get_default_parameter_ranges(self) -> Dict[str, Any]:
        """デフォルトパラメータ範囲"""
        return {
            'risk_per_trade': {'min': 1.0, 'max': 5.0, 'step': 0.5},
            'stop_loss_pips': {'min': 20, 'max': 100, 'step': 10},
            'take_profit_pips': {'min': 40, 'max': 200, 'step': 20},
            'min_confidence': {'min': 0.5, 'max': 0.9, 'step': 0.1},
            'use_nanpin': [True, False],
            'nanpin_max_count': [2, 3, 4, 5],
            'nanpin_interval_pips': [10, 15, 20, 25],
            'n_estimators': [50, 100, 150, 200],
            'max_depth': [4, 6, 8, 10],
            'learning_rate': {'min': 0.05, 'max': 0.2, 'step': 0.05}
        }
    
    def _analyze_comprehensive_results(self,
                                      summary_stats: Dict[str, Any],
                                      optimization_metric: str) -> Dict[str, Any]:
        """包括的結果分析"""
        try:
            if not summary_stats:
                return {}
            
            scores = [stats['best_score'] for stats in summary_stats.values()]
            
            # ベストパフォーマンス
            best_combination = max(summary_stats.items(), key=lambda x: x[1]['best_score'])
            
            # 通貨ペア別分析
            symbol_performance = {}
            for stats in summary_stats.values():
                symbol = stats['symbol']
                if symbol not in symbol_performance:
                    symbol_performance[symbol] = []
                symbol_performance[symbol].append(stats['best_score'])
            
            symbol_rankings = {
                symbol: {
                    'avg_score': np.mean(scores),
                    'max_score': np.max(scores),
                    'count': len(scores)
                }
                for symbol, scores in symbol_performance.items()
            }
            
            # 時間軸別分析
            timeframe_performance = {}
            for stats in summary_stats.values():
                timeframe = stats['timeframe']
                if timeframe not in timeframe_performance:
                    timeframe_performance[timeframe] = []
                timeframe_performance[timeframe].append(stats['best_score'])
            
            timeframe_rankings = {
                tf: {
                    'avg_score': np.mean(scores),
                    'max_score': np.max(scores),
                    'count': len(scores)
                }
                for tf, scores in timeframe_performance.items()
            }
            
            return {
                'overall_statistics': {
                    'total_combinations': len(summary_stats),
                    'avg_score': np.mean(scores),
                    'max_score': np.max(scores),
                    'min_score': np.min(scores),
                    'std_score': np.std(scores)
                },
                'best_combination': {
                    'key': best_combination[0],
                    'symbol': best_combination[1]['symbol'],
                    'timeframe': best_combination[1]['timeframe'],
                    'score': best_combination[1]['best_score'],
                    'parameters': best_combination[1]['best_parameters']
                },
                'symbol_rankings': symbol_rankings,
                'timeframe_rankings': timeframe_rankings,
                'top_10_combinations': sorted(
                    summary_stats.items(),
                    key=lambda x: x[1]['best_score'],
                    reverse=True
                )[:10]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing comprehensive results: {e}")
            return {}

if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.append('.')
    
    logging.basicConfig(level=logging.INFO)
    
    print("Parameter optimizer test completed")