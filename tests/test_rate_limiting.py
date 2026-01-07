"""[SEC-001] Integration Tests for Rate Limiting"""

import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.middleware.rate_limiter import setup_rate_limiting
import time

setup_rate_limiting(app)
client = TestClient(app)


class TestRateLimiting:
    """Test suite for rate limiting functionality."""
    
    def test_rate_limit_enforcement(self):
        """Test that rate limits are enforced correctly."""
        # Make requests up to the limit
        for i in range(10):
            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "quantity": 0.01
                }
            )
            assert response.status_code in [200, 201], f"Request {i+1} failed"
        
        # Next request should be rate limited
        response = client.post(
            "/api/v1/orders",
            json={"symbol": "BTC/USDT", "side": "buy", "quantity": 0.01}
        )
        assert response.status_code == 429
        assert "rate_limit_exceeded" in response.json()["detail"]["error"]
    
    def test_rate_limit_per_endpoint(self):
        """Test that different endpoints have independent rate limits."""
        # Exhaust rate limit on /orders
        for _ in range(10):
            client.post("/api/v1/orders", json={})
        
        # /positions should still work
        response = client.get("/api/v1/positions")
        assert response.status_code != 429
    
    def test_rate_limit_reset(self):
        """Test that rate limits reset after the time window."""
        # Exhaust rate limit
        for _ in range(10):
            client.post("/api/v1/orders", json={})
        
        # Should be rate limited
        response = client.post("/api/v1/orders", json={})
        assert response.status_code == 429
        
        # Wait for rate limit to reset (1 minute)
        time.sleep(61)
        
        # Should work again
        response = client.post("/api/v1/orders", json={})
        assert response.status_code != 429
    
    def test_rate_limit_headers(self):
        """Test that Retry-After header is present in 429 responses."""
        # Exhaust rate limit
        for _ in range(10):
            client.post("/api/v1/orders", json={})
        
        response = client.post("/api/v1/orders", json={})
        assert response.status_code == 429
        assert "retry_after" in response.json()["detail"]
    
    def test_rate_limit_metrics(self, prometheus_client):
        """Test that Prometheus metrics are incremented on violations."""
        initial_count = prometheus_client.get_metric(
            "overlord_api_rate_limit_exceeded_total"
        )
        
        # Trigger rate limit
        for _ in range(11):
            client.post("/api/v1/orders", json={})
        
        final_count = prometheus_client.get_metric(
            "overlord_api_rate_limit_exceeded_total"
        )
        assert final_count > initial_count
