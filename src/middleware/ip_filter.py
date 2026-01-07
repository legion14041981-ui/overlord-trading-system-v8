"""[SEC-002] IP Whitelisting Middleware with Hot-Reload

Blocks requests from non-whitelisted IPs and logs violations.
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import ipaddress
import json
import logging
from pathlib import Path
from typing import Dict, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce IP whitelisting."""
    
    def __init__(self, app, config_path: str = "/config/allowed_ips.json"):
        super().__init__(app)
        self.config_path = Path(config_path)
        self.whitelist: Dict[str, List[str]] = {}
        self._load_whitelist()
        self._setup_watcher()
    
    def _load_whitelist(self):
        """Load IP whitelist from config file."""
        try:
            with open(self.config_path) as f:
                self.whitelist = json.load(f)
            logger.info(f"Loaded IP whitelist from {self.config_path}")
        except FileNotFoundError:
            logger.warning(f"IP whitelist config not found: {self.config_path}")
            self.whitelist = {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid IP whitelist JSON: {e}")
            self.whitelist = {}
    
    def _setup_watcher(self):
        """Setup file watcher for hot-reload."""
        event_handler = ConfigReloader(self)
        observer = Observer()
        observer.schedule(
            event_handler,
            str(self.config_path.parent),
            recursive=False
        )
        observer.start()
        logger.info("IP whitelist hot-reload watcher started")
    
    def _get_category(self, path: str) -> str:
        """Determine endpoint category from URL path."""
        if path.startswith("/admin"):
            return "admin_panel"
        elif path.startswith("/api/v1"):
            return "trading_api"
        else:
            return "internal_services"
    
    def _is_allowed(self, client_ip: str, category: str) -> bool:
        """Check if client IP is whitelisted for category."""
        try:
            ip = ipaddress.ip_address(client_ip)
            
            for cidr in self.whitelist.get(category, []):
                if ip in ipaddress.ip_network(cidr):
                    return True
            
            return False
        except ValueError:
            logger.error(f"Invalid IP address: {client_ip}")
            return False
    
    async def dispatch(self, request: Request, call_next):
        """Intercept requests and enforce whitelist."""
        client_ip = request.client.host
        endpoint_category = self._get_category(request.url.path)
        
        if not self._is_allowed(client_ip, endpoint_category):
            logger.warning(
                f"Blocked non-whitelisted IP: {client_ip} -> {request.url.path}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "ip_not_whitelisted",
                    "message": "Access denied: IP not in whitelist"
                }
            )
        
        response = await call_next(request)
        return response


class ConfigReloader(FileSystemEventHandler):
    """Hot-reload IP whitelist on file changes."""
    
    def __init__(self, middleware: IPWhitelistMiddleware):
        self.middleware = middleware
    
    def on_modified(self, event):
        if event.src_path.endswith("allowed_ips.json"):
            logger.info("IP whitelist config modified, reloading...")
            self.middleware._load_whitelist()
