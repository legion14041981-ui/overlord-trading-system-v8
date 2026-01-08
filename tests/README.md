# Overlord Trading System v8.1 - Test Suite

## Overview

Comprehensive test suite for Overlord Trading System v8.1 covering:
- Unit tests
- Integration tests
- End-to-end tests
- Performance tests

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── routers/            # Router tests
│   ├── middleware/         # Middleware tests
│   ├── services/           # Service tests
│   └── core/               # Core module tests
├── integration/            # Integration tests
│   ├── test_api_endpoints.py
│   └── test_middleware_stack.py
├── e2e/                    # End-to-end tests
├── conftest.py             # Pytest fixtures and configuration
└── README.md               # This file
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/unit/routers/test_analytics.py
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

### Run with verbose output
```bash
pytest -v
```

### Run only unit tests
```bash
pytest tests/unit/
```

### Run only integration tests
```bash
pytest tests/integration/
```

### Run tests matching pattern
```bash
pytest -k "test_middleware"
```

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Use mocks for external dependencies
- Fast execution (<1s per test)

### Integration Tests
- Test interaction between components
- May use test database/services
- Moderate execution time (1-5s per test)

### End-to-End Tests
- Test complete user workflows
- Use real or staging services
- Longer execution time (>5s per test)

## Code Coverage Goals

- Overall coverage: >80%
- Critical paths: >95%
- New code: 100%

## Writing Tests

### Test Naming Convention
```python
def test_<function_name>_<scenario>():
    """Test that <function> <expected behavior> when <condition>."""
    pass
```

### Example Unit Test
```python
import pytest

@pytest.mark.asyncio
async def test_get_portfolio_summary_returns_correct_structure():
    """Test that portfolio summary returns correct data structure."""
    from src.routers.analytics import get_portfolio_summary
    
    result = await get_portfolio_summary()
    
    assert isinstance(result, dict)
    assert "total_value" in result
    assert "positions_count" in result
```

### Using Fixtures
```python
def test_with_mock_database(mock_database):
    """Test using mock database fixture."""
    # Use mock_database here
    pass
```

## Continuous Integration

Tests are automatically run on:
- Every push to main branch
- Every pull request
- Scheduled daily runs

See `.github/workflows/ci.yml` for CI configuration.

## Debugging Tests

### Run with debugger
```bash
pytest --pdb
```

### Print output during tests
```bash
pytest -s
```

### Run last failed tests
```bash
pytest --lf
```

## Performance Testing

For performance tests:
```bash
pytest tests/performance/ --benchmark-only
```

## Test Requirements

All test dependencies are in `requirements-dev.txt`:
```bash
pip install -r requirements-dev.txt
```
