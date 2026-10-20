#!/bin/sh
set -e

echo "=== Unified Job Search Backend Starting ==="

# Run database migrations if alembic configuration is present
if [ -f "/app/alembic.ini" ] && [ -n "$DATABASE_URL" ]; then
    echo "Executing Alembic database migrations..."
    alembic upgrade head || echo "Warning: Alembic upgrade step skipped or database initializing..."
fi

echo "Launching application server: $@"
exec "$@"
