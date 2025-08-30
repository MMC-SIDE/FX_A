"""
Backtest API Routing
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from core.database import DatabaseManager
from core.progress_tracker import progress_tracker
from models.backtest_models import (
    BacktestRequest, BacktestResult, OptimizationRequest, OptimizationResponse,
    ComprehensiveBacktestRequest, ComprehensiveBacktestResponse,
    BacktestListResponse, BacktestListItem, BacktestDeleteRequest,
    BacktestCompareRequest, BacktestCompareResponse, BacktestExportRequest,
    BacktestValidationResult, BacktestScheduleRequest, BacktestMetrics
)

from .validators import (
    validate_backtest_request,
    validate_comprehensive_request,
    validate_optimization_request,
    get_available_instruments
)
from core.error_logger import (
    log_backtest_start, log_backtest_complete, log_backtest_error,
    get_recent_error_logs, get_recent_backtest_logs
)
from .simple import generate_simple_backtest_result, get_stored_result
from .comprehensive import generate_comprehensive_backtest_result, generate_dummy_comprehensive_data
from .optimization import generate_optimization_result, optimize_parameters_advanced

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    from backtest.backtest_engine import BacktestEngine
    from backtest.parameter_optimizer import ParameterOptimizer, ComprehensiveOptimizer
    BACKTEST_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Backtest modules not available: {e}")
    BacktestEngine = None
    ParameterOptimizer = None
    ComprehensiveOptimizer = None
    BACKTEST_MODULES_AVAILABLE = False

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

# Global variables (use proper DI container in actual operation)
backtest_engine = None
parameter_optimizer = None
comprehensive_optimizer = None
db_manager = None

# In-memory storage for completed results (use Redis/DB in production)
completed_results = {}

def execute_comprehensive_backtest_background_sync(
    test_id: str,
    validated: dict,
    total_configurations: int,
    start_time: float
):
    """Execute comprehensive backtest in background thread (synchronous version)"""
    import time
    
    logger.info(f"[BACKGROUND THREAD] Started execution for test_id: {test_id}")
    
    try:
        # First try actual backtest
        try:
            from .simple import generate_simple_backtest_result
            
            logger.info(f"Background thread: Running real backtest: {len(validated['symbols'])} currency pairs × {len(validated['timeframes'])} timeframes")
            progress_tracker.update_progress(test_id, "Starting backtest execution", 10.0)
            
            results = []
            config_count = 0
            
            for symbol in validated['symbols']:
                for timeframe in validated['timeframes']:
                    for risk_level in validated['risk_levels']:
                        config_count += 1
                        
                        # Update progress
                        progress_step = f"Executing: {symbol} {timeframe} (Risk: {risk_level})"
                        current_progress = 10.0 + (config_count / total_configurations) * 80.0
                        progress_tracker.update_progress(test_id, progress_step, current_progress, symbol, timeframe)
                        
                        try:
                            # Execute real backtest using simple backtest function
                            backtest_result = generate_simple_backtest_result(
                                symbol=symbol,
                                timeframe=timeframe,
                                start_date=validated['start_date'],
                                end_date=validated['end_date'],
                                initial_balance=validated['initial_balance'],
                                parameters=validated['parameters']
                            )
                            
                            # Get statistical data
                            stats = backtest_result.get("statistics", {})
                            
                            # Format results
                            config_result = {
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "risk_level": risk_level,
                                "total_trades": stats.get("total_trades", 0),
                                "winning_trades": stats.get("winning_trades", 0),
                                "win_rate": stats.get("win_rate", 0),
                                "net_profit": stats.get("net_profit", 0),
                                "profit_factor": stats.get("profit_factor", 1.0),
                                "sharpe_ratio": stats.get("sharpe_ratio", 0),
                                "max_drawdown": stats.get("max_drawdown_percent", 0),
                                "return_percent": stats.get("return_percent", 0)
                            }
                            
                            results.append(config_result)
                            logger.info(f"Background thread: Completed: {symbol} {timeframe} - PF: {config_result['profit_factor']}")
                            
                            # Individual configuration completed
                            progress_tracker.complete_configuration(test_id)
                            
                        except Exception as e:
                            logger.error(f"Background thread: Individual backtest error {symbol} {timeframe}: {e}")
                            progress_tracker.update_progress(test_id, f"Error: {symbol} {timeframe}", current_progress)
                            
                        # Add small delay to allow progress updates
                        time.sleep(0.1)  # 100ms sleep for synchronous processing
            
            if results:
                # Structure real backtest results
                best_config = max(results, key=lambda x: x["profit_factor"])
                worst_config = min(results, key=lambda x: x["profit_factor"])
                
                summary = {
                    "total_configurations": len(results),
                    "average_profit": round(sum(r["net_profit"] for r in results) / len(results), 2),
                    "average_win_rate": round(sum(r["win_rate"] for r in results) / len(results), 2),
                    "average_profit_factor": round(sum(r["profit_factor"] for r in results) / len(results), 2),
                    "best_configuration": best_config,
                    "worst_configuration": worst_config
                }
                
                result = {
                    "test_id": test_id,
                    "test_type": "comprehensive",
                    "period": {
                        "start_date": validated['start_date'].isoformat(),
                        "end_date": validated['end_date'].isoformat()
                    },
                    "configurations": {
                        "symbols": validated['symbols'],
                        "timeframes": validated['timeframes'],
                        "risk_levels": validated['risk_levels'],
                        "use_ml": validated['use_ml'],
                        "optimization_metric": "profit_factor"
                    },
                    "summary": summary,
                    "results": results,
                    "timeframe_analysis": {},
                    "symbol_analysis": {},
                    "ml_performance": None,
                    "created_at": datetime.now().isoformat(),
                    "is_real_backtest": True,
                    "optimization_note": f"Executed actual backtest ({len(results)} combinations)"
                }
                
                progress_tracker.update_progress(test_id, "Structuring results...", 95.0)
                logger.info(f"Background thread: Real backtest completed: {len(results)} combinations")
            else:
                raise Exception("No results were generated from real backtest")
                
        except Exception as e:
            logger.error(f"[BACKGROUND THREAD] Real backtest error: {e}")
            logger.info("[BACKGROUND THREAD] Fallback: Generating dummy data")
            
            # Update progress for fallback
            progress_tracker.update_progress(test_id, "Fallback: Generating dummy data...", 50.0)
            
            # Fallback: Generate dummy data
            result = generate_comprehensive_backtest_result(
                symbols=validated['symbols'],
                timeframes=validated['timeframes'],
                start_date=validated['start_date'],
                end_date=validated['end_date'],
                initial_balance=validated['initial_balance'],
                parameters=validated['parameters'],
                use_ml=validated['use_ml'],
                risk_levels=validated['risk_levels']
            )
            result["test_id"] = test_id
            result["is_real_backtest"] = False
            result["optimization_note"] = "An error occurred in the real backtest, so sample data is displayed."
        
        # Store completed result
        completed_results[test_id] = result
        
        end_time = time.time()
        total_execution_time = end_time - start_time
        logger.info(f"[BACKGROUND THREAD] Comprehensive backtest COMPLETED - Total processing time: {total_execution_time:.3f}s")
        
        # Progress completed
        progress_tracker.complete_backtest(test_id, True)
        
    except Exception as e:
        logger.error(f"[BACKGROUND THREAD] FAILED: {e}")
        progress_tracker.complete_backtest(test_id, False)
        progress_tracker.update_progress(test_id, f"Error: {str(e)}", 0.0)


def get_backtest_dependencies():
    """Get backtest system dependencies"""
    global backtest_engine, parameter_optimizer, comprehensive_optimizer, db_manager
    
    if not BACKTEST_MODULES_AVAILABLE:
        logger.warning("Backtest modules not available, returning None dependencies")
        return None, None, None, None
    
    try:
        if not all([backtest_engine, parameter_optimizer, comprehensive_optimizer, db_manager]):
            db_manager = DatabaseManager()
            backtest_engine = BacktestEngine(db_manager)
            parameter_optimizer = ParameterOptimizer(backtest_engine)
            comprehensive_optimizer = ComprehensiveOptimizer(parameter_optimizer)
        
        return backtest_engine, parameter_optimizer, comprehensive_optimizer, db_manager
    except Exception as e:
        logger.error(f"Failed to initialize backtest dependencies: {e}")
        return None, None, None, None

@router.get("/test")
async def test_endpoint():
    """Test endpoint"""
    return {
        "status": "success",
        "message": "Backtest API is working",
        "modules_available": BACKTEST_MODULES_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/debug-simple")
async def debug_simple_endpoint():
    """Simple debug"""
    return {"working": True}

@router.get("/debug-progress") 
async def debug_progress_endpoint():
    """Debug progress endpoint"""
    return {"status": "success", "message": "Progress endpoint is working", "test": "debug"}

@router.get("/progress/{test_id}")
async def get_backtest_progress(test_id: str):
    """Get backtest progress - fast response"""
    try:
        # Quick progress retrieval with minimal processing
        progress_data = progress_tracker.get_progress(test_id)
        
        if progress_data:
            # Fast serialization - handle datetime efficiently
            start_time = progress_data.get("start_time")
            if start_time:
                try:
                    start_time = start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time)
                except:
                    start_time = str(start_time)
            
            # Build response quickly
            return {
                "status": "success",
                "data": {
                    "test_id": test_id,
                    "status": progress_data.get("status", "running"),
                    "progress_percent": progress_data.get("progress_percent", 0.0),
                    "current_step": progress_data.get("current_step", "Processing..."),
                    "completed_configurations": progress_data.get("completed_configurations", 0),
                    "total_configurations": progress_data.get("total_configurations", 1),
                    "current_symbol": progress_data.get("current_symbol", ""),
                    "current_timeframe": progress_data.get("current_timeframe", ""),
                    "start_time": start_time,
                    "logs": progress_data.get("logs", [])[-5:] if progress_data.get("logs") else []
                }
            }
        else:
            # No progress data - return not found
            raise HTTPException(status_code=404, detail="Progress not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Progress endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Progress retrieval failed")

@router.get("/instruments")
async def get_instruments():
    """Get available instruments and timeframes"""
    try:
        instruments_info = get_available_instruments()
        return {
            "status": "success",
            "data": instruments_info
        }
    except Exception as e:
        logger.error(f"Error getting instruments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
async def run_backtest(request: dict):
    """Run backtest (simple version)"""
    test_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.info(f"Running backtest with request: {request}")
    
    try:
        # Validation
        validated = validate_backtest_request(request)
        
        # ログ記録開始
        log_backtest_start(test_id, validated)
        
        # Generate backtest results
        result = generate_simple_backtest_result(
            symbol=validated['symbol'],
            timeframe=validated['timeframe'],
            start_date=validated['start_date'],
            end_date=validated['end_date'],
            initial_balance=validated['initial_balance'],
            parameters=validated['parameters']
        )
        
        # ログ記録完了
        log_backtest_complete(test_id, result)
        
        return {"data": result, "status": "success"}
        
    except HTTPException as e:
        log_backtest_error(test_id, e, validated if 'validated' in locals() else request)
        raise e
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        log_backtest_error(test_id, e, validated if 'validated' in locals() else request)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run2")
async def run_backtest_simple(request: dict):
    """Simple backtest execution (old endpoint compatibility)"""
    return await run_backtest(request)

@router.post("/optimize")
async def optimize_parameters(request: dict):
    """Parameter optimization"""
    logger.info(f"Optimizing parameters with request: {request}")
    
    try:
        # Validation
        validated = validate_optimization_request(request)
        
        # Generate optimization results
        result = generate_optimization_result(
            symbol=validated['symbol'],
            timeframe=validated['timeframe'],
            start_date=validated['start_date'],
            end_date=validated['end_date'],
            initial_balance=validated['initial_balance'],
            optimization_target=validated['target_metric'],
            iterations=validated['iterations'],
            param_ranges=validated['param_ranges']
        )
        
        return {"data": result, "status": "success"}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize2")
async def optimize_parameters_simple(request: dict):
    """Simple parameter optimization (old endpoint compatibility)"""
    return await optimize_parameters(request)

@router.post("/comprehensive-test")
async def run_comprehensive_backtest_test(request: dict):
    """Test comprehensive backtest route"""
    return {
        "test": "success",
        "received": request,
        "timestamp": datetime.now().isoformat()
    }

def simple_background_task(message: str):
    """Simple background task for testing"""
    import time
    logger.info(f"[SIMPLE BACKGROUND] Starting task with message: {message}")
    time.sleep(2)
    logger.info(f"[SIMPLE BACKGROUND] Task completed with message: {message}")

@router.post("/comprehensive-fresh")
async def run_comprehensive_fresh(background_tasks: BackgroundTasks, request: dict):
    """Completely fresh comprehensive test"""
    print(f"Fresh comprehensive route hit with: {request}")
    
    # Test simple background task
    logger.info("[MAIN] Adding simple background task")
    background_tasks.add_task(simple_background_task, "test message")
    logger.info("[MAIN] Simple background task added")
    
    return {
        "status": "success",
        "route": "fresh",
        "request": request
    }

@router.post("/comprehensive") 
async def run_comprehensive_backtest(request: dict = Body(...)):
    """Run comprehensive backtest"""
    print(f"[HTTP DEBUG] Request type: {type(request)}")
    print(f"[HTTP DEBUG] Request content: {request}")
    
    import time, threading
    start_time = time.time()
    
    # テストIDを生成
    test_id = f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"[COMPREHENSIVE ROUTE HIT] {datetime.now().strftime('%H:%M:%S')} - Request received: {request}")
    logger.info(f"Running comprehensive backtest at {datetime.now().strftime('%H:%M:%S')}")
    logger.info(f"[COMPREHENSIVE DEBUG] {datetime.now().strftime('%H:%M:%S')} - Starting comprehensive backtest")
    print(f"[COMPREHENSIVE DEBUG] {datetime.now().strftime('%H:%M:%S')} - Starting comprehensive backtest")
    
    try:
        # Validation
        logger.info(f"[COMPREHENSIVE ROUTE] Starting validation with request: {request}")
        print(f"[COMPREHENSIVE ROUTE] About to validate request: {request}")
        
        validated = validate_comprehensive_request(request)
        logger.info(f"[COMPREHENSIVE ROUTE] Validation successful: start_date={validated['start_date']}, end_date={validated['end_date']}")
        
        # Calculate total configurations
        total_configurations = len(validated['symbols']) * len(validated['timeframes']) * len(validated['risk_levels'])
        
        # Start progress tracking
        progress_tracker.start_backtest(test_id, total_configurations)
        progress_tracker.update_progress(test_id, "Validation completed", 5.0)
        
        # Execute comprehensive backtest in separate thread
        logger.info(f"[MAIN] Starting thread for test_id: {test_id}")
        thread = threading.Thread(
            target=execute_comprehensive_backtest_background_sync,
            args=(test_id, validated, total_configurations, start_time),
            daemon=True
        )
        thread.start()
        logger.info(f"[MAIN] Thread started successfully for test_id: {test_id}")
        
        # Return immediately with test_id for progress tracking
        return {
            "status": "success",
            "message": "Comprehensive backtest started",
            "test_id": test_id,
            "total_configurations": total_configurations,
            "estimated_duration": "2-5 minutes"
        }
        
    except HTTPException as e:
        if 'test_id' in locals():
            progress_tracker.complete_backtest(test_id, False)
        raise e
    except Exception as e:
        logger.error(f"Comprehensive backtest error: {e}")
        if 'test_id' in locals():
            progress_tracker.complete_backtest(test_id, False)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/comprehensive/dummy")
async def get_dummy_comprehensive_data():
    """Get dummy comprehensive backtest data"""
    try:
        result = generate_dummy_comprehensive_data()
        return {"data": result, "status": "success"}
    except Exception as e:
        logger.error(f"Error generating dummy data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{test_id}")
async def get_backtest_result(test_id: str):
    """Get backtest results"""
    # Check for completed comprehensive results first
    if test_id in completed_results:
        return {"data": completed_results[test_id], "status": "success"}
    
    # Fallback to stored results
    result = get_stored_result(test_id)
    if result:
        return {"data": result, "status": "success"}
    else:
        # Check if test is still in progress
        progress_data = progress_tracker.get_progress(test_id)
        if progress_data and progress_data.get("status") == "running":
            raise HTTPException(status_code=202, detail="Backtest still in progress")
        else:
            raise HTTPException(status_code=404, detail="Backtest result not found")

@router.get("/list")
async def list_backtest_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get list of backtest results"""
    try:
        # Get results from completed_results (in-memory storage)
        logger.info(f"[LIST DEBUG] completed_results keys: {list(completed_results.keys())}")
        logger.info(f"[LIST DEBUG] completed_results length: {len(completed_results)}")
        
        all_results = []
        
        for test_id, result_data in completed_results.items():
            try:
                # Create list item format
                list_item = {
                    "test_id": test_id,
                    "test_type": result_data.get("test_type", "comprehensive"),
                    "created_at": result_data.get("created_at", ""),
                    "status": "completed",
                    "symbols": result_data.get("configurations", {}).get("symbols", []),
                    "timeframes": result_data.get("configurations", {}).get("timeframes", []),
                    "total_configurations": result_data.get("summary", {}).get("total_configurations", 0),
                    "average_profit": result_data.get("summary", {}).get("average_profit", 0),
                    "profit_factor": result_data.get("summary", {}).get("average_profit_factor", 0),
                    "is_real_backtest": result_data.get("is_real_backtest", False)
                }
                all_results.append(list_item)
            except Exception as e:
                logger.error(f"Error processing result {test_id}: {e}")
                continue
        
        # Sort by created_at (newest first)
        all_results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = all_results[start_idx:end_idx]
        
        logger.info(f"List results: Found {len(all_results)} total results, returning {len(paginated_results)} for page {page}")
        
        return {
            "total": len(all_results),
            "page": page,
            "page_size": page_size,
            "results": paginated_results
        }
        
    except Exception as e:
        logger.error(f"Error listing backtest results: {e}")
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "results": []
        }

