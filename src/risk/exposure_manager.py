"""Exposure management and limit enforcement."""
import asyncio
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from collections import defaultdict

from ..core.models import Position, Order, OrderSide
from ..core.logging.structured_logger import get_logger


@dataclass
class ExposureLimits:
    """Risk limits configuration."""
    # Portfolio-level limits
    max_portfolio_value: Optional[float] = None
    max_gross_exposure: Optional[float] = None
    max_net_exposure: Optional[float] = None
    max_leverage: Optional[float] = None
    
    # Position-level limits
    max_position_size: Optional[float] = None  # Per position
    max_position_concentration: float = 0.20  # % of portfolio
    
    # Symbol-level limits
    symbol_limits: Dict[str, float] = field(default_factory=dict)
    
    # Sector/category limits
    sector_limits: Dict[str, float] = field(default_factory=dict)
    
    # Venue limits
    venue_limits: Dict[str, float] = field(default_factory=dict)
    
    # Order limits
    max_order_value: Optional[float] = None
    max_orders_per_minute: int = 100
    max_orders_per_day: int = 10000
    

@dataclass
class ExposureMetrics:
    """Current exposure metrics."""
    gross_exposure: float
    net_exposure: float
    long_exposure: float
    short_exposure: float
    leverage: float
    portfolio_value: float
    position_count: int
    largest_position_pct: float
    sector_exposures: Dict[str, float]
    venue_exposures: Dict[str, float]
    

@dataclass
class LimitViolation:
    """Risk limit violation."""
    limit_type: str
    current_value: float
    limit_value: float
    symbol: Optional[str]
    action: str  # 'reject_order', 'reduce_position', 'warning'
    timestamp: datetime
    message: str


