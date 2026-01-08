# Overlord Trading System v8

[![CI Status](https://github.com/legion14041981-ui/overlord-trading-system-v8/workflows/CI/badge.svg)](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**LEGION v8.1 Autonomous Mission Weaver** — Полностью автономная торговая система с самоорганизующейся архитектурой, реализованная в рамках экосистемы LEGION.

## 🚀 Ключевые возможности

### Торговые функции
- **Мультибиржевая поддержка**: Binance, Bybit, OKX через унифицированный CCXT API
- **Умное управление ордерами**: Лимитные, рыночные, стоп-ордера с автоматической маршрутизацией
- **Управление позициями**: Полный цикл от открытия до закрытия с отслеживанием P&L
- **Риск-менеджмент**: Динамические лимиты, стоп-лоссы, position sizing

### Аналитика и мониторинг
- **Метрики производительности в реальном времени**: Sharpe, Sortino, Max Drawdown
- **Кривая доходности**: Визуализация и анализ эквити
- **Система аудита**: Полное логирование всех действий для соответствия регуляторным требованиям
- **Мониторинг здоровья системы**: Prometheus метрики, health checks

### Архитектура
- **Асинхронная обработка**: Полностью async/await на базе FastAPI
- **Микросервисная структура**: Независимые модули для каждой функциональности
- **Event-driven**: Шина событий для межсервисного взаимодействия
- **Распределенная система**: Поддержка горизонтального масштабирования

## 📋 Требования

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (опционально)

## 🔧 Быстрый старт

### Локальная установка

```bash
# Клонирование репозитория
git clone https://github.com/legion14041981-ui/overlord-trading-system-v8.git
cd overlord-trading-system-v8

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-dev.txt  # для разработки

# Настройка окружения
cp .env.example .env
# Отредактируйте .env, добавьте API ключи

# Запуск миграций базы данных
alembic upgrade head

# Запуск сервера
uvicorn src.main:app --reload --port 8000
```

### Запуск через Docker

```bash
# Сборка и запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f api
```

### Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# API документация
open http://localhost:8000/docs
```

## 📚 Документация

- [API Documentation](docs/API.md) — Полное описание REST и WebSocket API
- [Architecture Guide](docs/ARCHITECTURE.md) — Архитектура и дизайн системы
- [Deployment Guide](docs/DEPLOYMENT.md) — Руководство по развертыванию
- [Development Guide](docs/DEVELOPMENT.md) — Руководство для разработчиков
- [Service Integration](docs/SERVICE_INTEGRATION.md) — Интеграция сервисов

## 🏗️ Архитектура

```
overlord-trading-system-v8/
├── src/
│   ├── core/              # Базовые компоненты
│   │   ├── config.py      # Конфигурация
│   │   ├── structured_logger.py  # Логирование
│   │   └── exceptions.py  # Исключения
│   ├── api/               # API слой
│   │   ├── routers/       # REST endpoints
│   │   └── middleware/    # Middleware компоненты
│   ├── services/          # Бизнес-логика
│   │   ├── notification_service.py
│   │   ├── audit_service.py
│   │   └── cache_service.py
│   ├── models/            # Модели данных
│   ├── repositories/      # Слой доступа к данным
│   └── main.py            # Точка входа
├── tests/                 # Тесты
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── alembic/               # Миграции БД
├── docker/                # Docker конфигурация
└── docs/                  # Документация
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# С покрытием кода
pytest --cov=src --cov-report=html

# Только unit тесты
pytest tests/unit/

# Только integration тесты
pytest tests/integration/

# Конкретный тест
pytest tests/unit/test_risk_manager.py -v
```

## 🔒 Безопасность

- JWT аутентификация для всех API endpoints
- Rate limiting для защиты от DDoS
- Шифрование чувствительных данных
- Регулярные security аудиты через GitHub Actions
- Санитизация логов (автоматическое скрытие API ключей)

## 📊 Мониторинг

### Prometheus метрики

Система экспортирует метрики в формате Prometheus:

```
http://localhost:8000/metrics
```

Основные метрики:
- `http_requests_total` — Общее количество запросов
- `http_request_duration_seconds` — Длительность запросов
- `trading_orders_total` — Количество ордеров
- `trading_pnl_total` — Общий P&L
- `system_health_status` — Статус здоровья системы

### Логирование

Структурированные JSON логи с correlation ID для трейсинга:

```json
{
  "timestamp": "2026-01-08T06:50:00Z",
  "level": "INFO",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "service": "trading",
  "message": "Order executed",
  "order_id": "12345",
  "symbol": "BTCUSDT"
}
```

## 🚀 Производственное развертывание

### Kubernetes

```bash
# Применить манифесты
kubectl apply -f k8s/

# Проверить статус
kubectl get pods -n overlord-trading

# Просмотр логов
kubectl logs -f deployment/overlord-api -n overlord-trading
```

### Docker Swarm

```bash
# Инициализация swarm
docker swarm init

# Развертывание стека
docker stack deploy -c docker-compose.prod.yml overlord

# Масштабирование
docker service scale overlord_api=3
```

## 🔄 CI/CD

Автоматизированный pipeline через GitHub Actions:

1. **CI (Continuous Integration)**:
   - Линтинг (black, flake8, mypy)
   - Unit & Integration тесты
   - Security сканирование (Bandit)
   - Coverage проверка (>80%)

2. **CD (Continuous Deployment)**:
   - Сборка Docker образов
   - Публикация в registry
   - Развертывание в staging
   - Smoke тесты
   - Развертывание в production (manual approval)

## 📈 Performance

- **Латентность**: < 50ms для order placement
- **Throughput**: > 1000 req/sec на single instance
- **Uptime**: 99.95% SLA
- **Масштабируемость**: Горизонтальное масштабирование до 10+ nodes

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

См. [CONTRIBUTING.md](CONTRIBUTING.md) для деталей.

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE) файл для деталей.

## 👥 Авторы

- **LEGION Team** - [legion14041981-ui](https://github.com/legion14041981-ui)

## 🙏 Благодарности

- FastAPI framework
- CCXT library
- LEGION v8.1 Architecture
- Все контрибьюторы проекта

## 📞 Поддержка

- Issues: [GitHub Issues](https://github.com/legion14041981-ui/overlord-trading-system-v8/issues)
- Email: legion14041981@gmail.com
- Documentation: [docs/](docs/)

---

**LEGION v8.1 Autonomous Mission Weaver** — Built with ❤️ for algorithmic traders