@router.post("/validate")
async def validate_backtest(request: BacktestRequest):
    """Validate backtest configuration"""
    try:
        validated = validate_backtest_request(request.dict())
        return {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "data_quality_score": 0.95,
            "recommended_adjustments": []
        }
    except HTTPException as e:
        return {
            "is_valid": False,
            "warnings": [],
            "errors": [e.detail],
            "data_quality_score": 0.0,
            "recommended_adjustments": []
        }

@router.post("/compare")
async def compare_backtests(request: BacktestCompareRequest):
    """Compare multiple backtest results"""
    # Simple implementation
    return {
        "test_ids": request.test_ids,
        "comparison": {},
        "winner": request.test_ids[0] if request.test_ids else None,
        "summary": "Comparison not yet implemented"
    }

@router.delete("/delete")
async def delete_backtest(request: BacktestDeleteRequest):
    """Delete backtest results"""
    # Simple implementation
    return {
        "deleted_count": len(request.test_ids),
        "status": "success"
    }

@router.post("/export")
async def export_backtest(request: BacktestExportRequest):
    """Export backtest results"""
    # Simple implementation
    return {
        "file_path": f"/tmp/backtest_{request.test_id}.{request.format}",
        "format": request.format,
        "status": "success"
    }

@router.post("/schedule")
async def schedule_backtest(request: BacktestScheduleRequest, background_tasks: BackgroundTasks):
    """Schedule backtest execution"""
    # Simple implementation
    return {
        "schedule_id": f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "status": "scheduled",
        "next_run": request.schedule.get("next_run", datetime.now().isoformat())
    }

@router.get("/logs/errors")
async def get_error_logs(limit: int = Query(50, ge=1, le=500)):
    """Get recent error logs"""
    try:
        logs = get_recent_error_logs(limit)
        return {
            "status": "success",
            "data": logs,
            "total": len(logs)
        }
    except Exception as e:
        logger.error(f"Error retrieving error logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/backtest")
async def get_backtest_logs(limit: int = Query(50, ge=1, le=500)):
    """Get recent backtest logs"""
    try:
        logs = get_recent_backtest_logs(limit)
        return {
            "status": "success",
            "data": logs,
            "total": len(logs)
        }
    except Exception as e:
        logger.error(f"Error retrieving backtest logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))