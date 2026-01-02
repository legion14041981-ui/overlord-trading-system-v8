"""Coinbase exchange collector implementation."""
import asyncio
import aiohttp
import json
import hmac
import hashlib
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import time

from .base import BaseCollector
from ..models import Quote, Trade, OHLCV, OrderBook
from ...core.logging.structured_logger import get_logger


logger = get_logger(__name__)


class CoinbaseCollector(BaseCollector):
    """Coinbase Pro market data collector."""
    
    BASE_URL = "https://api.exchange.coinbase.com"
    WS_URL = "wss://ws-feed.exchange.coinbase.com"
    
    def __init__(self, name: str, symbols: List[str],
                 api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None):
        super().__init__(name, "coinbase", symbols, api_key, api_secret)
        self.passphrase = passphrase
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection = None
    
    async def connect(self) -> bool:
        """Connect to Coinbase API."""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{self.BASE_URL}/v3/brokerage/time") as resp:
                if resp.status == 200:
                    self.is_connected = True
                    logger.info(
                        "Coinbase collector connected",
                        context={"venue": "coinbase", "symbols": len(self.symbols)}
                    )
                    self._reset_error_count()
                    return True
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Coinbase."""
        try:
            if self.ws_connection:
                await self.ws_connection.close()
            if self.session:
                await self.session.close()
            self.is_connected = False
            logger.info("Coinbase collector disconnected", context={"venue": "coinbase"})
        except Exception as e:
            logger.error("Error disconnecting from Coinbase", error=e)
    
    async def subscribe_quotes(self, symbols: Optional[List[str]] = None) -> None:
        """Subscribe to ticker updates."""
        symbols = symbols or self.symbols
        await self._subscribe_websocket(symbols, "ticker")
    
    async def subscribe_trades(self, symbols: Optional[List[str]] = None) -> None:
        """Subscribe to match (trade) stream."""
        symbols = symbols or self.symbols
        await self._subscribe_websocket(symbols, "match")
    
    async def subscribe_orderbook(self, symbols: Optional[List[str]] = None,
                                  depth: int = 20) -> None:
        """Subscribe to level2 (order book) updates."""
        symbols = symbols or self.symbols
        await self._subscribe_websocket(symbols, "level2")
    
    async def _subscribe_websocket(self, symbols: List[str], channels: List[str]) -> None:
        """Connect to WebSocket and subscribe to channels."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.WS_URL) as ws:
                    self.ws_connection = ws
                    
                    subscribe_msg = {
                        "type": "subscribe",
                        "product_ids": symbols,
                        "channels": [channels] if isinstance(channels, str) else channels
                    }
                    
                    await ws.send_json(subscribe_msg)
                    logger.info(
                        "Coinbase WebSocket subscribed",
                        context={"venue": "coinbase", "symbols": len(symbols), "channels": channels}
                    )
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._process_message(json.loads(msg.data))
                        elif msg.type in [aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR]:
                            break
        except Exception as e:
            await self._handle_error(e)
    
    async def _process_message(self, data: dict) -> None:
        """Process incoming WebSocket message."""
        try:
            msg_type = data.get('type', '')
            
            if msg_type == 'ticker':
                quote = self._parse_ticker(data)
                if quote:
                    await self._emit_data(quote)
                    self._reset_error_count()
            
            elif msg_type == 'match':
                trade = self._parse_match(data)
                if trade:
                    await self._emit_data(trade)
                    self._reset_error_count()
            
            elif msg_type in ['snapshot', 'l2update']:
                # Order book updates handled separately
                pass
        
        except Exception as e:
            logger.error("Error processing Coinbase message", error=e)
    
    def _parse_ticker(self, data: dict) -> Optional[Quote]:
        """Parse quote from Coinbase ticker."""
        try:
            return Quote(
                symbol=data.get('product_id', ''),
                venue="coinbase",
                timestamp=datetime.fromisoformat(data.get('time', '').replace('Z', '+00:00')),
                bid_price=Decimal(data.get('best_bid', '0')),
                bid_size=Decimal(data.get('best_bid_size', '0')),
                ask_price=Decimal(data.get('best_ask', '0')),
                ask_size=Decimal(data.get('best_ask_size', '0'))
            )
        except Exception as e:
            logger.error("Error parsing Coinbase ticker", error=e)
            return None
    
    def _parse_match(self, data: dict) -> Optional[Trade]:
        """Parse trade from Coinbase match message."""
        try:
            return Trade(
                trade_id=str(data.get('trade_id', '')),
                symbol=data.get('product_id', ''),
                venue="coinbase",
                timestamp=datetime.fromisoformat(data.get('time', '').replace('Z', '+00:00')),
                price=Decimal(data.get('price', '0')),
                quantity=Decimal(data.get('size', '0')),
                side=data.get('side', 'buy')
            )
        except Exception as e:
            logger.error("Error parsing Coinbase match", error=e)
            return None
    
    async def get_ohlcv(self, symbol: str, interval: str,
                       start: Optional[datetime] = None,
                       end: Optional[datetime] = None) -> List[OHLCV]:
        """Fetch historical OHLCV data."""
        if not self.session:
            return []
        
        try:
            url = f"{self.BASE_URL}/v3/brokerage/product/{symbol}/candles"
            params = {'granularity': self._map_interval(interval)}
            
            if start:
                params['start_date'] = start.isoformat()
            if end:
                params['end_date'] = end.isoformat()
            
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [self._parse_candle(candle, symbol) for candle in data.get('candles', [])]
        except Exception as e:
            logger.error("Error fetching Coinbase OHLCV", error=e)
        
        return []
    
    @staticmethod
    def _map_interval(interval: str) -> str:
        """Map interval to Coinbase granularity."""
        mapping = {
            '1m': '60', '5m': '300', '15m': '900',
            '1h': '3600', '6h': '21600', '1d': '86400'
        }
        return mapping.get(interval, '3600')
    
    def _parse_candle(self, candle: list, symbol: str) -> OHLCV:
        """Parse OHLCV from Coinbase candle format."""
        return OHLCV(
            symbol=symbol,
            venue="coinbase",
            timestamp=datetime.fromtimestamp(candle[0]),
            open=Decimal(str(candle[3])),
            high=Decimal(str(candle[2])),
            low=Decimal(str(candle[1])),
            close=Decimal(str(candle[4])),
            volume=Decimal(str(candle[5]))
        )
    
    async def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get current order book snapshot."""
        if not self.session:
            return OrderBook(symbol=symbol, venue="coinbase", bids=[], asks=[])
        
        try:
            url = f"{self.BASE_URL}/v3/brokerage/product_book"
            params = {'product_id': symbol, 'limit': min(depth, 500)}
            
            headers = self._generate_auth_headers('GET', '/v3/brokerage/product_book', '')
            
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bids = [(Decimal(p), Decimal(q)) for p, q in data.get('bids', [])]
                    asks = [(Decimal(p), Decimal(q)) for p, q in data.get('asks', [])]
                    
                    return OrderBook(
                        symbol=symbol,
                        venue="coinbase",
                        timestamp=datetime.utcnow(),
                        bids=bids,
                        asks=asks
                    )
        except Exception as e:
            logger.error("Error fetching Coinbase order book", error=e)
        
        return OrderBook(symbol=symbol, venue="coinbase", bids=[], asks=[])
    
    def _generate_auth_headers(self, method: str, request_path: str, body: str) -> dict:
        """Generate Coinbase API authentication headers."""
        if not self.api_key or not self.api_secret or not self.passphrase:
            return {}
        
        timestamp = str(time.time())
        message = timestamp + method + request_path + body
        hmac_key = self.api_secret.encode('utf-8')
        signature = hmac.new(hmac_key, message.encode('utf-8'), hashlib.sha256).digest()
        
        import base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return {
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase
        }
