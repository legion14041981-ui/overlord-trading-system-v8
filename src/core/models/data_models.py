"""Core data models for Overlord Trading System v9."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from .enums import (
    OrderType, OrderSide, OrderStatus, PositionSide,
    VenueType, AssetClass, RiskLevel, StrategyType
)


@dataclass
class Quote:
    """Market quote data (bid/ask)."""
    symbol: str
    venue: str
    timestamp: datetime
    bid_price: Decimal
    bid_size: Decimal
    ask_price: Decimal
    ask_size: Decimal
    spread: Decimal = field(init=False)
    mid_price: Decimal = field(init=False)
    
    def __post_init__(self):
        self.spread = self.ask_price - self.bid_price
        self.mid_price = (self.bid_price + self.ask_price) / Decimal('2')


@dataclass
class Trade:
    """Executed trade record."""
    trade_id: str
    symbol: str
    venue: str
    timestamp: datetime
    price: Decimal
    quantity: Decimal
    side: OrderSide
    is_buyer_maker: bool = False
    

@dataclass
class OHLCV:
    """OHLCV candlestick data."""
    symbol: str
    venue: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    interval: str  # '1m', '5m', '1h', '1d', etc.
    trades_count: Optional[int] = None


@dataclass
class OrderBook:
    """Order book snapshot."""
    symbol: str
    venue: str
    timestamp: datetime
    bids: List[tuple[Decimal, Decimal]]  # [(price, size), ...]
    asks: List[tuple[Decimal, Decimal]]
    
    def get_depth(self, levels: int = 10) -> Dict[str, Any]:
        """Get order book depth statistics."""
        return {
            'bid_depth': sum(size for _, size in self.bids[:levels]),
            'ask_depth': sum(size for _, size in self.asks[:levels]),
            'spread': self.asks[0][0] - self.bids[0][0] if self.bids and self.asks else Decimal('0'),
            'mid_price': (self.bids[0][0] + self.asks[0][0]) / Decimal('2') if self.bids and self.asks else Decimal('0')
        }


@dataclass
class Order:
    """Trading order."""
    order_id: str
    client_order_id: str
    symbol: str
    venue: str
    order_type: OrderType
    side: OrderSide
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal('0')
    average_fill_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    strategy_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity
    
    @property
    def is_complete(self) -> bool:
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]


@dataclass
class Position:
    """Trading position."""
    symbol: str
    venue: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal = field(init=False)
    realized_pnl: Decimal = Decimal('0')
    opened_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    strategy_id: Optional[str] = None
    leverage: Decimal = Decimal('1')
    margin_used: Decimal = Decimal('0')
    liquidation_price: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.unrealized_pnl = self._calculate_unrealized_pnl()
    
    def _calculate_unrealized_pnl(self) -> Decimal:
        if self.side == PositionSide.LONG:
            return (self.current_price - self.entry_price) * self.quantity
        elif self.side == PositionSide.SHORT:
            return (self.entry_price - self.current_price) * self.quantity
        return Decimal('0')
    
    def update_price(self, new_price: Decimal):
        """Update current price and recalculate PnL."""
        self.current_price = new_price
        self.unrealized_pnl = self._calculate_unrealized_pnl()
        self.updated_at = datetime.utcnow()


@dataclass
class Portfolio:
    """Portfolio snapshot."""
    portfolio_id: str
    timestamp: datetime
    total_equity: Decimal
    available_cash: Decimal
    used_margin: Decimal
    positions: List[Position]
    total_unrealized_pnl: Decimal = field(init=False)
    total_realized_pnl: Decimal = Decimal('0')
    leverage_ratio: Decimal = Decimal('1')
    
    def __post_init__(self):
        self.total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions)
    
    def get_position(self, symbol: str, venue: str) -> Optional[Position]:
        """Get position by symbol and venue."""
        for pos in self.positions:
            if pos.symbol == symbol and pos.venue == venue:
                return pos
        return None


@dataclass
class PnL:
    """Profit and Loss record."""
    timestamp: datetime
    strategy_id: Optional[str]
    symbol: Optional[str]
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    fees: Decimal
    net_pnl: Decimal = field(init=False)
    
    def __post_init__(self):
        self.net_pnl = self.realized_pnl + self.unrealized_pnl - self.fees


@dataclass
class RiskMetrics:
    """Risk management metrics."""
    timestamp: datetime
    portfolio_value: Decimal
    var_95: Decimal  # Value at Risk 95%
    var_99: Decimal  # Value at Risk 99%
    max_drawdown: Decimal
    current_drawdown: Decimal
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    correlation_to_benchmark: Optional[Decimal] = None
    liquidity_ratio: Decimal = Decimal('2.0')
    risk_level: RiskLevel = RiskLevel.LOW
    breach_alerts: List[str] = field(default_factory=list)


@dataclass
class Signal:
    """Trading signal from strategy."""
    signal_id: str
    strategy_id: str
    strategy_type: StrategyType
    symbol: str
    venue: str
    timestamp: datetime
    action: OrderSide  # BUY or SELL
    confidence: Decimal  # 0.0 to 1.0
    suggested_quantity: Optional[Decimal] = None
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyPerformance:
    """Strategy performance metrics."""
    strategy_id: str
    strategy_type: StrategyType
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: Decimal
    total_fees: Decimal
    net_pnl: Decimal
    win_rate: Decimal = field(init=False)
    average_win: Decimal = Decimal('0')
    average_loss: Decimal = Decimal('0')
    profit_factor: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Decimal = Decimal('0')
    
    def __post_init__(self):
        self.win_rate = (Decimal(self.winning_trades) / Decimal(self.total_trades) * Decimal('100')) if self.total_trades > 0 else Decimal('0')
