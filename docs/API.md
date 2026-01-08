# Overlord Trading System v8 - API Documentation

## Overview

This document provides comprehensive documentation for the Overlord Trading System v8 API endpoints, WebSocket connections, and service interfaces.

## Table of Contents

- [REST API Endpoints](#rest-api-endpoints)
- [WebSocket API](#websocket-api)
- [Service Layer](#service-layer)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

---

## REST API Endpoints

### Health Check

```http
GET /health
```

Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-08T06:50:00Z",
  "services": {
    "database": "up",
    "redis": "up",
    "exchanges": ["binance", "bybit"]
  }
}
```

### System Metrics

```http
GET /api/v1/metrics
```

Returns current system metrics.

**Response:**
```json
{
  "equity": "105000.00",
  "pnl_daily": "5000.00",
  "pnl_total": "15000.00",
  "positions": 3,
  "open_orders": 5,
  "sharpe_ratio": 2.34,
  "max_drawdown": "0.0834"
}
```

### Order Management

#### Create Order

```http
POST /api/v1/orders
```

**Request Body:**
```json
{
  "symbol": "BTCUSDT",
  "side": "buy",
  "order_type": "limit",
  "quantity": "0.001",
  "price": "45000.00",
  "time_in_force": "GTC"
}
```

**Response:**
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-01-08T06:50:00Z"
}
```

#### Get Order Status

```http
GET /api/v1/orders/{order_id}
```

**Response:**
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "symbol": "BTCUSDT",
  "side": "buy",
  "status": "filled",
  "filled_quantity": "0.001",
  "average_price": "44995.50",
  "created_at": "2026-01-08T06:50:00Z",
  "updated_at": "2026-01-08T06:50:15Z"
}
```

#### Cancel Order

```http
DELETE /api/v1/orders/{order_id}
```

**Response:**
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "cancelled_at": "2026-01-08T06:51:00Z"
}
```

### Position Management

#### Get All Positions

```http
GET /api/v1/positions
```

**Response:**
```json
[
  {
    "symbol": "BTCUSDT",
    "side": "long",
    "quantity": "0.15",
    "entry_price": "43500.00",
    "current_price": "45000.00",
    "unrealized_pnl": "225.00",
    "realized_pnl": "0.00"
  }
]
```

#### Close Position

```http
POST /api/v1/positions/{symbol}/close
```

**Request Body:**
```json
{
  "quantity": "0.15",
  "order_type": "market"
}
```

### Analytics

#### Get Performance Metrics

```http
GET /api/v1/analytics/performance
```

**Query Parameters:**
- `period`: Time period (default: "30d")
- `metrics`: Comma-separated list of metrics

**Response:**
```json
{
  "period": "30d",
  "total_return": "0.1547",
  "sharpe_ratio": 2.34,
  "sortino_ratio": 3.12,
  "max_drawdown": "0.0834",
  "win_rate": "0.6234",
  "profit_factor": 2.45,
  "trades_count": 147
}
```

#### Get Equity Curve

```http
GET /api/v1/analytics/equity-curve
```

**Response:**
```json
{
  "data_points": [
    {"timestamp": "2026-01-01T00:00:00Z", "equity": "100000.00"},
    {"timestamp": "2026-01-02T00:00:00Z", "equity": "101250.00"}
  ]
}
```

---

## WebSocket API

### Connection

```
ws://localhost:8000/ws/trading
```

**Authentication:**
Send authentication message immediately after connection:

```json
{
  "type": "auth",
  "token": "your-jwt-token"
}
```

### Subscribe to Market Data

```json
{
  "type": "subscribe",
  "channel": "market_data",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

**Server Response:**
```json
{
  "type": "market_data",
  "symbol": "BTCUSDT",
  "price": "45000.00",
  "volume": "123.45",
  "timestamp": "2026-01-08T06:50:00Z"
}
```

### Subscribe to Order Updates

```json
{
  "type": "subscribe",
  "channel": "orders"
}
```

**Server Response:**
```json
{
  "type": "order_update",
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "filled",
  "filled_quantity": "0.001",
  "timestamp": "2026-01-08T06:50:15Z"
}
```

---

## Service Layer

### Notification Service

```python
from src.services import NotificationService
from src.services.notification_service import (
    NotificationChannel,
    NotificationPriority
)

service = NotificationService()

# Send single notification
await service.send_notification(
    message="Order filled: BTCUSDT",
    channel=NotificationChannel.SLACK,
    priority=NotificationPriority.HIGH
)

# Send to multiple channels
await service.send_multi_channel(
    message="Risk limit breached!",
    channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
    priority=NotificationPriority.CRITICAL
)
```

### Audit Service

```python
from src.services import AuditService
from src.services.audit_service import AuditEventType

audit = AuditService(enable_persistent_storage=True)

# Log audit event
await audit.log_event(
    event_type=AuditEventType.ORDER_PLACED,
    user_id="system",
    details={
        "order_id": "550e8400-e29b-41d4-a716-446655440000",
        "symbol": "BTCUSDT",
        "quantity": "0.001"
    }
)

# Get recent events
events = await audit.get_recent_events(
    limit=50,
    event_type=AuditEventType.ORDER_PLACED
)
```

### Cache Service

```python
from src.services import CacheService

cache = CacheService(default_ttl=300)
await cache.start()

# Set value
await cache.set("market_data:BTCUSDT", price_data, ttl=60)

# Get value
price = await cache.get("market_data:BTCUSDT")

# Get statistics
stats = await cache.get_stats()

await cache.stop()
```

---

## Authentication

### JWT Token

All API requests (except `/health`) require a valid JWT token in the Authorization header:

```http
Authorization: Bearer <your-jwt-token>
```

### Token Structure

```json
{
  "sub": "user_id",
  "exp": 1736324400,
  "roles": ["trader", "admin"]
}
```

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "INVALID_ORDER",
    "message": "Insufficient balance",
    "details": {
      "required": "1000.00",
      "available": "500.00"
    },
    "timestamp": "2026-01-08T06:50:00Z"
  }
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

---

## Rate Limiting

### Limits

- **REST API**: 100 requests per minute per IP
- **WebSocket**: 50 messages per second per connection
- **Order Placement**: 20 orders per second

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1736324460
```

### Rate Limit Exceeded Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 42,
    "timestamp": "2026-01-08T06:50:00Z"
  }
}
```

---

## Examples

### Python Client Example

```python
import aiohttp
import asyncio

class OverlordClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def create_order(self, symbol: str, side: str, quantity: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/orders",
                headers=self.headers,
                json={
                    "symbol": symbol,
                    "side": side,
                    "order_type": "market",
                    "quantity": quantity
                }
            ) as response:
                return await response.json()

# Usage
client = OverlordClient("http://localhost:8000", "your-token")
order = await client.create_order("BTCUSDT", "buy", "0.001")
```

---

## Version History

- **v8.1** (2026-01-08): Added service layer documentation
- **v8.0** (2026-01-01): Initial API documentation
