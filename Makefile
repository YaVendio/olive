.PHONY: help install dev test coverage lint format type-check clean run-example run-client run-server all push

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      Install dependencies"
	@echo "  make dev          Install with dev dependencies"
	@echo "  make test         Run tests"
	@echo "  make coverage     Run tests with coverage report"
	@echo "  make lint         Run linter (ruff)"
	@echo "  make format       Format code with ruff"
	@echo "  make type-check   Run type checker (basedpyright)"
	@echo "  make clean        Clean cache files"
	@echo "  make run-example  Run the example server"
	@echo "  make run-client   Run the example client"
	@echo "  make all          Run format, lint, type-check, and test"
	@echo "  make push         Run pre-push checks and push to git"

# Install dependencies
install:
	uv sync

# Install with dev dependencies
dev:
	uv sync --all-extras

# Run tests
test:
	uv run python -m pytest tests/ -v

# Run tests with coverage
coverage:
	uv run python -m pytest tests/ --cov=olive --cov=olive_client --cov-report=term-missing --cov-report=html --cov-fail-under=100

# Run linter
lint:
	uv run ruff check olive/ olive_client/ tests/

# Format code
format:
	uv run ruff format olive/ olive_client/ tests/

# Run type checker
type-check:
	uv run basedpyright olive/ olive_client/

# Clean cache files
clean:
	uv clean --all

# Run example server
run-example:
	uv run python example.py

# Run example client
run-client:
	uv run python example.py client

# Run example server with uvicorn
run-server:
	uv run uvicorn example:app --reload

# Run all checks
all: format lint type-check test

# Run pre-push checks and push to git
push:
	@echo "Running pre-push checks..."
	@uv run pre-commit run --hook-stage pre-push --all-files
	@echo "All checks passed! Pushing to remote..."
	@git push
