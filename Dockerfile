FROM python:3.13-slim

# Install system dependencies and packages like curl, vim, less postgresql-client, build-essential, ping
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    vim \
    less \
    postgresql-client \
    iputils-ping \
    netcat-openbsd \
    tree \
    bsdmainutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install uv
RUN pip install uv

# Set workdir
WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"
ENV UV_LINK_MODE=copy

# Copy project files
COPY pyproject.toml /app/
COPY . /app

# Install dependencies with uv
RUN uv sync --no-dev --frozen --link-mode=copy

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn via ASGI
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
