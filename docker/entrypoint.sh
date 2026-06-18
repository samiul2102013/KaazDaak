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
    python manage.py migrate --noinput
fi

exec "$@"
