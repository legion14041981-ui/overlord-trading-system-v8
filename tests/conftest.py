"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database():
    """Mock database connection for testing."""
    class MockDatabase:
        async def execute(self, query: str):
            return []
        
        async def fetch_one(self, query: str):
            return None
        
        async def fetch_all(self, query: str):
            return []
    
    return MockDatabase()


@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    class MockRedis:
        def __init__(self):
            self._data = {}
        
        async def get(self, key: str):
            return self._data.get(key)
        
        async def set(self, key: str, value: str, ex: int = None):
            self._data[key] = value
        
        async def delete(self, key: str):
            self._data.pop(key, None)
    
    return MockRedis()


@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {
        "id": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True
    }


@pytest.fixture
def sample_strategy():
    """Sample strategy data for testing."""
    return {
        "id": "strat-123",
        "name": "Test Strategy",
        "type": "momentum",
        "status": "active",
        "parameters": {}
    }
