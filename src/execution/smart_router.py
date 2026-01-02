"""Smart order routing for optimal execution."""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from ..core.models import Order, OrderSide, Quote
from ..core.logging.structured_logger import get_logger


class SmartRouter:
    """Routes orders to optimal venues based on market conditions."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Venue capabilities and characteristics
        self._venue_configs: Dict[str, Dict] = {
            'binance': {
                'enabled': True,
                'priority': 1,
                'min_order_size': Decimal('0.0001'),
                'max_order_size': Decimal('9000'),
                'maker_fee': Decimal('0.001'),
                'taker_fee': Decimal('0.001')
            },
            'coinbase': {
                'enabled': True,
                'priority': 2,
                'min_order_size': Decimal('0.001'),
                'max_order_size': Decimal('5000'),
                'maker_fee': Decimal('0.005'),
                'taker_fee': Decimal('0.005')
            },
            'bybit': {
                'enabled': True,
                'priority': 3,
                'min_order_size': Decimal('0.0001'),
                'max_order_size': Decimal('8000'),
                'maker_fee': Decimal('0.001'),
                'taker_fee': Decimal('0.001')
            }
        }
        
        # Market data cache
        self._latest_quotes: Dict[str, Dict[str, Quote]] = {}
        self._venue_health: Dict[str, bool] = {}
    
    def update_venue_config(self, venue: str, config: Dict) -> None:
        """Update venue configuration."""
        if venue in self._venue_configs:
            self._venue_configs[venue].update(config)
        else:
            self._venue_configs[venue] = config
        
        self.logger.info(f"Updated venue config: {venue}", config)
    
    def update_quote(self, quote: Quote) -> None:
        """Update latest quote for routing decisions."""
        symbol = quote.symbol
        venue = quote.venue
        
        if symbol not in self._latest_quotes:
            self._latest_quotes[symbol] = {}
        
        self._latest_quotes[symbol][venue] = quote
    
    def set_venue_health(self, venue: str, healthy: bool) -> None:
        """Update venue health status."""
        self._venue_health[venue] = healthy
        self.logger.info(f"Venue health updated: {venue} = {healthy}")
    
    async def route_order(self, order: Order) -> List[str]:
        """Determine optimal venue(s) for order execution."""
        # If venue explicitly specified, use it
        if order.venue:
            if self._is_venue_available(order.venue):
                return [order.venue]
            else:
                self.logger.warning(f"Specified venue unavailable: {order.venue}")
                return []
        
        # Get available venues for symbol
        venues = self._get_available_venues(order.symbol)
        
        if not venues:
            self.logger.error(f"No available venues for {order.symbol}")
            return []
        
        # Rank venues by multiple criteria
        ranked_venues = await self._rank_venues(order, venues)
        
        if not ranked_venues:
            return []
        
        # Return best venue(s)
        best_venue = ranked_venues[0][0]
        
        self.logger.info("Order routed", {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "venue": best_venue,
            "candidates": len(venues)
        })
        
        return [best_venue]
    
    async def _rank_venues(self, order: Order, venues: List[str]) -> List[Tuple[str, float]]:
        """Rank venues by execution quality score."""
        scored_venues = []
        
        for venue in venues:
            score = await self._calculate_venue_score(order, venue)
            if score > 0:
                scored_venues.append((venue, score))
        
        # Sort by score descending
        scored_venues.sort(key=lambda x: x[1], reverse=True)
        
        return scored_venues
    
    async def _calculate_venue_score(self, order: Order, venue: str) -> float:
        """Calculate execution quality score for venue."""
        score = 0.0
        
        config = self._venue_configs.get(venue)
        if not config:
            return 0.0
        
        # Base priority
        score += (10 - config.get('priority', 5)) * 10
        
        # Check order size constraints
        min_size = config.get('min_order_size', Decimal('0'))
        max_size = config.get('max_order_size', Decimal('999999'))
        
        if order.quantity < min_size or order.quantity > max_size:
            return 0.0  # Venue cannot handle this order size
        
        # Liquidity score (based on latest quote)
        quotes = self._latest_quotes.get(order.symbol, {})
        quote = quotes.get(venue)
        
        if quote:
            # Check spread
            spread = float(quote.ask_price - quote.bid_price)
            mid = float((quote.ask_price + quote.bid_price) / 2)
            spread_bps = (spread / mid * 10000) if mid > 0 else 999
            
            # Better score for tighter spreads
            if spread_bps < 5:
                score += 30
            elif spread_bps < 10:
                score += 20
            elif spread_bps < 20:
                score += 10
            
            # Check available liquidity
            if order.side == OrderSide.BUY:
                available = float(quote.ask_size)
            else:
                available = float(quote.bid_size)
            
            required = float(order.quantity)
            
            if available >= required * 2:
                score += 20  # Ample liquidity
            elif available >= required:
                score += 10  # Sufficient liquidity
            else:
                score -= 10  # Insufficient liquidity
        else:
            # No recent quote, penalize
            score -= 20
        
        # Fee consideration
        taker_fee = config.get('taker_fee', Decimal('0.001'))
        fee_bps = float(taker_fee * 10000)
        
        if fee_bps < 5:
            score += 10
        elif fee_bps < 10:
            score += 5
        
        # Health check
        if not self._venue_health.get(venue, True):
            score -= 50  # Heavy penalty for unhealthy venue
        
        return max(score, 0.0)
    
    def _get_available_venues(self, symbol: str) -> List[str]:
        """Get list of venues that support the symbol."""
        available = []
        
        for venue, config in self._venue_configs.items():
            if not config.get('enabled', False):
                continue
            
            if not self._is_venue_available(venue):
                continue
            
            # Check if venue has recent quotes for symbol
            if symbol in self._latest_quotes and venue in self._latest_quotes[symbol]:
                available.append(venue)
        
        return available
    
    def _is_venue_available(self, venue: str) -> bool:
        """Check if venue is available and healthy."""
        config = self._venue_configs.get(venue)
        if not config or not config.get('enabled', False):
            return False
        
        # Check health status
        if not self._venue_health.get(venue, True):
            return False
        
        return True
    
    async def split_order(self, order: Order, venues: List[str]) -> List[Order]:
        """Split order across multiple venues for better execution."""
        # For now, simple implementation - could be enhanced with VWAP, TWAP, etc.
        if len(venues) <= 1:
            return [order]
        
        split_orders = []
        quantity_per_venue = order.quantity / len(venues)
        
        for i, venue in enumerate(venues):
            split_order = Order(
                symbol=order.symbol,
                venue=venue,
                side=order.side,
                order_type=order.order_type,
                quantity=quantity_per_venue,
                price=order.price,
                strategy_id=order.strategy_id,
                parent_order_id=order.order_id
            )
            split_orders.append(split_order)
        
        self.logger.info(f"Order split into {len(split_orders)} parts", {
            "parent_order_id": order.order_id,
            "venues": venues
        })
        
        return split_orders
