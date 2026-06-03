install:
	pip install uv
	uv sync

set-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make set-env ENV=development|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "test" ]; then \
		echo "ENV is not valid. Must be one of: development, staging, production, test"; \
		exit 1; \
	fi
	@echo "Setting environment to $(ENV)"
	@bash -c "source scripts/set_env.sh $(ENV)"

prod:
	@echo "Starting server in production environment"
	@bash -c "source scripts/set_env.sh production && ./.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --loop uvloop"

staging:
	@echo "Starting server in staging environment"
	@bash -c "source scripts/set_env.sh staging && ./.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --loop uvloop"

dev:
	@echo "Starting server in development environment"
	@bash -c "source scripts/set_env.sh development && uv run uvicorn src.main:app --reload --port 8000 --loop uvloop"

# Evaluation commands
eval:
	@echo "Running evaluation with interactive mode"
	@bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --interactive"

eval-quick:
	@echo "Running evaluation with default settings"
	@bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --quick"

eval-no-report:
	@echo "Running evaluation without generating report"
	@bash -c "source scripts/set_env.sh ${ENV:-development} && python -m evals.main --no-report"

lint:
	ruff check .

format:
	ruff format .

clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf .pytest_cache

# Local dev: db + app only (no monitoring stack)
# For full stack deployment, use deploy/deploy.sh
docker-run:
	@ENV_FILE=.env.development; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	APP_ENV=development docker compose --env-file $$ENV_FILE up -d --build db app

docker-stop:
	APP_ENV=development docker compose down

docker-logs:
	APP_ENV=development docker compose logs -f app db

# Help
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Development:"
	@echo "  install                  Install dependencies"
	@echo "  dev                      Start dev server with hot reload (port 8000)"
	@echo "  staging                  Start server in staging environment"
	@echo "  prod                     Start server in production environment"
	@echo "  lint                     Run ruff linter"
	@echo "  format                   Run ruff formatter"
	@echo "  clean                    Remove .venv and caches"
	@echo ""
	@echo "Evaluation:"
	@echo "  eval [ENV=development]   Run evaluation (interactive)"
	@echo "  eval-quick               Run evaluation with defaults"
	@echo "  eval-no-report           Run evaluation without report"
	@echo ""
	@echo "Local Docker (db + app only):"
	@echo "  docker-run               Start db + app containers"
	@echo "  docker-stop              Stop containers"
	@echo "  docker-logs              Follow app and db logs"
	@echo ""
	@echo "Full stack deployment: see deploy/README.md"
