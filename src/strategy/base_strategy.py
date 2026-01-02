"""Base strategy class for all trading strategies."""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from ..core.models import Order, Position, Quote, Trade, OrderSide, OrderType, TimeInForce
from ..core.logging.structured_logger import get_logger
from ..market_data.market_data_aggregator import MarketDataAggregator
from ..execution.position_tracker import PositionTracker


@dataclass
class StrategyConfig:
    """Base configuration for trading strategies."""
    strategy_id: str
    strategy_name: str
    symbols: List[str]
    venues: List[str]
    
    # Risk parameters
    max_position_size: float = 10000.0
    max_positions: int = 5
    position_sizing_method: str = 'fixed'  # 'fixed', 'kelly', 'risk_parity'
    
    # Timing parameters
    rebalance_frequency: str = '1h'  # '1m', '5m', '1h', '1d'
    signal_timeout_seconds: int = 300
    
    # Performance thresholds
    min_sharpe_ratio: float = 1.0
    max_drawdown_pct: float = 0.15
    
    # Strategy-specific parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Execution settings
    use_limit_orders: bool = True
    slippage_tolerance_pct: float = 0.001
    

@dataclass
class StrategyMetrics:
    """Performance metrics for a strategy."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    
    # Performance metrics
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Timing metrics
    avg_holding_period_hours: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self,
                 config: StrategyConfig,
                 market_data: MarketDataAggregator,
                 position_tracker: PositionTracker):
        """
        Args:
            config: Strategy configuration
            market_data: Market data aggregator
            position_tracker: Position tracker
        """
        self.config = config
        self.market_data = market_data
        self.position_tracker = position_tracker
        self.logger = get_logger(f"{__name__}.{config.strategy_name}")
        
        # Strategy state
        self._is_running = False
        self._positions: Dict[str, Position] = {}
        self._pending_signals: List[Dict] = []
        
        # Performance tracking
        self.metrics = StrategyMetrics()
        self._equity_curve: List[Dict] = []
        
        # Internal state for strategy logic
        self._state: Dict[str, Any] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize strategy state and load positions."""
        self.logger.info(f"Initializing strategy: {self.config.strategy_name}")
        
        # Load existing positions
        positions = await self.position_tracker.get_all_positions(
            strategy_id=self.config.strategy_id
        )
        
        for position in positions:
            self._positions[position.symbol] = position
        
        # Initialize strategy-specific state
        await self._initialize_strategy()
        
        self.logger.info(
            f"Strategy initialized",
            positions=len(self._positions),
            symbols=self.config.symbols
        )
    
    @abstractmethod
    async def _initialize_strategy(self) -> None:
        """Strategy-specific initialization logic."""
        pass
    
    async def start(self) -> None:
        """Start strategy execution."""
        if self._is_running:
            self.logger.warning("Strategy already running")
            return
        
        self._is_running = True
        self.logger.info(f"Starting strategy: {self.config.strategy_name}")
        
        # Start strategy loop
        asyncio.create_task(self._strategy_loop())
    
    async def stop(self) -> None:
        """Stop strategy execution."""
        self._is_running = False
        self.logger.info(f"Stopping strategy: {self.config.strategy_name}")
        
        # Strategy-specific cleanup
        await self._cleanup_strategy()
    
    async def _strategy_loop(self) -> None:
        """Main strategy execution loop."""
        while self._is_running:
            try:
                # Generate signals
                signals = await self.generate_signals()
                
                # Process signals and generate orders
                if signals:
                    orders = await self._process_signals(signals)
                    
                    # Emit orders for execution
                    for order in orders:
                        await self._emit_order(order)
                
                # Update metrics
                await self._update_metrics()
                
                # Sleep based on rebalance frequency
                await self._sleep_rebalance_period()
                
            except Exception as e:
                self.logger.error("Strategy loop error", error=e, exc_info=True)
                await asyncio.sleep(10)  # Back off on error
    
    @abstractmethod
    async def generate_signals(self) -> List[Dict]:
        """Generate trading signals based on strategy logic.
        
        Returns:
            List of signal dictionaries with structure:
            {
                'symbol': str,
                'action': 'buy'|'sell'|'hold',
                'strength': float (0.0 to 1.0),
                'target_size': Decimal,
                'reason': str,
                'metadata': Dict
            }
        """
        pass
    
    async def _process_signals(self, signals: List[Dict]) -> List[Order]:
        """Process signals and convert to orders."""
        orders = []
        
        for signal in signals:
            try:
                order = await self._signal_to_order(signal)
                if order:
                    orders.append(order)
            except Exception as e:
                self.logger.error(
                    "Failed to process signal",
                    signal=signal,
                    error=e
                )
        
        return orders
    
    async def _signal_to_order(self, signal: Dict) -> Optional[Order]:
        """Convert trading signal to order."""
        symbol = signal['symbol']
        action = signal['action']
        target_size = signal.get('target_size')
        
        if action == 'hold':
            return None
        
        # Get current position
        current_position = self._positions.get(symbol)
        current_size = current_position.quantity if current_position else Decimal('0')
        
        # Calculate order size
        if target_size is not None:
            order_size = abs(target_size - current_size)
        else:
            order_size = await self._calculate_position_size(signal)
        
        if order_size == 0:
            return None
        
        # Determine side
        if action == 'buy':
            side = OrderSide.BUY
        elif action == 'sell':
            side = OrderSide.SELL
        else:
            self.logger.warning(f"Unknown action: {action}")
            return None
        
        # Get current market price
        quote = await self.market_data.get_latest_quote(symbol)
        if not quote:
            self.logger.warning(f"No quote available for {symbol}")
            return None
        
        # Determine order price
        if self.config.use_limit_orders:
            if side == OrderSide.BUY:
                price = quote.ask_price * (Decimal('1') + Decimal(str(self.config.slippage_tolerance_pct)))
            else:
                price = quote.bid_price * (Decimal('1') - Decimal(str(self.config.slippage_tolerance_pct)))
            order_type = OrderType.LIMIT
        else:
            price = None
            order_type = OrderType.MARKET
        
        # Select venue (use first available for now)
        venue = quote.venue
        
        # Create order
        order = Order(
            symbol=symbol,
            venue=venue,
            side=side,
            order_type=order_type,
            quantity=order_size,
            price=price,
            time_in_force=TimeInForce.GTC,
            strategy_id=self.config.strategy_id,
            metadata={
                'signal_strength': signal.get('strength'),
                'signal_reason': signal.get('reason'),
                'strategy_name': self.config.strategy_name
            }
        )
        
        return order
    
    async def _calculate_position_size(self, signal: Dict) -> Decimal:
        """Calculate position size based on sizing method."""
        method = self.config.position_sizing_method
        
        if method == 'fixed':
            return Decimal(str(self.config.max_position_size))
        
        elif method == 'kelly':
            # Kelly criterion: f = (p*b - q) / b
            # where p = win rate, q = loss rate, b = win/loss ratio
            if self.metrics.total_trades < 30:
                # Not enough data, use conservative sizing
                return Decimal(str(self.config.max_position_size * 0.5))
            
            p = self.metrics.win_rate
            q = 1 - p
            b = abs(self.metrics.avg_win / self.metrics.avg_loss) if self.metrics.avg_loss != 0 else 1.0
            
            kelly_fraction = (p * b - q) / b
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
            
            return Decimal(str(self.config.max_position_size * kelly_fraction))
        
        elif method == 'risk_parity':
            # Size position inversely to volatility
            # Would require volatility estimation
            return Decimal(str(self.config.max_position_size * 0.8))
        
        else:
            return Decimal(str(self.config.max_position_size))
    
    async def _emit_order(self, order: Order) -> None:
        """Emit order for execution (to be connected to execution engine)."""
        self.logger.info(
            "Order generated",
            symbol=order.symbol,
            side=order.side.value,
            quantity=float(order.quantity),
            order_type=order.order_type.value
        )
        # In production, this would be connected to OrderManager
    
    async def on_fill(self, order: Order, fill_price: Decimal, fill_quantity: Decimal) -> None:
        """Handle order fill event."""
        async with self._lock:
            # Update position
            position = await self.position_tracker.handle_fill(
                order, fill_quantity, fill_price
            )
            
            self._positions[order.symbol] = position
            
            # Update metrics
            self.metrics.total_trades += 1
            
            self.logger.info(
                "Order filled",
                symbol=order.symbol,
                side=order.side.value,
                quantity=float(fill_quantity),
                price=float(fill_price)
            )
    
    async def _update_metrics(self) -> None:
        """Update strategy performance metrics."""
        # Calculate PnL
        total_pnl = Decimal('0')
        realized_pnl = Decimal('0')
        unrealized_pnl = Decimal('0')
        
        for position in self._positions.values():
            realized_pnl += position.realized_pnl
            unrealized_pnl += position.unrealized_pnl
            total_pnl += position.realized_pnl + position.unrealized_pnl
        
        self.metrics.total_pnl = float(total_pnl)
        self.metrics.realized_pnl = float(realized_pnl)
        self.metrics.unrealized_pnl = float(unrealized_pnl)
        
        # Update equity curve
        self._equity_curve.append({
            'timestamp': datetime.now(timezone.utc),
            'equity': self.metrics.total_pnl
        })
        
        # Calculate risk metrics (simplified)
        if len(self._equity_curve) > 1:
            self.metrics.max_drawdown = self._calculate_max_drawdown()
        
        # Update win rate
        if self.metrics.total_trades > 0:
            self.metrics.win_rate = self.metrics.winning_trades / self.metrics.total_trades
        
        self.metrics.last_updated = datetime.now(timezone.utc)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve."""
        if not self._equity_curve:
            return 0.0
        
        peak = float('-inf')
        max_dd = 0.0
        
        for point in self._equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            
            dd = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    async def _sleep_rebalance_period(self) -> None:
        """Sleep based on rebalance frequency."""
        freq = self.config.rebalance_frequency
        
        sleep_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        
        sleep_seconds = sleep_map.get(freq, 3600)
        await asyncio.sleep(sleep_seconds)
    
    @abstractmethod
    async def _cleanup_strategy(self) -> None:
        """Strategy-specific cleanup logic."""
        pass
    
    def get_state(self) -> Dict:
        """Get current strategy state for persistence."""
        return {
            'strategy_id': self.config.strategy_id,
            'strategy_name': self.config.strategy_name,
            'is_running': self._is_running,
            'positions': {k: str(v.quantity) for k, v in self._positions.items()},
            'metrics': {
                'total_pnl': self.metrics.total_pnl,
                'win_rate': self.metrics.win_rate,
                'sharpe_ratio': self.metrics.sharpe_ratio,
                'max_drawdown': self.metrics.max_drawdown
            },
            'state': self._state
        }
    
    async def load_state(self, state: Dict) -> None:
        """Load strategy state from persistence."""
        self._state = state.get('state', {})
        self.logger.info("Strategy state loaded", state_keys=list(self._state.keys()))
