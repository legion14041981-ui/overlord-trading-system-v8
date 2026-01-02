"""Advanced signal processing and filtering engine."""
import asyncio
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from collections import deque, defaultdict
import numpy as np

from ..core.models.trading import Signal, SignalType
from ..core.logging.structured_logger import get_logger


class FilterType(Enum):
    """Signal filter types."""
    STRENGTH = "strength"  # Filter by signal strength
    CONFIDENCE = "confidence"  # Filter by confidence level
    VOLUME = "volume"  # Filter by volume confirmation
    CORRELATION = "correlation"  # Filter by cross-asset correlation
    REGIME = "regime"  # Filter by market regime
    TIMING = "timing"  # Filter by market hours/session
    CONFLICT = "conflict"  # Remove conflicting signals
    REDUNDANCY = "redundancy"  # Remove redundant signals
    

@dataclass
class FilterConfig:
    """Configuration for signal filter."""
    filter_type: FilterType
    enabled: bool = True
    min_strength: float = 0.0
    min_confidence: float = 0.0
    min_volume_ratio: float = 1.0
    max_correlation: float = 0.95
    allowed_regimes: List[str] = field(default_factory=list)
    allowed_sessions: List[str] = field(default_factory=list)
    lookback_minutes: int = 60
    

@dataclass
class SignalAggregate:
    """Aggregated signal from multiple sources."""
    symbol: str
    signal_type: SignalType
    strength: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    source_count: int
    sources: List[str]
    timestamp: datetime
    metadata: Dict
    

@dataclass
class SignalMetrics:
    """Performance metrics for signal quality."""
    total_signals: int
    filtered_signals: int
    filter_rate: float
    avg_strength: float
    avg_confidence: float
    signal_distribution: Dict[SignalType, int]
    filter_breakdown: Dict[FilterType, int]
    

