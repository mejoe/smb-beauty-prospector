#!/bin/sh
set -e

echo "=== BeautyProspector Starting ==="
echo "PORT: ${PORT:-8000}"
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."

echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

echo "Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
