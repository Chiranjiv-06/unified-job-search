# ===================================================
# Multi-Stage Production Dockerfile for Backend Service
# Framework: FastAPI / Uvicorn (Python 3.11)
# ===================================================

# Stage 1: Build Dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime Execution Image
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime libraries and healthcheck utility
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled python packages from builder
COPY --from=builder /install /usr/local

# Create non-root system user and group for security
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/sh -m appuser

# Copy application code, database migrations, and config
COPY backend/app /app/app
COPY alembic.ini /app/alembic.ini
COPY database /app/database
COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh

# Configure uploads directory and ownership
RUN chmod +x /app/docker-entrypoint.sh && \
    mkdir -p /app/uploads && \
    chown -R appuser:appgroup /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
