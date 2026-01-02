"""Binance exchange collector implementation."""
import asyncio
import aiohttp
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import json

from .base import BaseCollector
from ..models import Quote, Trade, OHLCV, OrderBook
from ...core.logging.structured_logger import get_logger


logger = get_logger(__name__)


class BinanceCollector(BaseCollector):
    """Binance spot market data collector."""
    
    BASE_URL = "https://api.binance.com/api"
    WS_URL = "wss://stream.binance.com:9443/ws"
    
    def __init__(self, name: str, symbols: List[str], 
                 api_key: Optional[str] = None, api_secret: Optional[str] = None):
        super().__init__(name, "binance", symbols, api_key, api_secret)
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection = None
        self._subscribe_streams = []
    
    async def connect(self) -> bool:
        """Connect to Binance API."""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{self.BASE_URL}/v3/ping") as resp:
                if resp.status == 200:
                    self.is_connected = True
                    logger.info(
                        "Binance collector connected",
                        context={"venue": "binance", "symbols": len(self.symbols)}
                    )
                    self._reset_error_count()
                    return True
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Binance."""
        try:
            if self.ws_connection:
                await self.ws_connection.close()
            if self.session:
                await self.session.close()
            self.is_connected = False
            logger.info("Binance collector disconnected", context={"venue": "binance"})
        except Exception as e:
            logger.error("Error disconnecting from Binance", error=e)
    
    async def subscribe_quotes(self, symbols: Optional[List[str]] = None) -> None:
        """Subscribe to bid/ask updates."""
        symbols = symbols or self.symbols
        streams = [f"{symbol.lower()}@bookTicker" for symbol in symbols]
        self._subscribe_streams.extend(streams)
        await self._connect_websocket()
    
    async def subscribe_trades(self, symbols: Optional[List[str]] = None) -> None:
        """Subscribe to trade stream."""
        symbols = symbols or self.symbols
        streams = [f"{symbol.lower()}@trade" for symbol in symbols]
        self._subscribe_streams.extend(streams)
        await self._connect_websocket()
    
    async def subscribe_orderbook(self, symbols: Optional[List[str]] = None,
                                  depth: int = 20) -> None:
        """Subscribe to order book updates."""
        symbols = symbols or self.symbols
        valid_depths = [5, 10, 20, 50, 100, 500, 1000]
        depth = min(valid_depths, key=lambda x: abs(x - depth))
        streams = [f"{symbol.lower()}@depth{depth}@100ms" for symbol in symbols]
        self._subscribe_streams.extend(streams)
        await self._connect_websocket()
    
    async def _connect_websocket(self) -> None:
        """Establish WebSocket connection."""
        try:
            stream_url = f"{self.WS_URL}/{'/'.join(self._subscribe_streams)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(stream_url) as ws:
                    self.ws_connection = ws
                    logger.info(
                        "Binance WebSocket connected",
                        context={"venue": "binance", "streams": len(self._subscribe_streams)}
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
            stream = data.get('stream', '')
            payload = data.get('data', {})
            
            if 'bookTicker' in stream:
                quote = self._parse_quote(payload)
                if quote:
                    await self._emit_data(quote)
                    self._reset_error_count()
            
            elif '@trade' in stream:
                trade = self._parse_trade(payload)
                if trade:
                    await self._emit_data(trade)
                    self._reset_error_count()
            
            elif '@depth' in stream:
                orderbook = self._parse_orderbook(payload, stream)
                if orderbook:
                    await self._emit_data(orderbook)
                    self._reset_error_count()
        
        except Exception as e:
            logger.error("Error processing Binance message", error=e)
    
    def _parse_quote(self, data: dict) -> Optional[Quote]:
        """Parse quote from Binance ticker format."""
        try:
            return Quote(
                symbol=data.get('s', ''),
                venue="binance",
                timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
                bid_price=Decimal(data.get('b', '0')),
                bid_size=Decimal(data.get('B', '0')),
                ask_price=Decimal(data.get('a', '0')),
                ask_size=Decimal(data.get('A', '0'))
            )
        except Exception as e:
            logger.error("Error parsing quote", error=e)
            return None
    
    def _parse_trade(self, data: dict) -> Optional[Trade]:
        """Parse trade from Binance trade format."""
        try:
            return Trade(
                trade_id=str(data.get('t', '')),
                symbol=data.get('s', ''),
                venue="binance",
                timestamp=datetime.fromtimestamp(data.get('T', 0) / 1000),
                price=Decimal(data.get('p', '0')),
                quantity=Decimal(data.get('q', '0')),
                side="buy" if data.get('m') else "sell"
            )
        except Exception as e:
            logger.error("Error parsing trade", error=e)
            return None
    
    def _parse_orderbook(self, data: dict, stream: str) -> Optional[OrderBook]:
        """Parse order book from Binance depth format."""
        try:
            symbol = stream.split('@')[0].upper()
            bids = [(Decimal(p), Decimal(q)) for p, q in data.get('bids', [])]
            asks = [(Decimal(p), Decimal(q)) for p, q in data.get('asks', [])]
            
            return OrderBook(
                symbol=symbol,
                venue="binance",
                timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
                bids=bids,
                asks=asks
            )
        except Exception as e:
            logger.error("Error parsing orderbook", error=e)
            return None
    
    async def get_ohlcv(self, symbol: str, interval: str,
                       start: Optional[datetime] = None,
                       end: Optional[datetime] = None) -> List[OHLCV]:
        """Fetch historical OHLCV data."""
        if not self.session:
            return []
        
        try:
            url = f"{self.BASE_URL}/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': 1000
            }
            
            if start:
                params['startTime'] = int(start.timestamp() * 1000)
            if end:
                params['endTime'] = int(end.timestamp() * 1000)
            
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [self._parse_kline(kline, symbol) for kline in data]
        except Exception as e:
            logger.error("Error fetching OHLCV", error=e)
        
        return []
    
    def _parse_kline(self, kline: list, symbol: str) -> OHLCV:
        """Parse OHLCV from Binance kline format."""
        return OHLCV(
            symbol=symbol,
            venue="binance",
            timestamp=datetime.fromtimestamp(kline[0] / 1000),
            open=Decimal(str(kline[1])),
            high=Decimal(str(kline[2])),
            low=Decimal(str(kline[3])),
            close=Decimal(str(kline[4])),
            volume=Decimal(str(kline[7]))
        )
    
    async def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get current order book snapshot."""
        if not self.session:
            return OrderBook(symbol=symbol, venue="binance", bids=[], asks=[])
        
        try:
            url = f"{self.BASE_URL}/v3/depth"
            params = {'symbol': symbol, 'limit': min(depth, 5000)}
            
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bids = [(Decimal(p), Decimal(q)) for p, q in data.get('bids', [])]
                    asks = [(Decimal(p), Decimal(q)) for p, q in data.get('asks', [])]
                    
                    return OrderBook(
                        symbol=symbol,
                        venue="binance",
                        timestamp=datetime.utcnow(),
                        bids=bids,
                        asks=asks
                    )
        except Exception as e:
            logger.error("Error fetching order book", error=e)
        
        return OrderBook(symbol=symbol, venue="binance", bids=[], asks=[])
