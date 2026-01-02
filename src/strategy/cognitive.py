"""Cognitive trading strategy using machine learning and pattern recognition."""
import asyncio
from typing import List, Optional, Dict, Any, Deque
from collections import deque
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import numpy as np
from dataclasses import dataclass

from .base_strategy import BaseStrategy, Signal, SignalStrength, StrategyConfig
from ..core.models.order import OrderSide
from ..core.models.market_data import Bar
from ..core.logging.structured_logger import get_logger


@dataclass
class MarketRegime:
    """Detected market regime."""
    regime_type: str  # 'trending', 'ranging', 'volatile', 'calm'
    confidence: float
    detected_at: datetime
    features: Dict[str, float]


@dataclass
class PatternMatch:
    """Detected price pattern."""
    pattern_type: str  # 'head_shoulders', 'double_top', 'triangle', etc.
    confidence: float
    expected_move: float  # Expected price move in %
    timeframe: int  # Expected timeframe in bars
    detected_at: datetime


class CognitiveStrategy(BaseStrategy):
    """Advanced strategy using ML-based pattern recognition and adaptive learning.
    
    Features:
    - Market regime detection
    - Pattern recognition (chart patterns, candlestick patterns)
    - Adaptive parameter optimization
    - Multi-timeframe analysis
    - Sentiment integration (optional)
    - Reinforcement learning for strategy selection
    """
    
    DEFAULT_PARAMS = {
        'lookback_bars': 200,
        'min_confidence': 0.65,
        'regime_detection_enabled': True,
        'pattern_recognition_enabled': True,
        'adaptive_sizing': True,
        'use_ensemble': True,  # Combine multiple ML models
        'retrain_interval_hours': 24,
        'feature_window': 50,
        'n_features': 20,
        'regime_weights': {
            'trending': 0.4,
            'ranging': 0.3,
            'volatile': 0.2,
            'calm': 0.1
        }
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.params = {**self.DEFAULT_PARAMS, **self.config.parameters}
        
        # Market data storage
        self._price_history: Dict[tuple[str, str], Deque[Bar]] = {}
        
        # Market regime tracking
        self._current_regime: Dict[tuple[str, str], MarketRegime] = {}
        
        # Pattern detection cache
        self._detected_patterns: Dict[tuple[str, str], List[PatternMatch]] = {}
        
        # Feature cache for ML
        self._feature_cache: Dict[tuple[str, str], np.ndarray] = {}
        
        # Model storage (placeholder for actual ML models)
        self._models: Dict[str, Any] = {}
        
        # Performance tracking for adaptive learning
        self._strategy_performance: Dict[str, List[float]] = {
            'momentum': [],
            'mean_reversion': [],
            'breakout': [],
            'pattern': []
        }
        
        # Last training time
        self._last_training: Optional[datetime] = None
    
    async def initialize(self) -> None:
        """Initialize cognitive strategy."""
        self.logger.info(
            "Initializing cognitive strategy",
            params=self.params
        )
        
        for symbol in self.config.symbols:
            for venue in self.config.venues:
                key = (symbol, venue)
                self._price_history[key] = deque(maxlen=self.params['lookback_bars'])
                self._detected_patterns[key] = []
                
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
                            f"Loaded {len(historical_bars)} bars for cognitive analysis: {symbol}@{venue}"
                        )
                
                except Exception as e:
                    self.logger.warning(
                        f"Could not load historical data for {symbol}@{venue}",
                        error=e
                    )
        
        # Initialize ML models (placeholder)
        await self._initialize_models()
        
        self.logger.info("Cognitive strategy initialized")
    
    async def cleanup(self) -> None:
        """Cleanup cognitive strategy."""
        self._price_history.clear()
        self._current_regime.clear()
        self._detected_patterns.clear()
        self._feature_cache.clear()
        self.logger.info("Cognitive strategy cleaned up")
    
    async def on_bar(self, bar: Bar) -> None:
        """Process new bar with cognitive analysis."""
        key = (bar.symbol, bar.venue)
        
        if key in self._price_history:
            self._price_history[key].append(bar)
            
            # Update market regime
            if self.params['regime_detection_enabled']:
                await self._detect_market_regime(key)
            
            # Detect patterns
            if self.params['pattern_recognition_enabled']:
                await self._detect_patterns(key)
            
            # Generate signals
            await self.generate_signals(bar.symbol, bar.venue)
            
            # Periodic model retraining
            await self._check_retrain_schedule()
    
    async def calculate_signals(self, symbol: str, venue: str) -> List[Signal]:
        """Generate cognitive trading signals."""
        key = (symbol, venue)
        
        if key not in self._price_history:
            return []
        
        bars = list(self._price_history[key])
        if len(bars) < self.params['feature_window']:
            return []
        
        # Extract features
        features = await self._extract_features(bars)
        if features is None or len(features) == 0:
            return []
        
        # Get current market regime
        regime = self._current_regime.get(key)
        
        # Get detected patterns
        patterns = self._detected_patterns.get(key, [])
        
        # Generate predictions using ensemble approach
        if self.params['use_ensemble']:
            predictions = await self._ensemble_predict(features, regime, patterns)
        else:
            predictions = await self._single_model_predict(features)
        
        if not predictions:
            return []
        
        # Filter by confidence
        if predictions['confidence'] < self.params['min_confidence']:
            return []
        
        # Determine signal parameters
        current_bar = bars[-1]
        current_price = current_bar.close
        
        side = OrderSide.BUY if predictions['direction'] > 0 else OrderSide.SELL
        strength = self._confidence_to_strength(predictions['confidence'], side == OrderSide.BUY)
        
        # Adaptive position sizing based on confidence and regime
        if self.params['adaptive_sizing']:
            quantity = await self._adaptive_position_size(
                symbol, venue, current_price, predictions['confidence'], regime
            )
        else:
            quantity = await self._calculate_position_size(symbol, venue, current_price)
        
        if quantity <= 0:
            return []
        
        # Calculate dynamic stop loss and take profit
        stops = self._calculate_dynamic_stops(current_price, predictions, regime)
        
        # Create signal
        signal = Signal(
            strategy_id=self.strategy_id,
            symbol=symbol,
            venue=venue,
            side=side,
            strength=strength,
            confidence=predictions['confidence'],
            target_quantity=Decimal(str(quantity)),
            target_price=current_price,
            stop_loss=stops['stop_loss'],
            take_profit=stops['take_profit'],
            metadata={
                'predictions': predictions,
                'regime': regime.regime_type if regime else 'unknown',
                'patterns': [p.pattern_type for p in patterns[-3:]],
                'features': features.tolist() if isinstance(features, np.ndarray) else features,
                'strategy_type': 'cognitive'
            }
        )
        
        self.logger.info(
            "Cognitive signal generated",
            symbol=symbol,
            side=side.value,
            confidence=predictions['confidence'],
            regime=regime.regime_type if regime else 'unknown',
            patterns=len(patterns)
        )
        
        return [signal]
    
    async def _initialize_models(self) -> None:
        """Initialize ML models (placeholder for actual implementation)."""
        # In production, load pre-trained models or initialize new ones
        self.logger.info("Initializing ML models (placeholder)")
        
        # Placeholder: would load sklearn/pytorch/tensorflow models
        self._models = {
            'regime_classifier': None,  # Random Forest or Neural Net
            'pattern_detector': None,   # CNN for pattern recognition
            'signal_predictor': None,   # LSTM or Transformer
            'risk_assessor': None       # Gradient Boosting
        }
    
    async def _extract_features(self, bars: List[Bar]) -> Optional[np.ndarray]:
        """Extract ML features from price bars."""
        try:
            closes = np.array([float(bar.close) for bar in bars[-self.params['feature_window']:]])
            highs = np.array([float(bar.high) for bar in bars[-self.params['feature_window']:]])
            lows = np.array([float(bar.low) for bar in bars[-self.params['feature_window']:]])
            volumes = np.array([float(bar.volume) for bar in bars[-self.params['feature_window']:]])
            
            features = []
            
            # Price-based features
            returns = np.diff(closes) / closes[:-1]
            features.append(np.mean(returns))  # Mean return
            features.append(np.std(returns))   # Volatility
            features.append(returns[-1])       # Last return
            
            # Momentum features
            features.append((closes[-1] - closes[-10]) / closes[-10])  # 10-bar momentum
            features.append((closes[-1] - closes[-20]) / closes[-20])  # 20-bar momentum
            
            # Volatility features
            features.append(np.std(closes[-10:]) / np.mean(closes[-10:]))  # 10-bar CV
            features.append(np.std(closes[-20:]) / np.mean(closes[-20:]))  # 20-bar CV
            
            # Range features
            features.append(np.mean((highs - lows) / closes))  # Avg relative range
            features.append((highs[-1] - lows[-1]) / closes[-1])  # Current relative range
            
            # Volume features
            features.append(volumes[-1] / np.mean(volumes[-20:]))  # Relative volume
            features.append(np.std(volumes) / np.mean(volumes))    # Volume volatility
            
            # Autocorrelation (mean reversion indicator)
            if len(returns) > 10:
                features.append(np.corrcoef(returns[:-1], returns[1:])[0, 1])
            else:
                features.append(0.0)
            
            # Price level features
            features.append(closes[-1] / np.max(closes))  # Distance from high
            features.append(closes[-1] / np.min(closes))  # Distance from low
            features.append(closes[-1] / np.mean(closes)) # Distance from mean
            
            # Trend features
            short_ma = np.mean(closes[-10:])
            long_ma = np.mean(closes[-30:]) if len(closes) >= 30 else np.mean(closes)
            features.append((short_ma - long_ma) / long_ma)  # MA crossover signal
            
            # Pad to n_features if needed
            while len(features) < self.params['n_features']:
                features.append(0.0)
            
            return np.array(features[:self.params['n_features']])
        
        except Exception as e:
            self.logger.error("Error extracting features", error=e)
            return None
    
    async def _detect_market_regime(self, key: tuple[str, str]) -> None:
        """Detect current market regime."""
        bars = list(self._price_history[key])
        if len(bars) < 50:
            return
        
        try:
            closes = np.array([float(bar.close) for bar in bars[-50:]])
            returns = np.diff(closes) / closes[:-1]
            
            # Simple regime detection based on volatility and trend
            volatility = np.std(returns)
            trend_strength = abs(np.mean(returns)) / volatility if volatility > 0 else 0
            
            # Classify regime
            if trend_strength > 0.3:
                regime_type = 'trending'
                confidence = min(trend_strength, 1.0)
            elif volatility > np.percentile(np.abs(returns), 80):
                regime_type = 'volatile'
                confidence = 0.7
            elif volatility < np.percentile(np.abs(returns), 20):
                regime_type = 'calm'
                confidence = 0.8
            else:
                regime_type = 'ranging'
                confidence = 0.6
            
            regime = MarketRegime(
                regime_type=regime_type,
                confidence=confidence,
                detected_at=datetime.now(timezone.utc),
                features={
                    'volatility': float(volatility),
                    'trend_strength': float(trend_strength)
                }
            )
            
            self._current_regime[key] = regime
        
        except Exception as e:
            self.logger.error("Error detecting market regime", error=e)
    
    async def _detect_patterns(self, key: tuple[str, str]) -> None:
        """Detect chart patterns (simplified)."""
        bars = list(self._price_history[key])
        if len(bars) < 30:
            return
        
        try:
            closes = np.array([float(bar.close) for bar in bars[-30:]])
            
            patterns = []
            
            # Simple pattern: Double top/bottom
            peaks = self._find_peaks(closes)
            if len(peaks) >= 2:
                last_two_peaks = peaks[-2:]
                if abs(closes[last_two_peaks[0]] - closes[last_two_peaks[1]]) / closes[last_two_peaks[0]] < 0.02:
                    pattern = PatternMatch(
                        pattern_type='double_top',
                        confidence=0.7,
                        expected_move=-0.03,  # Expect 3% down move
                        timeframe=10,
                        detected_at=datetime.now(timezone.utc)
                    )
                    patterns.append(pattern)
            
            self._detected_patterns[key] = patterns
        
        except Exception as e:
            self.logger.error("Error detecting patterns", error=e)
    
    async def _ensemble_predict(self, features: np.ndarray, 
                               regime: Optional[MarketRegime],
                               patterns: List[PatternMatch]) -> Dict:
        """Generate ensemble prediction from multiple models."""
        # Placeholder: would use actual ML models
        
        # Simulate prediction based on features
        momentum_signal = features[3]  # 10-bar momentum
        volatility = features[1]
        
        # Adjust based on regime
        regime_weight = 1.0
        if regime:
            regime_weight = self.params['regime_weights'].get(regime.regime_type, 1.0)
        
        # Base prediction
        direction = 1.0 if momentum_signal > 0 else -1.0
        confidence = min(abs(momentum_signal) * 10 * regime_weight, 1.0)
        
        # Boost confidence if patterns align
        if patterns:
            latest_pattern = patterns[-1]
            if (latest_pattern.expected_move > 0 and direction > 0) or \
               (latest_pattern.expected_move < 0 and direction < 0):
                confidence = min(confidence * 1.2, 1.0)
        
        return {
            'direction': direction,
            'confidence': confidence,
            'expected_return': direction * 0.02,  # 2% expected move
            'time_horizon': 20  # bars
        }
    
    async def _single_model_predict(self, features: np.ndarray) -> Dict:
        """Generate prediction from single model."""
        return await self._ensemble_predict(features, None, [])
    
    async def _adaptive_position_size(self, symbol: str, venue: str, 
                                     price: Decimal, confidence: float,
                                     regime: Optional[MarketRegime]) -> float:
        """Calculate adaptive position size based on confidence and regime."""
        capital = 100000.0  # TODO: Get from portfolio manager
        
        base_size = capital * self.config.position_size_pct
        
        # Adjust by confidence
        size = base_size * confidence
        
        # Adjust by regime
        if regime:
            if regime.regime_type == 'volatile':
                size *= 0.5  # Reduce size in volatile markets
            elif regime.regime_type == 'trending':
                size *= 1.2  # Increase size in trending markets
        
        quantity = size / float(price)
        
        if self.config.max_position_size:
            max_quantity = self.config.max_position_size / float(price)
            quantity = min(quantity, max_quantity)
        
        return quantity
    
    async def _calculate_position_size(self, symbol: str, venue: str, price: Decimal) -> float:
        """Standard position size calculation."""
        capital = 100000.0
        size = capital * self.config.position_size_pct
        return size / float(price)
    
    def _calculate_dynamic_stops(self, price: Decimal, predictions: Dict,
                                 regime: Optional[MarketRegime]) -> Dict:
        """Calculate dynamic stop loss and take profit."""
        base_stop_pct = self.config.stop_loss_pct
        base_tp_pct = self.config.take_profit_pct
        
        # Adjust based on regime volatility
        if regime and regime.regime_type == 'volatile':
            stop_multiplier = 1.5  # Wider stops in volatile markets
            tp_multiplier = 2.0    # Wider targets
        else:
            stop_multiplier = 1.0
            tp_multiplier = 1.0
        
        direction = predictions['direction']
        
        if direction > 0:
            stop_loss = price * Decimal(str(1 - base_stop_pct * stop_multiplier))
            take_profit = price * Decimal(str(1 + base_tp_pct * tp_multiplier))
        else:
            stop_loss = price * Decimal(str(1 + base_stop_pct * stop_multiplier))
            take_profit = price * Decimal(str(1 - base_tp_pct * tp_multiplier))
        
        return {'stop_loss': stop_loss, 'take_profit': take_profit}
    
    def _confidence_to_strength(self, confidence: float, is_buy: bool) -> SignalStrength:
        """Convert confidence to signal strength."""
        if confidence >= 0.85:
            return SignalStrength.STRONG_BUY if is_buy else SignalStrength.STRONG_SELL
        elif confidence >= 0.7:
            return SignalStrength.BUY if is_buy else SignalStrength.SELL
        elif confidence >= 0.55:
            return SignalStrength.WEAK_BUY if is_buy else SignalStrength.WEAK_SELL
        else:
            return SignalStrength.NEUTRAL
    
    async def _check_retrain_schedule(self) -> None:
        """Check if models need retraining."""
        if not self._last_training:
            self._last_training = datetime.now(timezone.utc)
            return
        
        hours_since_training = (datetime.now(timezone.utc) - self._last_training).total_seconds() / 3600
        
        if hours_since_training >= self.params['retrain_interval_hours']:
            await self._retrain_models()
            self._last_training = datetime.now(timezone.utc)
    
    async def _retrain_models(self) -> None:
        """Retrain ML models with recent data (placeholder)."""
        self.logger.info("Retraining models (placeholder)")
        # In production: collect recent performance data, retrain models
    
    @staticmethod
    def _find_peaks(data: np.ndarray, threshold: float = 0.01) -> List[int]:
        """Find local peaks in price data."""
        peaks = []
        for i in range(1, len(data) - 1):
            if data[i] > data[i-1] and data[i] > data[i+1]:
                if data[i] - min(data[i-1], data[i+1]) > threshold * data[i]:
                    peaks.append(i)
        return peaks
