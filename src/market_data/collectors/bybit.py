"""Bybit market data collector."""
import asyncio
import hmac
import hashlib
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
import json

from .base import BaseCollector
from ...core.models import Quote, Trade, OHLCV
from ..adapters.http_adapter import HTTPAdapter
from ..adapters.ws_adapter import WebSocketAdapter


class BybitCollector(BaseCollector):
    """Bybit Spot market data collector."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("bybit", config)
        self.base_url = config.get('base_url', 'https://api.bybit.com')
        self.ws_url = config.get('websocket_url', 'wss://stream.bybit.com/v5/public/spot')
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        
        self.http = HTTPAdapter(
            base_url=self.base_url,
            timeout=config.get('timeout', 30),
            max_retries=config.get('retry_attempts', 3)
        )
        self.ws: Optional[WebSocketAdapter] = None
        self._subscribed_symbols: List[str] = []
    
    async def connect(self) -> None:
        """Connect to Bybit API."""
        try:
            # Test REST API connectivity
            response = await self.http.get('/v5/market/time')
            
            # Initialize WebSocket
            self.ws = WebSocketAdapter(
                url=self.ws_url,
                on_message=self._handle_ws_message,
                on_error=self._handle_ws_error,
                on_close=self._handle_ws_close
            )
            await self.ws.connect()
            
            self._connected = True
            self.logger.info("Connected to Bybit", {
                "base_url": self.base_url,
                "ws_url": self.ws_url
            })
        except Exception as e:
            self.logger.error("Failed to connect to Bybit", error=e)
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Bybit."""
        if self.ws:
            await self.ws.disconnect()
        await self.http.close()
        self._connected = False
        self.logger.info("Disconnected from Bybit")
    
    async def subscribe_quotes(self, symbols: List[str]) -> None:
        """Subscribe to book ticker updates."""
        for symbol in symbols:
            subscribe_msg = {
                "op": "subscribe",
                "args": [f"bookticker.{symbol}"]
            }
            if self.ws:
                await self.ws.send(json.dumps(subscribe_msg))
        
        self._subscribed_symbols.extend(symbols)
        self.logger.info("Subscribed to book ticker", {
            "symbols": symbols
        })
    
    async def subscribe_trades(self, symbols: List[str]) -> None:
        """Subscribe to public trades."""
        for symbol in symbols:
            subscribe_msg = {
                "op": "subscribe",
                "args": [f"publicTrade.{symbol}"]
            }
            if self.ws:
                await self.ws.send(json.dumps(subscribe_msg))
        
        self.logger.info("Subscribed to public trades", {
            "symbols": symbols
        })
    
    async def fetch_ohlcv(self, symbol: str, interval: str,
                          start: Optional[datetime] = None,
                          end: Optional[datetime] = None,
                          limit: int = 1000) -> List[OHLCV]:
        """Fetch kline data."""
        params = {
            'category': 'spot',
            'symbol': symbol,
            'interval': self._convert_interval(interval),
            'limit': min(limit, 1000)
        }
        
        if start:
            params['start'] = int(start.timestamp() * 1000)
        if end:
            params['end'] = int(end.timestamp() * 1000)
        
        try:
            response = await self.http.get('/v5/market/kline', params=params)
            data = response.get('result', {}).get('list', [])
            
            ohlcvs = []
            for candle in data:
                ohlcvs.append(OHLCV(
                    symbol=symbol,
                    venue="bybit",
                    interval=interval,
                    timestamp=datetime.fromtimestamp(int(candle[0]) / 1000, tz=timezone.utc),
                    open=Decimal(candle[1]),
                    high=Decimal(candle[2]),
                    low=Decimal(candle[3]),
                    close=Decimal(candle[4]),
                    volume=Decimal(candle[5]),
                    quote_volume=Decimal(candle[6]),
                    trades_count=None
                ))
            
            # Bybit returns newest first, reverse for chronological order
            ohlcvs.reverse()
            
            self.logger.debug(f"Fetched {len(ohlcvs)} OHLCV candles", {
                "symbol": symbol,
                "interval": interval
            })
            
            return ohlcvs
        except Exception as e:
            self.logger.error("Failed to fetch OHLCV", error=e, context={
                "symbol": symbol,
                "interval": interval
            })
            raise
    
    async def fetch_order_book(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """Fetch order book snapshot."""
        params = {
            'category': 'spot',
            'symbol': symbol,
            'limit': min(depth, 50)
        }
        
        try:
            response = await self.http.get('/v5/market/orderbook', params=params)
            data = response.get('result', {})
            
            return {
                'symbol': symbol,
                'venue': 'bybit',
                'timestamp': datetime.fromtimestamp(int(data['ts']) / 1000, tz=timezone.utc),
                'bids': [[Decimal(p), Decimal(s)] for p, s in data['b']],
                'asks': [[Decimal(p), Decimal(s)] for p, s in data['a']]
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
            topic = data.get('topic', '')
            
            # Book ticker (quotes)
            if topic.startswith('bookticker.'):
                ticker_data = data['data']
                quote = Quote(
                    symbol=ticker_data['s'],
                    venue="bybit",
                    timestamp=datetime.fromtimestamp(int(ticker_data['ts']) / 1000, tz=timezone.utc),
                    bid_price=Decimal(ticker_data['bp']),
                    bid_size=Decimal(ticker_data['bq']),
                    ask_price=Decimal(ticker_data['ap']),
                    ask_size=Decimal(ticker_data['aq'])
                )
                await self._emit_quote(quote)
            
            # Public trade
            elif topic.startswith('publicTrade.'):
                for trade_data in data['data']:
                    trade = Trade(
                        trade_id=trade_data['i'],
                        symbol=trade_data['s'],
                        venue="bybit",
                        timestamp=datetime.fromtimestamp(int(trade_data['T']) / 1000, tz=timezone.utc),
                        side="buy" if trade_data['S'] == 'Buy' else "sell",
                        price=Decimal(trade_data['p']),
                        quantity=Decimal(trade_data['v'])
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
    
    def _convert_interval(self, interval: str) -> str:
        """Convert standard interval to Bybit format."""
        mapping = {
            '1m': '1', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '4h': '240', '1d': 'D', '1w': 'W'
        }
        return mapping.get(interval, '1')
