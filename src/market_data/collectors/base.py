"""Abstract base collector for market data."""
from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
import asyncio

from ...core.models import Quote, Trade, OHLCV
from ...core.logging.structured_logger import get_logger


class BaseCollector(ABC):
    """Abstract base class for exchange data collectors."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = get_logger(f"collector.{name}")
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = config.get('retry_attempts', 5)
        self._reconnect_delay = 5
        self._callbacks: Dict[str, List[Callable]] = {
            'quote': [],
            'trade': [],
            'ohlcv': []
        }
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to exchange."""
        pass
    
    @abstractmethod
    async def subscribe_quotes(self, symbols: List[str]) -> None:
        """Subscribe to real-time quote updates."""
        pass
    
    @abstractmethod
    async def subscribe_trades(self, symbols: List[str]) -> None:
        """Subscribe to real-time trade updates."""
        pass
    
    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, interval: str, 
                          start: Optional[datetime] = None,
                          end: Optional[datetime] = None,
                          limit: int = 1000) -> List[OHLCV]:
        """Fetch historical OHLCV data."""
        pass
    
    @abstractmethod
    async def fetch_order_book(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """Fetch order book snapshot."""
        pass
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register callback for market data events."""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
            self.logger.debug(f"Registered {event_type} callback", {
                "callback": callback.__name__
            })
    
    async def _emit_quote(self, quote: Quote) -> None:
        """Emit quote to all registered callbacks."""
        for callback in self._callbacks['quote']:
            try:
                await callback(quote)
            except Exception as e:
                self.logger.error(f"Quote callback error", error=e, context={
                    "callback": callback.__name__,
                    "symbol": quote.symbol
                })
    
    async def _emit_trade(self, trade: Trade) -> None:
        """Emit trade to all registered callbacks."""
        for callback in self._callbacks['trade']:
            try:
                await callback(trade)
            except Exception as e:
                self.logger.error(f"Trade callback error", error=e, context={
                    "callback": callback.__name__,
                    "symbol": trade.symbol
                })
    
    async def _emit_ohlcv(self, ohlcv: OHLCV) -> None:
        """Emit OHLCV to all registered callbacks."""
        for callback in self._callbacks['ohlcv']:
            try:
                await callback(ohlcv)
            except Exception as e:
                self.logger.error(f"OHLCV callback error", error=e, context={
                    "callback": callback.__name__,
                    "symbol": ohlcv.symbol
                })
    
    async def _reconnect_loop(self) -> None:
        """Fault-tolerant reconnection logic."""
        while self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            delay = self._reconnect_delay * (2 ** (self._reconnect_attempts - 1))
            
            self.logger.warning(f"Reconnecting to {self.name}", {
                "attempt": self._reconnect_attempts,
                "max_attempts": self._max_reconnect_attempts,
                "delay": delay
            })
            
            await asyncio.sleep(delay)
            
            try:
                await self.connect()
                self._reconnect_attempts = 0
                self.logger.info(f"Reconnected to {self.name}")
                return
            except Exception as e:
                self.logger.error(f"Reconnection failed", error=e, context={
                    "attempt": self._reconnect_attempts
                })
        
        self.logger.critical(f"Max reconnection attempts reached for {self.name}")
    
    @property
    def is_connected(self) -> bool:
        """Check if collector is connected."""
        return self._connected
    
    async def health_check(self) -> bool:
        """Perform health check."""
        return self._connected
