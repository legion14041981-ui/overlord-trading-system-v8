"""Metrics Calculator for Advanced Portfolio Performance Metrics.

Provides specialized calculations for:
- Risk-adjusted returns
- Statistical distributions
- Market correlation analysis
- Custom performance indicators
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from ..core.logging import structured_logger


class MetricsCalculator:
    """Calculator for advanced portfolio metrics and statistics.
    
    Features:
    - Information ratio
    - Tracking error
    - Beta and alpha calculation
    - Omega ratio
    - Tail ratio
    - Common sense ratio
    - Rolling correlations
    - Recovery time analysis
    """
    
    def __init__(self, risk_free_rate: Decimal = Decimal("0.02")):
        self.risk_free_rate = risk_free_rate
        self.logger = structured_logger.get_logger(__name__)
        
    @staticmethod
    def calculate_information_ratio(
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
    ) -> Optional[Decimal]:
        """Calculate Information Ratio.
        
        Information Ratio = E[R_p - R_b] / std(R_p - R_b)
        
        Args:
            portfolio_returns: Portfolio returns array
            benchmark_returns: Benchmark returns array
            
        Returns:
            Information ratio or None if calculation not possible
        """
        if len(portfolio_returns) != len(benchmark_returns):
            return None
            
        active_returns = portfolio_returns - benchmark_returns
        tracking_error = np.std(active_returns)
        
        if tracking_error == 0:
            return None
            
        ir = np.mean(active_returns) / tracking_error
        return Decimal(str(ir * np.sqrt(252)))  # Annualized
        
    @staticmethod
    def calculate_tracking_error(
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
    ) -> Optional[Decimal]:
        """Calculate Tracking Error.
        
        Tracking Error = std(R_p - R_b)
        
        Args:
            portfolio_returns: Portfolio returns array
            benchmark_returns: Benchmark returns array
            
        Returns:
            Annualized tracking error
        """
        if len(portfolio_returns) != len(benchmark_returns):
            return None
            
        active_returns = portfolio_returns - benchmark_returns
        te = np.std(active_returns) * np.sqrt(252)  # Annualized
        return Decimal(str(te))
        
    @staticmethod
    def calculate_beta(
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
    ) -> Optional[Decimal]:
        """Calculate portfolio beta.
        
        Beta = Cov(R_p, R_b) / Var(R_b)
        
        Args:
            portfolio_returns: Portfolio returns array
            benchmark_returns: Benchmark returns array
            
        Returns:
            Portfolio beta
        """
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return None
            
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        
        if benchmark_variance == 0:
            return None
            
        beta = covariance / benchmark_variance
        return Decimal(str(beta))
        
    @staticmethod
    def calculate_alpha(
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        risk_free_rate: Decimal,
    ) -> Optional[Decimal]:
        """Calculate Jensen's alpha.
        
        Alpha = R_p - [R_f + beta * (R_b - R_f)]
        
        Args:
            portfolio_returns: Portfolio returns array
            benchmark_returns: Benchmark returns array
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Annualized alpha
        """
        beta = MetricsCalculator.calculate_beta(portfolio_returns, benchmark_returns)
        if beta is None:
            return None
            
        portfolio_return = np.mean(portfolio_returns) * 252  # Annualized
        benchmark_return = np.mean(benchmark_returns) * 252  # Annualized
        rf = float(risk_free_rate)
        
        alpha = portfolio_return - (rf + float(beta) * (benchmark_return - rf))
        return Decimal(str(alpha))
        
    @staticmethod
    def calculate_omega_ratio(
        returns: np.ndarray,
        threshold: float = 0.0,
    ) -> Optional[Decimal]:
        """Calculate Omega ratio.
        
        Omega = E[max(R - threshold, 0)] / E[max(threshold - R, 0)]
        
        Args:
            returns: Returns array
            threshold: Return threshold (default 0)
            
        Returns:
            Omega ratio
        """
        if len(returns) == 0:
            return None
            
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns < threshold]
        
        if len(losses) == 0 or np.sum(losses) == 0:
            return None
            
        omega = np.sum(gains) / np.sum(losses)
        return Decimal(str(omega))
        
    @staticmethod
    def calculate_tail_ratio(
        returns: np.ndarray,
        percentile: float = 95.0,
    ) -> Optional[Decimal]:
        """Calculate Tail Ratio.
        
        Tail Ratio = |95th percentile| / |5th percentile|
        
        Args:
            returns: Returns array
            percentile: Percentile for calculation (default 95)
            
        Returns:
            Tail ratio
        """
        if len(returns) < 10:
            return None
            
        upper_tail = np.percentile(returns, percentile)
        lower_tail = np.percentile(returns, 100 - percentile)
        
        if lower_tail == 0:
            return None
            
        tail_ratio = abs(upper_tail / lower_tail)
        return Decimal(str(tail_ratio))
        
    @staticmethod
    def calculate_common_sense_ratio(
        returns: np.ndarray,
        risk_free_rate: Decimal,
    ) -> Optional[Decimal]:
        """Calculate Common Sense Ratio.
        
        CSR = (Total Return - Risk Free Rate) / Max Drawdown
        
        Args:
            returns: Returns array
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Common sense ratio
        """
        if len(returns) == 0:
            return None
            
        # Total return
        total_return = (1 + returns).prod() - 1
        
        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_dd = abs(np.min(drawdown))
        
        if max_dd == 0:
            return None
            
        # Annualize
        periods_per_year = 252 / len(returns)
        annual_return = (1 + total_return) ** periods_per_year - 1
        
        csr = (annual_return - float(risk_free_rate)) / max_dd
        return Decimal(str(csr))
        
    @staticmethod
    def calculate_rolling_correlation(
        returns1: np.ndarray,
        returns2: np.ndarray,
        window: int = 30,
    ) -> List[Tuple[int, Decimal]]:
        """Calculate rolling correlation between two return series.
        
        Args:
            returns1: First returns array
            returns2: Second returns array
            window: Rolling window size
            
        Returns:
            List of (index, correlation) tuples
        """
        if len(returns1) != len(returns2) or len(returns1) < window:
            return []
            
        correlations = []
        for i in range(window, len(returns1)):
            window_r1 = returns1[i-window:i]
            window_r2 = returns2[i-window:i]
            
            if len(window_r1) > 1 and len(window_r2) > 1:
                corr = np.corrcoef(window_r1, window_r2)[0, 1]
                correlations.append((i, Decimal(str(corr))))
                
        return correlations
        
    @staticmethod
    def calculate_recovery_time(
        equity_curve: np.ndarray,
        timestamps: List[datetime],
    ) -> Dict[str, timedelta]:
        """Calculate recovery times from drawdowns.
        
        Args:
            equity_curve: Array of equity values
            timestamps: Corresponding timestamps
            
        Returns:
            Dictionary with recovery statistics
        """
        if len(equity_curve) < 2:
            return {}
            
        # Find peaks and troughs
        cummax = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - cummax) / cummax
        
        # Identify drawdown periods
        in_drawdown = drawdown < -0.01  # More than 1% drawdown
        
        recovery_times = []
        start_idx = None
        
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                start_idx = i
            elif not is_dd and start_idx is not None:
                # End of drawdown
                recovery_time = timestamps[i] - timestamps[start_idx]
                recovery_times.append(recovery_time)
                start_idx = None
                
        if not recovery_times:
            return {}
            
        return {
            "avg_recovery": sum(recovery_times, timedelta()) / len(recovery_times),
            "max_recovery": max(recovery_times),
            "min_recovery": min(recovery_times),
            "total_drawdown_periods": len(recovery_times),
        }
        
    @staticmethod
    def calculate_skewness(returns: np.ndarray) -> Optional[Decimal]:
        """Calculate return distribution skewness.
        
        Args:
            returns: Returns array
            
        Returns:
            Skewness value
        """
        if len(returns) < 3:
            return None
            
        skew = stats.skew(returns)
        return Decimal(str(skew))
        
    @staticmethod
    def calculate_kurtosis(returns: np.ndarray) -> Optional[Decimal]:
        """Calculate return distribution kurtosis (excess).
        
        Args:
            returns: Returns array
            
        Returns:
            Excess kurtosis value
        """
        if len(returns) < 4:
            return None
            
        kurt = stats.kurtosis(returns)
        return Decimal(str(kurt))
        
    @staticmethod
    def calculate_value_at_risk(
        returns: np.ndarray,
        confidence_level: float = 0.95,
        method: str = "historical",
    ) -> Optional[Decimal]:
        """Calculate Value at Risk (VaR).
        
        Args:
            returns: Returns array
            confidence_level: Confidence level (default 95%)
            method: 'historical', 'parametric', or 'modified'
            
        Returns:
            VaR value (positive number representing loss)
        """
        if len(returns) == 0:
            return None
            
        if method == "historical":
            var = np.percentile(returns, (1 - confidence_level) * 100)
        elif method == "parametric":
            mean = np.mean(returns)
            std = np.std(returns)
            var = mean - stats.norm.ppf(confidence_level) * std
        elif method == "modified":
            # Cornish-Fisher VaR (accounts for skewness and kurtosis)
            mean = np.mean(returns)
            std = np.std(returns)
            skew = stats.skew(returns)
            kurt = stats.kurtosis(returns)
            
            z = stats.norm.ppf(confidence_level)
            z_cf = (z +
                   (z**2 - 1) * skew / 6 +
                   (z**3 - 3*z) * kurt / 24 -
                   (2*z**3 - 5*z) * skew**2 / 36)
            
            var = mean - z_cf * std
        else:
            return None
            
        return Decimal(str(abs(var)))
        
    @staticmethod
    def calculate_conditional_var(
        returns: np.ndarray,
        confidence_level: float = 0.95,
    ) -> Optional[Decimal]:
        """Calculate Conditional Value at Risk (CVaR/Expected Shortfall).
        
        Args:
            returns: Returns array
            confidence_level: Confidence level (default 95%)
            
        Returns:
            CVaR value (positive number representing expected loss)
        """
        if len(returns) == 0:
            return None
            
        var = np.percentile(returns, (1 - confidence_level) * 100)
        cvar_returns = returns[returns <= var]
        
        if len(cvar_returns) == 0:
            return None
            
        cvar = np.mean(cvar_returns)
        return Decimal(str(abs(cvar)))
        
    @staticmethod
    def calculate_ulcer_index(
        equity_curve: np.ndarray,
    ) -> Optional[Decimal]:
        """Calculate Ulcer Index (downside volatility measure).
        
        Args:
            equity_curve: Array of equity values
            
        Returns:
            Ulcer Index value
        """
        if len(equity_curve) < 2:
            return None
            
        cummax = np.maximum.accumulate(equity_curve)
        drawdown_pct = 100 * (equity_curve - cummax) / cummax
        
        ulcer = np.sqrt(np.mean(drawdown_pct ** 2))
        return Decimal(str(ulcer))
        
    async def calculate_all_metrics(
        self,
        returns: np.ndarray,
        equity_curve: Optional[np.ndarray] = None,
        benchmark_returns: Optional[np.ndarray] = None,
        timestamps: Optional[List[datetime]] = None,
    ) -> Dict:
        """Calculate comprehensive set of metrics.
        
        Args:
            returns: Returns array
            equity_curve: Equity curve array (optional)
            benchmark_returns: Benchmark returns (optional)
            timestamps: Timestamps for equity curve (optional)
            
        Returns:
            Dictionary with all calculated metrics
        """
        metrics = {}
        
        # Distribution metrics
        metrics["skewness"] = self.calculate_skewness(returns)
        metrics["kurtosis"] = self.calculate_kurtosis(returns)
        
        # Risk metrics
        metrics["var_95_hist"] = self.calculate_value_at_risk(returns, 0.95, "historical")
        metrics["var_95_param"] = self.calculate_value_at_risk(returns, 0.95, "parametric")
        metrics["var_99_hist"] = self.calculate_value_at_risk(returns, 0.99, "historical")
        metrics["cvar_95"] = self.calculate_conditional_var(returns, 0.95)
        metrics["cvar_99"] = self.calculate_conditional_var(returns, 0.99)
        
        # Advanced ratios
        metrics["omega_ratio"] = self.calculate_omega_ratio(returns)
        metrics["tail_ratio"] = self.calculate_tail_ratio(returns)
        metrics["common_sense_ratio"] = self.calculate_common_sense_ratio(
            returns, self.risk_free_rate
        )
        
        # Equity curve metrics
        if equity_curve is not None:
            metrics["ulcer_index"] = self.calculate_ulcer_index(equity_curve)
            
            if timestamps is not None:
                recovery_stats = self.calculate_recovery_time(equity_curve, timestamps)
                metrics["recovery_stats"] = recovery_stats
                
        # Benchmark comparison
        if benchmark_returns is not None:
            metrics["beta"] = self.calculate_beta(returns, benchmark_returns)
            metrics["alpha"] = self.calculate_alpha(returns, benchmark_returns, self.risk_free_rate)
            metrics["information_ratio"] = self.calculate_information_ratio(returns, benchmark_returns)
            metrics["tracking_error"] = self.calculate_tracking_error(returns, benchmark_returns)
            
        # Convert to serializable format
        serializable_metrics = {}
        for key, value in metrics.items():
            if isinstance(value, Decimal):
                serializable_metrics[key] = float(value)
            elif isinstance(value, dict):
                serializable_metrics[key] = {
                    k: str(v) if isinstance(v, timedelta) else v
                    for k, v in value.items()
                }
            else:
                serializable_metrics[key] = value
                
        self.logger.info(
            "advanced_metrics_calculated",
            num_metrics=len(serializable_metrics),
        )
        
        return serializable_metrics
