# Development shortcuts. Everything runs inside Docker.
COMPOSE := docker compose
UV_IMAGE := ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim
# Frontend tooling in the web-dev image, on the current code (bind mount) and
# with the node_modules of the image (anonymous volume), without starting the API.
WEB_RUN := $(COMPOSE) --profile dev run --rm --no-deps --build -v "$(CURDIR)/frontend:/app" -v /app/node_modules web-dev

.PHONY: help env lock lock-web up up-backend dev down logs shell migrate test test-unit lint format test-web lint-web format-web clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

env: ## Create .env from .env.example to customize the configuration (optional)
	@test -f .env && echo ".env ya existe" || (cp .env.example .env && echo "creado .env a partir de .env.example")

lock: ## Regenerate backend/uv.lock
	docker run --rm -v "$(CURDIR)/backend:/app" -w /app $(UV_IMAGE) uv lock

lock-web: ## Regenerate frontend/package-lock.json
	docker run --rm -v "$(CURDIR)/frontend:/app" -v /app/node_modules -w /app node:22-alpine npm install --package-lock-only --no-audit --no-fund

up: ## Build and start the whole stack (frontend on http://localhost:3000)
	$(COMPOSE) up --build

up-backend: ## Start only the backend services (api, worker, infra, tracing)
	$(COMPOSE) up --build postgres redis migrate api worker otel-collector jaeger

dev: ## Start everything with hot reload (frontend on http://localhost:5173)
	$(COMPOSE) up --build --watch postgres redis migrate api worker otel-collector jaeger web-dev

down: ## Stop the stack
	$(COMPOSE) down

logs: ## Follow api and worker logs
	$(COMPOSE) logs -f api worker

shell: ## Open a shell in a throwaway api container
	$(COMPOSE) run --rm api bash

migrate: ## Apply database migrations
	$(COMPOSE) run --rm --build migrate

test: ## Run every backend test
	$(COMPOSE) --profile test run --rm --build tests pytest -v

test-unit: ## Run only unit tests
	$(COMPOSE) --profile test run --rm --build tests pytest tests/unit -v

lint: ## Check lint and formatting
	$(COMPOSE) --profile test run --rm --build tests sh -c "ruff check . && ruff format --check ."

format: ## Apply formatting and safe lint fixes
	$(COMPOSE) --profile test run --rm --build tests sh -c "ruff format . && ruff check --fix ."

test-web: ## Run the frontend tests (Vitest)
	$(WEB_RUN) npm run test

lint-web: ## Check frontend types, lint and formatting
	$(WEB_RUN) sh -c "npm run typecheck && npm run lint && npm run format:check"

format-web: ## Format the frontend and apply safe lint fixes
	$(WEB_RUN) sh -c "npm run format && npx eslint . --fix"

clean: ## Stop the stack and delete its volumes (database, uploads, model cache)
	$(COMPOSE) down -v
