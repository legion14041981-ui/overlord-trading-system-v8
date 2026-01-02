"""Strategy parameter optimization engine."""
import asyncio
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import numpy as np
from scipy.optimize import minimize, differential_evolution
import itertools

from ..core.logging.structured_logger import get_logger


class OptimizationMethod(Enum):
    """Optimization algorithm types."""
    GRID_SEARCH = "grid_search"  # Exhaustive grid search
    RANDOM_SEARCH = "random_search"  # Random parameter sampling
    BAYESIAN = "bayesian"  # Bayesian optimization
    GENETIC = "genetic"  # Genetic algorithm
    GRADIENT = "gradient"  # Gradient-based (L-BFGS-B)
    WALK_FORWARD = "walk_forward"  # Walk-forward analysis
    

class ObjectiveMetric(Enum):
    """Optimization objective metrics."""
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    TOTAL_RETURN = "total_return"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    RISK_ADJUSTED_RETURN = "risk_adjusted_return"
    

@dataclass
class ParameterSpace:
    """Parameter search space definition."""
    name: str
    min_value: float
    max_value: float
    step: Optional[float] = None  # For grid search
    param_type: str = "continuous"  # continuous, discrete, integer
    default_value: Optional[float] = None
    

@dataclass
class OptimizationConfig:
    """Configuration for optimization run."""
    method: OptimizationMethod
    objective: ObjectiveMetric
    parameter_spaces: List[ParameterSpace]
    max_iterations: int = 100
    population_size: int = 50  # For genetic algorithms
    cv_folds: int = 5  # Cross-validation folds
    train_ratio: float = 0.7  # Train/test split
    min_trades: int = 30  # Minimum trades for valid backtest
    risk_free_rate: float = 0.02  # Annual risk-free rate
    transaction_cost: float = 0.001  # Per-trade cost
    

@dataclass
class OptimizationResult:
    """Results from optimization run."""
    best_parameters: Dict[str, float]
    best_score: float
    all_results: List[Dict[str, Any]]
    optimization_time: float
    iterations_completed: int
    convergence_achieved: bool
    in_sample_metrics: Dict[str, float]
    out_of_sample_metrics: Dict[str, float]
    stability_score: float  # Parameter stability across CV folds
    overfitting_score: float  # IS vs OOS performance ratio
    

@dataclass
class BacktestResult:
    """Simplified backtest result for optimization."""
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return: float
    volatility: float
    

