#!/bin/sh
set -e

echo "Waiting for database to be ready..."
# 简单的等待逻辑，生产环境可配合 depends_on condition
sleep 2

if [ "$SKIP_ALEMBIC" != "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

echo "Starting application..."
exec "$@"
