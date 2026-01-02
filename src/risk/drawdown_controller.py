"""Drawdown monitoring and control system."""
import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections import deque

from ..core.models import Position
from ..core.logging.structured_logger import get_logger


@dataclass
class DrawdownMetrics:
    """Drawdown analysis metrics."""
    current_drawdown: float
    current_drawdown_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    max_drawdown_date: datetime
    peak_value: float
    current_value: float
    drawdown_duration_days: int
    recovery_date: Optional[datetime]
    underwater_periods: List[Dict]
    

@dataclass
class DrawdownAlert:
    """Drawdown threshold breach alert."""
    alert_type: str  # 'warning', 'critical', 'emergency'
    current_drawdown_pct: float
    threshold_pct: float
    action_required: str
    timestamp: datetime
    portfolio_value: float
    message: str


class DrawdownController:
    """Monitor and control portfolio drawdowns."""
    
    def __init__(self, 
                 warning_threshold: float = 0.05,  # 5%
                 critical_threshold: float = 0.10,  # 10%
                 emergency_threshold: float = 0.15,  # 15%
                 max_underwater_days: int = 30):
        """
        Args:
            warning_threshold: Drawdown % that triggers warning
            critical_threshold: Drawdown % that triggers critical alert
            emergency_threshold: Drawdown % that triggers emergency stop
            max_underwater_days: Max days allowed in drawdown before intervention
        """
        self.logger = get_logger(__name__)
        
        # Thresholds
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.emergency_threshold = emergency_threshold
        self.max_underwater_days = max_underwater_days
        
        # Historical tracking
        self._equity_curve: deque = deque(maxlen=10000)  # Store last 10k values
        self._peak_value: float = 0.0
        self._peak_date: datetime = datetime.now(timezone.utc)
        self._max_drawdown: float = 0.0
        self._max_drawdown_pct: float = 0.0
        self._max_drawdown_date: Optional[datetime] = None
        
        # Current state
        self._current_drawdown_start: Optional[datetime] = None
        self._last_alert_level: Optional[str] = None
        
        # Alert callbacks
        self._alert_callbacks: List[Callable] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def register_alert_callback(self, callback: Callable) -> None:
        """Register callback for drawdown alerts."""
        self._alert_callbacks.append(callback)
    
    async def update_portfolio_value(self, portfolio_value: float) -> DrawdownMetrics:
        """Update with current portfolio value and calculate drawdown metrics."""
        async with self._lock:
            timestamp = datetime.now(timezone.utc)
            
            # Store in equity curve
            self._equity_curve.append({
                'timestamp': timestamp,
                'value': portfolio_value
            })
            
            # Update peak if new high
            if portfolio_value > self._peak_value:
                self._peak_value = portfolio_value
                self._peak_date = timestamp
                self._current_drawdown_start = None  # Exited drawdown
            
            # Calculate current drawdown
            if self._peak_value > 0:
                current_drawdown = self._peak_value - portfolio_value
                current_drawdown_pct = current_drawdown / self._peak_value
            else:
                current_drawdown = 0.0
                current_drawdown_pct = 0.0
            
            # Track drawdown start
            if current_drawdown > 0 and self._current_drawdown_start is None:
                self._current_drawdown_start = timestamp
            
            # Update max drawdown
            if current_drawdown > self._max_drawdown:
                self._max_drawdown = current_drawdown
                self._max_drawdown_pct = current_drawdown_pct
                self._max_drawdown_date = timestamp
            
            # Calculate underwater duration
            if self._current_drawdown_start:
                underwater_days = (timestamp - self._current_drawdown_start).days
            else:
                underwater_days = 0
            
            # Check thresholds and generate alerts
            await self._check_thresholds(current_drawdown_pct, portfolio_value)
            
            # Find underwater periods
            underwater_periods = self._calculate_underwater_periods()
            
            # Determine recovery date
            recovery_date = None
            if current_drawdown == 0 and self._max_drawdown > 0:
                recovery_date = timestamp
            
            metrics = DrawdownMetrics(
                current_drawdown=current_drawdown,
                current_drawdown_pct=current_drawdown_pct,
                max_drawdown=self._max_drawdown,
                max_drawdown_pct=self._max_drawdown_pct,
                max_drawdown_date=self._max_drawdown_date,
                peak_value=self._peak_value,
                current_value=portfolio_value,
                drawdown_duration_days=underwater_days,
                recovery_date=recovery_date,
                underwater_periods=underwater_periods
            )
            
            return metrics
    
    async def _check_thresholds(self, drawdown_pct: float, portfolio_value: float) -> None:
        """Check drawdown thresholds and generate alerts."""
        alert = None
        
        if drawdown_pct >= self.emergency_threshold:
            if self._last_alert_level != 'emergency':
                alert = DrawdownAlert(
                    alert_type='emergency',
                    current_drawdown_pct=drawdown_pct,
                    threshold_pct=self.emergency_threshold,
                    action_required='STOP_ALL_TRADING',
                    timestamp=datetime.now(timezone.utc),
                    portfolio_value=portfolio_value,
                    message=f"EMERGENCY: Drawdown {drawdown_pct:.2%} exceeded emergency threshold {self.emergency_threshold:.2%}"
                )
                self._last_alert_level = 'emergency'
                
        elif drawdown_pct >= self.critical_threshold:
            if self._last_alert_level not in ['emergency', 'critical']:
                alert = DrawdownAlert(
                    alert_type='critical',
                    current_drawdown_pct=drawdown_pct,
                    threshold_pct=self.critical_threshold,
                    action_required='REDUCE_EXPOSURE',
                    timestamp=datetime.now(timezone.utc),
                    portfolio_value=portfolio_value,
                    message=f"CRITICAL: Drawdown {drawdown_pct:.2%} exceeded critical threshold {self.critical_threshold:.2%}"
                )
                self._last_alert_level = 'critical'
                
        elif drawdown_pct >= self.warning_threshold:
            if self._last_alert_level not in ['emergency', 'critical', 'warning']:
                alert = DrawdownAlert(
                    alert_type='warning',
                    current_drawdown_pct=drawdown_pct,
                    threshold_pct=self.warning_threshold,
                    action_required='MONITOR_CLOSELY',
                    timestamp=datetime.now(timezone.utc),
                    portfolio_value=portfolio_value,
                    message=f"WARNING: Drawdown {drawdown_pct:.2%} exceeded warning threshold {self.warning_threshold:.2%}"
                )
                self._last_alert_level = 'warning'
        else:
            # Reset alert level if drawdown is below warning
            self._last_alert_level = None
        
        if alert:
            self.logger.warning(
                "Drawdown alert",
                alert_type=alert.alert_type,
                drawdown_pct=alert.current_drawdown_pct,
                action=alert.action_required
            )
            
            # Notify callbacks
            await self._notify_alert_callbacks(alert)
    
    async def _notify_alert_callbacks(self, alert: DrawdownAlert) -> None:
        """Notify registered callbacks of drawdown alert."""
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error("Alert callback error", error=e)
    
    def _calculate_underwater_periods(self) -> List[Dict]:
        """Calculate all underwater (drawdown) periods from equity curve."""
        if len(self._equity_curve) < 2:
            return []
        
        underwater_periods = []
        current_period = None
        running_peak = 0.0
        
        for point in self._equity_curve:
            value = point['value']
            timestamp = point['timestamp']
            
            if value > running_peak:
                running_peak = value
                
                # End current underwater period
                if current_period:
                    current_period['end'] = timestamp
                    current_period['duration_days'] = (
                        current_period['end'] - current_period['start']
                    ).days
                    underwater_periods.append(current_period)
                    current_period = None
            
            elif value < running_peak:
                # In drawdown
                drawdown = running_peak - value
                drawdown_pct = drawdown / running_peak if running_peak > 0 else 0
                
                if current_period is None:
                    # Start new underwater period
                    current_period = {
                        'start': timestamp,
                        'peak_value': running_peak,
                        'max_drawdown': drawdown,
                        'max_drawdown_pct': drawdown_pct
                    }
                else:
                    # Update current period
                    if drawdown > current_period['max_drawdown']:
                        current_period['max_drawdown'] = drawdown
                        current_period['max_drawdown_pct'] = drawdown_pct
        
        # If still in drawdown, add current period
        if current_period:
            current_period['end'] = None  # Ongoing
            current_period['duration_days'] = (
                datetime.now(timezone.utc) - current_period['start']
            ).days
            underwater_periods.append(current_period)
        
        return underwater_periods
    
    async def get_drawdown_statistics(self) -> Dict:
        """Get comprehensive drawdown statistics."""
        async with self._lock:
            underwater_periods = self._calculate_underwater_periods()
            
            if not underwater_periods:
                return {
                    'total_underwater_periods': 0,
                    'avg_drawdown_pct': 0.0,
                    'avg_underwater_days': 0,
                    'max_underwater_days': 0,
                    'current_underwater_days': 0,
                    'recovery_rate': 0.0
                }
            
            # Calculate statistics
            completed_periods = [p for p in underwater_periods if p['end'] is not None]
            
            avg_drawdown = sum(p['max_drawdown_pct'] for p in underwater_periods) / len(underwater_periods)
            avg_duration = sum(p['duration_days'] for p in underwater_periods) / len(underwater_periods)
            max_duration = max(p['duration_days'] for p in underwater_periods)
            
            # Current underwater status
            current_period = next((p for p in underwater_periods if p['end'] is None), None)
            current_underwater_days = current_period['duration_days'] if current_period else 0
            
            # Recovery rate (% of periods that recovered)
            recovery_rate = len(completed_periods) / len(underwater_periods) if underwater_periods else 0
            
            return {
                'total_underwater_periods': len(underwater_periods),
                'avg_drawdown_pct': avg_drawdown,
                'avg_underwater_days': avg_duration,
                'max_underwater_days': max_duration,
                'current_underwater_days': current_underwater_days,
                'recovery_rate': recovery_rate,
                'max_drawdown_all_time': self._max_drawdown_pct,
                'current_peak': self._peak_value
            }
    
    async def should_stop_trading(self, current_value: float) -> bool:
        """Determine if trading should be stopped due to drawdown."""
        if self._peak_value == 0:
            return False
        
        current_drawdown_pct = (self._peak_value - current_value) / self._peak_value
        
        # Emergency stop if threshold exceeded
        if current_drawdown_pct >= self.emergency_threshold:
            return True
        
        # Stop if underwater too long
        if self._current_drawdown_start:
            underwater_days = (datetime.now(timezone.utc) - self._current_drawdown_start).days
            if underwater_days >= self.max_underwater_days:
                self.logger.warning(
                    "Stop trading due to prolonged drawdown",
                    underwater_days=underwater_days,
                    max_days=self.max_underwater_days
                )
                return True
        
        return False
    
    async def calculate_position_size_multiplier(self, current_value: float) -> float:
        """Calculate position size multiplier based on drawdown.
        
        Reduces position sizing during drawdowns to protect capital.
        Returns multiplier between 0.0 and 1.0.
        """
        if self._peak_value == 0:
            return 1.0
        
        current_drawdown_pct = (self._peak_value - current_value) / self._peak_value
        
        if current_drawdown_pct <= 0:
            return 1.0  # No drawdown, full size
        
        elif current_drawdown_pct < self.warning_threshold:
            return 1.0  # Minor drawdown, full size
        
        elif current_drawdown_pct < self.critical_threshold:
            # Linear reduction from 1.0 to 0.5
            reduction_range = self.critical_threshold - self.warning_threshold
            drawdown_range = current_drawdown_pct - self.warning_threshold
            multiplier = 1.0 - 0.5 * (drawdown_range / reduction_range)
            return max(0.5, multiplier)
        
        elif current_drawdown_pct < self.emergency_threshold:
            # Linear reduction from 0.5 to 0.25
            reduction_range = self.emergency_threshold - self.critical_threshold
            drawdown_range = current_drawdown_pct - self.critical_threshold
            multiplier = 0.5 - 0.25 * (drawdown_range / reduction_range)
            return max(0.25, multiplier)
        
        else:
            # Emergency level - minimal sizing
            return 0.1
    
    def reset_peak(self, new_peak: float) -> None:
        """Manually reset peak value (e.g., after capital injection)."""
        self._peak_value = new_peak
        self._peak_date = datetime.now(timezone.utc)
        self._current_drawdown_start = None
        self.logger.info("Peak value reset", new_peak=new_peak)
