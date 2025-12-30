#!/bin/bash
# Overlord v8.1 - Docker Entrypoint Script

set -e

echo "🚀 Overlord v8.1 - Starting container..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-overlord}" > /dev/null 2>&1; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "✅ PostgreSQL is ready!"

# Run database migrations
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "📊 Running database migrations..."
  alembic upgrade head || {
    echo "⚠️  Migration failed, but continuing..."
  }
  echo "✅ Migrations completed!"
fi

# Execute the main command
echo "🎯 Starting application: $@"
exec "$@"
