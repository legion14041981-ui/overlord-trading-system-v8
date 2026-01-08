"""
Pytest configuration and shared fixtures.
"""
import sys
from pathlib import Path

import pytest

# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def project_root_path():
    """Return project root path."""
    return project_root


@pytest.fixture(scope="session")
def src_path_fixture():
    """Return src directory path."""
    return src_path
