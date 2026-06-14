#!/bin/bash
set -e

echo "Waiting for postgres..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
done
echo "Postgres ready."

python manage.py migrate --noinput

exec "$@"
