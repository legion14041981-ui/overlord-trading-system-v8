"""Bybit exchange collector implementation."""
import asyncio
import aiohttp
import json
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from .base import BaseCollector
from ..models import Quote, Trade, OHLCV, OrderBook
from ...core.logging.structured_logger import get_logger


logger = get_logger(__name__)


class BybitCollector(BaseCollector):
    """Bybit exchange collector for spot and derivatives."""
    
    BASE_URL = "https://api.bybit.com"
    WS_URL = "wss://stream.bybit.com/v5/public/spot"
    WS_URL_PERP = "wss://stream.bybit.com/v5/public/linear"
    
    def __init__(self, name: str, symbols: List[str],
                 api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 market_type: str = "spot"):
        super().__init__(name, "bybit", symbols, api_key, api_secret)
        self.market_type = market_type  # 'spot' or 'linear' (perpetual)
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection = None
    
    async def connect(self) -> bool:
        """Connect to Bybit API."""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{self.BASE_URL}/v5/market/time") as resp:
                if resp.status == 200:
                    self.is_connected = True
                    logger.info(
                        "Bybit collector connected",
                        context={"venue": "bybit", "market_type": self.market_type, "symbols": len(self.symbols)}
                    )
                    self._reset_error_count()
                    return True
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Bybit."""
        try:
            if self.ws_connection:
                await self.ws_connection.close()
            if self.session:
                await self.session.close()
            self.is_connected = False
            logger.info("Bybit collector disconnected", context={"venue": "bybit"})
        except Exception as e:
            logger.error("Error disconnecting from Bybit", error=e)
    
    async def subscribe_quotes(self, symbols: Optional[List[str]] = None) -> None:
        """Subscribe to ticker (quote) updates."""
        symbols = symbols or self.symbols
        await self._subscribe_websocket(symbols, "tickers")
    
    async def subscribe_trades(self, symbols: Optional[List[str]] = None) -> None:
        """Subscribe to trade stream."""
        symbols = symbols or self.symbols
        await self._subscribe_websocket(symbols, "trades")
    
    async def subscribe_orderbook(self, symbols: Optional[List[str]] = None,
                                  depth: int = 20) -> None:
        """Subscribe to order book updates."""
        symbols = symbols or self.symbols
        depth_str = f"orderbook.{min(depth, 500)}"
        await self._subscribe_websocket(symbols, [depth_str])
    
    async def _subscribe_websocket(self, symbols: List[str], channels: List[str] | str) -> None:
        """Connect to WebSocket and subscribe to channels."""
        try:
            ws_url = self.WS_URL_PERP if self.market_type == "linear" else self.WS_URL
            channels = [channels] if isinstance(channels, str) else channels
            
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    self.ws_connection = ws
                    
                    for symbol in symbols:
                        for channel in channels:
                            subscribe_msg = {
                                "op": "subscribe",
                                "args": [f"{channel}.{symbol}"]
                            }
                            await ws.send_json(subscribe_msg)
                    
                    logger.info(
                        "Bybit WebSocket subscribed",
                        context={"venue": "bybit", "symbols": len(symbols), "channels": channels}
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
            topic = data.get('topic', '')
            
            if 'tickers' in topic:
                quote = self._parse_ticker(data)
                if quote:
                    await self._emit_data(quote)
                    self._reset_error_count()
            
            elif 'trades' in topic:
                trades = self._parse_trades(data)
                for trade in trades:
                    if trade:
                        await self._emit_data(trade)
                self._reset_error_count()
            
            elif 'orderbook' in topic:
                orderbook = self._parse_orderbook(data)
                if orderbook:
                    await self._emit_data(orderbook)
                    self._reset_error_count()
        
        except Exception as e:
            logger.error("Error processing Bybit message", error=e)
    
    def _parse_ticker(self, data: dict) -> Optional[Quote]:
        """Parse quote from Bybit ticker."""
        try:
            ticker_data = data.get('data', {})
            symbol = data.get('topic', '').split('.')[-1]
            
            return Quote(
                symbol=symbol,
                venue="bybit",
                timestamp=datetime.fromtimestamp(int(data.get('ts', 0)) / 1000),
                bid_price=Decimal(ticker_data.get('bid1Price', '0')),
                bid_size=Decimal(ticker_data.get('bid1Size', '0')),
                ask_price=Decimal(ticker_data.get('ask1Price', '0')),
                ask_size=Decimal(ticker_data.get('ask1Size', '0'))
            )
        except Exception as e:
            logger.error("Error parsing Bybit ticker", error=e)
            return None
    
    def _parse_trades(self, data: dict) -> List[Optional[Trade]]:
        """Parse trades from Bybit trade stream."""
        trades = []
        try:
            symbol = data.get('topic', '').split('.')[-1]
            for trade_data in data.get('data', []):
                trade = Trade(
                    trade_id=str(trade_data.get('execId', '')),
                    symbol=symbol,
                    venue="bybit",
                    timestamp=datetime.fromtimestamp(int(trade_data.get('time', 0)) / 1000),
                    price=Decimal(trade_data.get('price', '0')),
                    quantity=Decimal(trade_data.get('size', '0')),
                    side=trade_data.get('side', 'buy')
                )
                trades.append(trade)
        except Exception as e:
            logger.error("Error parsing Bybit trades", error=e)
        
        return trades
    
    def _parse_orderbook(self, data: dict) -> Optional[OrderBook]:
        """Parse order book from Bybit."""
        try:
            symbol = data.get('topic', '').split('.')[-1]
            ob_data = data.get('data', {})
            
            bids = [(Decimal(p), Decimal(q)) for p, q in ob_data.get('b', [])]
            asks = [(Decimal(p), Decimal(q)) for p, q in ob_data.get('a', [])]
            
            return OrderBook(
                symbol=symbol,
                venue="bybit",
                timestamp=datetime.fromtimestamp(int(data.get('ts', 0)) / 1000),
                bids=bids,
                asks=asks
            )
        except Exception as e:
            logger.error("Error parsing Bybit orderbook", error=e)
            return None
    
    async def get_ohlcv(self, symbol: str, interval: str,
                       start: Optional[datetime] = None,
                       end: Optional[datetime] = None) -> List[OHLCV]:
        """Fetch historical OHLCV data."""
        if not self.session:
            return []
        
        try:
            category = "linear" if self.market_type == "linear" else "spot"
            url = f"{self.BASE_URL}/v5/market/kline"
            params = {
                'category': category,
                'symbol': symbol,
                'interval': self._map_interval(interval),
                'limit': 1000
            }
            
            if start:
                params['start'] = int(start.timestamp() * 1000)
            if end:
                params['end'] = int(end.timestamp() * 1000)
            
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('retCode') == 0:
                        return [self._parse_kline(kline, symbol) for kline in result.get('result', {}).get('list', [])]
        except Exception as e:
            logger.error("Error fetching Bybit OHLCV", error=e)
        
        return []
    
    @staticmethod
    def _map_interval(interval: str) -> str:
        """Map interval to Bybit kline interval."""
        mapping = {
            '1m': '1', '5m': '5', '15m': '15',
            '1h': '60', '4h': '240', '1d': 'D', '1w': 'W', '1M': 'M'
        }
        return mapping.get(interval, '60')
    
    def _parse_kline(self, kline: list, symbol: str) -> OHLCV:
        """Parse OHLCV from Bybit kline format."""
        return OHLCV(
            symbol=symbol,
            venue="bybit",
            timestamp=datetime.fromtimestamp(int(kline[0]) / 1000),
            open=Decimal(str(kline[1])),
            high=Decimal(str(kline[2])),
            low=Decimal(str(kline[3])),
            close=Decimal(str(kline[4])),
            volume=Decimal(str(kline[5]))
        )
    
    async def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get current order book snapshot."""
        if not self.session:
            return OrderBook(symbol=symbol, venue="bybit", bids=[], asks=[])
        
        try:
            category = "linear" if self.market_type == "linear" else "spot"
            url = f"{self.BASE_URL}/v5/market/orderbook"
            params = {'category': category, 'symbol': symbol, 'limit': min(depth, 500)}
            
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('retCode') == 0:
                        data = result.get('result', {})
                        bids = [(Decimal(p), Decimal(q)) for p, q in data.get('b', [])]
                        asks = [(Decimal(p), Decimal(q)) for p, q in data.get('a', [])]
                        
                        return OrderBook(
                            symbol=symbol,
                            venue="bybit",
                            timestamp=datetime.utcnow(),
                            bids=bids,
                            asks=asks
                        )
        except Exception as e:
            logger.error("Error fetching Bybit order book", error=e)
        
        return OrderBook(symbol=symbol, venue="bybit", bids=[], asks=[])
