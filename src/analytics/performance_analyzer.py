"""Performance Analyzer for Portfolio Performance Tracking.

Provides real-time and historical portfolio performance analysis
with comprehensive metrics calculation and attribution analysis.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np
import pandas as pd

from ..core.models.position import Position
from ..core.models.order import Order, OrderStatus
from ..core.models.market_data import MarketData
from ..core.logging import structured_logger


class PerformanceMetrics:
    """Container for performance metrics."""
    
    def __init__(self):
        self.total_return: Decimal = Decimal("0")
        self.daily_returns: List[Decimal] = []
        self.sharpe_ratio: Optional[Decimal] = None
        self.sortino_ratio: Optional[Decimal] = None
        self.calmar_ratio: Optional[Decimal] = None
        self.max_drawdown: Decimal = Decimal("0")
        self.win_rate: Decimal = Decimal("0")
        self.profit_factor: Decimal = Decimal("0")
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.avg_win: Decimal = Decimal("0")
        self.avg_loss: Decimal = Decimal("0")
        self.largest_win: Decimal = Decimal("0")
        self.largest_loss: Decimal = Decimal("0")
        self.cumulative_pnl: Decimal = Decimal("0")
        self.unrealized_pnl: Decimal = Decimal("0")
        self.realized_pnl: Decimal = Decimal("0")
        self.volatility: Optional[Decimal] = None
        self.var_95: Optional[Decimal] = None  # Value at Risk 95%
        self.cvar_95: Optional[Decimal] = None  # Conditional VaR
        
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "total_return": float(self.total_return),
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "sortino_ratio": float(self.sortino_ratio) if self.sortino_ratio else None,
            "calmar_ratio": float(self.calmar_ratio) if self.calmar_ratio else None,
            "max_drawdown": float(self.max_drawdown),
            "win_rate": float(self.win_rate),
            "profit_factor": float(self.profit_factor),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win": float(self.avg_win),
            "avg_loss": float(self.avg_loss),
            "largest_win": float(self.largest_win),
            "largest_loss": float(self.largest_loss),
            "cumulative_pnl": float(self.cumulative_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "realized_pnl": float(self.realized_pnl),
            "volatility": float(self.volatility) if self.volatility else None,
            "var_95": float(self.var_95) if self.var_95 else None,
            "cvar_95": float(self.cvar_95) if self.cvar_95 else None,
        }


class PerformanceAnalyzer:
    """Analyzes portfolio performance with comprehensive metrics.
    
    Features:
    - Real-time performance tracking
    - Risk-adjusted return metrics (Sharpe, Sortino, Calmar)
    - Drawdown analysis
    - Trade statistics
    - Attribution analysis
    - Rolling period analysis
    """
    
    def __init__(
        self,
        initial_capital: Decimal,
        risk_free_rate: Decimal = Decimal("0.02"),  # 2% annual
        lookback_days: int = 252,  # Trading days in a year
    ):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_free_rate = risk_free_rate
        self.lookback_days = lookback_days
        
        # Performance tracking
        self.equity_curve: List[Tuple[datetime, Decimal]] = []
        self.trade_history: List[Dict] = []
        self.daily_pnl: Dict[datetime, Decimal] = {}
        self.position_pnl: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        
        # Metrics cache
        self._metrics_cache: Optional[PerformanceMetrics] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=60)  # Cache for 1 minute
        
        self._lock = asyncio.Lock()
        self.logger = structured_logger.get_logger(__name__)
        
    async def update_equity(self, timestamp: datetime, equity: Decimal) -> None:
        """Update equity curve with new data point.
        
        Args:
            timestamp: Time of update
            equity: Current equity value
        """
        async with self._lock:
            self.equity_curve.append((timestamp, equity))
            self.current_capital = equity
            
            # Calculate daily PnL
            date = timestamp.date()
            if date not in self.daily_pnl:
                # Get previous day's equity
                if len(self.equity_curve) > 1:
                    prev_equity = self.equity_curve[-2][1]
                    self.daily_pnl[date] = equity - prev_equity
                    
            # Invalidate cache
            self._metrics_cache = None
            
    async def record_trade(
        self,
        order: Order,
        fill_price: Decimal,
        fill_quantity: Decimal,
        pnl: Optional[Decimal] = None,
    ) -> None:
        """Record completed trade for analysis.
        
        Args:
            order: Executed order
            fill_price: Execution price
            fill_quantity: Filled quantity
            pnl: Realized P&L (for closing trades)
        """
        async with self._lock:
            trade = {
                "timestamp": datetime.utcnow(),
                "symbol": order.symbol,
                "side": order.side,
                "quantity": fill_quantity,
                "price": fill_price,
                "order_id": order.id,
                "pnl": pnl or Decimal("0"),
            }
            self.trade_history.append(trade)
            
            # Update position P&L
            if pnl:
                self.position_pnl[order.symbol] += pnl
                
            # Invalidate cache
            self._metrics_cache = None
            
            self.logger.info(
                "trade_recorded",
                symbol=order.symbol,
                side=order.side.value,
                quantity=float(fill_quantity),
                price=float(fill_price),
                pnl=float(pnl) if pnl else None,
            )
            
    async def calculate_metrics(
        self,
        force_refresh: bool = False,
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics.
        
        Args:
            force_refresh: Force recalculation ignoring cache
            
        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        async with self._lock:
            # Check cache
            if not force_refresh and self._metrics_cache and self._cache_timestamp:
                if datetime.utcnow() - self._cache_timestamp < self._cache_duration:
                    return self._metrics_cache
                    
            metrics = PerformanceMetrics()
            
            if not self.equity_curve:
                return metrics
                
            # Convert equity curve to numpy arrays for efficient calculation
            timestamps, equity_values = zip(*self.equity_curve)
            equity_array = np.array([float(e) for e in equity_values])
            
            # Total return
            metrics.total_return = Decimal(str(
                (equity_array[-1] - float(self.initial_capital)) / float(self.initial_capital)
            ))
            
            # Daily returns
            if len(equity_array) > 1:
                returns = np.diff(equity_array) / equity_array[:-1]
                metrics.daily_returns = [Decimal(str(r)) for r in returns]
                
                # Volatility (annualized)
                if len(returns) > 0:
                    volatility = np.std(returns) * np.sqrt(252)  # Annualized
                    metrics.volatility = Decimal(str(volatility))
                    
                # Sharpe ratio (annualized)
                if len(returns) > 0 and volatility > 0:
                    daily_rf = float(self.risk_free_rate) / 252
                    excess_returns = returns - daily_rf
                    sharpe = (np.mean(excess_returns) / np.std(returns)) * np.sqrt(252)
                    metrics.sharpe_ratio = Decimal(str(sharpe))
                    
                # Sortino ratio (annualized)
                if len(returns) > 0:
                    daily_rf = float(self.risk_free_rate) / 252
                    excess_returns = returns - daily_rf
                    downside_returns = excess_returns[excess_returns < 0]
                    if len(downside_returns) > 0:
                        downside_std = np.std(downside_returns)
                        if downside_std > 0:
                            sortino = (np.mean(excess_returns) / downside_std) * np.sqrt(252)
                            metrics.sortino_ratio = Decimal(str(sortino))
                            
            # Maximum drawdown
            if len(equity_array) > 0:
                cummax = np.maximum.accumulate(equity_array)
                drawdown = (equity_array - cummax) / cummax
                max_dd = np.min(drawdown)
                metrics.max_drawdown = Decimal(str(abs(max_dd)))
                
                # Calmar ratio (annualized return / max drawdown)
                if abs(max_dd) > 0:
                    annual_return = float(metrics.total_return) * (252 / len(equity_array))
                    calmar = annual_return / abs(max_dd)
                    metrics.calmar_ratio = Decimal(str(calmar))
                    
            # Value at Risk (95%)
            if len(metrics.daily_returns) > 0:
                returns_array = np.array([float(r) for r in metrics.daily_returns])
                var_95 = np.percentile(returns_array, 5)
                metrics.var_95 = Decimal(str(abs(var_95)))
                
                # Conditional VaR (average of returns below VaR)
                cvar_returns = returns_array[returns_array <= var_95]
                if len(cvar_returns) > 0:
                    metrics.cvar_95 = Decimal(str(abs(np.mean(cvar_returns))))
                    
            # Trade statistics
            if self.trade_history:
                trades_with_pnl = [t for t in self.trade_history if t["pnl"] != Decimal("0")]
                metrics.total_trades = len(trades_with_pnl)
                
                if trades_with_pnl:
                    winning = [t for t in trades_with_pnl if t["pnl"] > 0]
                    losing = [t for t in trades_with_pnl if t["pnl"] < 0]
                    
                    metrics.winning_trades = len(winning)
                    metrics.losing_trades = len(losing)
                    metrics.win_rate = Decimal(str(len(winning) / len(trades_with_pnl)))
                    
                    if winning:
                        metrics.avg_win = sum(t["pnl"] for t in winning) / len(winning)
                        metrics.largest_win = max(t["pnl"] for t in winning)
                        
                    if losing:
                        metrics.avg_loss = sum(t["pnl"] for t in losing) / len(losing)
                        metrics.largest_loss = min(t["pnl"] for t in losing)
                        
                    # Profit factor
                    total_wins = sum(t["pnl"] for t in winning) if winning else Decimal("0")
                    total_losses = abs(sum(t["pnl"] for t in losing)) if losing else Decimal("0")
                    if total_losses > 0:
                        metrics.profit_factor = total_wins / total_losses
                        
                    # P&L
                    metrics.realized_pnl = sum(t["pnl"] for t in trades_with_pnl)
                    metrics.cumulative_pnl = metrics.realized_pnl + metrics.unrealized_pnl
                    
            # Cache results
            self._metrics_cache = metrics
            self._cache_timestamp = datetime.utcnow()
            
            self.logger.info(
                "metrics_calculated",
                total_return=float(metrics.total_return),
                sharpe_ratio=float(metrics.sharpe_ratio) if metrics.sharpe_ratio else None,
                max_drawdown=float(metrics.max_drawdown),
                total_trades=metrics.total_trades,
            )
            
            return metrics
            
    async def get_attribution(
        self,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Decimal]:
        """Get P&L attribution by symbol.
        
        Args:
            symbols: List of symbols to analyze (None for all)
            
        Returns:
            Dictionary mapping symbols to their P&L contribution
        """
        async with self._lock:
            if symbols:
                return {s: self.position_pnl[s] for s in symbols if s in self.position_pnl}
            return dict(self.position_pnl)
            
    async def get_rolling_metrics(
        self,
        window_days: int = 30,
    ) -> List[Dict]:
        """Calculate metrics over rolling windows.
        
        Args:
            window_days: Size of rolling window in days
            
        Returns:
            List of metrics dictionaries for each window
        """
        async with self._lock:
            if len(self.equity_curve) < 2:
                return []
                
            rolling_metrics = []
            timestamps, equity_values = zip(*self.equity_curve)
            
            for i in range(len(equity_values)):
                # Get window data
                start_idx = max(0, i - window_days)
                window_equity = equity_values[start_idx:i+1]
                
                if len(window_equity) < 2:
                    continue
                    
                # Calculate window metrics
                window_return = (window_equity[-1] - window_equity[0]) / window_equity[0]
                window_array = np.array([float(e) for e in window_equity])
                
                # Drawdown
                cummax = np.maximum.accumulate(window_array)
                drawdown = (window_array - cummax) / cummax
                max_dd = abs(np.min(drawdown))
                
                rolling_metrics.append({
                    "timestamp": timestamps[i],
                    "return": float(window_return),
                    "max_drawdown": float(max_dd),
                    "equity": float(window_equity[-1]),
                })
                
            return rolling_metrics
            
    async def reset(self) -> None:
        """Reset analyzer state."""
        async with self._lock:
            self.current_capital = self.initial_capital
            self.equity_curve.clear()
            self.trade_history.clear()
            self.daily_pnl.clear()
            self.position_pnl.clear()
            self._metrics_cache = None
            self._cache_timestamp = None
            
            self.logger.info("performance_analyzer_reset")
