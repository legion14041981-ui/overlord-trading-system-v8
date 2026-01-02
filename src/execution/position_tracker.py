"""Real-time position tracking and P&L calculation."""
import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone
from decimal import Decimal
from collections import defaultdict

from ..core.models import Position, Order, OrderSide, Trade, Quote
from ..core.storage.base import PositionStorage
from ..core.logging.structured_logger import get_logger


class PositionTracker:
    """Tracks and manages trading positions in real-time."""
    
    def __init__(self, storage: PositionStorage):
        self.storage = storage
        self.logger = get_logger(__name__)
        
        # In-memory position cache
        self._positions: Dict[str, Position] = {}  # key: symbol_venue
        self._positions_by_strategy: Dict[str, Dict[str, Position]] = defaultdict(dict)
        
        # Market data cache for P&L calculation
        self._latest_quotes: Dict[str, Quote] = {}
        
        # Position update callbacks
        self._position_callbacks: List[Callable] = []
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Load existing positions from storage."""
        positions = await self.storage.get_all_positions()
        
        async with self._lock:
            for position in positions:
                key = self._get_position_key(position.symbol, position.venue)
                self._positions[key] = position
                
                if position.strategy_id:
                    self._positions_by_strategy[position.strategy_id][key] = position
        
        self.logger.info(f"Loaded {len(positions)} positions from storage")
    
    def register_position_callback(self, callback: Callable) -> None:
        """Register callback for position updates."""
        self._position_callbacks.append(callback)
    
    def update_quote(self, quote: Quote) -> None:
        """Update latest quote for mark-to-market P&L."""
        key = self._get_position_key(quote.symbol, quote.venue)
        self._latest_quotes[key] = quote
    
    async def handle_fill(self, order: Order, filled_quantity: Decimal, 
                         fill_price: Decimal) -> Position:
        """Handle order fill and update position."""
        async with self._lock:
            key = self._get_position_key(order.symbol, order.venue)
            position = self._positions.get(key)
            
            if not position:
                # Create new position
                position = Position(
                    symbol=order.symbol,
                    venue=order.venue,
                    strategy_id=order.strategy_id,
                    quantity=Decimal('0'),
                    average_entry_price=Decimal('0'),
                    realized_pnl=Decimal('0'),
                    unrealized_pnl=Decimal('0'),
                    opened_at=datetime.now(timezone.utc)
                )
                self._positions[key] = position
                
                if order.strategy_id:
                    self._positions_by_strategy[order.strategy_id][key] = position
            
            # Update position based on fill
            await self._update_position(position, order.side, filled_quantity, fill_price)
            
            # Persist to storage
            await self.storage.save_position(position)
            
            # Notify callbacks
            await self._notify_position_callbacks(position)
            
            return position
    
    async def _update_position(self, position: Position, side: OrderSide,
                              quantity: Decimal, price: Decimal) -> None:
        """Update position with new fill."""
        if side == OrderSide.BUY:
            # Buying increases position
            if position.quantity >= 0:
                # Adding to long or creating long
                new_quantity = position.quantity + quantity
                position.average_entry_price = (
                    (position.quantity * position.average_entry_price + quantity * price)
                    / new_quantity
                )
                position.quantity = new_quantity
            else:
                # Covering short
                if quantity > abs(position.quantity):
                    # Short fully covered, going long
                    realized_pnl = -position.quantity * (price - position.average_entry_price)
                    position.realized_pnl += realized_pnl
                    
                    remaining = quantity + position.quantity  # position.quantity is negative
                    position.quantity = remaining
                    position.average_entry_price = price
                else:
                    # Partial cover
                    realized_pnl = quantity * (position.average_entry_price - price)
                    position.realized_pnl += realized_pnl
                    position.quantity += quantity
        
        else:  # SELL
            # Selling decreases position
            if position.quantity <= 0:
                # Adding to short or creating short
                new_quantity = position.quantity - quantity
                position.average_entry_price = (
                    (abs(position.quantity) * position.average_entry_price + quantity * price)
                    / abs(new_quantity)
                )
                position.quantity = new_quantity
            else:
                # Closing long
                if quantity > position.quantity:
                    # Long fully closed, going short
                    realized_pnl = position.quantity * (price - position.average_entry_price)
                    position.realized_pnl += realized_pnl
                    
                    remaining = -(quantity - position.quantity)
                    position.quantity = remaining
                    position.average_entry_price = price
                else:
                    # Partial close
                    realized_pnl = quantity * (price - position.average_entry_price)
                    position.realized_pnl += realized_pnl
                    position.quantity -= quantity
        
        position.updated_at = datetime.now(timezone.utc)
        
        # Check if position is closed
        if position.quantity == 0:
            position.closed_at = datetime.now(timezone.utc)
            self.logger.log_position_change(
                symbol=position.symbol,
                action="closed",
                quantity=Decimal('0'),
                pnl=position.realized_pnl
            )
    
    async def update_unrealized_pnl(self, symbol: str, venue: str,
                                   mark_price: Decimal) -> Optional[Position]:
        """Update unrealized P&L based on mark price."""
        async with self._lock:
            key = self._get_position_key(symbol, venue)
            position = self._positions.get(key)
            
            if not position or position.quantity == 0:
                return None
            
            # Calculate unrealized P&L
            if position.quantity > 0:
                # Long position
                position.unrealized_pnl = position.quantity * (mark_price - position.average_entry_price)
            else:
                # Short position
                position.unrealized_pnl = position.quantity * (mark_price - position.average_entry_price)
            
            position.current_price = mark_price
            position.updated_at = datetime.now(timezone.utc)
            
            return position
    
    async def get_position(self, symbol: str, venue: str) -> Optional[Position]:
        """Get position for symbol and venue."""
        key = self._get_position_key(symbol, venue)
        position = self._positions.get(key)
        
        if position:
            # Update with latest mark price
            quote = self._latest_quotes.get(key)
            if quote:
                mark_price = (quote.bid_price + quote.ask_price) / Decimal('2')
                await self.update_unrealized_pnl(symbol, venue, mark_price)
        
        return position
    
    async def get_all_positions(self, strategy_id: Optional[str] = None,
                               include_closed: bool = False) -> List[Position]:
        """Get all positions, optionally filtered by strategy."""
        if strategy_id:
            positions = list(self._positions_by_strategy.get(strategy_id, {}).values())
        else:
            positions = list(self._positions.values())
        
        if not include_closed:
            positions = [p for p in positions if p.quantity != 0]
        
        # Update unrealized P&L for open positions
        for position in positions:
            if position.quantity != 0:
                key = self._get_position_key(position.symbol, position.venue)
                quote = self._latest_quotes.get(key)
                if quote:
                    mark_price = (quote.bid_price + quote.ask_price) / Decimal('2')
                    await self.update_unrealized_pnl(position.symbol, position.venue, mark_price)
        
        return positions
    
    async def close_position(self, symbol: str, venue: str,
                            close_price: Decimal) -> Optional[Position]:
        """Force close a position."""
        async with self._lock:
            key = self._get_position_key(symbol, venue)
            position = self._positions.get(key)
            
            if not position or position.quantity == 0:
                return None
            
            # Calculate final realized P&L
            if position.quantity > 0:
                final_pnl = position.quantity * (close_price - position.average_entry_price)
            else:
                final_pnl = position.quantity * (close_price - position.average_entry_price)
            
            position.realized_pnl += final_pnl
            position.quantity = Decimal('0')
            position.unrealized_pnl = Decimal('0')
            position.closed_at = datetime.now(timezone.utc)
            
            # Persist
            await self.storage.close_position(symbol, venue, position.realized_pnl)
            
            self.logger.log_position_change(
                symbol=symbol,
                action="force_closed",
                quantity=Decimal('0'),
                pnl=position.realized_pnl
            )
            
            return position
    
    async def get_portfolio_value(self, strategy_id: Optional[str] = None) -> Decimal:
        """Calculate total portfolio value (realized + unrealized P&L)."""
        positions = await self.get_all_positions(strategy_id)
        
        total_pnl = Decimal('0')
        for position in positions:
            total_pnl += position.realized_pnl + position.unrealized_pnl
        
        return total_pnl
    
    async def get_exposure(self, strategy_id: Optional[str] = None) -> Dict[str, Decimal]:
        """Calculate market exposure by symbol."""
        positions = await self.get_all_positions(strategy_id)
        
        exposure: Dict[str, Decimal] = defaultdict(Decimal)
        
        for position in positions:
            if position.quantity == 0:
                continue
            
            # Calculate notional exposure
            mark_price = position.current_price or position.average_entry_price
            notional = abs(position.quantity * mark_price)
            
            exposure[position.symbol] += notional
        
        return dict(exposure)
    
    async def get_position_summary(self, strategy_id: Optional[str] = None) -> Dict:
        """Get summary statistics for positions."""
        positions = await self.get_all_positions(strategy_id, include_closed=False)
        
        total_realized_pnl = Decimal('0')
        total_unrealized_pnl = Decimal('0')
        long_exposure = Decimal('0')
        short_exposure = Decimal('0')
        
        for position in positions:
            total_realized_pnl += position.realized_pnl
            total_unrealized_pnl += position.unrealized_pnl
            
            mark_price = position.current_price or position.average_entry_price
            notional = abs(position.quantity * mark_price)
            
            if position.quantity > 0:
                long_exposure += notional
            elif position.quantity < 0:
                short_exposure += notional
        
        return {
            'total_positions': len(positions),
            'realized_pnl': float(total_realized_pnl),
            'unrealized_pnl': float(total_unrealized_pnl),
            'total_pnl': float(total_realized_pnl + total_unrealized_pnl),
            'long_exposure': float(long_exposure),
            'short_exposure': float(short_exposure),
            'net_exposure': float(long_exposure - short_exposure),
            'gross_exposure': float(long_exposure + short_exposure)
        }
    
    async def _notify_position_callbacks(self, position: Position) -> None:
        """Notify registered callbacks of position update."""
        for callback in self._position_callbacks:
            try:
                await callback(position)
            except Exception as e:
                self.logger.error("Position callback error", error=e)
    
    def _get_position_key(self, symbol: str, venue: str) -> str:
        """Generate position cache key."""
        return f"{symbol}_{venue}"