class ExposureManager:
    """Manage and enforce position and portfolio exposure limits."""
    
    def __init__(self, 
                 limits: ExposureLimits,
                 capital: float = 100000.0):
        """
        Args:
            limits: Exposure limits configuration
            capital: Starting capital for portfolio
        """
        self.limits = limits
        self.capital = capital
        self.logger = get_logger(__name__)
        
        # Symbol to sector mapping (can be loaded from config)
        self._symbol_sectors: Dict[str, str] = {}
        
        # Order tracking for rate limits
        self._order_count_minute: int = 0
        self._order_count_day: int = 0
        self._minute_reset_time: datetime = datetime.now(timezone.utc)
        self._day_reset_time: datetime = datetime.now(timezone.utc)
        
        # Blocked symbols (temporary risk restrictions)
        self._blocked_symbols: Set[str] = set()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def set_symbol_sector(self, symbol: str, sector: str) -> None:
        """Map symbol to sector for sector exposure tracking."""
        self._symbol_sectors[symbol] = sector
    
    def block_symbol(self, symbol: str, reason: str) -> None:
        """Temporarily block trading for a symbol."""
        self._blocked_symbols.add(symbol)
        self.logger.warning(f"Symbol blocked: {symbol}", reason=reason)
    
    def unblock_symbol(self, symbol: str) -> None:
        """Remove trading block for a symbol."""
        if symbol in self._blocked_symbols:
            self._blocked_symbols.remove(symbol)
            self.logger.info(f"Symbol unblocked: {symbol}")
    
    async def check_order_allowed(self, 
                                 order: Order, 
                                 positions: List[Position]) -> Optional[LimitViolation]:
        """Check if order violates any exposure limits.
        
        Returns:
            LimitViolation if order should be rejected, None if allowed
        """
        async with self._lock:
            # Check if symbol is blocked
            if order.symbol in self._blocked_symbols:
                return LimitViolation(
                    limit_type='symbol_blocked',
                    current_value=0,
                    limit_value=0,
                    symbol=order.symbol,
                    action='reject_order',
                    timestamp=datetime.now(timezone.utc),
                    message=f"Symbol {order.symbol} is temporarily blocked"
                )
            
            # Check order rate limits
            violation = await self._check_order_rate_limits()
            if violation:
                return violation
            
            # Check order value limit
            order_value = float(order.quantity * order.price) if order.price else 0
            if self.limits.max_order_value and order_value > self.limits.max_order_value:
                return LimitViolation(
                    limit_type='max_order_value',
                    current_value=order_value,
                    limit_value=self.limits.max_order_value,
                    symbol=order.symbol,
                    action='reject_order',
                    timestamp=datetime.now(timezone.utc),
                    message=f"Order value ${order_value:,.2f} exceeds limit ${self.limits.max_order_value:,.2f}"
                )
            
            # Simulate position after order
            simulated_positions = self._simulate_order_fill(order, positions)
            
            # Check position-level limits
            violation = await self._check_position_limits(order.symbol, simulated_positions)
            if violation:
                return violation
            
            # Check portfolio-level limits
            violation = await self._check_portfolio_limits(simulated_positions)
            if violation:
                return violation
            
            # Check symbol-specific limits
            violation = await self._check_symbol_limits(order.symbol, simulated_positions)
            if violation:
                return violation
            
            # Check sector limits
            violation = await self._check_sector_limits(simulated_positions)
            if violation:
                return violation
            
            # Check venue limits
            violation = await self._check_venue_limits(order.venue, simulated_positions)
            if violation:
                return violation
            
            # All checks passed
            return None
    
    async def _check_order_rate_limits(self) -> Optional[LimitViolation]:
        """Check order rate limits."""
        now = datetime.now(timezone.utc)
        
        # Reset minute counter
        if (now - self._minute_reset_time).total_seconds() >= 60:
            self._order_count_minute = 0
            self._minute_reset_time = now
        
        # Reset day counter
        if (now - self._day_reset_time).days >= 1:
            self._order_count_day = 0
            self._day_reset_time = now
        
        # Check minute limit
        if self._order_count_minute >= self.limits.max_orders_per_minute:
            return LimitViolation(
                limit_type='order_rate_minute',
                current_value=self._order_count_minute,
                limit_value=self.limits.max_orders_per_minute,
                symbol=None,
                action='reject_order',
                timestamp=now,
                message=f"Order rate limit exceeded: {self._order_count_minute} orders/minute"
            )
        
        # Check day limit
        if self._order_count_day >= self.limits.max_orders_per_day:
            return LimitViolation(
                limit_type='order_rate_day',
                current_value=self._order_count_day,
                limit_value=self.limits.max_orders_per_day,
                symbol=None,
                action='reject_order',
                timestamp=now,
                message=f"Daily order limit exceeded: {self._order_count_day} orders/day"
            )
        
        # Increment counters
        self._order_count_minute += 1
        self._order_count_day += 1
        
        return None
    
    def _simulate_order_fill(self, order: Order, positions: List[Position]) -> List[Position]:
        """Simulate position after order fill."""
        simulated = [p for p in positions if p.symbol != order.symbol or p.venue != order.venue]
        
        # Find existing position
        existing = next(
            (p for p in positions if p.symbol == order.symbol and p.venue == order.venue),
            None
        )
        
        if existing:
            # Simulate position update
            new_quantity = existing.quantity
            if order.side == OrderSide.BUY:
                new_quantity += order.quantity
            else:
                new_quantity -= order.quantity
            
            if new_quantity != 0:
                simulated_position = Position(
                    symbol=order.symbol,
                    venue=order.venue,
                    strategy_id=order.strategy_id,
                    quantity=new_quantity,
                    average_entry_price=existing.average_entry_price,
                    realized_pnl=existing.realized_pnl,
                    unrealized_pnl=existing.unrealized_pnl,
                    opened_at=existing.opened_at
                )
                simulated.append(simulated_position)
        else:
            # New position
            quantity = order.quantity if order.side == OrderSide.BUY else -order.quantity
            simulated_position = Position(
                symbol=order.symbol,
                venue=order.venue,
                strategy_id=order.strategy_id,
                quantity=quantity,
                average_entry_price=order.price or Decimal('0'),
                realized_pnl=Decimal('0'),
                unrealized_pnl=Decimal('0'),
                opened_at=datetime.now(timezone.utc)
            )
            simulated.append(simulated_position)
        
        return simulated
    
    async def _check_position_limits(self, symbol: str, positions: List[Position]) -> Optional[LimitViolation]:
        """Check position-level limits."""
        position = next((p for p in positions if p.symbol == symbol), None)
        if not position:
            return None
        
        # Calculate position value
        position_value = abs(float(position.quantity * position.average_entry_price))
        
        # Check max position size
        if self.limits.max_position_size and position_value > self.limits.max_position_size:
            return LimitViolation(
                limit_type='max_position_size',
                current_value=position_value,
                limit_value=self.limits.max_position_size,
                symbol=symbol,
                action='reject_order',
                timestamp=datetime.now(timezone.utc),
                message=f"Position size ${position_value:,.2f} exceeds limit ${self.limits.max_position_size:,.2f}"
            )
        
        # Check position concentration
        metrics = await self.calculate_exposure_metrics(positions)
        position_pct = position_value / max(metrics.portfolio_value, 1.0)
        
        if position_pct > self.limits.max_position_concentration:
            return LimitViolation(
                limit_type='position_concentration',
                current_value=position_pct,
                limit_value=self.limits.max_position_concentration,
                symbol=symbol,
                action='reject_order',
                timestamp=datetime.now(timezone.utc),
                message=f"Position concentration {position_pct:.2%} exceeds limit {self.limits.max_position_concentration:.2%}"
            )
        
        return None
    
    async def _check_portfolio_limits(self, positions: List[Position]) -> Optional[LimitViolation]:
        """Check portfolio-level limits."""
        metrics = await self.calculate_exposure_metrics(positions)
        
        # Check gross exposure
        if self.limits.max_gross_exposure and metrics.gross_exposure > self.limits.max_gross_exposure:
            return LimitViolation(
                limit_type='max_gross_exposure',
                current_value=metrics.gross_exposure,
                limit_value=self.limits.max_gross_exposure,
                symbol=None,
                action='reject_order',
                timestamp=datetime.now(timezone.utc),
                message=f"Gross exposure ${metrics.gross_exposure:,.2f} exceeds limit ${self.limits.max_gross_exposure:,.2f}"
            )
        
        # Check net exposure
        if self.limits.max_net_exposure and abs(metrics.net_exposure) > self.limits.max_net_exposure:
            return LimitViolation(
                limit_type='max_net_exposure',
                current_value=abs(metrics.net_exposure),
                limit_value=self.limits.max_net_exposure,
                symbol=None,
                action='reject_order',
                timestamp=datetime.now(timezone.utc),
                message=f"Net exposure ${abs(metrics.net_exposure):,.2f} exceeds limit ${self.limits.max_net_exposure:,.2f}"
            )
        
        # Check leverage
        if self.limits.max_leverage and metrics.leverage > self.limits.max_leverage:
            return LimitViolation(
                limit_type='max_leverage',
                current_value=metrics.leverage,
                limit_value=self.limits.max_leverage,
                symbol=None,
                action='reject_order',
                timestamp=datetime.now(timezone.utc),
                message=f"Leverage {metrics.leverage:.2f}x exceeds limit {self.limits.max_leverage:.2f}x"
            )
        
        return None
    
    async def _check_symbol_limits(self, symbol: str, positions: List[Position]) -> Optional[LimitViolation]:
        """Check symbol-specific limits."""
        if symbol not in self.limits.symbol_limits:
            return None
        
        position = next((p for p in positions if p.symbol == symbol), None)
        if not position:
            return None
        
        position_value = abs(float(position.quantity * position.average_entry_price))
        limit = self.limits.symbol_limits[symbol]
        
        if position_value > limit:
            return LimitViolation(
                limit_type='symbol_limit',
                current_value=position_value,
                limit_value=limit,
                symbol=symbol,
                action='reject_order',
                timestamp=datetime.now(timezone.utc),
                message=f"Symbol {symbol} exposure ${position_value:,.2f} exceeds limit ${limit:,.2f}"
            )
        
        return None
    
    async def _check_sector_limits(self, positions: List[Position]) -> Optional[LimitViolation]:
        """Check sector exposure limits."""
        if not self.limits.sector_limits:
            return None
        
        # Calculate sector exposures
        sector_exposures: Dict[str, float] = defaultdict(float)
        
        for position in positions:
            sector = self._symbol_sectors.get(position.symbol, 'unknown')
            position_value = abs(float(position.quantity * position.average_entry_price))
            sector_exposures[sector] += position_value
        
        # Check limits
        for sector, exposure in sector_exposures.items():
            if sector in self.limits.sector_limits:
                limit = self.limits.sector_limits[sector]
                if exposure > limit:
                    return LimitViolation(
                        limit_type='sector_limit',
                        current_value=exposure,
                        limit_value=limit,
                        symbol=None,
                        action='reject_order',
                        timestamp=datetime.now(timezone.utc),
                        message=f"Sector {sector} exposure ${exposure:,.2f} exceeds limit ${limit:,.2f}"
                    )
        
        return None
    
    async def _check_venue_limits(self, venue: str, positions: List[Position]) -> Optional[LimitViolation]:
        """Check venue exposure limits."""
        if venue not in self.limits.venue_limits:
            return None
        
        # Calculate venue exposure
        venue_exposure = sum(
            abs(float(p.quantity * p.average_entry_price))
            for p in positions if p.venue == venue
        )
        
        limit = self.limits.venue_limits[venue]
        if venue_exposure > limit:
            return LimitViolation(
                limit_type='venue_limit',
                current_value=venue_exposure,
                limit_value=limit,
                symbol=None,
                action='reject_order',
                timestamp=datetime.now(timezone.utc),
                message=f"Venue {venue} exposure ${venue_exposure:,.2f} exceeds limit ${limit:,.2f}"
            )
        
        return None
    
    async def calculate_exposure_metrics(self, positions: List[Position]) -> ExposureMetrics:
        """Calculate current exposure metrics."""
        long_exposure = 0.0
        short_exposure = 0.0
        sector_exposures: Dict[str, float] = defaultdict(float)
        venue_exposures: Dict[str, float] = defaultdict(float)
        largest_position = 0.0
        
        for position in positions:
            if position.quantity == 0:
                continue
            
            position_value = abs(float(position.quantity * (position.current_price or position.average_entry_price)))
            
            if position.quantity > 0:
                long_exposure += position_value
            else:
                short_exposure += position_value
            
            # Track largest position
            largest_position = max(largest_position, position_value)
            
            # Sector exposure
            sector = self._symbol_sectors.get(position.symbol, 'unknown')
            sector_exposures[sector] += position_value
            
            # Venue exposure
            venue_exposures[position.venue] += position_value
        
        gross_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure
        leverage = gross_exposure / self.capital if self.capital > 0 else 0.0
        
        portfolio_value = self.capital + sum(
            float(p.realized_pnl + p.unrealized_pnl) for p in positions
        )
        
        largest_position_pct = largest_position / max(portfolio_value, 1.0)
        
        return ExposureMetrics(
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            leverage=leverage,
            portfolio_value=portfolio_value,
            position_count=len([p for p in positions if p.quantity != 0]),
            largest_position_pct=largest_position_pct,
            sector_exposures=dict(sector_exposures),
            venue_exposures=dict(venue_exposures)
        )
