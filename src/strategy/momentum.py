"""Momentum-based trading strategy."""
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .base_strategy import BaseStrategy, StrategyConfig
from ..core.models import Quote


class MomentumStrategy(BaseStrategy):
    """Trend-following momentum strategy.
    
    Generates buy signals when price momentum is positive and strong,
    sell signals when momentum turns negative.
    """
    
    async def _initialize_strategy(self) -> None:
        """Initialize momentum-specific state."""
        # Price history for momentum calculation
        self._price_history: Dict[str, List[Dict]] = {
            symbol: [] for symbol in self.config.symbols
        }
        
        # Momentum parameters
        self.lookback_periods = self.config.parameters.get('lookback_periods', [20, 50, 200])
        self.momentum_threshold = self.config.parameters.get('momentum_threshold', 0.02)  # 2%
        self.volume_confirmation = self.config.parameters.get('volume_confirmation', True)
        self.volume_threshold = self.config.parameters.get('volume_threshold', 1.5)  # 1.5x avg
        
        # Trend filter
        self.use_trend_filter = self.config.parameters.get('use_trend_filter', True)
        self.trend_period = self.config.parameters.get('trend_period', 200)
        
        self.logger.info(
            "Momentum strategy initialized",
            lookback_periods=self.lookback_periods,
            momentum_threshold=self.momentum_threshold
        )
    
    async def generate_signals(self) -> List[Dict]:
        """Generate momentum-based trading signals."""
        signals = []
        
        for symbol in self.config.symbols:
            try:
                # Get current quote
                quote = await self.market_data.get_latest_quote(symbol)
                if not quote:
                    continue
                
                # Update price history
                await self._update_price_history(symbol, quote)
                
                # Calculate momentum indicators
                momentum_scores = await self._calculate_momentum(symbol)
                if not momentum_scores:
                    continue
                
                # Check trend filter
                if self.use_trend_filter:
                    trend_direction = await self._check_trend(symbol)
                    if trend_direction == 0:
                        continue  # No clear trend
                else:
                    trend_direction = 1  # Assume uptrend if no filter
                
                # Generate signal based on momentum
                signal = await self._evaluate_momentum_signal(
                    symbol, momentum_scores, trend_direction, quote
                )
                
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.error(f"Error generating signal for {symbol}", error=e)
        
        return signals
    
    async def _update_price_history(self, symbol: str, quote: Quote) -> None:
        """Update price history for momentum calculation."""
        mid_price = float((quote.bid_price + quote.ask_price) / 2)
        volume = float(quote.bid_size + quote.ask_size)
        
        self._price_history[symbol].append({
            'timestamp': datetime.now(timezone.utc),
            'price': mid_price,
            'volume': volume
        })
        
        # Keep only necessary history (max lookback + buffer)
        max_lookback = max(self.lookback_periods) + 50
        if len(self._price_history[symbol]) > max_lookback:
            self._price_history[symbol] = self._price_history[symbol][-max_lookback:]
    
    async def _calculate_momentum(self, symbol: str) -> Optional[Dict[str, float]]:
        """Calculate momentum scores for different periods."""
        history = self._price_history.get(symbol, [])
        
        if len(history) < max(self.lookback_periods):
            return None
        
        prices = np.array([p['price'] for p in history])
        current_price = prices[-1]
        
        momentum_scores = {}
        
        for period in self.lookback_periods:
            if len(prices) >= period:
                past_price = prices[-period]
                momentum = (current_price - past_price) / past_price
                momentum_scores[f'mom_{period}'] = momentum
        
        # Calculate rate of change (ROC)
        if len(prices) >= 10:
            roc_10 = (prices[-1] - prices[-10]) / prices[-10]
            momentum_scores['roc_10'] = roc_10
        
        # Calculate momentum acceleration
        if len(prices) >= 20:
            momentum_now = (prices[-1] - prices[-10]) / prices[-10]
            momentum_past = (prices[-10] - prices[-20]) / prices[-20]
            acceleration = momentum_now - momentum_past
            momentum_scores['acceleration'] = acceleration
        
        return momentum_scores
    
    async def _check_trend(self, symbol: str) -> int:
        """Check long-term trend direction.
        
        Returns:
            1 for uptrend, -1 for downtrend, 0 for no trend
        """
        history = self._price_history.get(symbol, [])
        
        if len(history) < self.trend_period:
            return 0
        
        prices = np.array([p['price'] for p in history])
        current_price = prices[-1]
        trend_sma = np.mean(prices[-self.trend_period:])
        
        if current_price > trend_sma * 1.01:  # 1% above SMA
            return 1  # Uptrend
        elif current_price < trend_sma * 0.99:  # 1% below SMA
            return -1  # Downtrend
        else:
            return 0  # No clear trend
    
    async def _evaluate_momentum_signal(
        self,
        symbol: str,
        momentum_scores: Dict[str, float],
        trend_direction: int,
        quote: Quote
    ) -> Optional[Dict]:
        """Evaluate momentum scores and generate signal."""
        # Calculate composite momentum score
        short_mom = momentum_scores.get(f'mom_{self.lookback_periods[0]}', 0)
        medium_mom = momentum_scores.get(f'mom_{self.lookback_periods[1]}', 0) if len(self.lookback_periods) > 1 else 0
        acceleration = momentum_scores.get('acceleration', 0)
        
        # Weighted momentum score
        composite_score = (
            0.5 * short_mom +
            0.3 * medium_mom +
            0.2 * acceleration
        )
        
        # Check volume confirmation
        if self.volume_confirmation:
            volume_confirmed = await self._check_volume_confirmation(symbol)
            if not volume_confirmed:
                composite_score *= 0.5  # Reduce signal strength
        
        # Determine action
        action = 'hold'
        strength = 0.0
        reason = ""
        
        # Get current position
        current_position = self._positions.get(symbol)
        current_size = float(current_position.quantity) if current_position else 0.0
        
        # Buy signal: positive momentum in uptrend
        if composite_score > self.momentum_threshold and trend_direction >= 0:
            if current_size <= 0:  # Not long or short
                action = 'buy'
                strength = min(abs(composite_score) / (self.momentum_threshold * 2), 1.0)
                reason = f"Strong momentum ({composite_score:.2%}), uptrend"
        
        # Sell signal: negative momentum or downtrend
        elif composite_score < -self.momentum_threshold or trend_direction < 0:
            if current_size > 0:  # Currently long
                action = 'sell'
                strength = min(abs(composite_score) / (self.momentum_threshold * 2), 1.0)
                reason = f"Negative momentum ({composite_score:.2%}) or downtrend"
        
        # Exit long if momentum weakens
        elif current_size > 0 and composite_score < self.momentum_threshold / 2:
            action = 'sell'
            strength = 0.5
            reason = "Momentum weakening, exit long"
        
        if action == 'hold':
            return None
        
        return {
            'symbol': symbol,
            'action': action,
            'strength': strength,
            'target_size': None,  # Will be calculated based on sizing method
            'reason': reason,
            'metadata': {
                'momentum_scores': momentum_scores,
                'composite_score': composite_score,
                'trend_direction': trend_direction,
                'current_price': float((quote.bid_price + quote.ask_price) / 2)
            }
        }
    
    async def _check_volume_confirmation(self, symbol: str) -> bool:
        """Check if current volume confirms the momentum."""
        history = self._price_history.get(symbol, [])
        
        if len(history) < 20:
            return True  # Not enough data, assume confirmed
        
        volumes = np.array([p['volume'] for p in history])
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-20:-1])  # Exclude current
        
        return current_volume > avg_volume * self.volume_threshold
    
    async def _cleanup_strategy(self) -> None:
        """Cleanup momentum strategy state."""
        # Clear price history
        self._price_history.clear()
        self.logger.info("Momentum strategy cleaned up")
    
    def get_state(self) -> Dict:
        """Get momentum strategy state."""
        state = super().get_state()
        
        # Add momentum-specific state
        state['momentum_state'] = {
            'price_history_lengths': {
                symbol: len(history)
                for symbol, history in self._price_history.items()
            },
            'lookback_periods': self.lookback_periods
        }
        
        return state
