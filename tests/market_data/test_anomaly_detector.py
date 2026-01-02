"""Unit tests for AnomalyDetector."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from src.core.models import Quote, Trade, OHLCV
from src.market_data.anomaly_detector import AnomalyDetector


class TestAnomalyDetector:
    """Test suite for AnomalyDetector."""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector(lookback_window=50, std_threshold=3.0)
    
    def test_no_anomaly_insufficient_data(self, detector):
        """Test no anomaly detection with insufficient historical data."""
        quote = Quote(
            symbol='BTC/USDT',
            venue='binance',
            timestamp=datetime.now(timezone.utc),
            bid_price=Decimal('50000'),
            bid_size=Decimal('1'),
            ask_price=Decimal('50010'),
            ask_size=Decimal('1')
        )
        
        anomaly = detector.check_quote_anomaly(quote)
        assert anomaly is None  # Not enough history
    
    def test_spread_anomaly_detection(self, detector):
        """Test spread anomaly detection."""
        # Build history with normal spreads
        for i in range(30):
            quote = Quote(
                symbol='BTC/USDT',
                venue='binance',
                timestamp=datetime.now(timezone.utc),
                bid_price=Decimal('50000'),
                bid_size=Decimal('1'),
                ask_price=Decimal('50010'),  # $10 spread
                ask_size=Decimal('1')
            )
            detector.check_quote_anomaly(quote)
        
        # Insert anomalous spread
        anomalous_quote = Quote(
            symbol='BTC/USDT',
            venue='binance',
            timestamp=datetime.now(timezone.utc),
            bid_price=Decimal('50000'),
            bid_size=Decimal('1'),
            ask_price=Decimal('50100'),  # $100 spread (10x normal)
            ask_size=Decimal('1')
        )
        
        anomaly = detector.check_quote_anomaly(anomalous_quote)
        
        assert anomaly is not None
        assert anomaly['type'] == 'spread_anomaly'
        assert anomaly['severity'] in ['MEDIUM', 'HIGH']
    
    def test_crossed_quote_detection(self, detector):
        """Test crossed quote detection (bid >= ask)."""
        crossed_quote = Quote(
            symbol='BTC/USDT',
            venue='binance',
            timestamp=datetime.now(timezone.utc),
            bid_price=Decimal('50020'),
            bid_size=Decimal('1'),
            ask_price=Decimal('50010'),  # Ask < Bid (crossed)
            ask_size=Decimal('1')
        )
        
        anomaly = detector.check_quote_anomaly(crossed_quote)
        
        assert anomaly is not None
        assert anomaly['type'] == 'crossed_quote'
        assert anomaly['severity'] == 'CRITICAL'
    
    def test_price_anomaly_detection(self, detector):
        """Test trade price anomaly detection."""
        # Build history with normal prices
        for i in range(30):
            trade = Trade(
                trade_id=str(i),
                symbol='BTC/USDT',
                venue='binance',
                timestamp=datetime.now(timezone.utc),
                side='buy',
                price=Decimal('50000'),
                quantity=Decimal('1')
            )
            detector.check_trade_anomaly(trade)
        
        # Insert anomalous price
        anomalous_trade = Trade(
            trade_id='999',
            symbol='BTC/USDT',
            venue='binance',
            timestamp=datetime.now(timezone.utc),
            side='buy',
            price=Decimal('55000'),  # 10% higher
            quantity=Decimal('1')
        )
        
        anomaly = detector.check_trade_anomaly(anomalous_trade)
        
        assert anomaly is not None
        assert anomaly['type'] == 'price_anomaly'
    
    def test_volume_spike_detection(self, detector):
        """Test volume spike detection in OHLCV."""
        # Build history with normal volume
        for i in range(30):
            ohlcv = OHLCV(
                symbol='BTC/USDT',
                venue='binance',
                interval='1h',
                timestamp=datetime.now(timezone.utc),
                open=Decimal('50000'),
                high=Decimal('50100'),
                low=Decimal('49900'),
                close=Decimal('50050'),
                volume=Decimal('100'),  # Normal volume
                quote_volume=Decimal('5000000'),
                trades_count=1000
            )
            detector.check_ohlcv_anomaly(ohlcv)
        
        # Insert volume spike
        spike_ohlcv = OHLCV(
            symbol='BTC/USDT',
            venue='binance',
            interval='1h',
            timestamp=datetime.now(timezone.utc),
            open=Decimal('50000'),
            high=Decimal('50100'),
            low=Decimal('49900'),
            close=Decimal('50050'),
            volume=Decimal('1000'),  # 10x normal volume
            quote_volume=Decimal('50000000'),
            trades_count=10000
        )
        
        anomaly = detector.check_ohlcv_anomaly(spike_ohlcv)
        
        assert anomaly is not None
        assert anomaly['type'] == 'volume_spike'
    
    def test_stale_data_detection(self, detector):
        """Test stale data detection."""
        # Recent data
        recent = datetime.now(timezone.utc)
        assert detector.check_stale_data(recent, max_age_seconds=60) is False
        
        # Stale data (2 minutes old)
        stale = datetime.now(timezone.utc) - timedelta(minutes=2)
        assert detector.check_stale_data(stale, max_age_seconds=60) is True
    
    def test_reset_history(self, detector):
        """Test history reset functionality."""
        # Build some history
        for i in range(10):
            quote = Quote(
                symbol='BTC/USDT',
                venue='binance',
                timestamp=datetime.now(timezone.utc),
                bid_price=Decimal('50000'),
                bid_size=Decimal('1'),
                ask_price=Decimal('50010'),
                ask_size=Decimal('1')
            )
            detector.check_quote_anomaly(quote)
        
        # Verify history exists
        assert len(detector._spread_history) > 0
        
        # Reset specific symbol
        detector.reset_history('BTC/USDT')
        assert len(detector._spread_history) == 0
        
        # Build history again
        for i in range(10):
            quote = Quote(
                symbol='ETH/USDT',
                venue='binance',
                timestamp=datetime.now(timezone.utc),
                bid_price=Decimal('3000'),
                bid_size=Decimal('1'),
                ask_price=Decimal('3005'),
                ask_size=Decimal('1')
            )
            detector.check_quote_anomaly(quote)
        
        # Reset all
        detector.reset_history()
        assert len(detector._spread_history) == 0
