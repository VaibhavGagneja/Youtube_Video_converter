.PHONY: help build up down logs test lint clean deploy

SERVICES = auth gateway converter notification
DOCKER_USERNAME ?= vaibhavgagneja

# ─── Help ──────────────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Local Development ─────────────────────────────────────────
up: ## Start all services with docker-compose
	docker-compose up -d --build

down: ## Stop all services
	docker-compose down

logs: ## Tail logs from all services
	docker-compose logs -f

restart: ## Restart all services
	docker-compose down && docker-compose up -d --build

ps: ## Show running containers
	docker-compose ps

# ─── Build ─────────────────────────────────────────────────────
build: ## Build all Docker images
	@for svc in $(SERVICES); do \
		echo "Building $$svc..."; \
		docker build -t $(DOCKER_USERNAME)/mp3-$$svc:latest ./src/$$svc; \
	done

push: ## Push all Docker images to Docker Hub
	@for svc in $(SERVICES); do \
		echo "Pushing $$svc..."; \
		docker push $(DOCKER_USERNAME)/mp3-$$svc:latest; \
	done

# ─── Quality ───────────────────────────────────────────────────
lint: ## Run flake8 linter on all services
	@for svc in $(SERVICES); do \
		echo "Linting $$svc..."; \
		flake8 src/$$svc/ --max-line-length=120 --exclude=__pycache__,authenv,venv,.eggs; \
	done

test: ## Run pytest on all services
	@for svc in $(SERVICES); do \
		echo "Testing $$svc..."; \
		cd src/$$svc && python -m pytest tests/ -v --cov=. --cov-report=term-missing || true; \
		cd ../..; \
	done

# ─── Kubernetes  ───────────────────────────────────────────────
deploy-staging: ## Deploy to staging via Helm
	helm upgrade --install video-converter helm/video-converter \
		--namespace video-converter-staging \
		--create-namespace \
		--values helm/video-converter/values-staging.yaml

deploy-prod: ## Deploy to production via Helm
	helm upgrade --install video-converter helm/video-converter \
		--namespace video-converter-production \
		--create-namespace \
		--values helm/video-converter/values-production.yaml

helm-lint: ## Lint the Helm chart
	helm lint helm/video-converter

helm-template: ## Render Helm chart templates locally
	helm template video-converter helm/video-converter

# ─── Cleanup ───────────────────────────────────────────────────
clean: ## Remove containers, volumes, and build artifacts
	docker-compose down -v --rmi local
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
