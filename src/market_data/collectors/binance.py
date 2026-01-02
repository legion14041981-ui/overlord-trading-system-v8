"""Binance market data collector."""
import asyncio
import hmac
import hashlib
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
import aiohttp
import json

from .base import BaseCollector
from ...core.models import Quote, Trade, OHLCV
from ..adapters.http_adapter import HTTPAdapter
from ..adapters.ws_adapter import WebSocketAdapter


class BinanceCollector(BaseCollector):
    """Binance Spot market data collector."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("binance", config)
        self.base_url = config.get('base_url', 'https://api.binance.com')
        self.ws_url = config.get('websocket_url', 'wss://stream.binance.com:9443/ws')
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
        """Connect to Binance API."""
        try:
            # Test REST API connectivity
            response = await self.http.get('/api/v3/ping')
            
            # Initialize WebSocket
            self.ws = WebSocketAdapter(
                url=self.ws_url,
                on_message=self._handle_ws_message,
                on_error=self._handle_ws_error,
                on_close=self._handle_ws_close
            )
            await self.ws.connect()
            
            self._connected = True
            self.logger.info("Connected to Binance", {
                "base_url": self.base_url,
                "ws_url": self.ws_url
            })
        except Exception as e:
            self.logger.error("Failed to connect to Binance", error=e)
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Binance."""
        if self.ws:
            await self.ws.disconnect()
        await self.http.close()
        self._connected = False
        self.logger.info("Disconnected from Binance")
    
    async def subscribe_quotes(self, symbols: List[str]) -> None:
        """Subscribe to book ticker (best bid/ask) updates."""
        streams = [f"{s.lower()}@bookTicker" for s in symbols]
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000)
        }
        
        if self.ws:
            await self.ws.send(json.dumps(subscribe_msg))
            self._subscribed_symbols.extend(symbols)
            self.logger.info("Subscribed to quote streams", {
                "symbols": symbols,
                "streams": streams
            })
    
    async def subscribe_trades(self, symbols: List[str]) -> None:
        """Subscribe to trade stream."""
        streams = [f"{s.lower()}@trade" for s in symbols]
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000)
        }
        
        if self.ws:
            await self.ws.send(json.dumps(subscribe_msg))
            self.logger.info("Subscribed to trade streams", {
                "symbols": symbols,
                "streams": streams
            })
    
    async def fetch_ohlcv(self, symbol: str, interval: str,
                          start: Optional[datetime] = None,
                          end: Optional[datetime] = None,
                          limit: int = 1000) -> List[OHLCV]:
        """Fetch kline/candlestick data."""
        params = {
            'symbol': symbol,
            'interval': self._convert_interval(interval),
            'limit': min(limit, 1000)
        }
        
        if start:
            params['startTime'] = int(start.timestamp() * 1000)
        if end:
            params['endTime'] = int(end.timestamp() * 1000)
        
        try:
            data = await self.http.get('/api/v3/klines', params=params)
            
            ohlcvs = []
            for candle in data:
                ohlcvs.append(OHLCV(
                    symbol=symbol,
                    venue="binance",
                    interval=interval,
                    timestamp=datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                    open=Decimal(str(candle[1])),
                    high=Decimal(str(candle[2])),
                    low=Decimal(str(candle[3])),
                    close=Decimal(str(candle[4])),
                    volume=Decimal(str(candle[5])),
                    quote_volume=Decimal(str(candle[7])),
                    trades_count=int(candle[8])
                ))
            
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
        params = {'symbol': symbol, 'limit': depth}
        
        try:
            data = await self.http.get('/api/v3/depth', params=params)
            return {
                'symbol': symbol,
                'venue': 'binance',
                'timestamp': datetime.now(timezone.utc),
                'bids': [[Decimal(p), Decimal(q)] for p, q in data['bids']],
                'asks': [[Decimal(p), Decimal(q)] for p, q in data['asks']]
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
            
            # Book ticker (quotes)
            if 'e' in data and data['e'] == 'bookTicker':
                quote = Quote(
                    symbol=data['s'],
                    venue="binance",
                    timestamp=datetime.fromtimestamp(data['E'] / 1000, tz=timezone.utc),
                    bid_price=Decimal(data['b']),
                    bid_size=Decimal(data['B']),
                    ask_price=Decimal(data['a']),
                    ask_size=Decimal(data['A'])
                )
                await self._emit_quote(quote)
            
            # Trade stream
            elif 'e' in data and data['e'] == 'trade':
                trade = Trade(
                    trade_id=str(data['t']),
                    symbol=data['s'],
                    venue="binance",
                    timestamp=datetime.fromtimestamp(data['T'] / 1000, tz=timezone.utc),
                    side="buy" if data['m'] else "sell",
                    price=Decimal(data['p']),
                    quantity=Decimal(data['q'])
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
        """Convert standard interval to Binance format."""
        mapping = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '4h': '4h', '1d': '1d', '1w': '1w'
        }
        return mapping.get(interval, '1m')
