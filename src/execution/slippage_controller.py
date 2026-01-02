"""Slippage control and pre-trade cost estimation."""
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from ..core.models import OrderSide, Quote
from ..core.logging.structured_logger import get_logger


class SlippageController:
    """Controls and monitors slippage for order execution."""
    
    def __init__(self, tolerance_bps: float = 10.0):
        self.tolerance_bps = tolerance_bps  # Basis points (0.1% = 10 bps)
        self.logger = get_logger(__name__)
        
        # Market data cache
        self._latest_quotes: Dict[str, Quote] = {}
        
        # Historical slippage tracking
        self._realized_slippage: Dict[str, list] = {}
    
    def update_tolerance(self, tolerance_bps: float) -> None:
        """Update slippage tolerance."""
        self.tolerance_bps = tolerance_bps
        self.logger.info(f"Slippage tolerance updated to {tolerance_bps} bps")
    
    def update_quote(self, quote: Quote) -> None:
        """Update latest quote for slippage calculation."""
        key = f"{quote.symbol}_{quote.venue}"
        self._latest_quotes[key] = quote
    
    async def check_slippage(self, symbol: str, side: OrderSide,
                            quantity: Decimal, limit_price: Optional[Decimal] = None) -> bool:
        """Check if expected slippage is within tolerance."""
        # Get best quote
        quote = self._get_best_quote(symbol)
        
        if not quote:
            self.logger.warning(f"No quote available for slippage check: {symbol}")
            return True  # Allow execution (fail open)
        
        # Estimate execution price
        estimated_price = self._estimate_execution_price(quote, side, quantity)
        
        # Get reference price
        if limit_price:
            reference_price = limit_price
        else:
            reference_price = quote.mid_price or (
                (quote.bid_price + quote.ask_price) / Decimal('2')
            )
        
        # Calculate slippage
        if reference_price == 0:
            return False
        
        slippage = abs(estimated_price - reference_price) / reference_price
        slippage_bps = float(slippage * 10000)
        
        # Check against tolerance
        within_tolerance = slippage_bps <= self.tolerance_bps
        
        if not within_tolerance:
            self.logger.warning("Slippage tolerance exceeded", {
                "symbol": symbol,
                "side": side.value,
                "quantity": str(quantity),
                "estimated_price": str(estimated_price),
                "reference_price": str(reference_price),
                "slippage_bps": slippage_bps,
                "tolerance_bps": self.tolerance_bps
            })
        
        return within_tolerance
    
    def _estimate_execution_price(self, quote: Quote, side: OrderSide, 
                                  quantity: Decimal) -> Decimal:
        """Estimate execution price considering market impact."""
        if side == OrderSide.BUY:
            # Use ask price plus impact
            base_price = quote.ask_price
            available_liquidity = quote.ask_size
        else:
            # Use bid price minus impact
            base_price = quote.bid_price
            available_liquidity = quote.bid_size
        
        # Simple market impact model
        if available_liquidity > 0:
            liquidity_ratio = float(quantity / available_liquidity)
            
            # Impact increases with order size relative to liquidity
            if liquidity_ratio < 0.1:
                impact = Decimal('0')  # Negligible impact
            elif liquidity_ratio < 0.5:
                impact = base_price * Decimal('0.0005')  # 5 bps
            elif liquidity_ratio < 1.0:
                impact = base_price * Decimal('0.001')  # 10 bps
            else:
                impact = base_price * Decimal('0.002')  # 20 bps
            
            if side == OrderSide.BUY:
                return base_price + impact
            else:
                return base_price - impact
        
        return base_price
    
    def _get_best_quote(self, symbol: str) -> Optional[Quote]:
        """Get best available quote across venues."""
        symbol_quotes = [
            q for key, q in self._latest_quotes.items()
            if q.symbol == symbol
        ]
        
        if not symbol_quotes:
            return None
        
        # Return quote with tightest spread
        return min(symbol_quotes, key=lambda q: q.ask_price - q.bid_price)
    
    def record_realized_slippage(self, symbol: str, side: OrderSide,
                                expected_price: Decimal,
                                actual_price: Decimal) -> None:
        """Record realized slippage for analysis."""
        slippage = abs(actual_price - expected_price) / expected_price
        slippage_bps = float(slippage * 10000)
        
        if symbol not in self._realized_slippage:
            self._realized_slippage[symbol] = []
        
        self._realized_slippage[symbol].append({
            'timestamp': datetime.utcnow(),
            'side': side.value,
            'expected_price': float(expected_price),
            'actual_price': float(actual_price),
            'slippage_bps': slippage_bps
        })
        
        # Keep only recent history (last 1000 records per symbol)
        if len(self._realized_slippage[symbol]) > 1000:
            self._realized_slippage[symbol] = self._realized_slippage[symbol][-1000:]
        
        self.logger.info("Realized slippage recorded", {
            "symbol": symbol,
            "side": side.value,
            "slippage_bps": slippage_bps
        })
    
    def get_average_slippage(self, symbol: str, 
                            lookback_minutes: int = 60) -> Optional[float]:
        """Calculate average realized slippage."""
        if symbol not in self._realized_slippage:
            return None
        
        cutoff = datetime.utcnow() - timedelta(minutes=lookback_minutes)
        recent = [
            record['slippage_bps']
            for record in self._realized_slippage[symbol]
            if record['timestamp'] >= cutoff
        ]
        
        if not recent:
            return None
        
        return sum(recent) / len(recent)
    
    def get_slippage_statistics(self, symbol: Optional[str] = None) -> Dict:
        """Get slippage statistics."""
        if symbol:
            records = self._realized_slippage.get(symbol, [])
            symbols = [symbol]
        else:
            records = []
            for sym_records in self._realized_slippage.values():
                records.extend(sym_records)
            symbols = list(self._realized_slippage.keys())
        
        if not records:
            return {
                'count': 0,
                'symbols': symbols
            }
        
        slippages = [r['slippage_bps'] for r in records]
        
        return {
            'count': len(records),
            'symbols': symbols,
            'average_bps': sum(slippages) / len(slippages),
            'min_bps': min(slippages),
            'max_bps': max(slippages),
            'median_bps': sorted(slippages)[len(slippages) // 2]
        }
