#!/bin/sh
set -e

echo "Waiting for database to be ready..."
sleep 2

if [ "$SKIP_MIGRATIONS" != "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

echo "Starting application..."
exec "$@"
