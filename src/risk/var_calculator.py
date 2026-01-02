"""Value at Risk (VaR) calculation using historical and parametric methods."""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..core.models import Position
from ..core.logging.structured_logger import get_logger
from ..market_data.historical_data import HistoricalDataProvider


@dataclass
class VaRResult:
    """Value at Risk calculation result."""
    var_1day_95: float
    var_1day_99: float
    var_10day_95: float
    var_10day_99: float
    method: str
    calculated_at: datetime
    portfolio_value: float
    confidence_interval: Dict[str, float]
    

class VaRCalculator:
    """Calculate Value at Risk using multiple methodologies."""
    
    def __init__(self, historical_data: HistoricalDataProvider):
        self.historical_data = historical_data
        self.logger = get_logger(__name__)
        
        # VaR configuration
        self.confidence_levels = [0.95, 0.99]
        self.time_horizons = [1, 10]  # days
        self.lookback_period = 252  # trading days (1 year)
        
    async def calculate_portfolio_var(
        self,
        positions: List[Position],
        method: str = 'historical'
    ) -> VaRResult:
        """Calculate portfolio VaR using specified method.
        
        Args:
            positions: List of current positions
            method: 'historical', 'parametric', or 'monte_carlo'
            
        Returns:
            VaRResult with VaR estimates at different confidence levels
        """
        if not positions:
            return self._zero_var_result(method)
        
        # Get historical returns for all positions
        returns_data = await self._get_portfolio_returns(positions)
        
        if len(returns_data) < 30:
            self.logger.warning("Insufficient data for VaR calculation", data_points=len(returns_data))
            return self._zero_var_result(method)
        
        # Calculate VaR based on method
        if method == 'historical':
            var_result = self._calculate_historical_var(returns_data, positions)
        elif method == 'parametric':
            var_result = self._calculate_parametric_var(returns_data, positions)
        elif method == 'monte_carlo':
            var_result = self._calculate_monte_carlo_var(returns_data, positions)
        else:
            raise ValueError(f"Unknown VaR method: {method}")
        
        self.logger.info(
            "VaR calculated",
            method=method,
            var_1day_95=var_result.var_1day_95,
            var_1day_99=var_result.var_1day_99
        )
        
        return var_result
    
    async def _get_portfolio_returns(self, positions: List[Position]) -> np.ndarray:
        """Calculate historical portfolio returns."""
        # Get historical prices for all symbols
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.lookback_period * 2)  # Extra buffer
        
        portfolio_values = []
        
        # For simplicity, we'll calculate weighted returns
        # In production, you'd want to use actual portfolio rebalancing history
        position_weights = {}
        total_notional = sum(
            abs(float(p.quantity) * float(p.average_entry_price))
            for p in positions
        )
        
        if total_notional == 0:
            return np.array([])
        
        for position in positions:
            notional = abs(float(position.quantity) * float(position.average_entry_price))
            weight = notional / total_notional
            position_weights[position.symbol] = {
                'weight': weight,
                'direction': 1 if position.quantity > 0 else -1
            }
        
        # Get price history for each symbol
        symbol_returns = {}
        for symbol in position_weights.keys():
            try:
                prices = await self.historical_data.get_historical_prices(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval='1d'
                )
                
                if len(prices) < 2:
                    continue
                
                # Calculate returns
                price_array = np.array([float(p.close) for p in prices])
                returns = np.diff(price_array) / price_array[:-1]
                symbol_returns[symbol] = returns
                
            except Exception as e:
                self.logger.warning(f"Failed to get history for {symbol}", error=e)
                continue
        
        if not symbol_returns:
            return np.array([])
        
        # Align returns to common dates and calculate portfolio returns
        min_length = min(len(r) for r in symbol_returns.values())
        
        portfolio_returns = np.zeros(min_length)
        for symbol, returns in symbol_returns.items():
            weight = position_weights[symbol]['weight']
            direction = position_weights[symbol]['direction']
            portfolio_returns += weight * direction * returns[:min_length]
        
        return portfolio_returns
    
    def _calculate_historical_var(self, returns: np.ndarray, positions: List[Position]) -> VaRResult:
        """Calculate VaR using historical simulation."""
        portfolio_value = sum(
            float(p.quantity) * float(p.current_price or p.average_entry_price)
            for p in positions
        )
        
        # Sort returns
        sorted_returns = np.sort(returns)
        
        # Calculate VaR at different confidence levels and horizons
        var_1day_95 = -float(np.percentile(sorted_returns, 5)) * portfolio_value
        var_1day_99 = -float(np.percentile(sorted_returns, 1)) * portfolio_value
        
        # Scale to 10-day using square root of time rule
        var_10day_95 = var_1day_95 * np.sqrt(10)
        var_10day_99 = var_1day_99 * np.sqrt(10)
        
        # Calculate confidence intervals
        mean_return = float(np.mean(returns))
        std_return = float(np.std(returns))
        
        return VaRResult(
            var_1day_95=var_1day_95,
            var_1day_99=var_1day_99,
            var_10day_95=var_10day_95,
            var_10day_99=var_10day_99,
            method='historical',
            calculated_at=datetime.now(timezone.utc),
            portfolio_value=portfolio_value,
            confidence_interval={
                'mean': mean_return * portfolio_value,
                'std': std_return * portfolio_value,
                '95_lower': float(np.percentile(returns, 2.5)) * portfolio_value,
                '95_upper': float(np.percentile(returns, 97.5)) * portfolio_value
            }
        )
    
    def _calculate_parametric_var(self, returns: np.ndarray, positions: List[Position]) -> VaRResult:
        """Calculate VaR using parametric (variance-covariance) method."""
        portfolio_value = sum(
            float(p.quantity) * float(p.current_price or p.average_entry_price)
            for p in positions
        )
        
        # Calculate mean and std of returns
        mean_return = float(np.mean(returns))
        std_return = float(np.std(returns))
        
        # Z-scores for confidence levels
        z_95 = 1.645  # 95% confidence
        z_99 = 2.326  # 99% confidence
        
        # Calculate VaR (assuming normal distribution)
        var_1day_95 = (mean_return - z_95 * std_return) * portfolio_value
        var_1day_99 = (mean_return - z_99 * std_return) * portfolio_value
        
        # Scale to 10-day
        var_10day_95 = var_1day_95 * np.sqrt(10)
        var_10day_99 = var_1day_99 * np.sqrt(10)
        
        # Make VaR positive (loss amount)
        var_1day_95 = abs(var_1day_95)
        var_1day_99 = abs(var_1day_99)
        var_10day_95 = abs(var_10day_95)
        var_10day_99 = abs(var_10day_99)
        
        return VaRResult(
            var_1day_95=var_1day_95,
            var_1day_99=var_1day_99,
            var_10day_95=var_10day_95,
            var_10day_99=var_10day_99,
            method='parametric',
            calculated_at=datetime.now(timezone.utc),
            portfolio_value=portfolio_value,
            confidence_interval={
                'mean': mean_return * portfolio_value,
                'std': std_return * portfolio_value,
                '95_lower': (mean_return - 1.96 * std_return) * portfolio_value,
                '95_upper': (mean_return + 1.96 * std_return) * portfolio_value
            }
        )
    
    def _calculate_monte_carlo_var(self, returns: np.ndarray, positions: List[Position],
                                   simulations: int = 10000) -> VaRResult:
        """Calculate VaR using Monte Carlo simulation."""
        portfolio_value = sum(
            float(p.quantity) * float(p.current_price or p.average_entry_price)
            for p in positions
        )
        
        # Estimate parameters from historical data
        mean_return = float(np.mean(returns))
        std_return = float(np.std(returns))
        
        # Run Monte Carlo simulations
        np.random.seed(42)  # For reproducibility
        simulated_returns = np.random.normal(mean_return, std_return, simulations)
        
        # Calculate portfolio P&L for each simulation
        simulated_pnl = simulated_returns * portfolio_value
        
        # Calculate VaR from simulated distribution
        var_1day_95 = -float(np.percentile(simulated_pnl, 5))
        var_1day_99 = -float(np.percentile(simulated_pnl, 1))
        
        # Scale to 10-day
        var_10day_95 = var_1day_95 * np.sqrt(10)
        var_10day_99 = var_1day_99 * np.sqrt(10)
        
        return VaRResult(
            var_1day_95=var_1day_95,
            var_1day_99=var_1day_99,
            var_10day_95=var_10day_95,
            var_10day_99=var_10day_99,
            method='monte_carlo',
            calculated_at=datetime.now(timezone.utc),
            portfolio_value=portfolio_value,
            confidence_interval={
                'mean': float(np.mean(simulated_pnl)),
                'std': float(np.std(simulated_pnl)),
                '95_lower': float(np.percentile(simulated_pnl, 2.5)),
                '95_upper': float(np.percentile(simulated_pnl, 97.5))
            }
        )
    
    def _zero_var_result(self, method: str) -> VaRResult:
        """Return zero VaR result when no positions or insufficient data."""
        return VaRResult(
            var_1day_95=0.0,
            var_1day_99=0.0,
            var_10day_95=0.0,
            var_10day_99=0.0,
            method=method,
            calculated_at=datetime.now(timezone.utc),
            portfolio_value=0.0,
            confidence_interval={'mean': 0.0, 'std': 0.0, '95_lower': 0.0, '95_upper': 0.0}
        )
    
    async def calculate_marginal_var(
        self,
        positions: List[Position],
        position_to_analyze: Position
    ) -> float:
        """Calculate marginal VaR - contribution of single position to portfolio VaR."""
        # Calculate VaR with position
        var_with = await self.calculate_portfolio_var(positions, method='historical')
        
        # Calculate VaR without position
        positions_without = [p for p in positions if p.symbol != position_to_analyze.symbol]
        var_without = await self.calculate_portfolio_var(positions_without, method='historical')
        
        # Marginal VaR is the difference
        marginal_var = var_with.var_1day_95 - var_without.var_1day_95
        
        return marginal_var
    
    async def calculate_component_var(
        self,
        positions: List[Position]
    ) -> Dict[str, float]:
        """Calculate component VaR for each position."""
        component_vars = {}
        
        for position in positions:
            marginal = await self.calculate_marginal_var(positions, position)
            
            # Component VaR = Marginal VaR × Position Weight
            total_value = sum(
                abs(float(p.quantity) * float(p.average_entry_price))
                for p in positions
            )
            
            if total_value > 0:
                position_value = abs(float(position.quantity) * float(position.average_entry_price))
                weight = position_value / total_value
                component_vars[position.symbol] = marginal * weight
            else:
                component_vars[position.symbol] = 0.0
        
        return component_vars
