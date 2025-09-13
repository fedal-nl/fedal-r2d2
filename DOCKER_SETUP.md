# FastAPI Docker Setup with uv and Python 3.13

This repository provides a complete Docker setup for a FastAPI application using Python 3.13 and uv package manager.

## Files Overview

### Application Files
- `app/main.py` - Main FastAPI application with health check endpoint
- `app/__init__.py` - Python package initialization file

### Docker Configuration
- `Dockerfile` - Main Docker configuration with uv and pip fallback for reliability
- `Dockerfile.uv` - Production-ready Dockerfile using pure uv (requires `uv.lock`)
- `docker-compose.yaml` - Docker Compose configuration with health checks
- `.dockerignore` - Optimizes Docker build context

### Project Configuration
- `pyproject.toml` - Python project configuration compatible with uv
- `requirements.txt` - Fallback requirements file for pip

## Usage

### Using Docker Compose (Recommended)
```bash
# Build and start the application
docker compose up --build

# Run in background
docker compose up -d --build

# Stop the application
docker compose down
```

### Using Docker directly
```bash
# Build the image
docker build -t fedal-r2d2 .

# Run the container
docker run -p 8000:8000 fedal-r2d2
```

### Using the production uv Dockerfile
```bash
# First create a uv.lock file (in an environment with network access)
uv lock

# Build with the production Dockerfile
docker build -f Dockerfile.uv -t fedal-r2d2-uv .
```

## Endpoints

- **Root**: `GET /` - Welcome message
- **Health Check**: `GET /health` - Application health status
- **API Documentation**: `GET /docs` - Interactive API documentation
- **OpenAPI Schema**: `GET /openapi.json` - OpenAPI specification

## Features

- **Python 3.13**: Latest Python version for optimal performance
- **uv Package Manager**: Fast, modern Python package management
- **FastAPI**: High-performance async web framework
- **Health Checks**: Built-in health monitoring
- **Development Volume**: Live reload during development
- **Multi-stage Builds**: Optimized for production use

## Development

The docker-compose setup includes volume mounting for the `app/` directory, enabling live reload during development. Changes to Python files will be reflected immediately in the running container.

## Production Deployment

For production, use `Dockerfile.uv` after generating a `uv.lock` file to ensure reproducible builds with exact dependency versions.