"""Core execution engine coordinating order flow."""
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
from decimal import Decimal

from ..core.models import Order, OrderStatus, OrderSide, ExecutionMode
from ..core.logging.structured_logger import get_logger
from .order_manager import OrderManager
from .smart_router import SmartRouter
from .slippage_controller import SlippageController


class ExecutionEngine:
    """Core execution engine managing order lifecycle."""
    
    def __init__(self, 
                 order_manager: OrderManager,
                 smart_router: SmartRouter,
                 slippage_controller: SlippageController,
                 mode: ExecutionMode = ExecutionMode.SMART_ROUTING):
        self.order_manager = order_manager
        self.smart_router = smart_router
        self.slippage_controller = slippage_controller
        self.mode = mode
        self.logger = get_logger(__name__)
        
        # Venue connectors (will be injected)
        self._venue_connectors: Dict[str, Any] = {}
        
        # Execution callbacks
        self._execution_callbacks: List[Callable] = []
        
        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
    
    def register_venue_connector(self, venue: str, connector: Any) -> None:
        """Register venue-specific execution connector."""
        self._venue_connectors[venue] = connector
        self.logger.info(f"Registered venue connector: {venue}")
    
    def register_execution_callback(self, callback: Callable) -> None:
        """Register callback for execution events."""
        self._execution_callbacks.append(callback)
    
    async def start(self) -> None:
        """Start execution engine."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_orders())
        
        self.logger.info("Execution engine started", {
            "mode": self.mode.value,
            "venues": list(self._venue_connectors.keys())
        })
    
    async def stop(self) -> None:
        """Stop execution engine."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Execution engine stopped")
    
    async def execute_order(self, order: Order) -> Order:
        """Execute order through appropriate routing."""
        try:
            # Create order in manager
            order = await self.order_manager.create_order(order)
            
            # Determine execution venue(s)
            if self.mode == ExecutionMode.SMART_ROUTING:
                venues = await self.smart_router.route_order(order)
            else:
                venues = [order.venue] if order.venue else []
            
            if not venues:
                await self.order_manager.update_order_status(
                    order.order_id,
                    OrderStatus.REJECTED,
                    error_message="No suitable venue found"
                )
                return order
            
            # Check slippage before execution
            slippage_ok = await self.slippage_controller.check_slippage(
                order.symbol,
                order.side,
                order.quantity,
                order.price
            )
            
            if not slippage_ok:
                await self.order_manager.update_order_status(
                    order.order_id,
                    OrderStatus.REJECTED,
                    error_message="Slippage tolerance exceeded"
                )
                return order
            
            # Execute on primary venue
            primary_venue = venues[0]
            await self._execute_on_venue(order, primary_venue)
            
            return order
        
        except Exception as e:
            self.logger.error("Order execution failed", error=e, context={
                "order_id": order.order_id,
                "symbol": order.symbol
            })
            
            await self.order_manager.update_order_status(
                order.order_id,
                OrderStatus.REJECTED,
                error_message=str(e)
            )
            
            raise
    
    async def _execute_on_venue(self, order: Order, venue: str) -> None:
        """Execute order on specific venue."""
        connector = self._venue_connectors.get(venue)
        if not connector:
            raise RuntimeError(f"No connector for venue: {venue}")
        
        try:
            # Update status to submitted
            await self.order_manager.update_order_status(
                order.order_id,
                OrderStatus.SUBMITTED
            )
            
            # Submit to venue (this would be venue-specific API call)
            # For now, simulate immediate acceptance
            venue_order_id = await connector.submit_order(order)
            
            # Update with venue order ID
            order.venue_order_id = venue_order_id
            await self.order_manager.update_order_status(
                order.order_id,
                OrderStatus.ACCEPTED
            )
            
            self.logger.info("Order submitted to venue", {
                "order_id": order.order_id,
                "venue": venue,
                "venue_order_id": venue_order_id
            })
        
        except Exception as e:
            self.logger.error(f"Failed to execute on venue {venue}", error=e)
            raise
    
    async def cancel_order(self, order_id: str) -> Order:
        """Cancel an order."""
        order = await self.order_manager.get_order(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        if order.status.is_terminal():
            raise ValueError(f"Cannot cancel order in terminal state: {order.status.value}")
        
        # Request cancellation at venue
        connector = self._venue_connectors.get(order.venue)
        if connector and order.venue_order_id:
            try:
                await connector.cancel_order(order.venue_order_id)
            except Exception as e:
                self.logger.error("Failed to cancel at venue", error=e, context={
                    "order_id": order_id,
                    "venue": order.venue
                })
        
        # Update order status
        return await self.order_manager.update_order_status(
            order_id,
            OrderStatus.CANCELLED
        )
    
    async def handle_fill_update(self, order_id: str, 
                                 filled_quantity: Decimal,
                                 fill_price: Decimal) -> None:
        """Handle fill update from venue."""
        order = await self.order_manager.get_order(order_id)
        if not order:
            self.logger.error(f"Fill update for unknown order: {order_id}")
            return
        
        # Calculate average fill price
        previous_filled = order.filled_quantity or Decimal('0')
        previous_avg_price = order.average_fill_price or Decimal('0')
        
        total_filled = previous_filled + filled_quantity
        avg_price = (
            (previous_filled * previous_avg_price + filled_quantity * fill_price)
            / total_filled
        )
        
        # Determine new status
        if total_filled >= order.quantity:
            new_status = OrderStatus.FILLED
        else:
            new_status = OrderStatus.PARTIALLY_FILLED
        
        # Update order
        await self.order_manager.update_order_status(
            order_id,
            new_status,
            filled_quantity=total_filled,
            average_fill_price=avg_price
        )
        
        # Notify callbacks
        await self._notify_execution_callbacks(order, filled_quantity, fill_price)
        
        self.logger.log_trade(
            trade_id=order.venue_order_id or order_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=filled_quantity,
            price=fill_price
        )
    
    async def _notify_execution_callbacks(self, order: Order, 
                                         filled_qty: Decimal,
                                         fill_price: Decimal) -> None:
        """Notify registered callbacks of execution."""
        for callback in self._execution_callbacks:
            try:
                await callback(order, filled_qty, fill_price)
            except Exception as e:
                self.logger.error("Execution callback error", error=e)
    
    async def _monitor_orders(self) -> None:
        """Background task to monitor order states."""
        while self._running:
            try:
                active_orders = await self.order_manager.get_active_orders()
                
                for order in active_orders:
                    # Check for stale orders
                    if order.created_at:
                        age = (datetime.now(timezone.utc) - order.created_at).total_seconds()
                        if age > 3600:  # 1 hour timeout
                            self.logger.warning("Order timeout detected", {
                                "order_id": order.order_id,
                                "age_seconds": age
                            })
                            await self.order_manager.update_order_status(
                                order.order_id,
                                OrderStatus.EXPIRED,
                                error_message="Order timeout"
                            )
                
                await asyncio.sleep(10)  # Check every 10 seconds
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in order monitor", error=e)
                await asyncio.sleep(10)
    
    async def get_execution_stats(self) -> Dict:
        """Get execution statistics."""
        return await self.order_manager.get_order_statistics()
