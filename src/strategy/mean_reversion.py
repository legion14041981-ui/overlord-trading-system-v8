"""Mean reversion trading strategy."""
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from collections import deque

from .base_strategy import BaseStrategy, StrategyConfig
from ..core.models import Quote


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands and RSI.
    
    Buys when price is oversold (below lower band, low RSI),
    sells when price is overbought (above upper band, high RSI).
    """
    
    async def _initialize_strategy(self) -> None:
        """Initialize mean reversion-specific state."""
        # Price history for indicators
        self._price_history: Dict[str, deque] = {
            symbol: deque(maxlen=300) for symbol in self.config.symbols
        }
        
        # Mean reversion parameters
        self.bb_period = self.config.parameters.get('bb_period', 20)
        self.bb_std_dev = self.config.parameters.get('bb_std_dev', 2.0)
        self.rsi_period = self.config.parameters.get('rsi_period', 14)
        self.rsi_oversold = self.config.parameters.get('rsi_oversold', 30)
        self.rsi_overbought = self.config.parameters.get('rsi_overbought', 70)
        
        # Entry/exit thresholds
        self.entry_z_score = self.config.parameters.get('entry_z_score', -2.0)
        self.exit_z_score = self.config.parameters.get('exit_z_score', 0.0)
        
        # Risk management
        self.max_holding_period_hours = self.config.parameters.get('max_holding_period_hours', 24)
        self.stop_loss_pct = self.config.parameters.get('stop_loss_pct', 0.05)
        
        # Indicator cache
        self._indicators: Dict[str, Dict] = {}
        
        self.logger.info(
            "Mean reversion strategy initialized",
            bb_period=self.bb_period,
            rsi_period=self.rsi_period
        )
    
    async def generate_signals(self) -> List[Dict]:
        """Generate mean reversion trading signals."""
        signals = []
        
        for symbol in self.config.symbols:
            try:
                # Get current quote
                quote = await self.market_data.get_latest_quote(symbol)
                if not quote:
                    continue
                
                # Update price history
                await self._update_price_history(symbol, quote)
                
                # Calculate indicators
                indicators = await self._calculate_indicators(symbol)
                if not indicators:
                    continue
                
                self._indicators[symbol] = indicators
                
                # Generate signal
                signal = await self._evaluate_mean_reversion_signal(
                    symbol, indicators, quote
                )
                
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.error(f"Error generating signal for {symbol}", error=e)
        
        return signals
    
    async def _update_price_history(self, symbol: str, quote: Quote) -> None:
        """Update price history for indicator calculation."""
        mid_price = float((quote.bid_price + quote.ask_price) / 2)
        
        self._price_history[symbol].append({
            'timestamp': datetime.now(timezone.utc),
            'price': mid_price,
            'high': float(quote.ask_price),
            'low': float(quote.bid_price)
        })
    
    async def _calculate_indicators(self, symbol: str) -> Optional[Dict]:
        """Calculate mean reversion indicators."""
        history = self._price_history.get(symbol)
        if not history or len(history) < max(self.bb_period, self.rsi_period):
            return None
        
        prices = np.array([p['price'] for p in history])
        
        indicators = {}
        
        # Bollinger Bands
        bb_sma, bb_upper, bb_lower = self._calculate_bollinger_bands(prices)
        indicators['bb_sma'] = bb_sma
        indicators['bb_upper'] = bb_upper
        indicators['bb_lower'] = bb_lower
        indicators['bb_width'] = (bb_upper - bb_lower) / bb_sma if bb_sma > 0 else 0
        
        # Z-score (standardized distance from mean)
        current_price = prices[-1]
        indicators['z_score'] = (current_price - bb_sma) / ((bb_upper - bb_lower) / 4) if bb_upper != bb_lower else 0
        
        # RSI
        rsi = self._calculate_rsi(prices)
        indicators['rsi'] = rsi
        
        # Price position relative to bands
        if bb_upper != bb_lower:
            indicators['percent_b'] = (current_price - bb_lower) / (bb_upper - bb_lower)
        else:
            indicators['percent_b'] = 0.5
        
        # Mean reversion potential
        indicators['reversion_potential'] = abs(indicators['z_score']) * (1 - abs(indicators['percent_b'] - 0.5) * 2)
        
        return indicators
    
    def _calculate_bollinger_bands(self, prices: np.ndarray) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands."""
        sma = np.mean(prices[-self.bb_period:])
        std = np.std(prices[-self.bb_period:])
        
        upper_band = sma + (self.bb_std_dev * std)
        lower_band = sma - (self.bb_std_dev * std)
        
        return sma, upper_band, lower_band
    
    def _calculate_rsi(self, prices: np.ndarray) -> float:
        """Calculate Relative Strength Index."""
        if len(prices) < self.rsi_period + 1:
            return 50.0  # Neutral
        
        # Calculate price changes
        deltas = np.diff(prices[-self.rsi_period-1:])
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0  # Maximum RSI
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def _evaluate_mean_reversion_signal(
        self,
        symbol: str,
        indicators: Dict,
        quote: Quote
    ) -> Optional[Dict]:
        """Evaluate indicators and generate mean reversion signal."""
        current_price = float((quote.bid_price + quote.ask_price) / 2)
        z_score = indicators['z_score']
        rsi = indicators['rsi']
        percent_b = indicators['percent_b']
        
        # Get current position
        current_position = self._positions.get(symbol)
        current_size = float(current_position.quantity) if current_position else 0.0
        
        action = 'hold'
        strength = 0.0
        reason = ""
        
        # Check if position needs to be closed due to time limit
        if current_position and current_size != 0:
            holding_period = (datetime.now(timezone.utc) - current_position.opened_at).total_seconds() / 3600
            if holding_period > self.max_holding_period_hours:
                action = 'sell' if current_size > 0 else 'buy'
                strength = 0.8
                reason = f"Max holding period exceeded ({holding_period:.1f}h)"
                
                return {
                    'symbol': symbol,
                    'action': action,
                    'strength': strength,
                    'target_size': Decimal('0'),  # Close position
                    'reason': reason,
                    'metadata': {'indicators': indicators}
                }
        
        # Oversold condition - potential buy
        if z_score < self.entry_z_score and rsi < self.rsi_oversold:
            if current_size <= 0:  # Not currently long
                action = 'buy'
                strength = min(
                    abs(z_score / self.entry_z_score) * ((100 - rsi) / (100 - self.rsi_oversold)),
                    1.0
                )
                reason = f"Oversold: Z={z_score:.2f}, RSI={rsi:.1f}"
        
        # Overbought condition - potential sell
        elif z_score > -self.entry_z_score and rsi > self.rsi_overbought:
            if current_size > 0:  # Currently long
                action = 'sell'
                strength = min(
                    abs(z_score / self.entry_z_score) * (rsi / self.rsi_overbought),
                    1.0
                )
                reason = f"Overbought: Z={z_score:.2f}, RSI={rsi:.1f}"
        
        # Exit condition - mean reversion completed
        elif current_size > 0 and z_score > self.exit_z_score:
            action = 'sell'
            strength = 0.7
            reason = f"Mean reversion target reached: Z={z_score:.2f}"
        
        # Stop loss check
        if current_position and current_size != 0:
            entry_price = float(current_position.average_entry_price)
            price_change = (current_price - entry_price) / entry_price
            
            if current_size > 0 and price_change < -self.stop_loss_pct:
                action = 'sell'
                strength = 1.0
                reason = f"Stop loss triggered: {price_change:.2%}"
            elif current_size < 0 and price_change > self.stop_loss_pct:
                action = 'buy'
                strength = 1.0
                reason = f"Stop loss triggered: {price_change:.2%}"
        
        if action == 'hold':
            return None
        
        return {
            'symbol': symbol,
            'action': action,
            'strength': strength,
            'target_size': None,  # Will be calculated
            'reason': reason,
            'metadata': {
                'indicators': indicators,
                'current_price': current_price,
                'z_score': z_score,
                'rsi': rsi
            }
        }
    
    async def _cleanup_strategy(self) -> None:
        """Cleanup mean reversion strategy state."""
        self._price_history.clear()
        self._indicators.clear()
        self.logger.info("Mean reversion strategy cleaned up")
    
    def get_state(self) -> Dict:
        """Get mean reversion strategy state."""
        state = super().get_state()
        
        state['mean_reversion_state'] = {
            'price_history_lengths': {
                symbol: len(history)
                for symbol, history in self._price_history.items()
            },
            'current_indicators': {
                symbol: {
                    'z_score': ind.get('z_score'),
                    'rsi': ind.get('rsi'),
                    'bb_width': ind.get('bb_width')
                }
                for symbol, ind in self._indicators.items()
            }
        }
        
        return state
