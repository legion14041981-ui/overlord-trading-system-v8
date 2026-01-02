"""Automated hedging engine for portfolio risk management."""
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from ..core.models import Position, Order, OrderSide, OrderType, TimeInForce
from ..core.logging.structured_logger import get_logger
from ..market_data.market_data_aggregator import MarketDataAggregator


class HedgeType(Enum):
    """Type of hedge recommendation."""
    DELTA_HEDGE = "delta_hedge"  # Hedge directional exposure
    CROSS_HEDGE = "cross_hedge"  # Hedge with correlated instrument
    SECTOR_HEDGE = "sector_hedge"  # Hedge sector exposure
    CURRENCY_HEDGE = "currency_hedge"  # Hedge FX exposure
    VOLATILITY_HEDGE = "volatility_hedge"  # Hedge vol exposure
    

@dataclass
class HedgeRecommendation:
    """Hedge trade recommendation."""
    hedge_type: HedgeType
    target_symbol: str
    hedge_symbol: str
    hedge_quantity: Decimal
    hedge_side: OrderSide
    hedge_venue: str
    rationale: str
    expected_risk_reduction: float  # %
    cost_estimate: float
    urgency: str  # 'low', 'medium', 'high', 'critical'
    timestamp: datetime
    metadata: Dict
    

@dataclass
class HedgePosition:
    """Tracking for hedged position pairs."""
    primary_position: Position
    hedge_position: Position
    hedge_ratio: float
    effectiveness: float  # Historical hedge effectiveness
    created_at: datetime
    last_rebalanced: datetime
    

