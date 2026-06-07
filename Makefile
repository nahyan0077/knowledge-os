SHELL := /bin/sh
BACKEND_DIR := backend
PYTHON_VERSION ?= 3.13
UV ?= uv

.DEFAULT_GOAL := help

.PHONY: help setup install env migrate migration-sql run test lint format format-check typecheck check clean services-up services-down frontend-install frontend worker qdrant-ui temporal-ui

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; print "Knowledge OS commands:"} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: env install migrate ## Create local environment, install dependencies, and migrate database

install: ## Install backend dependencies with Python 3.13
	cd $(BACKEND_DIR) && $(UV) sync --python $(PYTHON_VERSION)

env: ## Create backend/.env from the example if it does not exist
	@test -f $(BACKEND_DIR)/.env || cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env

migrate: ## Apply all database migrations
	cd $(BACKEND_DIR) && $(UV) run alembic upgrade head

migration-sql: ## Validate migrations by generating PostgreSQL SQL
	cd $(BACKEND_DIR) && $(UV) run alembic upgrade head --sql

run: ## Run the FastAPI development server
	cd $(BACKEND_DIR) && $(UV) run uvicorn knowledge_os.main:app --reload

test: ## Run tests
	cd $(BACKEND_DIR) && $(UV) run pytest -q

lint: ## Run Ruff lint checks
	cd $(BACKEND_DIR) && $(UV) run ruff check .

format: ## Format backend Python files
	cd $(BACKEND_DIR) && $(UV) run ruff format .

format-check: ## Check formatting without modifying files
	cd $(BACKEND_DIR) && $(UV) run ruff format --check .

typecheck: ## Run strict mypy checks
	cd $(BACKEND_DIR) && $(UV) run mypy src

check: lint format-check typecheck test migration-sql ## Run all repository quality gates

clean: ## Remove generated Python caches, preserving dependencies and data
	find $(BACKEND_DIR) -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache \) -prune -exec rm -rf {} +

services-up: ## Start Qdrant and Temporal in Docker Compose
	docker compose up -d

services-down: ## Stop Qdrant and Temporal Docker containers
	docker compose down

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend: ## Run the Next.js frontend development server
	cd frontend && npm run dev

worker: ## Run the Temporal background workers
	cd $(BACKEND_DIR) && $(UV) run python -m knowledge_os.worker

qdrant-ui: ## Open Qdrant Web UI Dashboard
	$(UV) run python -m webbrowser http://localhost:6333/dashboard

temporal-ui: ## Open Temporal Web UI Dashboard
	$(UV) run python -m webbrowser http://localhost:8233



