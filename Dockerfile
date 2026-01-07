# [DEP-001] Multi-Stage Dockerfile for OVERLORD v8
# Optimized for production deployment with minimal image size

# =============================================================================
# Stage 1: Base Image
# =============================================================================
FROM python:3.11-slim as base

LABEL maintainer="OVERLORD Team <overlord@legion.ai>"
LABEL description="OVERLORD v8 Autonomous Trading System"
LABEL version="8.1.0"

# Install system dependencies (minimal set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r overlord && useradd -r -g overlord overlord

# Set working directory
WORKDIR /app

# =============================================================================
# Stage 2: Builder (Dependencies Installation)
# =============================================================================
FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Export dependencies and install to /install prefix
RUN poetry export -f requirements.txt --without-hashes --only main | \
    pip install --no-cache-dir --prefix=/install -r /dev/stdin

# Install additional performance packages
RUN pip install --no-cache-dir --prefix=/install \
    uvloop \
    httptools \
    ujson

# =============================================================================
# Stage 3: Runtime (Production)
# =============================================================================
FROM base as runtime

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY ./src /app/src
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

# Set ownership to non-root user
RUN chown -R overlord:overlord /app

# Switch to non-root user
USER overlord

# Expose ports
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# Start application
CMD ["uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--log-level", "info", \
     "--no-access-log"]

# =============================================================================
# Stage 4: Development (Optional)
# =============================================================================
FROM builder as development

# Install development dependencies
RUN poetry install --with dev

# Copy application code
COPY . /app

# Set ownership
RUN chown -R overlord:overlord /app

USER overlord

EXPOSE 8000 9090

# Start with hot-reload
CMD ["uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--log-level", "debug"]
