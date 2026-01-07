"""[SEC-002] Integration Tests for IP Whitelisting"""

import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.middleware.ip_filter import IPWhitelistMiddleware
import json
import tempfile
from pathlib import Path


class TestIPWhitelisting:
    """Test suite for IP whitelisting functionality."""
    
    @pytest.fixture
    def whitelist_config(self):
        """Create temporary whitelist config."""
        config = {
            "admin_panel": ["127.0.0.1", "192.168.1.0/24"],
            "trading_api": ["10.0.0.0/8"],
            "internal_services": ["172.16.0.0/12"]
        }
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as f:
            json.dump(config, f)
            return Path(f.name)
    
    @pytest.fixture
    def app_with_ip_filter(self, whitelist_config):
        """Create app with IP filtering middleware."""
        app.add_middleware(IPWhitelistMiddleware, config_path=str(whitelist_config))
        return TestClient(app)
    
    def test_whitelisted_ip_allowed(self, app_with_ip_filter):
        """Test that whitelisted IPs are allowed."""
        response = app_with_ip_filter.get(
            "/api/v1/positions",
            headers={"X-Forwarded-For": "10.0.0.100"}  # Whitelisted
        )
        assert response.status_code != 403
    
    def test_non_whitelisted_ip_blocked(self, app_with_ip_filter):
        """Test that non-whitelisted IPs are blocked."""
        response = app_with_ip_filter.get(
            "/api/v1/positions",
            headers={"X-Forwarded-For": "203.0.113.50"}  # Not whitelisted
        )
        assert response.status_code == 403
        assert "ip_not_whitelisted" in response.json()["detail"]["error"]
    
    def test_admin_panel_restricted(self, app_with_ip_filter):
        """Test that admin panel has stricter IP restrictions."""
        # Trading API IP should not access admin panel
        response = app_with_ip_filter.get(
            "/admin/users",
            headers={"X-Forwarded-For": "10.0.0.100"}
        )
        assert response.status_code == 403
        
        # Admin IP should access admin panel
        response = app_with_ip_filter.get(
            "/admin/users",
            headers={"X-Forwarded-For": "127.0.0.1"}
        )
        assert response.status_code != 403
    
    def test_hot_reload(self, app_with_ip_filter, whitelist_config):
        """Test that whitelist updates are applied without restart."""
        # Initially blocked
        response = app_with_ip_filter.get(
            "/api/v1/positions",
            headers={"X-Forwarded-For": "203.0.113.50"}
        )
        assert response.status_code == 403
        
        # Update whitelist
        with open(whitelist_config, 'w') as f:
            json.dump({
                "trading_api": ["203.0.113.0/24"]  # Now whitelisted
            }, f)
        
        # Wait for file watcher
        import time
        time.sleep(2)
        
        # Should now be allowed
        response = app_with_ip_filter.get(
            "/api/v1/positions",
            headers={"X-Forwarded-For": "203.0.113.50"}
        )
        assert response.status_code != 403