class StrategyOptimizer:
    """Optimize strategy parameters using various algorithms."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Cache for backtest results to avoid recomputation
        self._result_cache: Dict[str, BacktestResult] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def optimize(
        self,
        config: OptimizationConfig,
        backtest_func: Callable,
        data: Any
    ) -> OptimizationResult:
        """Run parameter optimization.
        
        Args:
            config: Optimization configuration
            backtest_func: Async function that runs backtest with parameters
            data: Market data for backtesting
        
        Returns:
            OptimizationResult with best parameters and metrics
        """
        start_time = datetime.now(timezone.utc)
        
        self.logger.info(
            "Starting optimization",
            method=config.method.value,
            objective=config.objective.value,
            param_count=len(config.parameter_spaces)
        )
        
        # Split data for train/test
        train_data, test_data = self._split_data(data, config.train_ratio)
        
        # Run optimization based on method
        if config.method == OptimizationMethod.GRID_SEARCH:
            result = await self._grid_search(config, backtest_func, train_data, test_data)
        elif config.method == OptimizationMethod.RANDOM_SEARCH:
            result = await self._random_search(config, backtest_func, train_data, test_data)
        elif config.method == OptimizationMethod.GENETIC:
            result = await self._genetic_algorithm(config, backtest_func, train_data, test_data)
        elif config.method == OptimizationMethod.GRADIENT:
            result = await self._gradient_optimization(config, backtest_func, train_data, test_data)
        elif config.method == OptimizationMethod.WALK_FORWARD:
            result = await self._walk_forward_optimization(config, backtest_func, data)
        else:
            raise ValueError(f"Unsupported optimization method: {config.method}")
        
        # Calculate optimization time
        optimization_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        result.optimization_time = optimization_time
        
        self.logger.info(
            "Optimization completed",
            method=config.method.value,
            best_score=result.best_score,
            time_seconds=optimization_time
        )
        
        return result
    
    def _split_data(self, data: Any, train_ratio: float) -> Tuple[Any, Any]:
        """Split data into train and test sets."""
        # Simplified - in production, handle various data formats
        if isinstance(data, list):
            split_idx = int(len(data) * train_ratio)
            return data[:split_idx], data[split_idx:]
        return data, data  # Fallback
    
    async def _grid_search(
        self,
        config: OptimizationConfig,
        backtest_func: Callable,
        train_data: Any,
        test_data: Any
    ) -> OptimizationResult:
        """Exhaustive grid search over parameter space."""
        # Generate all parameter combinations
        param_grids = []
        for space in config.parameter_spaces:
            if space.step:
                values = np.arange(space.min_value, space.max_value + space.step, space.step)
            else:
                values = np.linspace(space.min_value, space.max_value, 10)
            
            if space.param_type == "integer":
                values = np.round(values).astype(int)
            
            param_grids.append(values)
        
        # Generate all combinations
        all_combinations = list(itertools.product(*param_grids))
        
        self.logger.info(f"Grid search: testing {len(all_combinations)} combinations")
        
        all_results = []
        best_score = float('-inf')
        best_params = None
        
        for combo in all_combinations[:config.max_iterations]:  # Limit iterations
            params = {
                space.name: value 
                for space, value in zip(config.parameter_spaces, combo)
            }
            
            # Run backtest
            result = await self._evaluate_parameters(
                params, backtest_func, train_data, config
            )
            
            if result:
                score = self._calculate_objective(result, config.objective)
                all_results.append({
                    'parameters': params,
                    'score': score,
                    'metrics': result
                })
                
                if score > best_score:
                    best_score = score
                    best_params = params
        
        # Evaluate best params on test set
        test_result = await self._evaluate_parameters(
            best_params, backtest_func, test_data, config
        )
        
        return self._build_result(
            best_params, best_score, all_results, 
            all_results[-1]['metrics'], test_result,
            len(all_results), True
        )
    
    async def _random_search(
        self,
        config: OptimizationConfig,
        backtest_func: Callable,
        train_data: Any,
        test_data: Any
    ) -> OptimizationResult:
        """Random sampling of parameter space."""
        all_results = []
        best_score = float('-inf')
        best_params = None
        
        for iteration in range(config.max_iterations):
            # Sample random parameters
            params = {}
            for space in config.parameter_spaces:
                if space.param_type == "integer":
                    value = np.random.randint(int(space.min_value), int(space.max_value) + 1)
                else:
                    value = np.random.uniform(space.min_value, space.max_value)
                params[space.name] = value
            
            # Run backtest
            result = await self._evaluate_parameters(
                params, backtest_func, train_data, config
            )
            
            if result:
                score = self._calculate_objective(result, config.objective)
                all_results.append({
                    'parameters': params,
                    'score': score,
                    'metrics': result
                })
                
                if score > best_score:
                    best_score = score
                    best_params = params
        
        # Evaluate on test set
        test_result = await self._evaluate_parameters(
            best_params, backtest_func, test_data, config
        )
        
        return self._build_result(
            best_params, best_score, all_results,
            all_results[-1]['metrics'], test_result,
            config.max_iterations, True
        )
    
    async def _genetic_algorithm(
        self,
        config: OptimizationConfig,
        backtest_func: Callable,
        train_data: Any,
        test_data: Any
    ) -> OptimizationResult:
        """Genetic algorithm optimization using differential evolution."""
        # Define bounds for scipy differential_evolution
        bounds = [(space.min_value, space.max_value) for space in config.parameter_spaces]
        
        all_results = []
        
        def objective_wrapper(params_array):
            """Wrapper for scipy optimizer."""
            params = {
                space.name: params_array[i]
                for i, space in enumerate(config.parameter_spaces)
            }
            
            # Run backtest synchronously (required by scipy)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self._evaluate_parameters(params, backtest_func, train_data, config)
            )
            loop.close()
            
            if result:
                score = self._calculate_objective(result, config.objective)
                all_results.append({
                    'parameters': params,
                    'score': score,
                    'metrics': result
                })
                return -score  # Minimize negative score
            else:
                return 1e10  # Penalize invalid results
        
        # Run differential evolution
        result = differential_evolution(
            objective_wrapper,
            bounds,
            maxiter=config.max_iterations // config.population_size,
            popsize=config.population_size,
            seed=42
        )
        
        best_params = {
            space.name: result.x[i]
            for i, space in enumerate(config.parameter_spaces)
        }
        best_score = -result.fun
        
        # Evaluate on test set
        test_result = await self._evaluate_parameters(
            best_params, backtest_func, test_data, config
        )
        
        return self._build_result(
            best_params, best_score, all_results,
            all_results[-1]['metrics'], test_result,
            len(all_results), result.success
        )
    
    async def _gradient_optimization(
        self,
        config: OptimizationConfig,
        backtest_func: Callable,
        train_data: Any,
        test_data: Any
    ) -> OptimizationResult:
        """Gradient-based optimization (L-BFGS-B)."""
        # Initial guess (midpoint of parameter ranges)
        x0 = [(space.min_value + space.max_value) / 2 for space in config.parameter_spaces]
        bounds = [(space.min_value, space.max_value) for space in config.parameter_spaces]
        
        all_results = []
        
        def objective_wrapper(params_array):
            params = {
                space.name: params_array[i]
                for i, space in enumerate(config.parameter_spaces)
            }
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self._evaluate_parameters(params, backtest_func, train_data, config)
            )
            loop.close()
            
            if result:
                score = self._calculate_objective(result, config.objective)
                all_results.append({
                    'parameters': params,
                    'score': score,
                    'metrics': result
                })
                return -score
            else:
                return 1e10
        
        result = minimize(
            objective_wrapper,
            x0,
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': config.max_iterations}
        )
        
        best_params = {
            space.name: result.x[i]
            for i, space in enumerate(config.parameter_spaces)
        }
        best_score = -result.fun
        
        test_result = await self._evaluate_parameters(
            best_params, backtest_func, test_data, config
        )
        
        return self._build_result(
            best_params, best_score, all_results,
            all_results[-1]['metrics'], test_result,
            len(all_results), result.success
        )
    
    async def _walk_forward_optimization(
        self,
        config: OptimizationConfig,
        backtest_func: Callable,
        data: Any
    ) -> OptimizationResult:
        """Walk-forward analysis with rolling optimization windows."""
        # Simplified walk-forward: optimize on first 70%, test on next 30%
        # In production, use multiple windows
        train_data, test_data = self._split_data(data, config.train_ratio)
        
        # Use random search for each window
        return await self._random_search(config, backtest_func, train_data, test_data)
    
    async def _evaluate_parameters(
        self,
        params: Dict[str, float],
        backtest_func: Callable,
        data: Any,
        config: OptimizationConfig
    ) -> Optional[BacktestResult]:
        """Evaluate strategy with given parameters."""
        # Check cache
        cache_key = str(sorted(params.items()))
        if cache_key in self._result_cache:
            return self._result_cache[cache_key]
        
        try:
            # Run backtest
            result = await backtest_func(params, data)
            
            # Validate result
            if result and result.total_trades >= config.min_trades:
                self._result_cache[cache_key] = result
                return result
            else:
                return None
                
        except Exception as e:
            self.logger.error("Backtest evaluation failed", error=e, params=params)
            return None
    
    def _calculate_objective(
        self,
        result: BacktestResult,
        objective: ObjectiveMetric
    ) -> float:
        """Calculate objective score from backtest result."""
        if objective == ObjectiveMetric.SHARPE_RATIO:
            return result.sharpe_ratio
        elif objective == ObjectiveMetric.SORTINO_RATIO:
            return result.sortino_ratio
        elif objective == ObjectiveMetric.TOTAL_RETURN:
            return result.total_return
        elif objective == ObjectiveMetric.MAX_DRAWDOWN:
            return -result.max_drawdown  # Minimize drawdown
        elif objective == ObjectiveMetric.WIN_RATE:
            return result.win_rate
        elif objective == ObjectiveMetric.PROFIT_FACTOR:
            return result.profit_factor
        elif objective == ObjectiveMetric.RISK_ADJUSTED_RETURN:
            # Custom: return / max_drawdown
            return result.total_return / max(abs(result.max_drawdown), 0.01)
        else:
            return result.sharpe_ratio
    
    def _build_result(
        self,
        best_params: Dict[str, float],
        best_score: float,
        all_results: List[Dict],
        in_sample: BacktestResult,
        out_of_sample: BacktestResult,
        iterations: int,
        converged: bool
    ) -> OptimizationResult:
        """Build final optimization result."""
        # Calculate stability score (variance of top results)
        top_results = sorted(all_results, key=lambda x: x['score'], reverse=True)[:10]
        if len(top_results) > 1:
            score_variance = np.var([r['score'] for r in top_results])
            stability_score = 1.0 / (1.0 + score_variance)
        else:
            stability_score = 1.0
        
        # Calculate overfitting score
        if in_sample and out_of_sample:
            oos_ratio = out_of_sample.sharpe_ratio / max(in_sample.sharpe_ratio, 0.01)
            overfitting_score = min(oos_ratio, 1.0)  # >1 means better OOS (unlikely)
        else:
            overfitting_score = 0.5
        
        return OptimizationResult(
            best_parameters=best_params,
            best_score=best_score,
            all_results=all_results,
            optimization_time=0.0,  # Will be set by caller
            iterations_completed=iterations,
            convergence_achieved=converged,
            in_sample_metrics={
                'sharpe': in_sample.sharpe_ratio if in_sample else 0,
                'return': in_sample.total_return if in_sample else 0,
                'max_dd': in_sample.max_drawdown if in_sample else 0
            },
            out_of_sample_metrics={
                'sharpe': out_of_sample.sharpe_ratio if out_of_sample else 0,
                'return': out_of_sample.total_return if out_of_sample else 0,
                'max_dd': out_of_sample.max_drawdown if out_of_sample else 0
            },
            stability_score=stability_score,
            overfitting_score=overfitting_score
        )
    
    def clear_cache(self) -> None:
        """Clear backtest result cache."""
        self._result_cache.clear()
        self.logger.info("Optimizer cache cleared")
