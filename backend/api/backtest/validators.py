"""
バックテストAPIのバリデーション処理
"""
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException
import logging
from config.trading_pairs import (
    ALL_INSTRUMENTS, TIMEFRAMES, 
    is_valid_pair, is_valid_timeframe
)

logger = logging.getLogger(__name__)

def validate_backtest_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """バックテストリクエストのバリデーション"""
    # 基本必須フィールドの確認
    required_fields = ['symbol', 'timeframe']
    for field in required_fields:
        if field not in request:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # 通貨ペア・銘柄の検証
    symbol = request['symbol']
    if not is_valid_pair(symbol):
        available_instruments = ", ".join(ALL_INSTRUMENTS[:20]) + "..." if len(ALL_INSTRUMENTS) > 20 else ", ".join(ALL_INSTRUMENTS)
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid symbol: {symbol}. Available instruments: {available_instruments}"
        )
    
    # 時間軸の検証
    timeframe = request['timeframe']
    if not is_valid_timeframe(timeframe):
        available_timeframes = ", ".join(TIMEFRAMES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe: {timeframe}. Available timeframes: {available_timeframes}"
        )
    
    # 日付のパースと検証（オプション）
    start_date = None
    end_date = None
    
    if 'start_date' in request and request['start_date'] is not None:
        try:
            if isinstance(request['start_date'], str):
                start_date = datetime.fromisoformat(request['start_date'].replace('Z', ''))
            else:
                raise HTTPException(status_code=400, detail=f"Invalid start_date type: {type(request['start_date'])}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid start_date format: {e}")
    
    if 'end_date' in request and request['end_date'] is not None:
        try:
            if isinstance(request['end_date'], str):
                end_date = datetime.fromisoformat(request['end_date'].replace('Z', ''))
            else:
                raise HTTPException(status_code=400, detail=f"Invalid end_date type: {type(request['end_date'])}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid end_date format: {e}")
    
    # 両方の日付が指定されている場合の妥当性チェック
    if start_date and end_date and start_date >= end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    
    # バックテスト期間の制限（最大5年）- 日付が両方指定されている場合のみ
    if start_date and end_date:
        max_days = 5 * 365
        if (end_date - start_date).days > max_days:
            raise HTTPException(
                status_code=400,
                detail=f"Backtest period too long. Maximum {max_days} days allowed"
            )
    
    # 初期残高の検証
    initial_balance = request.get('initial_balance', 100000)
    if initial_balance < 1000 or initial_balance > 100_000_000:
        raise HTTPException(
            status_code=400,
            detail="Initial balance must be between 1,000 and 100,000,000"
        )
    
    # デフォルト値の設定
    validated = {
        'symbol': symbol,
        'timeframe': timeframe,
        'start_date': start_date,
        'end_date': end_date,
        'initial_balance': initial_balance,
        'parameters': request.get('parameters', {}),
        'optimization_target': request.get('optimization_target', 'profit_factor'),
        'iterations': request.get('iterations', 100)
    }
    
    return validated