class HedgingEngine:
    """Automated hedging for portfolio risk management."""
    
    def __init__(self, market_data: MarketDataAggregator):
        self.market_data = market_data
        self.logger = get_logger(__name__)
        
        # Hedging configuration
        self.delta_threshold = 0.15  # Hedge when net delta > 15%
        self.min_position_value = 1000.0  # Min value to hedge
        self.rebalance_threshold = 0.10  # Rebalance when hedge ratio drifts > 10%
        
        # Correlation matrix for cross-hedging
        self._correlation_matrix: Dict[Tuple[str, str], float] = {}
        
        # Active hedges tracking
        self._active_hedges: Dict[str, HedgePosition] = {}  # key: primary_symbol
        
        # Hedge instrument mappings
        self._hedge_instruments: Dict[str, List[str]] = {
            'BTC': ['BTC-PERP', 'BTCUSDT'],
            'ETH': ['ETH-PERP', 'ETHUSDT'],
            'SPY': ['ES', 'SPX'],
            'QQQ': ['NQ', 'NDX']
        }
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def set_correlation(self, symbol1: str, symbol2: str, correlation: float) -> None:
        """Set correlation between two instruments."""
        self._correlation_matrix[(symbol1, symbol2)] = correlation
        self._correlation_matrix[(symbol2, symbol1)] = correlation
    
    def register_hedge_instrument(self, symbol: str, hedge_symbols: List[str]) -> None:
        """Register available hedge instruments for a symbol."""
        self._hedge_instruments[symbol] = hedge_symbols
    
    async def analyze_hedge_requirements(
        self,
        positions: List[Position],
        portfolio_value: float
    ) -> List[HedgeRecommendation]:
        """Analyze portfolio and generate hedge recommendations."""
        recommendations = []
        
        # Calculate portfolio-level exposures
        net_delta = await self._calculate_net_delta(positions)
        net_delta_pct = net_delta / portfolio_value if portfolio_value > 0 else 0
        
        # Check if portfolio-level hedge is needed
        if abs(net_delta_pct) > self.delta_threshold:
            portfolio_hedge = await self._generate_portfolio_hedge(
                positions, net_delta, portfolio_value
            )
            if portfolio_hedge:
                recommendations.append(portfolio_hedge)
        
        # Check individual position hedging needs
        for position in positions:
            if position.quantity == 0:
                continue
            
            position_value = abs(float(position.quantity * (position.current_price or position.average_entry_price)))
            
            if position_value < self.min_position_value:
                continue
            
            # Check if position needs hedging
            hedge_rec = await self._analyze_position_hedge(position, portfolio_value)
            if hedge_rec:
                recommendations.append(hedge_rec)
            
            # Check if existing hedge needs rebalancing
            rebalance_rec = await self._check_hedge_rebalance(position)
            if rebalance_rec:
                recommendations.append(rebalance_rec)
        
        # Sort by urgency
        recommendations.sort(
            key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}[x.urgency]
        )
        
        return recommendations
    
    async def _calculate_net_delta(self, positions: List[Position]) -> float:
        """Calculate net directional exposure (delta) of portfolio."""
        net_delta = 0.0
        
        for position in positions:
            if position.quantity == 0:
                continue
            
            # For simplicity, delta = position value (signed)
            # In reality, you'd calculate actual Greeks for options
            position_value = float(position.quantity * (position.current_price or position.average_entry_price))
            net_delta += position_value
        
        return net_delta
    
    async def _generate_portfolio_hedge(
        self,
        positions: List[Position],
        net_delta: float,
        portfolio_value: float
    ) -> Optional[HedgeRecommendation]:
        """Generate portfolio-level hedge recommendation."""
        # Find dominant sector/symbol
        symbol_exposures = {}
        for position in positions:
            value = abs(float(position.quantity * (position.current_price or position.average_entry_price)))
            symbol_exposures[position.symbol] = symbol_exposures.get(position.symbol, 0) + value
        
        if not symbol_exposures:
            return None
        
        dominant_symbol = max(symbol_exposures.items(), key=lambda x: x[1])[0]
        
        # Find hedge instrument
        hedge_symbol = await self._find_best_hedge_instrument(dominant_symbol)
        if not hedge_symbol:
            return None
        
        # Calculate hedge quantity
        hedge_side = OrderSide.SELL if net_delta > 0 else OrderSide.BUY
        
        # Get current price for hedge instrument
        try:
            hedge_quote = await self.market_data.get_latest_quote(hedge_symbol)
            if not hedge_quote:
                return None
            
            hedge_price = float((hedge_quote.bid_price + hedge_quote.ask_price) / 2)
            hedge_quantity = abs(Decimal(str(net_delta / hedge_price)))
            
            # Estimate cost (spread + fees)
            spread = float(hedge_quote.ask_price - hedge_quote.bid_price)
            cost_estimate = float(hedge_quantity) * spread
            
            return HedgeRecommendation(
                hedge_type=HedgeType.DELTA_HEDGE,
                target_symbol='PORTFOLIO',
                hedge_symbol=hedge_symbol,
                hedge_quantity=hedge_quantity,
                hedge_side=hedge_side,
                hedge_venue=hedge_quote.venue,
                rationale=f"Portfolio net delta {net_delta/portfolio_value:.2%} exceeds threshold {self.delta_threshold:.2%}",
                expected_risk_reduction=abs(net_delta) / portfolio_value,
                cost_estimate=cost_estimate,
                urgency='high' if abs(net_delta/portfolio_value) > 0.25 else 'medium',
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'net_delta': net_delta,
                    'net_delta_pct': net_delta / portfolio_value,
                    'hedge_price': hedge_price
                }
            )
            
        except Exception as e:
            self.logger.error("Failed to generate portfolio hedge", error=e)
            return None
    
    async def _analyze_position_hedge(
        self,
        position: Position,
        portfolio_value: float
    ) -> Optional[HedgeRecommendation]:
        """Analyze if individual position needs hedging."""
        position_value = abs(float(position.quantity * (position.current_price or position.average_entry_price)))
        position_pct = position_value / portfolio_value
        
        # Large positions should be hedged
        if position_pct < 0.20:  # Less than 20% of portfolio
            return None
        
        # Check if already hedged
        if position.symbol in self._active_hedges:
            return None
        
        # Find hedge instrument
        hedge_symbol = await self._find_best_hedge_instrument(position.symbol)
        if not hedge_symbol:
            return None
        
        # Calculate optimal hedge ratio
        hedge_ratio = await self._calculate_optimal_hedge_ratio(
            position.symbol, hedge_symbol
        )
        
        if hedge_ratio < 0.5:  # Not worth hedging if correlation too low
            return None
        
        # Determine hedge side (opposite of position)
        hedge_side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY
        hedge_quantity = abs(position.quantity * Decimal(str(hedge_ratio)))
        
        try:
            hedge_quote = await self.market_data.get_latest_quote(hedge_symbol)
            if not hedge_quote:
                return None
            
            spread = float(hedge_quote.ask_price - hedge_quote.bid_price)
            cost_estimate = float(hedge_quantity) * spread
            
            return HedgeRecommendation(
                hedge_type=HedgeType.CROSS_HEDGE,
                target_symbol=position.symbol,
                hedge_symbol=hedge_symbol,
                hedge_quantity=hedge_quantity,
                hedge_side=hedge_side,
                hedge_venue=hedge_quote.venue,
                rationale=f"Position concentration {position_pct:.2%} is high, hedging recommended",
                expected_risk_reduction=position_pct * hedge_ratio,
                cost_estimate=cost_estimate,
                urgency='medium' if position_pct > 0.30 else 'low',
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'position_value': position_value,
                    'position_pct': position_pct,
                    'hedge_ratio': hedge_ratio
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze hedge for {position.symbol}", error=e)
            return None
    
    async def _check_hedge_rebalance(
        self,
        position: Position
    ) -> Optional[HedgeRecommendation]:
        """Check if existing hedge needs rebalancing."""
        if position.symbol not in self._active_hedges:
            return None
        
        hedge_position = self._active_hedges[position.symbol]
        
        # Calculate current hedge ratio
        current_ratio = abs(float(hedge_position.hedge_position.quantity / position.quantity))
        target_ratio = hedge_position.hedge_ratio
        
        ratio_drift = abs(current_ratio - target_ratio) / target_ratio
        
        if ratio_drift < self.rebalance_threshold:
            return None
        
        # Need to rebalance
        quantity_adjustment = position.quantity * Decimal(str(target_ratio - current_ratio))
        
        if quantity_adjustment > 0:
            side = OrderSide.BUY if hedge_position.hedge_position.quantity < 0 else OrderSide.SELL
        else:
            side = OrderSide.SELL if hedge_position.hedge_position.quantity < 0 else OrderSide.BUY
            quantity_adjustment = abs(quantity_adjustment)
        
        return HedgeRecommendation(
            hedge_type=HedgeType.DELTA_HEDGE,
            target_symbol=position.symbol,
            hedge_symbol=hedge_position.hedge_position.symbol,
            hedge_quantity=abs(quantity_adjustment),
            hedge_side=side,
            hedge_venue=hedge_position.hedge_position.venue,
            rationale=f"Hedge ratio drifted {ratio_drift:.2%}, rebalancing needed",
            expected_risk_reduction=ratio_drift * 0.5,
            cost_estimate=float(abs(quantity_adjustment)) * 0.001,  # Estimate
            urgency='low',
            timestamp=datetime.now(timezone.utc),
            metadata={
                'current_ratio': current_ratio,
                'target_ratio': target_ratio,
                'ratio_drift': ratio_drift
            }
        )
    
    async def _find_best_hedge_instrument(self, symbol: str) -> Optional[str]:
        """Find best available hedge instrument for a symbol."""
        # Check pre-configured hedge instruments
        if symbol in self._hedge_instruments:
            candidates = self._hedge_instruments[symbol]
            
            # Check liquidity and pick best
            for candidate in candidates:
                try:
                    quote = await self.market_data.get_latest_quote(candidate)
                    if quote and quote.bid_size > 0 and quote.ask_size > 0:
                        return candidate
                except Exception:
                    continue
        
        # Fallback: use same symbol on different venue (if available)
        return None
    
    async def _calculate_optimal_hedge_ratio(
        self,
        symbol1: str,
        symbol2: str
    ) -> float:
        """Calculate optimal hedge ratio between two instruments.
        
        Uses correlation and volatility ratio.
        """
        # Check if we have historical correlation
        correlation = self._correlation_matrix.get((symbol1, symbol2))
        
        if correlation is None:
            # Estimate correlation from recent price movements
            # In production, calculate from historical data
            correlation = 0.8  # Conservative default
        
        # Optimal hedge ratio = correlation * (vol1 / vol2)
        # For simplicity, assume vol ratio is 1.0
        # In production, calculate from historical volatilities
        hedge_ratio = abs(correlation) * 1.0
        
        return min(hedge_ratio, 1.0)  # Cap at 1.0
    
    async def execute_hedge(
        self,
        recommendation: HedgeRecommendation
    ) -> Order:
        """Create order to execute hedge recommendation."""
        hedge_order = Order(
            symbol=recommendation.hedge_symbol,
            venue=recommendation.hedge_venue,
            side=recommendation.hedge_side,
            order_type=OrderType.LIMIT,  # Use limit for better execution
            quantity=recommendation.hedge_quantity,
            time_in_force=TimeInForce.GTC,
            strategy_id='hedge_engine',
            metadata={
                'hedge_type': recommendation.hedge_type.value,
                'target_symbol': recommendation.target_symbol,
                'rationale': recommendation.rationale
            }
        )
        
        self.logger.info(
            "Hedge order created",
            hedge_type=recommendation.hedge_type.value,
            symbol=recommendation.hedge_symbol,
            quantity=float(recommendation.hedge_quantity),
            side=recommendation.hedge_side.value
        )
        
        return hedge_order
    
    async def register_active_hedge(
        self,
        primary_position: Position,
        hedge_position: Position,
        hedge_ratio: float
    ) -> None:
        """Register an active hedge for tracking."""
        async with self._lock:
            self._active_hedges[primary_position.symbol] = HedgePosition(
                primary_position=primary_position,
                hedge_position=hedge_position,
                hedge_ratio=hedge_ratio,
                effectiveness=0.0,  # Will be calculated over time
                created_at=datetime.now(timezone.utc),
                last_rebalanced=datetime.now(timezone.utc)
            )
        
        self.logger.info(
            "Active hedge registered",
            symbol=primary_position.symbol,
            hedge_symbol=hedge_position.symbol,
            hedge_ratio=hedge_ratio
        )
    
    async def calculate_hedge_effectiveness(
        self,
        symbol: str,
        period_days: int = 30
    ) -> Optional[float]:
        """Calculate historical effectiveness of a hedge.
        
        Returns value between 0 and 1, where 1 is perfect hedge.
        """
        if symbol not in self._active_hedges:
            return None
        
        # In production, calculate from historical P&L correlation
        # For now, return estimated effectiveness based on correlation
        hedge_pos = self._active_hedges[symbol]
        correlation = self._correlation_matrix.get(
            (symbol, hedge_pos.hedge_position.symbol),
            0.8
        )
        
        effectiveness = abs(correlation) * hedge_pos.hedge_ratio
        return min(effectiveness, 1.0)
