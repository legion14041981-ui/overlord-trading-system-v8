"""Momentum-based trading strategy implementation."""
import asyncio
from typing import List, Optional, Deque
from collections import deque
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import numpy as np

from .base_strategy import BaseStrategy, Signal, SignalStrength, StrategyConfig
from ..core.models.order import OrderSide
from ..core.models.market_data import Bar
from ..core.logging.structured_logger import get_logger


class MomentumStrategy(BaseStrategy):
    """Momentum strategy using RSI, MACD, and trend following.
    
    Entry signals:
    - Strong momentum: RSI > 70 or < 30, MACD crossover, price above MA
    - Trend confirmation from multiple timeframes
    
    Exit signals:
    - Momentum reversal
    - Target profit reached
    - Stop loss hit
    """
    
    DEFAULT_PARAMS = {
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'ma_period': 50,
        'lookback_bars': 200,
        'min_momentum_score': 0.6,
        'use_volume_confirmation': True,
        'volume_ma_period': 20
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Merge default params with config params
        self.params = {**self.DEFAULT_PARAMS, **self.config.parameters}
        
        # Price history storage {(symbol, venue): deque of bars}
        self._price_history: dict[tuple[str, str], Deque[Bar]] = {}
        
        # Indicator cache
        self._indicator_cache: dict[tuple[str, str], dict] = {}
        
        # Last signal time (prevent over-trading)
        self._last_signal_time: dict[tuple[str, str], datetime] = {}
        self._min_signal_interval = timedelta(minutes=5)
    
    async def initialize(self) -> None:
        """Initialize momentum strategy components."""
        self.logger.info(
            f"Initializing momentum strategy",
            params=self.params
        )
        
        # Initialize price history for each symbol/venue
        for symbol in self.config.symbols:
            for venue in self.config.venues:
                key = (symbol, venue)
                self._price_history[key] = deque(maxlen=self.params['lookback_bars'])
                self._indicator_cache[key] = {}
                
                # Load historical bars
                try:
                    historical_bars = await self.market_data.get_historical_bars(
                        symbol=symbol,
                        venue=venue,
                        interval='1m',
                        limit=self.params['lookback_bars']
                    )
                    
                    if historical_bars:
                        self._price_history[key].extend(historical_bars)
                        self.logger.info(
                            f"Loaded {len(historical_bars)} historical bars for {symbol}@{venue}"
                        )
                
                except Exception as e:
                    self.logger.warning(
                        f"Could not load historical data for {symbol}@{venue}",
                        error=e
                    )
    
    async def cleanup(self) -> None:
        """Cleanup momentum strategy components."""
        self._price_history.clear()
        self._indicator_cache.clear()
        self.logger.info("Momentum strategy cleaned up")
    
    async def on_bar(self, bar: Bar) -> None:
        """Process new bar data."""
        key = (bar.symbol, bar.venue)
        
        # Add to price history
        if key in self._price_history:
            self._price_history[key].append(bar)
            
            # Clear cached indicators (will be recalculated)
            self._indicator_cache[key] = {}
            
            # Generate signals on each bar
            await self.generate_signals(bar.symbol, bar.venue)
    
    async def calculate_signals(self, symbol: str, venue: str) -> List[Signal]:
        """Calculate momentum signals."""
        key = (symbol, venue)
        
        # Check if enough data
        if key not in self._price_history:
            return []
        
        bars = list(self._price_history[key])
        if len(bars) < max(self.params['ma_period'], self.params['rsi_period'], self.params['macd_slow']):
            return []
        
        # Check signal interval
        last_signal = self._last_signal_time.get(key)
        if last_signal and (datetime.now(timezone.utc) - last_signal) < self._min_signal_interval:
            return []
        
        # Calculate indicators
        indicators = await self._calculate_indicators(bars)
        
        if not indicators:
            return []
        
        # Calculate momentum score
        momentum_score = self._calculate_momentum_score(indicators)
        
        # Generate signal if momentum is strong enough
        if abs(momentum_score) < self.params['min_momentum_score']:
            return []
        
        signals = []
        
        # Determine signal direction and strength
        if momentum_score > 0:
            # Bullish momentum
            strength = self._score_to_signal_strength(momentum_score, is_buy=True)
            side = OrderSide.BUY
        else:
            # Bearish momentum
            strength = self._score_to_signal_strength(abs(momentum_score), is_buy=False)
            side = OrderSide.SELL
        
        # Get current price
        current_bar = bars[-1]
        current_price = current_bar.close
        
        # Calculate position size
        quantity = await self._calculate_position_size(symbol, venue, current_price)
        
        if quantity <= 0:
            return []
        
        # Calculate stop loss and take profit
        if side == OrderSide.BUY:
            stop_loss = current_price * Decimal(str(1 - self.config.stop_loss_pct))
            take_profit = current_price * Decimal(str(1 + self.config.take_profit_pct))
        else:
            stop_loss = current_price * Decimal(str(1 + self.config.stop_loss_pct))
            take_profit = current_price * Decimal(str(1 - self.config.take_profit_pct))
        
        # Create signal
        signal = Signal(
            strategy_id=self.strategy_id,
            symbol=symbol,
            venue=venue,
            side=side,
            strength=strength,
            confidence=abs(momentum_score),
            target_quantity=Decimal(str(quantity)),
            target_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                'indicators': indicators,
                'momentum_score': momentum_score,
                'strategy_type': 'momentum'
            }
        )
        
        signals.append(signal)
        
        # Update last signal time
        self._last_signal_time[key] = datetime.now(timezone.utc)
        
        self.logger.info(
            f"Momentum signal generated",
            symbol=symbol,
            side=side.value,
            strength=strength.value,
            score=momentum_score,
            indicators=indicators
        )
        
        return signals
    
    async def _calculate_indicators(self, bars: List[Bar]) -> dict:
        """Calculate technical indicators."""
        try:
            # Extract close prices
            closes = np.array([float(bar.close) for bar in bars])
            volumes = np.array([float(bar.volume) for bar in bars])
            
            # RSI
            rsi = self._calculate_rsi(closes, self.params['rsi_period'])
            
            # MACD
            macd_line, signal_line, histogram = self._calculate_macd(
                closes,
                self.params['macd_fast'],
                self.params['macd_slow'],
                self.params['macd_signal']
            )
            
            # Moving Average
            ma = self._calculate_sma(closes, self.params['ma_period'])
            
            # Volume confirmation
            volume_ma = None
            if self.params['use_volume_confirmation']:
                volume_ma = self._calculate_sma(volumes, self.params['volume_ma_period'])
            
            # Current values
            indicators = {
                'rsi': float(rsi[-1]) if len(rsi) > 0 else 50.0,
                'macd': float(macd_line[-1]) if len(macd_line) > 0 else 0.0,
                'macd_signal': float(signal_line[-1]) if len(signal_line) > 0 else 0.0,
                'macd_histogram': float(histogram[-1]) if len(histogram) > 0 else 0.0,
                'ma': float(ma[-1]) if len(ma) > 0 else closes[-1],
                'current_price': float(closes[-1]),
                'volume': float(volumes[-1]),
                'volume_ma': float(volume_ma[-1]) if volume_ma is not None and len(volume_ma) > 0 else float(volumes[-1])
            }
            
            # Calculate previous values for crossover detection
            if len(macd_line) > 1:
                indicators['macd_prev'] = float(macd_line[-2])
                indicators['macd_signal_prev'] = float(signal_line[-2])
            
            return indicators
        
        except Exception as e:
            self.logger.error("Error calculating indicators", error=e)
            return {}
    
    def _calculate_momentum_score(self, indicators: dict) -> float:
        """Calculate overall momentum score from indicators.
        
        Returns value between -1 and 1.
        """
        score = 0.0
        weights = []
        
        # RSI component
        rsi = indicators.get('rsi', 50)
        if rsi > self.params['rsi_overbought']:
            rsi_score = 1.0  # Overbought = bullish momentum
        elif rsi < self.params['rsi_oversold']:
            rsi_score = -1.0  # Oversold = bearish momentum  
        else:
            # Normalize RSI to -1 to 1 scale
            rsi_score = (rsi - 50) / 50
        
        score += rsi_score * 0.3
        weights.append(0.3)
        
        # MACD component
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        macd_histogram = indicators.get('macd_histogram', 0)
        
        # Check for crossover
        macd_prev = indicators.get('macd_prev')
        macd_signal_prev = indicators.get('macd_signal_prev')
        
        if macd_prev is not None and macd_signal_prev is not None:
            # Bullish crossover
            if macd_prev < macd_signal_prev and macd > macd_signal:
                macd_score = 1.0
            # Bearish crossover
            elif macd_prev > macd_signal_prev and macd < macd_signal:
                macd_score = -1.0
            else:
                # Use histogram strength
                macd_score = np.tanh(macd_histogram / 10)  # Normalize
        else:
            macd_score = np.tanh(macd_histogram / 10)
        
        score += macd_score * 0.4
        weights.append(0.4)
        
        # Price vs MA component (trend)
        current_price = indicators.get('current_price', 0)
        ma = indicators.get('ma', current_price)
        
        if current_price > ma:
            ma_score = min((current_price - ma) / ma, 0.5)  # Cap at 0.5
        else:
            ma_score = max((current_price - ma) / ma, -0.5)
        
        score += ma_score * 0.2
        weights.append(0.2)
        
        # Volume confirmation
        if self.params['use_volume_confirmation']:
            volume = indicators.get('volume', 0)
            volume_ma = indicators.get('volume_ma', volume)
            
            if volume > volume_ma * 1.5:  # High volume
                volume_score = 0.5 if score > 0 else -0.5  # Amplify existing signal
            elif volume < volume_ma * 0.5:  # Low volume
                volume_score = -0.25 if score > 0 else 0.25  # Reduce signal strength
            else:
                volume_score = 0.0
            
            score += volume_score * 0.1
            weights.append(0.1)
        
        # Normalize final score to [-1, 1]
        normalized_score = np.clip(score, -1.0, 1.0)
        
        return normalized_score
    
    def _score_to_signal_strength(self, score: float, is_buy: bool) -> SignalStrength:
        """Convert momentum score to signal strength."""
        if score >= 0.8:
            return SignalStrength.STRONG_BUY if is_buy else SignalStrength.STRONG_SELL
        elif score >= 0.6:
            return SignalStrength.BUY if is_buy else SignalStrength.SELL
        elif score >= 0.4:
            return SignalStrength.WEAK_BUY if is_buy else SignalStrength.WEAK_SELL
        else:
            return SignalStrength.NEUTRAL
    
    async def _calculate_position_size(self, symbol: str, venue: str, price: Decimal) -> float:
        """Calculate position size based on risk parameters."""
        # Get current capital (simplified - would query from position tracker)
        capital = 100000.0  # TODO: Get from portfolio manager
        
        # Calculate size based on percentage of capital
        position_value = capital * self.config.position_size_pct
        quantity = position_value / float(price)
        
        # Apply max position size limit
        if self.config.max_position_size:
            max_quantity = self.config.max_position_size / float(price)
            quantity = min(quantity, max_quantity)
        
        return quantity
    
    @staticmethod
    def _calculate_rsi(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Relative Strength Index."""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        if down == 0:
            return np.full(len(prices), 100.0)
        
        rs = up / down
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)
        
        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
            
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            
            rs = up / down if down != 0 else 100
            rsi[i] = 100. - 100. / (1. + rs)
        
        return rsi
    
    @staticmethod
    def _calculate_macd(prices: np.ndarray, fast: int, slow: int, signal: int) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        exp1 = MomentumStrategy._calculate_ema(prices, fast)
        exp2 = MomentumStrategy._calculate_ema(prices, slow)
        macd_line = exp1 - exp2
        signal_line = MomentumStrategy._calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def _calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]
        
        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    @staticmethod
    def _calculate_sma(values: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average."""
        if len(values) < period:
            return np.array([np.mean(values)])
        
        return np.convolve(values, np.ones(period), 'valid') / period
