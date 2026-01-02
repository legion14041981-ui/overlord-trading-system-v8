"""Data normalization and standardization layer."""
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

from ..core.models import Quote, Trade, OHLCV
from ..core.logging.structured_logger import get_logger


class DataNormalizer:
    """Normalizes market data from different exchanges to unified format."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._symbol_mappings = self._build_symbol_mappings()
    
    def _build_symbol_mappings(self) -> Dict[str, Dict[str, str]]:
        """Build symbol mappings between exchanges."""
        return {
            'binance': {
                'BTCUSDT': 'BTC/USDT',
                'ETHUSDT': 'ETH/USDT',
                'BNBUSDT': 'BNB/USDT',
                'SOLUSDT': 'SOL/USDT',
                'ADAUSDT': 'ADA/USDT'
            },
            'coinbase': {
                'BTC-USD': 'BTC/USD',
                'ETH-USD': 'ETH/USD',
                'SOL-USD': 'SOL/USD',
                'BTC-USDT': 'BTC/USDT',
                'ETH-USDT': 'ETH/USDT'
            },
            'bybit': {
                'BTCUSDT': 'BTC/USDT',
                'ETHUSDT': 'ETH/USDT',
                'SOLUSDT': 'SOL/USDT'
            }
        }
    
    def normalize_symbol(self, symbol: str, venue: str) -> str:
        """Normalize symbol to unified format (BASE/QUOTE)."""
        mappings = self._symbol_mappings.get(venue, {})
        normalized = mappings.get(symbol, symbol)
        
        # If not in mappings, try to detect format
        if normalized == symbol:
            if '-' in symbol:
                normalized = symbol.replace('-', '/')
            elif symbol.endswith('USDT'):
                base = symbol[:-4]
                normalized = f"{base}/USDT"
            elif symbol.endswith('USD'):
                base = symbol[:-3]
                normalized = f"{base}/USD"
        
        return normalized
    
    def normalize_quote(self, quote: Quote) -> Quote:
        """Normalize quote data."""
        normalized_symbol = self.normalize_symbol(quote.symbol, quote.venue)
        
        # Validate spread
        if quote.ask_price <= quote.bid_price:
            self.logger.warning("Invalid spread detected", {
                "symbol": quote.symbol,
                "venue": quote.venue,
                "bid": str(quote.bid_price),
                "ask": str(quote.ask_price)
            })
        
        return Quote(
            symbol=normalized_symbol,
            venue=quote.venue,
            timestamp=quote.timestamp,
            bid_price=quote.bid_price,
            bid_size=quote.bid_size,
            ask_price=quote.ask_price,
            ask_size=quote.ask_size,
            spread=quote.ask_price - quote.bid_price,
            mid_price=(quote.bid_price + quote.ask_price) / Decimal('2')
        )
    
    def normalize_trade(self, trade: Trade) -> Trade:
        """Normalize trade data."""
        normalized_symbol = self.normalize_symbol(trade.symbol, trade.venue)
        
        # Standardize side notation
        side = trade.side.lower()
        if side not in ['buy', 'sell']:
            self.logger.warning(f"Unknown trade side: {side}", {
                "symbol": trade.symbol,
                "venue": trade.venue
            })
            side = 'buy' if side in ['bid', 'long'] else 'sell'
        
        return Trade(
            trade_id=trade.trade_id,
            symbol=normalized_symbol,
            venue=trade.venue,
            timestamp=trade.timestamp,
            side=side,
            price=trade.price,
            quantity=trade.quantity,
            notional=trade.price * trade.quantity
        )
    
    def normalize_ohlcv(self, ohlcv: OHLCV) -> OHLCV:
        """Normalize OHLCV data."""
        normalized_symbol = self.normalize_symbol(ohlcv.symbol, ohlcv.venue)
        
        # Validate OHLCV integrity
        if not (ohlcv.low <= ohlcv.open <= ohlcv.high and
                ohlcv.low <= ohlcv.close <= ohlcv.high):
            self.logger.warning("Invalid OHLCV data", {
                "symbol": ohlcv.symbol,
                "venue": ohlcv.venue,
                "timestamp": ohlcv.timestamp.isoformat(),
                "ohlc": f"O:{ohlcv.open} H:{ohlcv.high} L:{ohlcv.low} C:{ohlcv.close}"
            })
        
        return OHLCV(
            symbol=normalized_symbol,
            venue=ohlcv.venue,
            interval=ohlcv.interval,
            timestamp=ohlcv.timestamp,
            open=ohlcv.open,
            high=ohlcv.high,
            low=ohlcv.low,
            close=ohlcv.close,
            volume=ohlcv.volume,
            quote_volume=ohlcv.quote_volume,
            trades_count=ohlcv.trades_count,
            vwap=ohlcv.quote_volume / ohlcv.volume if ohlcv.volume > 0 else None
        )
    
    def normalize_batch_quotes(self, quotes: List[Quote]) -> List[Quote]:
        """Normalize batch of quotes."""
        return [self.normalize_quote(q) for q in quotes]
    
    def normalize_batch_trades(self, trades: List[Trade]) -> List[Trade]:
        """Normalize batch of trades."""
        return [self.normalize_trade(t) for t in trades]
    
    def normalize_batch_ohlcv(self, ohlcvs: List[OHLCV]) -> List[OHLCV]:
        """Normalize batch of OHLCV data."""
        return [self.normalize_ohlcv(o) for o in ohlcvs]
    
    def calculate_cross_exchange_spread(self, quotes: List[Quote]) -> Dict[str, Any]:
        """Calculate spread across exchanges for same symbol."""
        if not quotes:
            return {}
        
        # Group by normalized symbol
        by_symbol: Dict[str, List[Quote]] = {}
        for quote in quotes:
            norm_symbol = self.normalize_symbol(quote.symbol, quote.venue)
            if norm_symbol not in by_symbol:
                by_symbol[norm_symbol] = []
            by_symbol[norm_symbol].append(quote)
        
        spreads = {}
        for symbol, symbol_quotes in by_symbol.items():
            if len(symbol_quotes) < 2:
                continue
            
            best_bid = max(q.bid_price for q in symbol_quotes)
            best_ask = min(q.ask_price for q in symbol_quotes)
            
            best_bid_venue = next(q.venue for q in symbol_quotes if q.bid_price == best_bid)
            best_ask_venue = next(q.venue for q in symbol_quotes if q.ask_price == best_ask)
            
            spreads[symbol] = {
                'best_bid': best_bid,
                'best_bid_venue': best_bid_venue,
                'best_ask': best_ask,
                'best_ask_venue': best_ask_venue,
                'spread': best_ask - best_bid,
                'spread_bps': float((best_ask - best_bid) / best_bid * 10000) if best_bid > 0 else None
            }
        
        return spreads
