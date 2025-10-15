.PHONY: help venv install test test-cov lint format clean run docker-build docker-run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment
	python3 -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

install: ## Install dependencies (requires active venv)
	pip install --upgrade pip
	pip install -r requirements.txt

test: ## Run unit tests
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov=app --cov-report=term-missing --cov-report=html

lint: ## Run linting checks
	ruff check app/ tests/
	mypy app/

format: ## Format code with ruff
	ruff format app/ tests/

clean: ## Clean up cache and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

run: ## Run the application locally
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build: ## Build Docker image
	docker build -t codr:dev .

docker-run: ## Run Docker container
	docker run --rm -p 8000:8000 --env-file .env codr:dev
