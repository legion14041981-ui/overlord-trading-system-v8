"""Abstract base collector for market data."""
from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Any
from datetime import datetime
from decimal import Decimal
import asyncio

from ..models import Quote, Trade, OHLCV, OrderBook
from ...core.logging.structured_logger import get_logger


logger = get_logger(__name__)


class BaseCollector(ABC):
    """Abstract base collector for exchange data."""
    
    def __init__(self, name: str, venue: str, symbols: List[str], 
                 api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.name = name
        self.venue = venue
        self.symbols = symbols
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_connected = False
        self._callbacks: List[Callable] = []
        self._error_count = 0
        self._max_consecutive_errors = 5
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to data source."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from data source."""
        pass
    
    @abstractmethod
    async def subscribe_quotes(self, symbols: Optional[List[str]] = None) -> None:
        """Subscribe to quote updates."""
        pass
    
    @abstractmethod
    async def subscribe_trades(self, symbols: Optional[List[str]] = None) -> None:
        """Subscribe to trade updates."""
        pass
    
    @abstractmethod
    async def subscribe_orderbook(self, symbols: Optional[List[str]] = None, 
                                  depth: int = 20) -> None:
        """Subscribe to order book updates."""
        pass
    
    @abstractmethod
    async def get_ohlcv(self, symbol: str, interval: str, 
                       start: Optional[datetime] = None,
                       end: Optional[datetime] = None) -> List[OHLCV]:
        """Fetch historical OHLCV data."""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get current order book."""
        pass
    
    def subscribe_callback(self, callback: Callable[[Any], None]) -> None:
        """Register callback for data updates."""
        self._callbacks.append(callback)
    
    async def _emit_data(self, data: Any) -> None:
        """Emit data to all registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Callback error in {self.name}", error=e)
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle connection error with retry logic."""
        self._error_count += 1
        logger.error(
            f"Collector error in {self.name} ({self._error_count}/{self._max_consecutive_errors})",
            context={"venue": self.venue, "error_type": type(error).__name__},
            error=error
        )
        
        if self._error_count >= self._max_consecutive_errors:
            logger.critical(
                f"Max consecutive errors reached in {self.name}. Circuit breaker activated.",
                context={"venue": self.venue}
            )
            await self.disconnect()
            self.is_connected = False
    
    def _reset_error_count(self) -> None:
        """Reset error counter on successful operation."""
        if self._error_count > 0:
            logger.info(
                f"Error count reset for {self.name}",
                context={"venue": self.venue, "previous_errors": self._error_count}
            )
            self._error_count = 0
    
    async def health_check(self) -> bool:
        """Check if collector is healthy."""
        return self.is_connected and self._error_count < self._max_consecutive_errors
