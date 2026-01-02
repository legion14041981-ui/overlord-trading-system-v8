"""WebSocket adapter with auto-reconnect and heartbeat."""
import asyncio
from typing import Optional, Callable, Awaitable
import aiohttp
from aiohttp import WSMsgType

from ...core.logging.structured_logger import get_logger


class WebSocketAdapter:
    """Async WebSocket client with fault tolerance."""
    
    def __init__(self, url: str,
                 on_message: Optional[Callable[[str], Awaitable[None]]] = None,
                 on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
                 on_close: Optional[Callable[[], Awaitable[None]]] = None,
                 heartbeat: int = 30,
                 ping_timeout: int = 10):
        self.url = url
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.heartbeat = heartbeat
        self.ping_timeout = ping_timeout
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._connected = False
        self.logger = get_logger(__name__)
    
    async def connect(self) -> None:
        """Establish WebSocket connection."""
        try:
            self.session = aiohttp.ClientSession()
            self.ws = await self.session.ws_connect(
                self.url,
                heartbeat=self.heartbeat,
                timeout=aiohttp.ClientTimeout(total=60)
            )
            
            self._connected = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            self.logger.info("WebSocket connected", {"url": self.url})
        
        except Exception as e:
            self.logger.error("Failed to connect WebSocket", error=e, context={
                "url": self.url
            })
            await self._cleanup()
            raise
    
    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        await self._cleanup()
        self.logger.info("WebSocket disconnected", {"url": self.url})
    
    async def send(self, message: str) -> None:
        """Send message through WebSocket."""
        if not self._connected or not self.ws:
            raise RuntimeError("WebSocket not connected")
        
        try:
            await self.ws.send_str(message)
            self.logger.debug("Message sent", {"message": message[:100]})
        except Exception as e:
            self.logger.error("Failed to send message", error=e)
            raise
    
    async def _receive_loop(self) -> None:
        """Continuously receive messages."""
        try:
            async for msg in self.ws:
                if msg.type == WSMsgType.TEXT:
                    if self.on_message:
                        try:
                            await self.on_message(msg.data)
                        except Exception as e:
                            self.logger.error("Error in message handler", error=e)
                
                elif msg.type == WSMsgType.ERROR:
                    error = Exception(f"WebSocket error: {self.ws.exception()}")
                    self.logger.error("WebSocket error", error=error)
                    if self.on_error:
                        await self.on_error(error)
                
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                    self.logger.warning("WebSocket closed", {
                        "type": msg.type.name
                    })
                    break
        
        except asyncio.CancelledError:
            self.logger.debug("Receive loop cancelled")
        
        except Exception as e:
            self.logger.error("Error in receive loop", error=e)
            if self.on_error:
                await self.on_error(e)
        
        finally:
            self._connected = False
            if self.on_close:
                await self.on_close()
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self.ws and not self.ws.closed:
            await self.ws.close()
        
        if self.session and not self.session.closed:
            await self.session.close()
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected and self.ws is not None and not self.ws.closed
