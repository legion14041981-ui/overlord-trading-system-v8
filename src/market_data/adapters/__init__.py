"""Communication adapters for HTTP and WebSocket."""
from .http_adapter import HTTPAdapter
from .ws_adapter import WebSocketAdapter

__all__ = ['HTTPAdapter', 'WebSocketAdapter']
