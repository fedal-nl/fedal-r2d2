.DEFAULT_GOAL := help

.PHONY: help up down deploy prod-down prod-logs test lint migrate upgrade downgrade current history stamp clean

PROD_COMPOSE := docker compose -f docker-compose.prod.yaml

# ---------------------------------
# Application start command
# ---------------------------------
# Development: run container with live-reload
up:
	docker compose up

down:
	docker compose down

# Production: stop the current stack, pull the published image, and restart it.
deploy:
	$(PROD_COMPOSE) down
	$(PROD_COMPOSE) pull
	$(PROD_COMPOSE) up -d

prod-down:
	$(PROD_COMPOSE) down

prod-logs:
	$(PROD_COMPOSE) logs -f api

# ---------------------------------
# Alembic migration commands
# ---------------------------------
# To run migrations. first generate a new migration script:
migrate:
	@test -n "$(MESSAGE)" || (echo "Usage: make migrate MESSAGE='migration message'" && exit 1)
	uv run alembic revision --autogenerate -m "$(MESSAGE)"
# Then apply the migration: (Optional with envfile): ENV_FILE=.env.prod uv run alembic upgrade head
upgrade:
	uv run alembic upgrade head
# To downgrade to a previous migration:
downgrade:
	@test -n "$(REVISION)" || (echo "Usage: make downgrade REVISION=<revision_id>" && exit 1)
	uv run alembic downgrade $(REVISION)
# To view current revision:
current:
	uv run alembic current
# To view the history of migrations:
history:
	uv run alembic history --verbose
# To stamp the database with a specific revision without running migrations:
stamp:
	@test -n "$(REVISION)" || (echo "Usage: make stamp REVISION=<revision_id>" && exit 1)
	uv run alembic stamp $(REVISION)

test:
	uv run pytest -q

lint:
	uv run ruff check src tests

# ---------------------------------
# Clean Python cache
# ---------------------------------
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# ---------------------------------
# Help
# ---------------------------------
help:
	@echo "Available make commands:"
	@echo "  make up          - Run the api application with Docker Compose"
	@echo "  make down        - Stop the Docker Compose services"
	@echo "  make deploy      - Down, pull, and start the production image"
	@echo "  make prod-down   - Stop the production Compose services"
	@echo "  make prod-logs   - Follow production API logs"
	@echo "  make test        - Run tests with pytest"
	@echo "  make lint        - Run Ruff checks"
	@echo "  make migrate     - Generate Alembic migration"
	@echo "  make upgrade     - Apply Alembic migrations"
	@echo "  make downgrade   - Downgrade with REVISION=<revision_id>"
	@echo "  make current     - Show the current Alembic revision"
	@echo "  make history     - Show Alembic migration history"
	@echo "  make stamp       - Stamp with REVISION=<revision_id>"
	@echo "  make clean       - Remove Python cache files"
	@echo "  make help        - Show this help message"
