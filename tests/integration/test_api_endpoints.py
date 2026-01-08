"""
Integration tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "online"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_api_status_endpoint():
    """Test API status endpoint."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "api_version" in data
    assert data["api_version"] == "v1"


@pytest.mark.skip(reason="Requires database connection")
def test_users_endpoint():
    """Test users endpoint."""
    response = client.get("/api/v1/users")
    assert response.status_code in [200, 401]  # Depends on auth


@pytest.mark.skip(reason="Requires database connection")
def test_strategies_endpoint():
    """Test strategies endpoint."""
    response = client.get("/api/v1/strategies")
    assert response.status_code in [200, 401]  # Depends on auth
