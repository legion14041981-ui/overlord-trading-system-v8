# Overlord Trading System v8.1 - API Documentation

## Overview

RESTful API for the Overlord Trading System, providing comprehensive access to trading operations, analytics, risk management, and system monitoring.

## Base URL

```
https://api.overlord-trading.com/api/v1
```

Local development:
```
http://localhost:8000/api/v1
```

## Authentication

All API requests require authentication using Bearer tokens:

```bash
curl -H "Authorization: Bearer <your-token>" \
  https://api.overlord-trading.com/api/v1/users
```

### Getting a Token

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh token
- `GET /auth/me` - Get current user

### Users
- `GET /users` - List all users
- `GET /users/{user_id}` - Get user by ID
- `POST /users` - Create new user
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user

### Strategies
- `GET /strategies` - List all strategies
- `GET /strategies/{strategy_id}` - Get strategy details
- `POST /strategies` - Create new strategy
- `PUT /strategies/{strategy_id}` - Update strategy
- `DELETE /strategies/{strategy_id}` - Delete strategy
- `POST /strategies/{strategy_id}/start` - Start strategy
- `POST /strategies/{strategy_id}/stop` - Stop strategy

### Trades
- `GET /trades` - List trades
- `GET /trades/{trade_id}` - Get trade details
- `POST /trades` - Execute trade
- `GET /trades/history` - Get trade history

### Analytics
- `GET /analytics/portfolio/summary` - Portfolio summary
- `GET /analytics/portfolio/performance` - Performance metrics
- `GET /analytics/portfolio/allocation` - Asset allocation
- `GET /analytics/trades/statistics` - Trade statistics
- `GET /analytics/market/correlation` - Market correlation
- `GET /analytics/market/volatility` - Volatility analysis

### Risk Management
- `GET /risk/exposure/current` - Current exposure
- `GET /risk/limits` - Risk limits
- `POST /risk/limits` - Update limits
- `GET /risk/var` - Value at Risk calculation
- `GET /risk/stress-test` - Stress testing
- `GET /risk/alerts` - Risk alerts
- `POST /risk/alerts/{alert_id}/acknowledge` - Acknowledge alert

### Market Data
- `GET /market-data/ticker/{symbol}` - Get ticker
- `GET /market-data/tickers` - Get multiple tickers
- `GET /market-data/orderbook/{symbol}` - Get orderbook
- `GET /market-data/candles/{symbol}` - Get candles
- `GET /market-data/trades/{symbol}` - Get recent trades
- `GET /market-data/funding/{symbol}` - Get funding rate

### Monitoring
- `GET /monitoring/health/detailed` - Detailed health check
- `GET /monitoring/metrics` - System metrics
- `GET /monitoring/metrics/prometheus` - Prometheus metrics
- `GET /monitoring/performance` - Performance stats
- `GET /monitoring/status/exchanges` - Exchange status
- `GET /monitoring/status/strategies` - Strategy status

### System
- `GET /system/info` - System information
- `GET /system/config` - System configuration
- `POST /system/config` - Update configuration
- `GET /system/version` - Version information
- `POST /system/maintenance/enable` - Enable maintenance
- `POST /system/maintenance/disable` - Disable maintenance

## Response Format

All API responses follow this structure:

### Success Response
```json
{
  "data": { ... },
  "timestamp": "2026-01-08T06:20:00Z"
}
```

### Error Response
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request parameters",
    "details": { ... }
  },
  "timestamp": "2026-01-08T06:20:00Z"
}
```

## HTTP Status Codes

- `200 OK` - Successful request
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

## Rate Limiting

API requests are rate limited:
- **Standard**: 100 requests per minute
- **Burst**: Up to 200 requests in short bursts
- **Market Data**: 500 requests per minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1641600000
```

## Pagination

List endpoints support pagination:

```bash
GET /api/v1/trades?page=1&limit=50
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1000,
    "pages": 20
  }
}
```

## Filtering and Sorting

Many endpoints support filtering and sorting:

```bash
GET /api/v1/trades?status=completed&sort=created_at&order=desc
```

## WebSocket API

Real-time data via WebSocket:

```javascript
const ws = new WebSocket('wss://api.overlord-trading.com/ws');

// Subscribe to ticker updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'ticker',
  symbol: 'BTCUSDT'
}));
```

## SDKs

Official SDKs available:
- Python: `pip install overlord-trading-sdk`
- JavaScript/TypeScript: `npm install @overlord/trading-sdk`
- Go: `go get github.com/overlord/trading-sdk-go`

## Interactive Documentation

Explore the API interactively:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI Spec: `http://localhost:8000/api/openapi.json`

## Support

For API support:
- Email: api-support@overlord-trading.com
- Slack: #api-support
- Documentation: https://docs.overlord-trading.com
