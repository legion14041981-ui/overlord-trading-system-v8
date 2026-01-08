"""
Unit tests for Rate Limiting Middleware
"""
import pytest
import asyncio
from src.middleware.rate_limiting import TokenBucket


@pytest.mark.asyncio
async def test_token_bucket_init():
    """Test token bucket initialization."""
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    
    assert bucket.capacity == 10
    assert bucket.refill_rate == 1.0
    assert bucket.tokens == 10


@pytest.mark.asyncio
async def test_token_bucket_consume():
    """Test token consumption."""
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    
    # Should succeed
    result = await bucket.consume(5)
    assert result is True
    assert bucket.tokens == 5
    
    # Should succeed
    result = await bucket.consume(5)
    assert result is True
    assert bucket.tokens == 0
    
    # Should fail (no tokens left)
    result = await bucket.consume(1)
    assert result is False


@pytest.mark.asyncio
async def test_token_bucket_refill():
    """Test token refill over time."""
    bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens per second
    
    # Consume all tokens
    await bucket.consume(10)
    assert bucket.tokens == 0
    
    # Wait for refill (100ms = 1 token at 10 tokens/sec)
    await asyncio.sleep(0.1)
    
    # Should have ~1 token now
    result = await bucket.consume(1)
    assert result is True