def validate_comprehensive_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """包括的バックテストリクエストのバリデーション"""
    logger.info(f"[COMPREHENSIVE VALIDATOR] Received request: {request}")
    from config.trading_pairs import DEFAULT_PAIRS, DEFAULT_TIMEFRAMES
    
    # symbolsとtimeframesがNoneまたは空の場合、デフォルト値を使用
    symbols = request.get('symbols')
    if symbols is None or symbols == [] or symbols == "":
        # デフォルト: 7通貨ペア（メジャー通貨ペア）
        symbols = ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'CHFJPY']
    
    timeframes = request.get('timeframes')
    if timeframes is None or timeframes == [] or timeframes == "":
        # デフォルト: 全時間軸
        timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
    
    # デフォルト日付の設定（過去1年間）
    from datetime import datetime, timedelta
    
    default_end_date = datetime.now()
    default_start_date = default_end_date - timedelta(days=365)
    
    # 基本バリデーション（単一銘柄用）
    base_request = {
        'symbol': request.get('symbol', symbols[0] if symbols else 'USDJPY'),
        'timeframe': request.get('timeframe', timeframes[0] if timeframes else 'M5'),
        'initial_balance': request.get('initial_balance', 100000)
    }
    
    # 日付が指定されている場合のみ追加
    if request.get('start_date'):
        base_request['start_date'] = request['start_date']
    else:
        base_request['start_date'] = default_start_date.isoformat()
        
    if request.get('end_date'):
        base_request['end_date'] = request['end_date']
    else:
        base_request['end_date'] = default_end_date.isoformat()
        
    logger.info(f"[COMPREHENSIVE VALIDATOR] base_request: {base_request}")
    validated = validate_backtest_request(base_request)
    logger.info(f"[COMPREHENSIVE VALIDATOR] validation passed")
    
    # 複数銘柄の検証
    for symbol in symbols:
        if not is_valid_pair(symbol):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid symbol in symbols list: {symbol}"
            )
    
    # 複数時間軸の検証
    for timeframe in timeframes:
        if not is_valid_timeframe(timeframe):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe in timeframes list: {timeframe}"
            )
    
    # リスクレベルの取得と検証
    risk_levels = request.get('risk_levels', [0.02])
    
    # 組み合わせ数の制限（パフォーマンス対策）
    # リスクレベルも考慮した組み合わせ数の制限
    max_combinations = 500  # 7通貨×7時間軸×3リスクレベル = 147組み合わせに対応
    total_combinations = len(symbols) * len(timeframes) * len(risk_levels)
    if total_combinations > max_combinations:
        raise HTTPException(
            status_code=400,
            detail=f"Too many combinations ({total_combinations}). Maximum {max_combinations} allowed"
        )
    for risk in risk_levels:
        if not isinstance(risk, (int, float)) or risk < 0.001 or risk > 0.5:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid risk level: {risk}. Must be between 0.001 and 0.5"
            )
    
    validated.update({
        'symbols': symbols,
        'timeframes': timeframes,
        'use_ml': request.get('use_ml', False),
        'risk_levels': risk_levels
    })
    
    return validated

def validate_optimization_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """最適化リクエストのバリデーション"""
    validated = validate_backtest_request(request)
    
    # 最適化手法の検証
    optimization_method = request.get('optimization_method', 'grid_search')
    valid_methods = ['grid_search', 'random_search', 'bayesian', 'genetic']
    if optimization_method not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid optimization method: {optimization_method}. Valid methods: {', '.join(valid_methods)}"
        )
    
    # 最適化ターゲットの検証
    target_metric = request.get('target', 'profit_factor')
    valid_targets = [
        'profit_factor', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio',
        'net_profit', 'return_percent', 'win_rate', 'max_drawdown'
    ]
    if target_metric not in valid_targets:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target metric: {target_metric}. Valid targets: {', '.join(valid_targets)}"
        )
    
    # イテレーション数の検証
    iterations = request.get('iterations', 100)
    if not isinstance(iterations, int) or iterations < 10 or iterations > 10000:
        raise HTTPException(
            status_code=400,
            detail="Iterations must be an integer between 10 and 10000"
        )
    
    # パラメータ範囲の検証
    param_ranges = request.get('param_ranges', {})
    if param_ranges:
        for param_name, param_range in param_ranges.items():
            if not isinstance(param_range, dict) or 'min' not in param_range or 'max' not in param_range:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid parameter range for {param_name}. Must contain 'min' and 'max' keys"
                )
            
            if param_range['min'] >= param_range['max']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid parameter range for {param_name}. Min must be less than max"
                )
    
    validated.update({
        'optimization_method': optimization_method,
        'target_metric': target_metric,
        'param_ranges': param_ranges,
        'iterations': iterations
    })
    
    return validated

def get_available_instruments() -> Dict[str, Any]:
    """利用可能な銘柄・時間軸を取得"""
    from config.trading_pairs import (
        MAJOR_PAIRS, JPY_CROSS_PAIRS, OTHER_CROSS_PAIRS, 
        EXOTIC_PAIRS, METALS, ENERGY, INDICES,
        PAIR_CATEGORIES, DEFAULT_PAIRS, DEFAULT_TIMEFRAMES
    )
    
    return {
        "categories": {
            "major": list(MAJOR_PAIRS),
            "jpy_cross": list(JPY_CROSS_PAIRS),
            "other_cross": list(OTHER_CROSS_PAIRS),
            "exotic": list(EXOTIC_PAIRS),
            "metals": list(METALS),
            "energy": list(ENERGY),
            "indices": list(INDICES)
        },
        "all_instruments": ALL_INSTRUMENTS,
        "default_pairs": list(DEFAULT_PAIRS),
        "timeframes": dict(TIMEFRAMES),
        "default_timeframes": list(DEFAULT_TIMEFRAMES),
        "total_instruments": len(ALL_INSTRUMENTS)
    }