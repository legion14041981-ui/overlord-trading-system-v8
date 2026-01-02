"""Real-time anomaly detection for market data."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from collections import deque
import statistics

from ..core.models import Quote, Trade, OHLCV
from ..core.logging.structured_logger import get_logger


class AnomalyDetector:
    """Detects anomalies in market data streams."""
    
    def __init__(self, lookback_window: int = 100, std_threshold: float = 3.0):
        self.lookback_window = lookback_window
        self.std_threshold = std_threshold
        self.logger = get_logger(__name__)
        
        # Circular buffers for each symbol
        self._price_history: Dict[str, deque] = {}
        self._volume_history: Dict[str, deque] = {}
        self._spread_history: Dict[str, deque] = {}
        self._trade_size_history: Dict[str, deque] = {}
    
    def _get_buffer(self, buffer_dict: Dict[str, deque], key: str) -> deque:
        """Get or create circular buffer."""
        if key not in buffer_dict:
            buffer_dict[key] = deque(maxlen=self.lookback_window)
        return buffer_dict[key]
    
    def check_quote_anomaly(self, quote: Quote) -> Optional[Dict[str, Any]]:
        """Detect anomalies in quote data."""
        key = f"{quote.symbol}_{quote.venue}"
        
        # Check spread anomaly
        spread = float(quote.ask_price - quote.bid_price)
        spread_buffer = self._get_buffer(self._spread_history, key)
        
        anomaly = None
        
        if len(spread_buffer) >= 20:  # Minimum samples
            mean_spread = statistics.mean(spread_buffer)
            std_spread = statistics.stdev(spread_buffer) if len(spread_buffer) > 1 else 0
            
            if std_spread > 0:
                z_score = (spread - mean_spread) / std_spread
                
                if abs(z_score) > self.std_threshold:
                    anomaly = {
                        'type': 'spread_anomaly',
                        'symbol': quote.symbol,
                        'venue': quote.venue,
                        'timestamp': quote.timestamp,
                        'current_spread': spread,
                        'mean_spread': mean_spread,
                        'std_spread': std_spread,
                        'z_score': z_score,
                        'severity': 'HIGH' if abs(z_score) > 5 else 'MEDIUM'
                    }
                    
                    self.logger.warning("Spread anomaly detected", anomaly)
        
        spread_buffer.append(spread)
        
        # Check for crossed quotes (bid >= ask)
        if quote.bid_price >= quote.ask_price:
            anomaly = {
                'type': 'crossed_quote',
                'symbol': quote.symbol,
                'venue': quote.venue,
                'timestamp': quote.timestamp,
                'bid_price': float(quote.bid_price),
                'ask_price': float(quote.ask_price),
                'severity': 'CRITICAL'
            }
            self.logger.error("Crossed quote detected", anomaly)
        
        return anomaly
    
    def check_trade_anomaly(self, trade: Trade) -> Optional[Dict[str, Any]]:
        """Detect anomalies in trade data."""
        key = f"{trade.symbol}_{trade.venue}"
        
        price = float(trade.price)
        size = float(trade.quantity)
        
        price_buffer = self._get_buffer(self._price_history, key)
        size_buffer = self._get_buffer(self._trade_size_history, key)
        
        anomaly = None
        
        # Check price anomaly
        if len(price_buffer) >= 20:
            mean_price = statistics.mean(price_buffer)
            std_price = statistics.stdev(price_buffer) if len(price_buffer) > 1 else 0
            
            if std_price > 0:
                z_score = (price - mean_price) / std_price
                
                if abs(z_score) > self.std_threshold:
                    anomaly = {
                        'type': 'price_anomaly',
                        'symbol': trade.symbol,
                        'venue': trade.venue,
                        'timestamp': trade.timestamp,
                        'current_price': price,
                        'mean_price': mean_price,
                        'std_price': std_price,
                        'z_score': z_score,
                        'deviation_pct': ((price - mean_price) / mean_price * 100),
                        'severity': 'HIGH' if abs(z_score) > 5 else 'MEDIUM'
                    }
                    
                    self.logger.warning("Price anomaly detected", anomaly)
        
        # Check trade size anomaly
        if len(size_buffer) >= 20:
            mean_size = statistics.mean(size_buffer)
            std_size = statistics.stdev(size_buffer) if len(size_buffer) > 1 else 0
            
            if std_size > 0:
                z_score = (size - mean_size) / std_size
                
                if z_score > self.std_threshold:  # Only flag unusually large trades
                    if not anomaly:
                        anomaly = {}
                    anomaly.update({
                        'trade_size_anomaly': True,
                        'current_size': size,
                        'mean_size': mean_size,
                        'size_z_score': z_score
                    })
                    
                    self.logger.info("Large trade detected", {
                        'symbol': trade.symbol,
                        'venue': trade.venue,
                        'size': size,
                        'z_score': z_score
                    })
        
        price_buffer.append(price)
        size_buffer.append(size)
        
        return anomaly
    
    def check_ohlcv_anomaly(self, ohlcv: OHLCV) -> Optional[Dict[str, Any]]:
        """Detect anomalies in OHLCV data."""
        key = f"{ohlcv.symbol}_{ohlcv.venue}_{ohlcv.interval}"
        
        volume = float(ohlcv.volume)
        volume_buffer = self._get_buffer(self._volume_history, key)
        
        anomaly = None
        
        # Check volume anomaly
        if len(volume_buffer) >= 20:
            mean_volume = statistics.mean(volume_buffer)
            std_volume = statistics.stdev(volume_buffer) if len(volume_buffer) > 1 else 0
            
            if std_volume > 0 and mean_volume > 0:
                z_score = (volume - mean_volume) / std_volume
                
                if z_score > self.std_threshold:
                    anomaly = {
                        'type': 'volume_spike',
                        'symbol': ohlcv.symbol,
                        'venue': ohlcv.venue,
                        'interval': ohlcv.interval,
                        'timestamp': ohlcv.timestamp,
                        'current_volume': volume,
                        'mean_volume': mean_volume,
                        'volume_multiplier': volume / mean_volume,
                        'z_score': z_score,
                        'severity': 'HIGH' if z_score > 5 else 'MEDIUM'
                    }
                    
                    self.logger.info("Volume spike detected", anomaly)
        
        volume_buffer.append(volume)
        
        # Check price range anomaly
        price_range = float(ohlcv.high - ohlcv.low)
        avg_price = float((ohlcv.high + ohlcv.low) / 2)
        
        if avg_price > 0:
            range_pct = (price_range / avg_price) * 100
            
            if range_pct > 10:  # More than 10% intrabar range
                if not anomaly:
                    anomaly = {}
                anomaly.update({
                    'wide_range': True,
                    'range_pct': range_pct,
                    'high': float(ohlcv.high),
                    'low': float(ohlcv.low)
                })
                
                self.logger.warning("Wide price range detected", {
                    'symbol': ohlcv.symbol,
                    'venue': ohlcv.venue,
                    'range_pct': range_pct
                })
        
        return anomaly
    
    def check_stale_data(self, timestamp: datetime, max_age_seconds: int = 60) -> bool:
        """Check if data is stale."""
        now = datetime.utcnow()
        age = (now - timestamp.replace(tzinfo=None)).total_seconds()
        
        if age > max_age_seconds:
            self.logger.warning("Stale data detected", {
                'timestamp': timestamp.isoformat(),
                'age_seconds': age,
                'max_age': max_age_seconds
            })
            return True
        
        return False
    
    def reset_history(self, symbol: Optional[str] = None) -> None:
        """Reset anomaly detection history."""
        if symbol:
            # Clear specific symbol
            for buffer_dict in [self._price_history, self._volume_history, 
                               self._spread_history, self._trade_size_history]:
                keys_to_remove = [k for k in buffer_dict.keys() if k.startswith(symbol)]
                for key in keys_to_remove:
                    del buffer_dict[key]
            
            self.logger.info(f"Reset anomaly history for {symbol}")
        else:
            # Clear all
            self._price_history.clear()
            self._volume_history.clear()
            self._spread_history.clear()
            self._trade_size_history.clear()
            
            self.logger.info("Reset all anomaly history")
