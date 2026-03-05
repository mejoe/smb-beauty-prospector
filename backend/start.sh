#!/bin/sh
set -e

echo "=== BeautyProspector Starting ==="
echo "PORT: ${PORT:-8080}"
echo "DATABASE_URL set: yes"

echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

echo "Starting uvicorn on port ${PORT:-8080}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level info
