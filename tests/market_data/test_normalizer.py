"""Unit tests for DataNormalizer."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from src.core.models import Quote, Trade, OHLCV
from src.market_data.normalizer import DataNormalizer


class TestDataNormalizer:
    """Test suite for DataNormalizer."""
    
    @pytest.fixture
    def normalizer(self):
        return DataNormalizer()
    
    def test_normalize_symbol_binance(self, normalizer):
        """Test Binance symbol normalization."""
        assert normalizer.normalize_symbol('BTCUSDT', 'binance') == 'BTC/USDT'
        assert normalizer.normalize_symbol('ETHUSDT', 'binance') == 'ETH/USDT'
    
    def test_normalize_symbol_coinbase(self, normalizer):
        """Test Coinbase symbol normalization."""
        assert normalizer.normalize_symbol('BTC-USD', 'coinbase') == 'BTC/USD'
        assert normalizer.normalize_symbol('ETH-USDT', 'coinbase') == 'ETH/USDT'
    
    def test_normalize_symbol_auto_detect(self, normalizer):
        """Test automatic symbol format detection."""
        assert normalizer.normalize_symbol('SOLUSDT', 'unknown') == 'SOL/USDT'
        assert normalizer.normalize_symbol('ADA-USD', 'unknown') == 'ADA/USD'
    
    def test_normalize_quote(self, normalizer):
        """Test quote normalization."""
        quote = Quote(
            symbol='BTCUSDT',
            venue='binance',
            timestamp=datetime.now(timezone.utc),
            bid_price=Decimal('50000.00'),
            bid_size=Decimal('1.5'),
            ask_price=Decimal('50010.00'),
            ask_size=Decimal('2.0')
        )
        
        normalized = normalizer.normalize_quote(quote)
        
        assert normalized.symbol == 'BTC/USDT'
        assert normalized.spread == Decimal('10.00')
        assert normalized.mid_price == Decimal('50005.00')
    
    def test_normalize_trade(self, normalizer):
        """Test trade normalization."""
        trade = Trade(
            trade_id='12345',
            symbol='ETHUSDT',
            venue='binance',
            timestamp=datetime.now(timezone.utc),
            side='buy',
            price=Decimal('3000.50'),
            quantity=Decimal('10.0')
        )
        
        normalized = normalizer.normalize_trade(trade)
        
        assert normalized.symbol == 'ETH/USDT'
        assert normalized.side == 'buy'
        assert normalized.notional == Decimal('30005.00')
    
    def test_normalize_ohlcv(self, normalizer):
        """Test OHLCV normalization."""
        ohlcv = OHLCV(
            symbol='BTCUSDT',
            venue='binance',
            interval='1h',
            timestamp=datetime.now(timezone.utc),
            open=Decimal('50000'),
            high=Decimal('51000'),
            low=Decimal('49500'),
            close=Decimal('50500'),
            volume=Decimal('100'),
            quote_volume=Decimal('5000000'),
            trades_count=1000
        )
        
        normalized = normalizer.normalize_ohlcv(ohlcv)
        
        assert normalized.symbol == 'BTC/USDT'
        assert normalized.vwap == Decimal('50000')
    
    def test_cross_exchange_spread(self, normalizer):
        """Test cross-exchange spread calculation."""
        quotes = [
            Quote(
                symbol='BTCUSDT',
                venue='binance',
                timestamp=datetime.now(timezone.utc),
                bid_price=Decimal('50000'),
                bid_size=Decimal('1'),
                ask_price=Decimal('50010'),
                ask_size=Decimal('1')
            ),
            Quote(
                symbol='BTC-USDT',
                venue='coinbase',
                timestamp=datetime.now(timezone.utc),
                bid_price=Decimal('49995'),
                bid_size=Decimal('1'),
                ask_price=Decimal('50005'),
                ask_size=Decimal('1')
            )
        ]
        
        spreads = normalizer.calculate_cross_exchange_spread(quotes)
        
        assert 'BTC/USDT' in spreads
        assert spreads['BTC/USDT']['best_bid'] == Decimal('50000')
        assert spreads['BTC/USDT']['best_ask'] == Decimal('50005')
        assert spreads['BTC/USDT']['best_bid_venue'] == 'binance'
        assert spreads['BTC/USDT']['best_ask_venue'] == 'coinbase'
