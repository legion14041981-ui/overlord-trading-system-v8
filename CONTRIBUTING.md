# Contributing to Overlord Trading System v8

Welcome! We're excited that you're interested in contributing to the Overlord Trading System v8 project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in your interactions.

### Our Standards

**Examples of behavior that contributes to a positive environment:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

**Examples of unacceptable behavior:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/overlord-trading-system-v8.git
cd overlord-trading-system-v8

# Add upstream remote
git remote add upstream https://github.com/legion14041981-ui/overlord-trading-system-v8.git
```

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Start development services
docker-compose -f docker-compose.dev.yml up -d

# Run migrations
alembic upgrade head
```

## Development Workflow

### 1. Create a Branch

```bash
# Update your fork
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### Branch Naming Convention

- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation changes
- `refactor/` — Code refactoring
- `test/` — Adding tests
- `chore/` — Maintenance tasks

### 2. Make Changes

```bash
# Make your changes
vim src/some_file.py

# Run formatters
black src/
isort src/

# Run linters
flake8 src/
mypy src/

# Run tests
pytest
```

### 3. Commit Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

- Line length: 88 characters (Black default)
- Use type hints for all function arguments and return values
- Use docstrings for all public modules, functions, classes, and methods

### Code Formatting

**Black:**
```bash
black src/ tests/
```

**isort:**
```bash
isort src/ tests/
```

### Linting

**flake8:**
```bash
flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203
```

**mypy:**
```bash
mypy src/
```

### Type Hints Example

```python
from typing import List, Optional
from decimal import Decimal

async def calculate_position_size(
    account_balance: Decimal,
    risk_percentage: Decimal,
    stop_loss_distance: Decimal,
) -> Decimal:
    """Calculate position size based on risk management rules.
    
    Args:
        account_balance: Current account balance
        risk_percentage: Risk as percentage (e.g., 0.02 for 2%)
        stop_loss_distance: Distance to stop loss in price units
        
    Returns:
        Calculated position size
        
    Raises:
        ValueError: If any parameter is negative or zero
    """
    if account_balance <= 0 or risk_percentage <= 0 or stop_loss_distance <= 0:
        raise ValueError("All parameters must be positive")
    
    risk_amount = account_balance * risk_percentage
    position_size = risk_amount / stop_loss_distance
    
    return position_size
```

### Documentation Standards

**Module docstring:**
```python
"""Module for risk management calculations.

This module provides functions for calculating position sizes,
stop losses, and risk metrics for trading strategies.
"""
```

**Function docstring (Google style):**
```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of function.
    
    More detailed description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When invalid parameters are provided
        
    Example:
        >>> function_name("test", 42)
        True
    """
    pass
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/
│   ├── test_risk_manager.py
│   ├── test_order_manager.py
│   └── ...
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── ...
└── fixtures/
    ├── __init__.py
    └── sample_data.py
```

### Writing Tests

```python
import pytest
from decimal import Decimal
from src.core.risk_manager import RiskManager


@pytest.fixture
def risk_manager():
    """Fixture for RiskManager instance."""
    return RiskManager(
        max_position_size=Decimal("10000"),
        max_daily_loss=Decimal("1000"),
    )


class TestRiskManager:
    """Test suite for RiskManager."""
    
    def test_calculate_position_size_valid(self, risk_manager):
        """Test position size calculation with valid inputs."""
        result = risk_manager.calculate_position_size(
            account_balance=Decimal("100000"),
            risk_percentage=Decimal("0.02"),
            stop_loss_distance=Decimal("100"),
        )
        
        assert result == Decimal("20")
    
    def test_calculate_position_size_invalid_negative(self, risk_manager):
        """Test that negative values raise ValueError."""
        with pytest.raises(ValueError):
            risk_manager.calculate_position_size(
                account_balance=Decimal("-100000"),
                risk_percentage=Decimal("0.02"),
                stop_loss_distance=Decimal("100"),
            )
    
    @pytest.mark.asyncio
    async def test_async_method(self, risk_manager):
        """Test async method."""
        result = await risk_manager.async_calculate()
        assert result is not None
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html --cov-report=term

# Specific test file
pytest tests/unit/test_risk_manager.py

# Specific test
pytest tests/unit/test_risk_manager.py::TestRiskManager::test_calculate_position_size_valid

# With verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Coverage Requirements

- Minimum coverage: **80%**
- Critical modules (risk, order management): **90%+**

## Commit Message Guidelines

We follow the **Conventional Commits** specification.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Examples

```
feat(risk): add position sizing calculator

Implement Kelly Criterion-based position sizing with
configurable risk parameters.

Closes #123
```

```
fix(order): handle partial fill edge case

Fixed bug where partially filled orders were not
properly tracked in position manager.

Fixes #456
```

## Pull Request Process

### Before Submitting

- [ ] Run all tests: `pytest`
- [ ] Run linters: `flake8`, `mypy`
- [ ] Run formatters: `black`, `isort`
- [ ] Update documentation if needed
- [ ] Add tests for new features
- [ ] Ensure commit messages follow guidelines

### PR Title Format

```
<type>: Brief description of changes
```

Example: `feat: Add WebSocket support for real-time market data`

### PR Description Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe the tests you ran.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where needed
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective
- [ ] New and existing unit tests pass locally
```

### Review Process

1. **Automated Checks**: CI pipeline must pass
2. **Code Review**: At least one maintainer approval required
3. **Testing**: All tests must pass
4. **Documentation**: Docs must be updated if needed

## Documentation

### When to Update Docs

- Adding new API endpoints
- Changing configuration options
- Adding new features
- Changing deployment procedures
- Updating dependencies

### Documentation Files

- `README.md` — Project overview
- `docs/API.md` — API documentation
- `docs/ARCHITECTURE.md` — Architecture guide
- `docs/DEPLOYMENT.md` — Deployment guide
- `CONTRIBUTING.md` — This file

## Questions?

If you have questions, please:

1. Check existing [Issues](https://github.com/legion14041981-ui/overlord-trading-system-v8/issues)
2. Search [Discussions](https://github.com/legion14041981-ui/overlord-trading-system-v8/discussions)
3. Open a new issue with the `question` label

---

**Thank you for contributing!** 🚀
