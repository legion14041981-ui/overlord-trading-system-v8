"""Unit tests for market data collectors."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from src.market_data.collectors.base import BaseCollector
from src.market_data.collectors.binance import BinanceCollector
from src.core.models import Quote, Trade, OHLCV


class TestBaseCollector:
    """Test suite for BaseCollector."""
    
    def test_callback_registration(self):
        """Test callback registration."""
        config = {'retry_attempts': 3}
        
        class TestCollector(BaseCollector):
            async def connect(self): pass
            async def disconnect(self): pass
            async def subscribe_quotes(self, symbols): pass
            async def subscribe_trades(self, symbols): pass
            async def fetch_ohlcv(self, symbol, interval, start, end, limit): pass
            async def fetch_order_book(self, symbol, depth): pass
        
        collector = TestCollector('test', config)
        
        async def quote_callback(quote: Quote):
            pass
        
        collector.register_callback('quote', quote_callback)
        
        assert len(collector._callbacks['quote']) == 1
        assert collector._callbacks['quote'][0] == quote_callback
    
    @pytest.mark.asyncio
    async def test_emit_quote(self):
        """Test quote emission to callbacks."""
        config = {'retry_attempts': 3}
        
        class TestCollector(BaseCollector):
            async def connect(self): pass
            async def disconnect(self): pass
            async def subscribe_quotes(self, symbols): pass
            async def subscribe_trades(self, symbols): pass
            async def fetch_ohlcv(self, symbol, interval, start, end, limit): pass
            async def fetch_order_book(self, symbol, depth): pass
        
        collector = TestCollector('test', config)
        
        received_quotes = []
        
        async def quote_callback(quote: Quote):
            received_quotes.append(quote)
        
        collector.register_callback('quote', quote_callback)
        
        test_quote = Quote(
            symbol='BTC/USDT',
            venue='test',
            timestamp=datetime.now(timezone.utc),
            bid_price=Decimal('50000'),
            bid_size=Decimal('1'),
            ask_price=Decimal('50010'),
            ask_size=Decimal('1')
        )
        
        await collector._emit_quote(test_quote)
        
        assert len(received_quotes) == 1
        assert received_quotes[0] == test_quote


class TestBinanceCollector:
    """Test suite for BinanceCollector."""
    
    @pytest.fixture
    def config(self):
        return {
            'base_url': 'https://api.binance.com',
            'websocket_url': 'wss://stream.binance.com:9443/ws',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'timeout': 30,
            'retry_attempts': 3
        }
    
    def test_initialization(self, config):
        """Test collector initialization."""
        collector = BinanceCollector(config)
        
        assert collector.name == 'binance'
        assert collector.base_url == config['base_url']
        assert collector.api_key == config['api_key']
        assert not collector.is_connected
    
    def test_interval_conversion(self, config):
        """Test interval format conversion."""
        collector = BinanceCollector(config)
        
        assert collector._convert_interval('1m') == '1m'
        assert collector._convert_interval('1h') == '1h'
        assert collector._convert_interval('1d') == '1d'
        assert collector._convert_interval('1w') == '1w'
    
    @pytest.mark.asyncio
    async def test_handle_ws_book_ticker(self, config):
        """Test WebSocket book ticker message handling."""
        collector = BinanceCollector(config)
        
        received_quotes = []
        
        async def quote_callback(quote: Quote):
            received_quotes.append(quote)
        
        collector.register_callback('quote', quote_callback)
        
        # Simulate Binance bookTicker message
        message = '''{
            "e": "bookTicker",
            "s": "BTCUSDT",
            "b": "50000.00",
            "B": "1.5",
            "a": "50010.00",
            "A": "2.0",
            "E": 1640000000000
        }'''
        
        await collector._handle_ws_message(message)
        
        assert len(received_quotes) == 1
        quote = received_quotes[0]
        assert quote.symbol == 'BTCUSDT'
        assert quote.bid_price == Decimal('50000.00')
        assert quote.ask_price == Decimal('50010.00')
    
    @pytest.mark.asyncio
    async def test_handle_ws_trade(self, config):
        """Test WebSocket trade message handling."""
        collector = BinanceCollector(config)
        
        received_trades = []
        
        async def trade_callback(trade: Trade):
            received_trades.append(trade)
        
        collector.register_callback('trade', trade_callback)
        
        # Simulate Binance trade message
        message = '''{
            "e": "trade",
            "s": "BTCUSDT",
            "t": 12345,
            "p": "50005.00",
            "q": "0.5",
            "T": 1640000000000,
            "m": false
        }'''
        
        await collector._handle_ws_message(message)
        
        assert len(received_trades) == 1
        trade = received_trades[0]
        assert trade.symbol == 'BTCUSDT'
        assert trade.price == Decimal('50005.00')
        assert trade.quantity == Decimal('0.5')
        assert trade.side == 'sell'  # m=false means taker was seller
