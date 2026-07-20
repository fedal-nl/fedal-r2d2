.PHONY: run

# ---------------------------------
# Application start command
# ---------------------------------
# Variables
IMAGE_NAME=fedal-r2d2-api

.PHONY: up build build-tag

# Development: run container with live-reload
up:
	docker compose up

down:
	docker compose down

# Build image (latest tag)
build:
	docker compose build

# Build image with custom tag
build-tag:
ifndef TAG
	$(error TAG is not set. Usage: make build-tag TAG=v1.0.0)
endif
	docker compose build
	docker tag $(IMAGE_NAME):latest $(IMAGE_NAME):$(TAG)
# ---------------------------------
# Alembic migration commands
# ---------------------------------
# To run migrations. first generate a new migration script:
migrate:
	uv run alembic revision --autogenerate -m "<migration_message>"
# Then apply the migration: (Optional with envfile): ENV_FILE=.env.prod uv run alembic upgrade head
upgrade:
	uv run alembic upgrade head
# To downgrade to a previous migration:
downgrade:
	uv run alembic downgrade <revision_id>
# To view current revision:
current:
	uv run alembic current
# To view the history of migrations:
history:
	uv run alembic history --verbose
# To stamp the database with a specific revision without running migrations:
stamp:
	uv run alembic stamp <revision_id>

# ---------------------------------
# Clean Python cache
# ---------------------------------
clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__ *.pyc *.pyo

# ---------------------------------
# Help
# ---------------------------------
help:
	@echo "Available make commands:"
	@echo "  make up          - Run the api application with Docker Compose"
	@echo "  make down        - Stop the Docker Compose services"
	@echo "  make build       - Build the Docker image (latest tag)"
	@echo "  make build-tag   - Build the Docker image with a custom tag (usage: make build-tag TAG=v1.0.0)"
	@echo "  make test        - Run tests with pytest"
	@echo "  make migrate     - Generate Alembic migration"
	@echo "  make upgrade     - Apply Alembic migrations"
	@echo "  make clean       - Remove Python cache files"
	@echo "  make help        - Show this help message"