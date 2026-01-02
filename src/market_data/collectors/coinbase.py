"""Coinbase Pro market data collector."""
import asyncio
import hmac
import hashlib
import base64
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
import json

from .base import BaseCollector
from ...core.models import Quote, Trade, OHLCV
from ..adapters.http_adapter import HTTPAdapter
from ..adapters.ws_adapter import WebSocketAdapter


class CoinbaseCollector(BaseCollector):
    """Coinbase Pro market data collector."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("coinbase", config)
        self.base_url = config.get('base_url', 'https://api.exchange.coinbase.com')
        self.ws_url = config.get('websocket_url', 'wss://ws-feed.exchange.coinbase.com')
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.passphrase = config.get('passphrase', '')
        
        self.http = HTTPAdapter(
            base_url=self.base_url,
            timeout=config.get('timeout', 30),
            max_retries=config.get('retry_attempts', 3)
        )
        self.ws: Optional[WebSocketAdapter] = None
        self._subscribed_symbols: List[str] = []
    
    async def connect(self) -> None:
        """Connect to Coinbase Pro API."""
        try:
            # Test REST API connectivity
            response = await self.http.get('/products')
            
            # Initialize WebSocket
            self.ws = WebSocketAdapter(
                url=self.ws_url,
                on_message=self._handle_ws_message,
                on_error=self._handle_ws_error,
                on_close=self._handle_ws_close
            )
            await self.ws.connect()
            
            self._connected = True
            self.logger.info("Connected to Coinbase Pro", {
                "base_url": self.base_url,
                "ws_url": self.ws_url
            })
        except Exception as e:
            self.logger.error("Failed to connect to Coinbase Pro", error=e)
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Coinbase Pro."""
        if self.ws:
            await self.ws.disconnect()
        await self.http.close()
        self._connected = False
        self.logger.info("Disconnected from Coinbase Pro")
    
    async def subscribe_quotes(self, symbols: List[str]) -> None:
        """Subscribe to ticker (best bid/ask) channel."""
        subscribe_msg = {
            "type": "subscribe",
            "product_ids": symbols,
            "channels": ["ticker"]
        }
        
        if self.ws:
            await self.ws.send(json.dumps(subscribe_msg))
            self._subscribed_symbols.extend(symbols)
            self.logger.info("Subscribed to ticker channel", {
                "symbols": symbols
            })
    
    async def subscribe_trades(self, symbols: List[str]) -> None:
        """Subscribe to matches (trades) channel."""
        subscribe_msg = {
            "type": "subscribe",
            "product_ids": symbols,
            "channels": ["matches"]
        }
        
        if self.ws:
            await self.ws.send(json.dumps(subscribe_msg))
            self.logger.info("Subscribed to matches channel", {
                "symbols": symbols
            })
    
    async def fetch_ohlcv(self, symbol: str, interval: str,
                          start: Optional[datetime] = None,
                          end: Optional[datetime] = None,
                          limit: int = 300) -> List[OHLCV]:
        """Fetch candles data."""
        params = {
            'granularity': self._convert_interval(interval)
        }
        
        if start:
            params['start'] = start.isoformat()
        if end:
            params['end'] = end.isoformat()
        
        try:
            data = await self.http.get(f'/products/{symbol}/candles', params=params)
            
            ohlcvs = []
            for candle in data:
                ohlcvs.append(OHLCV(
                    symbol=symbol,
                    venue="coinbase",
                    interval=interval,
                    timestamp=datetime.fromtimestamp(candle[0], tz=timezone.utc),
                    open=Decimal(str(candle[3])),
                    high=Decimal(str(candle[2])),
                    low=Decimal(str(candle[1])),
                    close=Decimal(str(candle[4])),
                    volume=Decimal(str(candle[5])),
                    quote_volume=None,
                    trades_count=None
                ))
            
            # Coinbase returns newest first, reverse for chronological order
            ohlcvs.reverse()
            
            self.logger.debug(f"Fetched {len(ohlcvs)} OHLCV candles", {
                "symbol": symbol,
                "interval": interval
            })
            
            return ohlcvs[:limit]
        except Exception as e:
            self.logger.error("Failed to fetch OHLCV", error=e, context={
                "symbol": symbol,
                "interval": interval
            })
            raise
    
    async def fetch_order_book(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """Fetch order book snapshot."""
        params = {'level': 2}  # Level 2 = top 50 bids/asks
        
        try:
            data = await self.http.get(f'/products/{symbol}/book', params=params)
            
            bids = [[Decimal(p), Decimal(s)] for p, s, _ in data['bids'][:depth]]
            asks = [[Decimal(p), Decimal(s)] for p, s, _ in data['asks'][:depth]]
            
            return {
                'symbol': symbol,
                'venue': 'coinbase',
                'timestamp': datetime.now(timezone.utc),
                'bids': bids,
                'asks': asks
            }
        except Exception as e:
            self.logger.error("Failed to fetch order book", error=e, context={
                "symbol": symbol
            })
            raise
    
    async def _handle_ws_message(self, message: str) -> None:
        """Handle WebSocket messages."""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            # Ticker (quotes)
            if msg_type == 'ticker':
                quote = Quote(
                    symbol=data['product_id'],
                    venue="coinbase",
                    timestamp=datetime.fromisoformat(data['time'].replace('Z', '+00:00')),
                    bid_price=Decimal(data['best_bid']),
                    bid_size=Decimal(data.get('best_bid_size', '0')),
                    ask_price=Decimal(data['best_ask']),
                    ask_size=Decimal(data.get('best_ask_size', '0'))
                )
                await self._emit_quote(quote)
            
            # Matches (trades)
            elif msg_type == 'match':
                trade = Trade(
                    trade_id=str(data['trade_id']),
                    symbol=data['product_id'],
                    venue="coinbase",
                    timestamp=datetime.fromisoformat(data['time'].replace('Z', '+00:00')),
                    side=data['side'],
                    price=Decimal(data['price']),
                    quantity=Decimal(data['size'])
                )
                await self._emit_trade(trade)
        
        except Exception as e:
            self.logger.error("Error processing WebSocket message", error=e, context={
                "message": message[:200]
            })
    
    async def _handle_ws_error(self, error: Exception) -> None:
        """Handle WebSocket errors."""
        self.logger.error("WebSocket error", error=error)
        self._connected = False
        await self._reconnect_loop()
    
    async def _handle_ws_close(self) -> None:
        """Handle WebSocket closure."""
        self.logger.warning("WebSocket connection closed")
        self._connected = False
        await self._reconnect_loop()
    
    def _convert_interval(self, interval: str) -> int:
        """Convert standard interval to Coinbase granularity (seconds)."""
        mapping = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '6h': 21600,
            '1d': 86400
        }
        return mapping.get(interval, 60)
