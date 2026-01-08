"""
API endpoint tests using FastAPI TestClient.
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns correct response."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "online"
    assert data["service"] == "Overlord Trading System"
    assert data["version"] == "8.1.0"
    assert data["docs"] == "/api/docs"


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["version"] == "8.1.0"


def test_api_status_endpoint(client):
    """Test API status endpoint."""
    response = client.get("/api/v1/status")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["api_version"] == "v1"
    assert data["status"] == "operational"
    assert data["mode"] == "production"


def test_openapi_docs_available(client):
    """Test that OpenAPI documentation is available."""
    response = client.get("/api/openapi.json")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "info" in data
    assert "paths" in data
    assert data["info"]["title"] == "Overlord Trading System v8.1"
    assert data["info"]["version"] == "8.1.0"
