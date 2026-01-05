"""
API module — REST API интерфейс Overlord.

Exports:
- routes: маршруты API
- middleware: middleware компоненты
"""

from .routes import router
from .middleware import setup_middleware

__all__ = [
    "router",
    "setup_middleware",
]

__version__ = "1.0.0"
