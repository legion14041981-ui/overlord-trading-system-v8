"""Abstract base classes for data storage."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from ..models import Quote, Trade, OHLCV, Order, Position, Portfolio, PnL, RiskMetrics


class QuoteStorage(ABC):
    """Abstract storage for market quotes."""
    
    @abstractmethod
    async def save_quote(self, quote: Quote) -> None:
        """Save a single quote."""
        pass
    
    @abstractmethod
    async def save_quotes_bulk(self, quotes: List[Quote]) -> None:
        """Save multiple quotes in batch."""
        pass
    
    @abstractmethod
    async def get_latest_quote(self, symbol: str, venue: str) -> Optional[Quote]:
        """Get the most recent quote for symbol."""
        pass
    
    @abstractmethod
    async def get_quotes_range(self, symbol: str, venue: str, 
                               start: datetime, end: datetime) -> List[Quote]:
        """Get quotes within time range."""
        pass


class TradeStorage(ABC):
    """Abstract storage for executed trades."""
    
    @abstractmethod
    async def save_trade(self, trade: Trade) -> None:
        """Save a single trade."""
        pass
    
    @abstractmethod
    async def save_trades_bulk(self, trades: List[Trade]) -> None:
        """Save multiple trades in batch."""
        pass
    
    @abstractmethod
    async def get_trades_range(self, symbol: str, venue: str,
                               start: datetime, end: datetime) -> List[Trade]:
        """Get trades within time range."""
        pass
    
    @abstractmethod
    async def get_trades_by_id(self, trade_ids: List[str]) -> List[Trade]:
        """Get trades by their IDs."""
        pass


class OHLCVStorage(ABC):
    """Abstract storage for OHLCV candlestick data."""
    
    @abstractmethod
    async def save_ohlcv(self, ohlcv: OHLCV) -> None:
        """Save a single OHLCV candle."""
        pass
    
    @abstractmethod
    async def save_ohlcv_bulk(self, ohlcvs: List[OHLCV]) -> None:
        """Save multiple OHLCV candles in batch."""
        pass
    
    @abstractmethod
    async def get_ohlcv_range(self, symbol: str, venue: str, interval: str,
                              start: datetime, end: datetime) -> List[OHLCV]:
        """Get OHLCV data within time range."""
        pass
    
    @abstractmethod
    async def get_latest_ohlcv(self, symbol: str, venue: str, interval: str) -> Optional[OHLCV]:
        """Get the most recent OHLCV candle."""
        pass


class OrderStorage(ABC):
    """Abstract storage for orders."""
    
    @abstractmethod
    async def save_order(self, order: Order) -> None:
        """Save or update an order."""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        pass
    
    @abstractmethod
    async def get_orders_by_status(self, status: str, limit: int = 100) -> List[Order]:
        """Get orders by status."""
        pass
    
    @abstractmethod
    async def get_orders_by_strategy(self, strategy_id: str, 
                                     start: Optional[datetime] = None,
                                     end: Optional[datetime] = None) -> List[Order]:
        """Get orders for a specific strategy."""
        pass
    
    @abstractmethod
    async def update_order_status(self, order_id: str, status: str, 
                                  filled_quantity: Optional[Decimal] = None,
                                  average_fill_price: Optional[Decimal] = None) -> None:
        """Update order status and fill information."""
        pass


class PositionStorage(ABC):
    """Abstract storage for positions."""
    
    @abstractmethod
    async def save_position(self, position: Position) -> None:
        """Save or update a position."""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str, venue: str) -> Optional[Position]:
        """Get position by symbol and venue."""
        pass
    
    @abstractmethod
    async def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        pass
    
    @abstractmethod
    async def get_positions_by_strategy(self, strategy_id: str) -> List[Position]:
        """Get all positions for a specific strategy."""
        pass
    
    @abstractmethod
    async def close_position(self, symbol: str, venue: str, 
                            realized_pnl: Decimal) -> None:
        """Mark position as closed."""
        pass


class PortfolioStorage(ABC):
    """Abstract storage for portfolio snapshots."""
    
    @abstractmethod
    async def save_portfolio(self, portfolio: Portfolio) -> None:
        """Save portfolio snapshot."""
        pass
    
    @abstractmethod
    async def get_latest_portfolio(self) -> Optional[Portfolio]:
        """Get the most recent portfolio snapshot."""
        pass
    
    @abstractmethod
    async def get_portfolio_history(self, start: datetime, 
                                    end: datetime) -> List[Portfolio]:
        """Get portfolio snapshots within time range."""
        pass


class PnLStorage(ABC):
    """Abstract storage for P&L records."""
    
    @abstractmethod
    async def save_pnl(self, pnl: PnL) -> None:
        """Save P&L record."""
        pass
    
    @abstractmethod
    async def get_pnl_history(self, start: datetime, end: datetime,
                              strategy_id: Optional[str] = None,
                              symbol: Optional[str] = None) -> List[PnL]:
        """Get P&L history with optional filters."""
        pass
    
    @abstractmethod
    async def get_total_pnl(self, start: datetime, end: datetime,
                           strategy_id: Optional[str] = None) -> Dict[str, Decimal]:
        """Calculate total P&L statistics."""
        pass


class RiskMetricsStorage(ABC):
    """Abstract storage for risk metrics."""
    
    @abstractmethod
    async def save_risk_metrics(self, metrics: RiskMetrics) -> None:
        """Save risk metrics snapshot."""
        pass
    
    @abstractmethod
    async def get_latest_risk_metrics(self) -> Optional[RiskMetrics]:
        """Get the most recent risk metrics."""
        pass
    
    @abstractmethod
    async def get_risk_metrics_history(self, start: datetime, 
                                       end: datetime) -> List[RiskMetrics]:
        """Get risk metrics history."""
        pass
