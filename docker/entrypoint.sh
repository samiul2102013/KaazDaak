#!/bin/bash
set -e

echo "Waiting for postgres..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
done
echo "Postgres ready."

# Only the web (gunicorn) container runs migrations. Celery, beat, and flower
# share this entrypoint and start at the same time — concurrent migrate calls
# cause "relation already exists" errors on a fresh database.
if [ "$1" = "gunicorn" ]; then
    # Apply any pending initial migrations first via the migration executor
    # (bypasses InconsistentMigrationHistory when switching AUTH_USER_MODEL).
    # Then run the full migrate; if tables from a prior migration already exist
    # (same filename, different content), fall back to --fake-initial.
    python -c "
import django; django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
executor = MigrationExecutor(connection)
plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
for migration, backwards in plan:
    if backwards:
        continue
    print(f'Pre-applying {migration.app_label}: {migration.name}')
    executor.apply_migration(migration, fake=False)
" 2>/dev/null || true
    python manage.py migrate --noinput || python manage.py migrate --fake-initial --noinput
fi

exec "$@"
