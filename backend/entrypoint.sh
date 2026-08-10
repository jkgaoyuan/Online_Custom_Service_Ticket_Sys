#!/bin/sh
set -e

echo "Waiting for database to be ready..."
# 简单的等待逻辑，生产环境可配合 depends_on condition
sleep 2

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