class SignalProcessor:
    """Process, filter, and aggregate trading signals."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Filter configurations
        self.filters: Dict[FilterType, FilterConfig] = {
            FilterType.STRENGTH: FilterConfig(
                filter_type=FilterType.STRENGTH,
                min_strength=0.3
            ),
            FilterType.CONFIDENCE: FilterConfig(
                filter_type=FilterType.CONFIDENCE,
                min_confidence=0.5
            ),
            FilterType.VOLUME: FilterConfig(
                filter_type=FilterType.VOLUME,
                min_volume_ratio=1.2,
                enabled=False  # Optional
            ),
            FilterType.CONFLICT: FilterConfig(
                filter_type=FilterType.CONFLICT,
                enabled=True
            ),
            FilterType.REDUNDANCY: FilterConfig(
                filter_type=FilterType.REDUNDANCY,
                lookback_minutes=30,
                enabled=True
            )
        }
        
        # Signal history for filtering
        self._signal_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Volume data for volume filters
        self._volume_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Current market regime
        self._current_regime: str = "normal"
        
        # Performance tracking
        self._metrics = SignalMetrics(
            total_signals=0,
            filtered_signals=0,
            filter_rate=0.0,
            avg_strength=0.0,
            avg_confidence=0.0,
            signal_distribution={},
            filter_breakdown={}
        )
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def configure_filter(self, filter_config: FilterConfig) -> None:
        """Update filter configuration."""
        self.filters[filter_config.filter_type] = filter_config
        self.logger.info(
            "Filter configured",
            filter_type=filter_config.filter_type.value,
            enabled=filter_config.enabled
        )
    
    def set_market_regime(self, regime: str) -> None:
        """Set current market regime for regime-based filtering."""
        self._current_regime = regime
        self.logger.info("Market regime updated", regime=regime)
    
    async def process_signal(
        self,
        signal: Signal,
        volume_data: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """Process and filter a single signal.
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        async with self._lock:
            self._metrics.total_signals += 1
            
            # Apply filters in sequence
            for filter_type, config in self.filters.items():
                if not config.enabled:
                    continue
                
                passed, reason = await self._apply_filter(
                    signal, filter_type, config, volume_data
                )
                
                if not passed:
                    self._metrics.filtered_signals += 1
                    self._metrics.filter_breakdown[filter_type] = \
                        self._metrics.filter_breakdown.get(filter_type, 0) + 1
                    
                    self.logger.debug(
                        "Signal filtered",
                        symbol=signal.symbol,
                        filter_type=filter_type.value,
                        reason=reason
                    )
                    
                    return False, reason
            
            # Signal passed all filters
            self._signal_history[signal.symbol].append(signal)
            
            # Update metrics
            self._metrics.signal_distribution[signal.signal_type] = \
                self._metrics.signal_distribution.get(signal.signal_type, 0) + 1
            
            return True, None
    
    async def _apply_filter(
        self,
        signal: Signal,
        filter_type: FilterType,
        config: FilterConfig,
        volume_data: Optional[Dict]
    ) -> Tuple[bool, Optional[str]]:
        """Apply specific filter to signal."""
        if filter_type == FilterType.STRENGTH:
            return self._filter_by_strength(signal, config)
        
        elif filter_type == FilterType.CONFIDENCE:
            return self._filter_by_confidence(signal, config)
        
        elif filter_type == FilterType.VOLUME:
            return self._filter_by_volume(signal, config, volume_data)
        
        elif filter_type == FilterType.CONFLICT:
            return await self._filter_by_conflict(signal, config)
        
        elif filter_type == FilterType.REDUNDANCY:
            return await self._filter_by_redundancy(signal, config)
        
        elif filter_type == FilterType.REGIME:
            return self._filter_by_regime(signal, config)
        
        elif filter_type == FilterType.TIMING:
            return self._filter_by_timing(signal, config)
        
        return True, None
    
    def _filter_by_strength(self, signal: Signal, config: FilterConfig) -> Tuple[bool, Optional[str]]:
        """Filter signals by minimum strength."""
        if abs(signal.strength) < config.min_strength:
            return False, f"Strength {signal.strength:.3f} below minimum {config.min_strength}"
        return True, None
    
    def _filter_by_confidence(self, signal: Signal, config: FilterConfig) -> Tuple[bool, Optional[str]]:
        """Filter signals by minimum confidence."""
        if signal.confidence < config.min_confidence:
            return False, f"Confidence {signal.confidence:.3f} below minimum {config.min_confidence}"
        return True, None
    
    def _filter_by_volume(self, signal: Signal, config: FilterConfig, volume_data: Optional[Dict]) -> Tuple[bool, Optional[str]]:
        """Filter signals requiring volume confirmation."""
        if not volume_data:
            return True, None  # Skip if no volume data
        
        current_volume = volume_data.get('current_volume', 0)
        avg_volume = volume_data.get('avg_volume', 1)
        
        if avg_volume == 0:
            return True, None
        
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio < config.min_volume_ratio:
            return False, f"Volume ratio {volume_ratio:.2f} below minimum {config.min_volume_ratio}"
        
        return True, None
    
    async def _filter_by_conflict(self, signal: Signal, config: FilterConfig) -> Tuple[bool, Optional[str]]:
        """Filter conflicting signals for same symbol."""
        recent_signals = list(self._signal_history[signal.symbol])
        
        if not recent_signals:
            return True, None
        
        # Check last signal within 5 minutes
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent = [s for s in recent_signals if s.timestamp > cutoff_time]
        
        if not recent:
            return True, None
        
        last_signal = recent[-1]
        
        # Check for conflicting direction
        if signal.signal_type in [SignalType.LONG, SignalType.SHORT]:
            if last_signal.signal_type in [SignalType.LONG, SignalType.SHORT]:
                if signal.signal_type != last_signal.signal_type:
                    # Conflicting direction - only allow if new signal is stronger
                    if abs(signal.strength) <= abs(last_signal.strength):
                        return False, f"Conflicting with stronger recent {last_signal.signal_type.value} signal"
        
        return True, None
    
    async def _filter_by_redundancy(self, signal: Signal, config: FilterConfig) -> Tuple[bool, Optional[str]]:
        """Filter redundant signals (same direction within lookback)."""
        recent_signals = list(self._signal_history[signal.symbol])
        
        if not recent_signals:
            return True, None
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=config.lookback_minutes)
        recent = [s for s in recent_signals if s.timestamp > cutoff_time]
        
        # Check for same signal type recently
        same_type_count = sum(1 for s in recent if s.signal_type == signal.signal_type)
        
        if same_type_count > 0:
            # Allow if significantly stronger than recent
            recent_same = [s for s in recent if s.signal_type == signal.signal_type]
            max_recent_strength = max(abs(s.strength) for s in recent_same)
            
            if abs(signal.strength) <= max_recent_strength * 1.2:  # Must be 20% stronger
                return False, f"Redundant {signal.signal_type.value} signal within {config.lookback_minutes}min"
        
        return True, None
    
    def _filter_by_regime(self, signal: Signal, config: FilterConfig) -> Tuple[bool, Optional[str]]:
        """Filter signals based on market regime."""
        if not config.allowed_regimes:
            return True, None
        
        if self._current_regime not in config.allowed_regimes:
            return False, f"Signal not allowed in {self._current_regime} regime"
        
        return True, None
    
    def _filter_by_timing(self, signal: Signal, config: FilterConfig) -> Tuple[bool, Optional[str]]:
        """Filter signals based on market session/hours."""
        if not config.allowed_sessions:
            return True, None
        
        # Determine current session (simplified)
        hour = datetime.now(timezone.utc).hour
        
        if 13 <= hour < 21:  # US market hours (UTC)
            session = 'us'
        elif 0 <= hour < 9:  # Asian market hours
            session = 'asia'
        elif 7 <= hour < 17:  # European market hours
            session = 'europe'
        else:
            session = 'off_hours'
        
        if session not in config.allowed_sessions:
            return False, f"Signal not allowed during {session} session"
        
        return True, None
    
    async def aggregate_signals(
        self,
        signals: List[Signal],
        symbol: str
    ) -> Optional[SignalAggregate]:
        """Aggregate multiple signals for same symbol."""
        if not signals:
            return None
        
        # Separate by direction
        long_signals = [s for s in signals if s.signal_type == SignalType.LONG]
        short_signals = [s for s in signals if s.signal_type == SignalType.SHORT]
        exit_signals = [s for s in signals if s.signal_type == SignalType.EXIT]
        
        # Determine dominant signal
        long_strength = sum(s.strength for s in long_signals)
        short_strength = sum(abs(s.strength) for s in short_signals)
        exit_strength = sum(s.strength for s in exit_signals)
        
        if exit_strength > max(long_strength, short_strength):
            dominant_type = SignalType.EXIT
            dominant_signals = exit_signals
            net_strength = exit_strength
        elif long_strength > short_strength:
            dominant_type = SignalType.LONG
            dominant_signals = long_signals
            net_strength = long_strength - short_strength
        else:
            dominant_type = SignalType.SHORT
            dominant_signals = short_signals
            net_strength = short_strength - long_strength
        
        # Normalize strength to [-1, 1]
        max_possible = len(signals)
        normalized_strength = net_strength / max(max_possible, 1)
        normalized_strength = max(-1.0, min(1.0, normalized_strength))
        
        # Calculate weighted confidence
        total_weight = sum(abs(s.strength) for s in dominant_signals)
        if total_weight > 0:
            avg_confidence = sum(
                s.confidence * abs(s.strength) for s in dominant_signals
            ) / total_weight
        else:
            avg_confidence = 0.5
        
        # Collect sources
        sources = list(set(s.strategy_id for s in dominant_signals))
        
        return SignalAggregate(
            symbol=symbol,
            signal_type=dominant_type,
            strength=normalized_strength,
            confidence=avg_confidence,
            source_count=len(dominant_signals),
            sources=sources,
            timestamp=datetime.now(timezone.utc),
            metadata={
                'long_count': len(long_signals),
                'short_count': len(short_signals),
                'exit_count': len(exit_signals),
                'raw_strength': net_strength
            }
        )
    
    def get_metrics(self) -> SignalMetrics:
        """Get current signal processing metrics."""
        if self._metrics.total_signals > 0:
            self._metrics.filter_rate = self._metrics.filtered_signals / self._metrics.total_signals
        
        return self._metrics
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self._metrics = SignalMetrics(
            total_signals=0,
            filtered_signals=0,
            filter_rate=0.0,
            avg_strength=0.0,
            avg_confidence=0.0,
            signal_distribution={},
            filter_breakdown={}
        )
        self.logger.info("Signal processor metrics reset")
