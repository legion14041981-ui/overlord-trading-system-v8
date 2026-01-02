"""Mean reversion trading strategy implementation."""
import asyncio
from typing import List, Optional, Deque
from collections import deque
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import numpy as np
from scipy import stats

from .base_strategy import BaseStrategy, Signal, SignalStrength, StrategyConfig
from ..core.models.order import OrderSide
from ..core.models.market_data import Bar, Quote
from ..core.logging.structured_logger import get_logger


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands and Z-scores.
    
    Entry signals:
    - Price deviation from mean exceeds threshold
    - Bollinger Band breakout
    - Statistical significance via Z-score
    
    Exit signals:
    - Price returns to mean
    - Opposite signal
    - Stop loss / take profit
    """
    
    DEFAULT_PARAMS = {
        'bb_period': 20,
        'bb_std_dev': 2.0,
        'zscore_threshold': 2.0,
        'lookback_bars': 100,
        'min_reversion_confidence': 0.6,
        'use_volume_filter': True,
        'volume_threshold': 1.5,  # Multiple of average volume
        'atr_period': 14,  # For volatility adjustment
        'correlation_threshold': 0.7,  # For pair trading
        'use_halflife_optimization': True
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.params = {**self.DEFAULT_PARAMS, **self.config.parameters}
        
        # Price history
        self._price_history: dict[tuple[str, str], Deque[Bar]] = {}
        
        # Statistical cache
        self._stats_cache: dict[tuple[str, str], dict] = {}
        
        # Last signal tracking
        self._last_signal_time: dict[tuple[str, str], datetime] = {}
        self._min_signal_interval = timedelta(minutes=3)
        
        # Mean reversion tracking (for open positions)
        self._reversion_targets: dict[tuple[str, str], float] = {}
    
    async def initialize(self) -> None:
        """Initialize mean reversion strategy."""
        self.logger.info(
            "Initializing mean reversion strategy",
            params=self.params
        )
        
        for symbol in self.config.symbols:
            for venue in self.config.venues:
                key = (symbol, venue)
                self._price_history[key] = deque(maxlen=self.params['lookback_bars'])
                self._stats_cache[key] = {}
                
                # Load historical data
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
                            f"Loaded {len(historical_bars)} bars for {symbol}@{venue}"
                        )
                
                except Exception as e:
                    self.logger.warning(
                        f"Could not load historical data for {symbol}@{venue}",
                        error=e
                    )
    
    async def cleanup(self) -> None:
        """Cleanup mean reversion strategy."""
        self._price_history.clear()
        self._stats_cache.clear()
        self._reversion_targets.clear()
        self.logger.info("Mean reversion strategy cleaned up")
    
    async def on_bar(self, bar: Bar) -> None:
        """Process new bar."""
        key = (bar.symbol, bar.venue)
        
        if key in self._price_history:
            self._price_history[key].append(bar)
            self._stats_cache[key] = {}  # Invalidate cache
            
            # Check for reversion exit on open positions
            await self._check_reversion_exit(bar)
            
            # Generate new signals
            await self.generate_signals(bar.symbol, bar.venue)
    
    async def on_quote(self, quote: Quote) -> None:
        """Process quote for high-frequency reversion checks."""
        # Optional: use quotes for faster mean reversion detection
        pass
    
    async def calculate_signals(self, symbol: str, venue: str) -> List[Signal]:
        """Calculate mean reversion signals."""
        key = (symbol, venue)
        
        if key not in self._price_history:
            return []
        
        bars = list(self._price_history[key])
        if len(bars) < max(self.params['bb_period'], self.params['atr_period']):
            return []
        
        # Check signal interval
        last_signal = self._last_signal_time.get(key)
        if last_signal and (datetime.now(timezone.utc) - last_signal) < self._min_signal_interval:
            return []
        
        # Calculate statistical indicators
        stats_data = await self._calculate_statistics(bars)
        
        if not stats_data:
            return []
        
        # Calculate reversion score
        reversion_score, direction = self._calculate_reversion_score(stats_data)
        
        if abs(reversion_score) < self.params['min_reversion_confidence']:
            return []
        
        # Generate signal
        current_bar = bars[-1]
        current_price = current_bar.close
        
        # Determine side (mean reversion is contrarian)
        if direction == 'oversold':
            side = OrderSide.BUY  # Buy when oversold (expect reversion up)
        elif direction == 'overbought':
            side = OrderSide.SELL  # Sell when overbought (expect reversion down)
        else:
            return []
        
        # Calculate position size
        quantity = await self._calculate_position_size(symbol, venue, current_price, reversion_score)
        
        if quantity <= 0:
            return []
        
        # Calculate targets
        mean_price = Decimal(str(stats_data['mean']))
        
        if side == OrderSide.BUY:
            # Target is mean, stop is below current
            take_profit = mean_price
            stop_loss = current_price * Decimal(str(1 - self.config.stop_loss_pct))
        else:
            take_profit = mean_price
            stop_loss = current_price * Decimal(str(1 + self.config.stop_loss_pct))
        
        # Determine signal strength
        strength = self._score_to_signal_strength(reversion_score, side == OrderSide.BUY)
        
        # Create signal
        signal = Signal(
            strategy_id=self.strategy_id,
            symbol=symbol,
            venue=venue,
            side=side,
            strength=strength,
            confidence=reversion_score,
            target_quantity=Decimal(str(quantity)),
            target_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                'statistics': stats_data,
                'reversion_score': reversion_score,
                'direction': direction,
                'mean_target': float(mean_price),
                'strategy_type': 'mean_reversion'
            }
        )
        
        # Track reversion target
        self._reversion_targets[key] = float(mean_price)
        
        self._last_signal_time[key] = datetime.now(timezone.utc)
        
        self.logger.info(
            "Mean reversion signal generated",
            symbol=symbol,
            side=side.value,
            direction=direction,
            score=reversion_score,
            current_price=float(current_price),
            mean=stats_data['mean']
        )
        
        return [signal]
    
    async def _calculate_statistics(self, bars: List[Bar]) -> dict:
        """Calculate statistical indicators for mean reversion."""
        try:
            closes = np.array([float(bar.close) for bar in bars])
            highs = np.array([float(bar.high) for bar in bars])
            lows = np.array([float(bar.low) for bar in bars])
            volumes = np.array([float(bar.volume) for bar in bars])
            
            current_price = closes[-1]
            
            # Bollinger Bands
            bb_period = self.params['bb_period']
            bb_std = self.params['bb_std_dev']
            
            ma = np.mean(closes[-bb_period:])
            std = np.std(closes[-bb_period:])
            
            upper_band = ma + (bb_std * std)
            lower_band = ma - (bb_std * std)
            
            # Z-score
            zscore = (current_price - ma) / std if std > 0 else 0
            
            # ATR (Average True Range) for volatility
            atr = self._calculate_atr(highs, lows, closes, self.params['atr_period'])
            
            # Volume analysis
            avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
            volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1.0
            
            # Half-life of mean reversion (Ornstein-Uhlenbeck process)
            halflife = None
            if self.params['use_halflife_optimization']:
                halflife = self._calculate_halflife(closes)
            
            # Distance from bands
            dist_from_upper = (upper_band - current_price) / (upper_band - lower_band) if (upper_band - lower_band) > 0 else 0
            dist_from_lower = (current_price - lower_band) / (upper_band - lower_band) if (upper_band - lower_band) > 0 else 0
            
            stats_data = {
                'mean': ma,
                'std': std,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'current_price': current_price,
                'zscore': zscore,
                'atr': atr,
                'volume_ratio': volume_ratio,
                'halflife': halflife,
                'dist_from_upper': dist_from_upper,
                'dist_from_lower': dist_from_lower,
                'bb_width': (upper_band - lower_band) / ma if ma > 0 else 0
            }
            
            return stats_data
        
        except Exception as e:
            self.logger.error("Error calculating statistics", error=e)
            return {}
    
    def _calculate_reversion_score(self, stats: dict) -> tuple[float, str]:
        """Calculate mean reversion probability score.
        
        Returns:
            (score, direction) where score is 0-1 and direction is 'oversold'/'overbought'/None
        """
        score = 0.0
        direction = None
        
        zscore = stats.get('zscore', 0)
        zscore_threshold = self.params['zscore_threshold']
        
        current_price = stats.get('current_price', 0)
        upper_band = stats.get('upper_band', 0)
        lower_band = stats.get('lower_band', 0)
        
        # Check for oversold condition (buy signal)
        if zscore < -zscore_threshold or current_price < lower_band:
            direction = 'oversold'
            
            # Z-score component (stronger signal further from mean)
            zscore_component = min(abs(zscore) / (zscore_threshold * 2), 1.0) * 0.4
            score += zscore_component
            
            # Bollinger Band component
            if current_price < lower_band:
                bb_component = min(stats.get('dist_from_lower', 0) * 2, 1.0) * 0.3
                score += bb_component
            
            # Volume confirmation
            if self.params['use_volume_filter']:
                volume_ratio = stats.get('volume_ratio', 1.0)
                if volume_ratio > self.params['volume_threshold']:
                    score += 0.2  # High volume confirms signal
                elif volume_ratio < 0.5:
                    score -= 0.1  # Low volume reduces confidence
            
            # Halflife optimization
            if stats.get('halflife'):
                # Shorter halflife = faster mean reversion = better signal
                halflife = stats['halflife']
                if halflife < 10:  # Quick reversion expected
                    score += 0.1
        
        # Check for overbought condition (sell signal)
        elif zscore > zscore_threshold or current_price > upper_band:
            direction = 'overbought'
            
            zscore_component = min(abs(zscore) / (zscore_threshold * 2), 1.0) * 0.4
            score += zscore_component
            
            if current_price > upper_band:
                bb_component = min(stats.get('dist_from_upper', 0) * 2, 1.0) * 0.3
                score += bb_component
            
            if self.params['use_volume_filter']:
                volume_ratio = stats.get('volume_ratio', 1.0)
                if volume_ratio > self.params['volume_threshold']:
                    score += 0.2
                elif volume_ratio < 0.5:
                    score -= 0.1
            
            if stats.get('halflife'):
                halflife = stats['halflife']
                if halflife < 10:
                    score += 0.1
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return score, direction
    
    def _score_to_signal_strength(self, score: float, is_buy: bool) -> SignalStrength:
        """Convert reversion score to signal strength."""
        if score >= 0.85:
            return SignalStrength.STRONG_BUY if is_buy else SignalStrength.STRONG_SELL
        elif score >= 0.7:
            return SignalStrength.BUY if is_buy else SignalStrength.SELL
        elif score >= 0.55:
            return SignalStrength.WEAK_BUY if is_buy else SignalStrength.WEAK_SELL
        else:
            return SignalStrength.NEUTRAL
    
    async def _calculate_position_size(self, symbol: str, venue: str, price: Decimal, confidence: float) -> float:
        """Calculate position size adjusted by reversion confidence."""
        capital = 100000.0  # TODO: Get from portfolio manager
        
        # Base position size
        base_size = capital * self.config.position_size_pct
        
        # Adjust by confidence
        adjusted_size = base_size * confidence
        
        quantity = adjusted_size / float(price)
        
        # Apply max limit
        if self.config.max_position_size:
            max_quantity = self.config.max_position_size / float(price)
            quantity = min(quantity, max_quantity)
        
        return quantity
    
    async def _check_reversion_exit(self, bar: Bar) -> None:
        """Check if open positions should exit due to mean reversion."""
        key = (bar.symbol, bar.venue)
        
        if key not in self._reversion_targets:
            return
        
        target = self._reversion_targets[key]
        current_price = float(bar.close)
        
        # Check if price has reverted to mean
        reversion_tolerance = 0.002  # 0.2%
        
        if abs(current_price - target) / target < reversion_tolerance:
            self.logger.info(
                "Mean reversion target reached",
                symbol=bar.symbol,
                current_price=current_price,
                target=target
            )
            
            # TODO: Signal position exit
            # This would integrate with execution layer
            
            del self._reversion_targets[key]
    
    @staticmethod
    def _calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> float:
        """Calculate Average True Range."""
        if len(highs) < period + 1:
            return 0.0
        
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )
        
        atr = np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)
        return float(atr)
    
    @staticmethod
    def _calculate_halflife(prices: np.ndarray) -> Optional[float]:
        """Calculate half-life of mean reversion using Ornstein-Uhlenbeck.
        
        Returns the expected time (in bars) for price to revert halfway to mean.
        """
        try:
            if len(prices) < 20:
                return None
            
            # Calculate lagged prices
            lagged_prices = prices[:-1]
            current_prices = prices[1:]
            
            # Calculate price changes
            price_changes = current_prices - lagged_prices
            
            # Run regression: Δp(t) = λ(μ - p(t-1)) + ε
            # This simplifies to: Δp(t) = α + β*p(t-1) + ε
            X = np.column_stack([np.ones(len(lagged_prices)), lagged_prices])
            y = price_changes
            
            # Least squares
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            lambda_param = -beta[1]
            
            # Half-life = -ln(2) / λ
            if lambda_param > 0:
                halflife = -np.log(2) / lambda_param
                return float(halflife)
            
            return None
        
        except Exception:
            return None
