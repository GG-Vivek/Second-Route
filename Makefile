# SecondRoute
#
# `make dev` starts the whole application on a developer machine. See
# scripts/dev.sh for what it does.

.DEFAULT_GOAL := help
.PHONY: help dev setup test lint format typecheck check clean

help: ## Show this help
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

dev: ## Start the API and the frontend
	@bash scripts/dev.sh

setup: ## Install the dependencies
	cd backend && uv sync --all-extras
	cd frontend && npm install
	cd frontend-public && npm install

test: ## Run the test suite
	cd backend && uv run pytest tests/ -q
	cd frontend && npm run test:run
	cd frontend-public && npm run test:run

lint: ## Check the lint and the formatting
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint
	cd frontend-public && npm run lint

typecheck: ## Check the types
	cd backend && uv run mypy .
	cd frontend && npx tsc --noEmit
	cd frontend-public && npx tsc --noEmit

check: lint typecheck test ## Everything the CI checks

clean: ## Remove the build output
	rm -rf frontend/dist frontend/coverage frontend-public/dist frontend-public/coverage backend/coverage.xml backend/.coverage
