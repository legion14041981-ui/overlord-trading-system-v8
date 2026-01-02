"""HTTP client adapter with retry logic and rate limiting."""
import asyncio
from typing import Optional, Dict, Any
import aiohttp
from aiohttp import ClientTimeout, ClientError

from ...core.logging.structured_logger import get_logger


class HTTPAdapter:
    """Async HTTP client with fault tolerance."""
    
    def __init__(self, base_url: str, timeout: int = 30, 
                 max_retries: int = 3, headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip('/')
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.headers = headers or {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger(__name__)
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is created."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers
            )
        return self.session
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> Any:
        """Execute GET request with retries."""
        return await self._request('GET', endpoint, params=params, headers=headers)
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None,
                   json: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> Any:
        """Execute POST request with retries."""
        return await self._request('POST', endpoint, data=data, json=json, headers=headers)
    
    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None,
                  json: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> Any:
        """Execute PUT request with retries."""
        return await self._request('PUT', endpoint, data=data, json=json, headers=headers)
    
    async def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> Any:
        """Execute DELETE request with retries."""
        return await self._request('DELETE', endpoint, headers=headers)
    
    async def _request(self, method: str, endpoint: str,
                       params: Optional[Dict[str, Any]] = None,
                       data: Optional[Dict[str, Any]] = None,
                       json: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None) -> Any:
        """Execute HTTP request with exponential backoff retry."""
        session = await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        
        merged_headers = {**self.headers}
        if headers:
            merged_headers.update(headers)
        
        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=merged_headers
                ) as response:
                    response.raise_for_status()
                    
                    # Handle different content types
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        return await response.json()
                    else:
                        return await response.text()
            
            except ClientError as e:
                retry_delay = 2 ** attempt
                self.logger.warning(f"HTTP request failed, retrying", {
                    "method": method,
                    "url": url,
                    "attempt": attempt + 1,
                    "max_retries": self.max_retries,
                    "retry_delay": retry_delay,
                    "error": str(e)
                })
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.error(f"HTTP request failed after {self.max_retries} attempts", {
                        "method": method,
                        "url": url
                    }, error=e)
                    raise
            
            except Exception as e:
                self.logger.error(f"Unexpected error in HTTP request", {
                    "method": method,
                    "url": url
                }, error=e)
                raise
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("HTTP session closed")
