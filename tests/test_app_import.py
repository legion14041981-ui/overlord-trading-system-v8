"""
Basic test to verify application can be imported.
"""
import pytest


def test_app_import():
    """Test that main FastAPI app can be imported."""
    from src.main import app
    
    assert app is not None
    assert app.title == "Overlord Trading System v8.1"
    assert app.version == "8.1.0"


def test_app_routes():
    """Test that basic routes are registered."""
    from src.main import app
    
    routes = [route.path for route in app.routes]
    
    assert "/" in routes
    assert "/health" in routes
    assert "/api/v1/status" in routes


def test_app_metadata():
    """Test application metadata."""
    from src.main import app
    
    assert app.docs_url == "/api/docs"
    assert app.redoc_url == "/api/redoc"
    assert app.openapi_url == "/api/openapi.json"
