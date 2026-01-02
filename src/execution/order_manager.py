"""Order lifecycle management and tracking."""
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from ..core.models import Order, OrderStatus, OrderSide, OrderType
from ..core.storage.base import OrderStorage
from ..core.logging.structured_logger import get_logger


class OrderManager:
    """Manages order lifecycle, validation, and tracking."""
    
    def __init__(self, storage: OrderStorage, max_concurrent_orders: int = 100):
        self.storage = storage
        self.max_concurrent_orders = max_concurrent_orders
        self.logger = get_logger(__name__)
        
        # In-memory active orders cache
        self._active_orders: Dict[str, Order] = {}
        self._orders_by_strategy: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
    
    async def create_order(self, order: Order) -> Order:
        """Create and validate a new order."""
        async with self._lock:
            # Check concurrent order limit
            if len(self._active_orders) >= self.max_concurrent_orders:
                raise RuntimeError(
                    f"Maximum concurrent orders reached: {self.max_concurrent_orders}"
                )
            
            # Generate order ID if not provided
            if not order.order_id:
                order.order_id = self._generate_order_id()
            
            # Set initial status
            order.status = OrderStatus.PENDING
            order.created_at = datetime.now(timezone.utc)
            
            # Validate order
            self._validate_order(order)
            
            # Store order
            await self.storage.save_order(order)
            
            # Cache active order
            self._active_orders[order.order_id] = order
            
            # Index by strategy
            if order.strategy_id:
                if order.strategy_id not in self._orders_by_strategy:
                    self._orders_by_strategy[order.strategy_id] = set()
                self._orders_by_strategy[order.strategy_id].add(order.order_id)
            
            self.logger.log_order(
                action="created",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.quantity,
                price=order.price
            )
            
            return order
    
    async def update_order_status(self, order_id: str, status: OrderStatus,
                                  filled_quantity: Optional[Decimal] = None,
                                  average_fill_price: Optional[Decimal] = None,
                                  error_message: Optional[str] = None) -> Order:
        """Update order status and fill information."""
        async with self._lock:
            order = self._active_orders.get(order_id)
            if not order:
                # Load from storage if not in cache
                order = await self.storage.get_order(order_id)
                if not order:
                    raise ValueError(f"Order not found: {order_id}")
            
            # Update fields
            old_status = order.status
            order.status = status
            order.updated_at = datetime.now(timezone.utc)
            
            if filled_quantity is not None:
                order.filled_quantity = filled_quantity
            
            if average_fill_price is not None:
                order.average_fill_price = average_fill_price
            
            if error_message:
                order.error_message = error_message
            
            # Set timestamps for terminal states
            if status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
                if not order.first_fill_at:
                    order.first_fill_at = datetime.now(timezone.utc)
                if status == OrderStatus.FILLED:
                    order.completed_at = datetime.now(timezone.utc)
            
            elif status in [OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
                order.completed_at = datetime.now(timezone.utc)
            
            # Persist to storage
            await self.storage.save_order(order)
            
            # Update cache
            if status.is_terminal():
                self._active_orders.pop(order_id, None)
                if order.strategy_id in self._orders_by_strategy:
                    self._orders_by_strategy[order.strategy_id].discard(order_id)
            else:
                self._active_orders[order_id] = order
            
            self.logger.info(f"Order status updated: {old_status.value} -> {status.value}", {
                "order_id": order_id,
                "symbol": order.symbol,
                "filled_quantity": str(filled_quantity) if filled_quantity else None
            })
            
            return order
    
    async def cancel_order(self, order_id: str) -> Order:
        """Request order cancellation."""
        order = self._active_orders.get(order_id)
        if not order:
            order = await self.storage.get_order(order_id)
            if not order:
                raise ValueError(f"Order not found: {order_id}")
        
        if order.status.is_terminal():
            raise ValueError(f"Cannot cancel order in terminal state: {order.status.value}")
        
        return await self.update_order_status(order_id, OrderStatus.PENDING_CANCEL)
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        order = self._active_orders.get(order_id)
        if order:
            return order
        return await self.storage.get_order(order_id)
    
    async def get_active_orders(self, strategy_id: Optional[str] = None) -> List[Order]:
        """Get all active orders, optionally filtered by strategy."""
        if strategy_id:
            order_ids = self._orders_by_strategy.get(strategy_id, set())
            return [self._active_orders[oid] for oid in order_ids if oid in self._active_orders]
        else:
            return list(self._active_orders.values())
    
    async def get_orders_by_symbol(self, symbol: str, venue: Optional[str] = None) -> List[Order]:
        """Get active orders for a specific symbol."""
        orders = [o for o in self._active_orders.values() if o.symbol == symbol]
        if venue:
            orders = [o for o in orders if o.venue == venue]
        return orders
    
    async def cancel_all_orders(self, strategy_id: Optional[str] = None,
                               symbol: Optional[str] = None) -> List[Order]:
        """Cancel all orders matching filters."""
        orders_to_cancel = list(self._active_orders.values())
        
        if strategy_id:
            orders_to_cancel = [o for o in orders_to_cancel if o.strategy_id == strategy_id]
        
        if symbol:
            orders_to_cancel = [o for o in orders_to_cancel if o.symbol == symbol]
        
        cancelled = []
        for order in orders_to_cancel:
            if not order.status.is_terminal():
                try:
                    cancelled_order = await self.cancel_order(order.order_id)
                    cancelled.append(cancelled_order)
                except Exception as e:
                    self.logger.error(f"Failed to cancel order {order.order_id}", error=e)
        
        self.logger.warning(f"Cancelled {len(cancelled)} orders", {
            "strategy_id": strategy_id,
            "symbol": symbol
        })
        
        return cancelled
    
    def _validate_order(self, order: Order) -> None:
        """Validate order parameters."""
        if order.quantity <= 0:
            raise ValueError(f"Invalid order quantity: {order.quantity}")
        
        if order.order_type == OrderType.LIMIT and (not order.price or order.price <= 0):
            raise ValueError(f"Limit order requires valid price: {order.price}")
        
        if order.order_type == OrderType.STOP_LOSS and (not order.stop_price or order.stop_price <= 0):
            raise ValueError(f"Stop loss order requires valid stop price: {order.stop_price}")
        
        if not order.symbol or not order.venue:
            raise ValueError("Order must specify symbol and venue")
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        return f"ORD-{uuid4().hex[:16].upper()}"
    
    async def get_order_statistics(self, strategy_id: Optional[str] = None) -> Dict:
        """Get order execution statistics."""
        orders = await self.get_active_orders(strategy_id)
        
        stats = {
            'total_active': len(orders),
            'by_status': {},
            'by_type': {},
            'by_side': {}
        }
        
        for order in orders:
            # Count by status
            status_key = order.status.value
            stats['by_status'][status_key] = stats['by_status'].get(status_key, 0) + 1
            
            # Count by type
            type_key = order.order_type.value
            stats['by_type'][type_key] = stats['by_type'].get(type_key, 0) + 1
            
            # Count by side
            side_key = order.side.value
            stats['by_side'][side_key] = stats['by_side'].get(side_key, 0) + 1
        
        return stats
