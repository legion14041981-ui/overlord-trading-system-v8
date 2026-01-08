# Multi-Stage Dockerfile for OVERLORD v8
# CI-compatible version using requirements.txt

FROM python:3.11-slim as base

LABEL maintainer="OVERLORD Team"
LABEL version="8.1.0"

# Install system dependencies
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
# Stage 2: Builder
# =============================================================================
FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# =============================================================================
# Stage 3: Runtime
# =============================================================================
FROM base as runtime

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY ./src /app/src

# Set ownership to non-root user
RUN chown -R overlord:overlord /app

# Switch to non-root user
USER overlord

# Expose port
EXPOSE 8000

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
     "--log-level", "info"]
