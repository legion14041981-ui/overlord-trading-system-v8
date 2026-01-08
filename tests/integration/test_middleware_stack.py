"""
Integration tests for middleware stack
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.request_id import RequestIDMiddleware
from src.middleware.logging_middleware import LoggingMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.middleware.metrics import MetricsMiddleware


def test_middleware_stack_integration():
    """Test that all middleware work together."""
    app = FastAPI()
    
    # Add middleware in reverse order (last added = first executed)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "success"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Check request ID
    assert "X-Request-ID" in response.headers
    
    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    
    # Check response
    assert response.status_code == 200
    assert response.json()["message"] == "success"


def test_middleware_order_preserved():
    """Test that middleware execution order is correct."""
    app = FastAPI()
    execution_order = []
    
    class OrderTestMiddleware:
        def __init__(self, app, name):
            self.app = app
            self.name = name
        
        async def __call__(self, scope, receive, send):
            execution_order.append(f"{self.name}_start")
            await self.app(scope, receive, send)
            execution_order.append(f"{self.name}_end")
    
    app.add_middleware(OrderTestMiddleware, name="third")
    app.add_middleware(OrderTestMiddleware, name="second")
    app.add_middleware(OrderTestMiddleware, name="first")
    
    @app.get("/test")
    def test_endpoint():
        return {"ok": True}
    
    client = TestClient(app)
    execution_order.clear()
    response = client.get("/test")
    
    # Middleware added last executes first
    assert execution_order[0] == "first_start"
    assert execution_order[1] == "second_start"
    assert execution_order[2] == "third_start"
