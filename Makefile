# Makefile - Overlord v8.1
# Unified automation for development and deployment

.PHONY: help install test lint security build deploy clean

# Variables
PYTHON := python3
PIP := pip3
PYTEST := pytest
DOCKER := docker
KUBECTL := kubectl
HELM := helm
TERRAFORM := terraform

APP_NAME := overlord
VERSION := 8.1.0
REGISTRY := ghcr.io/legion14041981-ui
IMAGE := $(REGISTRY)/$(APP_NAME):$(VERSION)

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help: ## Show help
	@echo "$(GREEN)Overlord v8.1 - Available Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# === Development ===

install: ## Install dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

venv: ## Create virtual environment
	$(PYTHON) -m venv venv
	@echo "$(GREEN)✅ Virtual environment created. Activate: source venv/bin/activate$(NC)"

# === Testing ===

test: ## Run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	$(PYTEST) tests/ -v --cov=src --cov-report=term --cov-report=html

test-unit: ## Unit tests only
	$(PYTEST) tests/unit/ -v

test-integration: ## Integration tests only
	$(PYTEST) tests/integration/ -v

# === Code Quality ===

lint: ## Run linters
	@echo "$(GREEN)Running linters...$(NC)"
	flake8 src/ tests/
	mypy src/ --ignore-missing-imports
	pylint src/ --disable=C0111,W0212 --exit-zero

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	black src/ tests/
	isort src/ tests/ --profile=black
	@echo "$(GREEN)✅ Code formatted$(NC)"

# === Security ===

security: ## Security scan
	@echo "$(GREEN)Security scanning...$(NC)"
	bandit -r src/ -f json -o bandit-report.json || true
	safety check --json > safety-report.json || true
	@echo "$(GREEN)✅ Security scan complete$(NC)"

# === Docker ===

docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	$(DOCKER) build -t $(IMAGE) .
	$(DOCKER) tag $(IMAGE) $(REGISTRY)/$(APP_NAME):latest
	@echo "$(GREEN)✅ Image built: $(IMAGE)$(NC)"

docker-push: docker-build ## Build and push image
	@echo "$(GREEN)Pushing image to registry...$(NC)"
	$(DOCKER) push $(IMAGE)
	$(DOCKER) push $(REGISTRY)/$(APP_NAME):latest
	@echo "$(GREEN)✅ Image published$(NC)"

docker-run: ## Run container locally
	$(DOCKER) run -d --name $(APP_NAME) -p 8000:8000 --env-file .env $(IMAGE)
	@echo "$(GREEN)✅ Container running on http://localhost:8000$(NC)"

# === Database ===

db-migrate: ## Apply database migrations
	alembic upgrade head

db-rollback: ## Rollback database migration
	alembic downgrade -1

# === Kubernetes ===

k8s-apply: ## Apply K8s manifests
	$(KUBECTL) apply -f k8s/namespace.yaml
	$(KUBECTL) apply -f k8s/deployment.yaml
	$(KUBECTL) apply -f k8s/service.yaml

k8s-status: ## Check deployment status
	$(KUBECTL) get pods,svc,ingress -n overlord-production

k8s-logs: ## Show pod logs
	$(KUBECTL) logs -f deployment/$(APP_NAME) -n overlord-production

# === Helm ===

helm-install: ## Install via Helm
	$(HELM) install overlord helm/overlord/ --namespace overlord-production --create-namespace --values helm/overlord/values-production.yaml

helm-upgrade: ## Upgrade via Helm
	$(HELM) upgrade overlord helm/overlord/ --namespace overlord-production --values helm/overlord/values-production.yaml

# === Terraform ===

tf-init: ## Initialize Terraform
	cd terraform && $(TERRAFORM) init

tf-plan: ## Terraform plan
	cd terraform && $(TERRAFORM) plan -out=tfplan

tf-apply: ## Apply Terraform changes
	cd terraform && $(TERRAFORM) apply tfplan

# === Deployment ===

deploy-staging: ## Deploy to staging
	@echo "$(GREEN)Deploying to staging...$(NC)"
	./scripts/deploy.sh $(VERSION) staging
	@echo "$(GREEN)✅ Staging deployment complete$(NC)"

deploy-production: ## Deploy to production
	@echo "$(YELLOW)⚠️  Deploying to PRODUCTION$(NC)"
	@read -p "Continue? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		./scripts/deploy.sh $(VERSION) production; \
		echo "$(GREEN)✅ Production deployment complete$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# === Utilities ===

clean: ## Clean temporary files
	@echo "$(GREEN)Cleaning...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

version: ## Show version
	@echo "Overlord v$(VERSION)"

check-env: ## Check environment
	@echo "$(GREEN)Checking environment...$(NC)"
	@python3 -c "import sys; print(f'Python: {sys.version}')"
	@docker --version
	@kubectl version --client
	@helm version
	@echo "$(GREEN)✅ All tools installed$(NC)"

.DEFAULT_GOAL := help