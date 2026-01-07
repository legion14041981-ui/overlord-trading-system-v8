# [DEP-001] Makefile for OVERLORD v8
# Simplify Docker operations and development workflow

.PHONY: help build build-prod up down logs shell test clean

# Variables
IMAGE_NAME := overlord-api
IMAGE_TAG := latest
ECR_REGISTRY := $(shell aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
CONTAINER_NAME := overlord-api

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "OVERLORD v8 - Docker Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development
build: ## Build development Docker image
	@echo "🔨 Building development image..."
	docker-compose build
	@echo "✅ Development image built successfully"

build-prod: ## Build production Docker image
	@echo "🔨 Building production image..."
	docker build \
		--target runtime \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		--tag $(IMAGE_NAME):$(shell git rev-parse --short HEAD) \
		--cache-from $(IMAGE_NAME):latest \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		.
	@echo "✅ Production image built successfully"
	@echo "📦 Image size:"
	@docker images $(IMAGE_NAME):$(IMAGE_TAG) --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

up: ## Start all services
	@echo "🚀 Starting OVERLORD stack..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 10
	@docker-compose ps
	@echo ""
	@echo "✅ Services started!"
	@echo "📊 API: http://localhost:8000"
	@echo "📊 Docs: http://localhost:8000/docs"
	@echo "📊 Grafana: http://localhost:3000 (admin/admin)"
	@echo "📊 Prometheus: http://localhost:9091"

down: ## Stop all services
	@echo "🛑 Stopping OVERLORD stack..."
	docker-compose down
	@echo "✅ Services stopped"

restart: down up ## Restart all services

logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View API logs only
	docker-compose logs -f api

shell: ## Open shell in API container
	@echo "🐚 Opening shell in API container..."
	docker-compose exec api /bin/bash

shell-db: ## Open PostgreSQL shell
	@echo "🐚 Opening PostgreSQL shell..."
	docker-compose exec postgres psql -U overlord -d overlord

# Testing
test: ## Run all tests
	@echo "🧪 Running tests..."
	docker-compose exec api pytest tests/ -v

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	docker-compose exec api pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "🧪 Running integration tests..."
	docker-compose exec api pytest tests/integration/ -v

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	docker-compose exec api pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "📊 Coverage report: htmlcov/index.html"

# Database
migrate: ## Run database migrations
	@echo "🔄 Running database migrations..."
	docker-compose exec api alembic upgrade head
	@echo "✅ Migrations completed"

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	@echo "📝 Creating new migration: $(MSG)"
	docker-compose exec api alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Rollback last migration
	@echo "⏪ Rolling back last migration..."
	docker-compose exec api alembic downgrade -1

# Linting & Formatting
lint: ## Run linters
	@echo "🔍 Running linters..."
	docker-compose exec api black --check src/
	docker-compose exec api ruff check src/
	docker-compose exec api mypy src/

format: ## Format code
	@echo "🎨 Formatting code..."
	docker-compose exec api black src/
	docker-compose exec api ruff check --fix src/

# Security
scan: ## Scan image for vulnerabilities
	@echo "🔒 Scanning image for vulnerabilities..."
	docker run --rm \
		-v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy image $(IMAGE_NAME):$(IMAGE_TAG)

scan-high: ## Scan for HIGH and CRITICAL vulnerabilities only
	@echo "🔒 Scanning for critical vulnerabilities..."
	docker run --rm \
		-v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy image \
		--severity HIGH,CRITICAL \
		--exit-code 1 \
		$(IMAGE_NAME):$(IMAGE_TAG)

# AWS ECR
ecr-login: ## Login to AWS ECR
	@echo "🔐 Logging into AWS ECR..."
	aws ecr get-login-password --region us-east-1 | \
		docker login --username AWS --password-stdin $(ECR_REGISTRY)
	@echo "✅ Logged into ECR"

ecr-push: ecr-login build-prod ## Build and push image to ECR
	@echo "📤 Pushing image to ECR..."
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(ECR_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(ECR_REGISTRY)/$(IMAGE_NAME):$(shell git rev-parse --short HEAD)
	docker push $(ECR_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(ECR_REGISTRY)/$(IMAGE_NAME):$(shell git rev-parse --short HEAD)
	@echo "✅ Image pushed to ECR"

# Cleanup
clean: ## Remove stopped containers and dangling images
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup completed"

clean-all: ## Remove all containers, images, and volumes
	@echo "⚠️  WARNING: This will remove ALL Docker data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker system prune -a -f --volumes; \
		echo "✅ All Docker data removed"; \
	fi

# Health checks
health: ## Check health of all services
	@echo "🏥 Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "API Health:"
	@curl -s http://localhost:8000/health | jq .
	@echo ""
	@echo "Metrics:"
	@curl -s http://localhost:9090/metrics | head -n 20

# Monitoring
metrics: ## View Prometheus metrics
	@echo "📊 Opening Prometheus metrics..."
	@open http://localhost:9091 || xdg-open http://localhost:9091

dashboard: ## Open Grafana dashboard
	@echo "📊 Opening Grafana dashboard..."
	@open http://localhost:3000 || xdg-open http://localhost:3000

tracing: ## Open Jaeger tracing UI
	@echo "📊 Opening Jaeger tracing UI..."
	@open http://localhost:16686 || xdg-open http://localhost:16686

# Development helpers
shell-root: ## Open root shell in API container
	@echo "🐚 Opening root shell..."
	docker-compose exec -u root api /bin/bash

install-deps: ## Install/update Python dependencies
	@echo "📦 Installing dependencies..."
	docker-compose exec api poetry install
	@echo "✅ Dependencies installed"

generate-requirements: ## Generate requirements.txt from Poetry
	@echo "📝 Generating requirements.txt..."
	docker-compose exec api poetry export -f requirements.txt --output requirements.txt --without-hashes
	@echo "✅ requirements.txt generated"
