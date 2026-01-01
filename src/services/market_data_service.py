"""
Market Data Service for Overlord v8.1

Handles market data ingestion, storage, retrieval, and technical analysis.
Integrates with:
- Market data providers (Walbi, Binance, etc.)
- Technical analysis engine
- Alert system
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
import asyncio

from src.database.models import (
    MarketDataSource, OHLCData, MarketSnapshot, MarketEvent,
    PriceAlert, MarketStatistics, TimeframeEnum, ExchangeEnum,
    MarketEventTypeEnum
)
from src.monitoring.metrics import (
    dbquerydurationseconds, tradesexecutedtotal
)

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for managing market data"""
    
    def __init__(self, db_session: Session):
        """Initialize market data service
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    # ==================== Market Data Source Management ====================
    
    async def create_data_source(
        self,
        symbol: str,
        exchange: ExchangeEnum,
        base_asset: str,
        quote_asset: str,
        **kwargs
    ) -> MarketDataSource:
        """Create a new market data source
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            exchange: Exchange name
            base_asset: Base asset (e.g., "BTC")
            quote_asset: Quote asset (e.g., "USDT")
            **kwargs: Additional fields (min_price_increment, etc.)
            
        Returns:
            Created MarketDataSource object
        """
        source = MarketDataSource(
            symbol=symbol,
            exchange=exchange,
            base_asset=base_asset,
            quote_asset=quote_asset,
            **kwargs
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        
        logger.info(f"Created market data source: {symbol} on {exchange.value}")
        return source
    
    async def get_data_source(
        self,
        symbol: str,
        exchange: ExchangeEnum
    ) -> Optional[MarketDataSource]:
        """Get market data source by symbol and exchange
        
        Args:
            symbol: Trading pair symbol
            exchange: Exchange name
            
        Returns:
            MarketDataSource or None
        """
        return self.db.query(MarketDataSource).filter(
            and_(
                MarketDataSource.symbol == symbol,
                MarketDataSource.exchange == exchange,
                MarketDataSource.is_active == True
            )
        ).first()
    
    # ==================== OHLC Data Management ====================
    
    async def store_ohlc(
        self,
        source_id: int,
        timeframe: TimeframeEnum,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
        timestamp: datetime,
        **kwargs
    ) -> OHLCData:
        """Store OHLC candlestick data
        
        Args:
            source_id: Market data source ID
            timeframe: Timeframe of candle
            open_price: Open price
            high_price: High price
            low_price: Low price
            close_price: Close price
            volume: Trade volume
            timestamp: Candle timestamp
            **kwargs: Additional fields
            
        Returns:
            Created OHLCData object
        """
        # Check for existing candle
        existing = self.db.query(OHLCData).filter(
            and_(
                OHLCData.source_id == source_id,
                OHLCData.timeframe == timeframe,
                OHLCData.timestamp == timestamp
            )
        ).first()
        
        if existing:
            # Update existing candle (in case of late data)
            existing.close_price = close_price
            existing.high_price = max(existing.high_price, high_price)
            existing.low_price = min(existing.low_price, low_price)
            existing.volume = volume
            self.db.commit()
            return existing
        
        ohlc = OHLCData(
            source_id=source_id,
            timeframe=timeframe,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            timestamp=timestamp,
            **kwargs
        )
        self.db.add(ohlc)
        self.db.commit()
        self.db.refresh(ohlc)
        
        return ohlc
    
    async def get_ohlc_history(
        self,
        source_id: int,
        timeframe: TimeframeEnum,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[OHLCData]:
        """Get OHLC history for a symbol
        
        Args:
            source_id: Market data source ID
            timeframe: Timeframe
            limit: Maximum number of candles to return
            start_time: Start time filter
            end_time: End time filter
            
        Returns:
            List of OHLC data
        """
        query = self.db.query(OHLCData).filter(
            and_(
                OHLCData.source_id == source_id,
                OHLCData.timeframe == timeframe
            )
        )
        
        if start_time:
            query = query.filter(OHLCData.timestamp >= start_time)
        if end_time:
            query = query.filter(OHLCData.timestamp <= end_time)
        
        return query.order_by(desc(OHLCData.timestamp)).limit(limit).all()
    
    # ==================== Market Snapshot Management ====================
    
    async def create_market_snapshot(
        self,
        source_id: int,
        bid_price: float,
        ask_price: float,
        bid_volume: float,
        ask_volume: float,
        last_price: float,
        last_quantity: float,
        **kwargs
    ) -> MarketSnapshot:
        """Create a real-time market snapshot
        
        Args:
            source_id: Market data source ID
            bid_price: Best bid price
            ask_price: Best ask price
            bid_volume: Bid volume
            ask_volume: Ask volume
            last_price: Last trade price
            last_quantity: Last trade quantity
            **kwargs: Additional fields (24h stats, technical indicators)
            
        Returns:
            Created MarketSnapshot
        """
        snapshot = MarketSnapshot(
            source_id=source_id,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            last_price=last_price,
            last_quantity=last_quantity,
            timestamp=datetime.utcnow(),
            **kwargs
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        return snapshot
    
    async def get_latest_snapshot(
        self,
        source_id: int
    ) -> Optional[MarketSnapshot]:
        """Get latest market snapshot for a symbol
        
        Args:
            source_id: Market data source ID
            
        Returns:
            Latest MarketSnapshot or None
        """
        return self.db.query(MarketSnapshot).filter(
            MarketSnapshot.source_id == source_id
        ).order_by(desc(MarketSnapshot.timestamp)).first()
    
    # ==================== Market Event Detection ====================
    
    async def record_market_event(
        self,
        source_id: int,
        event_type: MarketEventTypeEnum,
        price: float,
        severity: str = "info",
        **kwargs
    ) -> MarketEvent:
        """Record a detected market event
        
        Args:
            source_id: Market data source ID
            event_type: Type of market event
            price: Current price
            severity: Event severity (info, warning, critical)
            **kwargs: Additional event details
            
        Returns:
            Created MarketEvent
        """
        event = MarketEvent(
            source_id=source_id,
            event_type=event_type,
            price=price,
            severity=severity,
            timestamp=datetime.utcnow(),
            **kwargs
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Market event: {event_type.value} at {price} (severity: {severity})")
        return event
    
    async def get_recent_events(
        self,
        source_id: int,
        hours: int = 24,
        event_type: Optional[MarketEventTypeEnum] = None
    ) -> List[MarketEvent]:
        """Get recent market events
        
        Args:
            source_id: Market data source ID
            hours: Number of hours to look back
            event_type: Filter by event type (optional)
            
        Returns:
            List of MarketEvent objects
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = self.db.query(MarketEvent).filter(
            and_(
                MarketEvent.source_id == source_id,
                MarketEvent.timestamp >= cutoff_time,
                MarketEvent.is_processed == False
            )
        )
        
        if event_type:
            query = query.filter(MarketEvent.event_type == event_type)
        
        return query.order_by(desc(MarketEvent.timestamp)).all()
    
    async def mark_event_processed(
        self,
        event_id: int
    ) -> None:
        """Mark a market event as processed
        
        Args:
            event_id: Market event ID
        """
        event = self.db.query(MarketEvent).filter(MarketEvent.id == event_id).first()
        if event:
            event.is_processed = True
            self.db.commit()
    
    # ==================== Market Statistics ====================
    
    async def update_market_statistics(
        self,
        source_id: int,
        statistics_data: Dict
    ) -> MarketStatistics:
        """Update market statistics (daily/weekly/monthly)
        
        Args:
            source_id: Market data source ID
            statistics_data: Dictionary with statistics
                - daily_high, daily_low, daily_open, daily_close
                - daily_volume, daily_trades
                - volatility_daily, market_regime, strength
                
        Returns:
            Created or updated MarketStatistics
        """
        date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        existing = self.db.query(MarketStatistics).filter(
            and_(
                MarketStatistics.source_id == source_id,
                MarketStatistics.date == date
            )
        ).first()
        
        if existing:
            for key, value in statistics_data.items():
                setattr(existing, key, value)
            self.db.commit()
            return existing
        
        stats = MarketStatistics(
            source_id=source_id,
            date=date,
            **statistics_data
        )
        self.db.add(stats)
        self.db.commit()
        self.db.refresh(stats)
        
        return stats
    
    # ==================== Technical Indicators ====================
    
    async def update_technical_indicators(
        self,
        snapshot_id: int,
        indicators: Dict[str, float]
    ) -> None:
        """Update technical indicators for a snapshot
        
        Args:
            snapshot_id: MarketSnapshot ID
            indicators: Dictionary of indicator values
                - sma_20, sma_50, sma_200
                - rsi_14
                - macd, macd_signal, macd_histogram
                - bollinger_upper, bollinger_middle, bollinger_lower
        """
        snapshot = self.db.query(MarketSnapshot).filter(
            MarketSnapshot.id == snapshot_id
        ).first()
        
        if snapshot:
            for indicator, value in indicators.items():
                if hasattr(snapshot, indicator):
                    setattr(snapshot, indicator, value)
            self.db.commit()
    
    # ==================== Price Alerts ====================
    
    async def get_triggered_price_alerts(
        self,
        source_id: int,
        current_price: float
    ) -> List[PriceAlert]:
        """Get price alerts that should trigger at current price
        
        Args:
            source_id: Market data source ID
            current_price: Current market price
            
        Returns:
            List of triggered PriceAlert objects
        """
        alerts = self.db.query(PriceAlert).filter(
            and_(
                PriceAlert.source_id == source_id,
                PriceAlert.is_active == True,
                PriceAlert.triggered_at == None  # Not yet triggered
            )
        ).all()
        
        triggered = []
        for alert in alerts:
            if alert.trigger_condition == "above" and current_price >= alert.target_price:
                triggered.append(alert)
            elif alert.trigger_condition == "below" and current_price <= alert.target_price:
                triggered.append(alert)
        
        return triggered
    
    # ==================== Data Cleanup ====================
    
    async def cleanup_old_data(
        self,
        days_retention: int = 90
    ) -> Dict[str, int]:
        """Clean up old market data beyond retention period
        
        Args:
            days_retention: Number of days to retain (default 90)
            
        Returns:
            Dictionary with counts of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_retention)
        
        deleted_ohlc = self.db.query(OHLCData).filter(
            OHLCData.timestamp < cutoff_date
        ).delete()
        
        deleted_snapshots = self.db.query(MarketSnapshot).filter(
            MarketSnapshot.timestamp < cutoff_date
        ).delete()
        
        deleted_events = self.db.query(MarketEvent).filter(
            and_(
                MarketEvent.timestamp < cutoff_date,
                MarketEvent.is_archived == True
            )
        ).delete()
        
        self.db.commit()
        
        logger.info(
            f"Cleaned up old market data: "
            f"{deleted_ohlc} OHLC, "
            f"{deleted_snapshots} snapshots, "
            f"{deleted_events} events"
        )
        
        return {
            "ohlc_deleted": deleted_ohlc,
            "snapshots_deleted": deleted_snapshots,
            "events_deleted": deleted_events
        }
