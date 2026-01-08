"""
Unit tests for Request ID Middleware
"""
import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient
from fastapi import FastAPI

from src.middleware.request_id import RequestIDMiddleware


def test_request_id_generation():
    """Test that request ID is generated when not provided."""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    def test_route():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_request_id_preservation():
    """Test that existing request ID is preserved."""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    def test_route():
        return {"message": "test"}
    
    client = TestClient(app)
    custom_id = "custom-request-id-123"
    response = client.get("/test", headers={"X-Request-ID": custom_id})
    
    assert response.headers["X-Request-ID"] == custom_id
