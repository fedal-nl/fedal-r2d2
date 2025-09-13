# fedal-r2d2
A FastAPI that contains services like Sending an email.

## Docker Setup

This project includes Docker configuration for running the FastAPI application with Python 3.13 and uv.

### Quick Start

1. Build and run with Docker Compose:
```bash
docker compose up --build
```

2. Access the application:
- API: http://localhost:8000
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### Docker Files

- `Dockerfile` - Main Docker configuration with uv and pip fallback
- `Dockerfile.uv` - Production-ready Dockerfile using pure uv (requires uv.lock)
- `docker-compose.yaml` - Docker Compose configuration
- `pyproject.toml` - Python project configuration for uv
- `requirements.txt` - Fallback requirements file

### Development

The application code is mounted as a volume for development, so changes to `app/` will be reflected in the running container.
