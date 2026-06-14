# Stage 1: Builder
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/ /app/requirements/

RUN pip install --no-cache-dir --prefix=/install -r requirements/production.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder — use separate COPY for bin and lib
# so they merge with existing /usr/local contents instead of replacing them.
COPY --from=builder /install/lib /usr/local/lib
COPY --from=builder /install/bin /usr/local/bin

RUN useradd -u 1000 -m appuser

WORKDIR /app

COPY --chown=appuser:appuser . /app

# Ensure entrypoint has execute permission
RUN chmod +x docker/entrypoint.sh

# Collect static files using production settings (no debug_toolbar dependency)
ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV SECRET_KEY=dummy-secret-key-for-collectstatic
ENV POSTGRES_DB=dummy_db
ENV POSTGRES_USER=dummy_user
ENV POSTGRES_PASSWORD=dummy_pass
ENV POSTGRES_HOST=dummy_host
ENV POSTGRES_PORT=5432
ENV REDIS_URL=redis://dummy:6379/0

RUN python manage.py collectstatic --noinput

# Reset DJANGO_SETTINGS_MODULE so it's controlled by .env at runtime
ENV DJANGO_SETTINGS_MODULE=""
# Clear dummy secrets from the image layer
ENV SECRET_KEY=""
ENV POSTGRES_DB=""
ENV POSTGRES_USER=""
ENV POSTGRES_PASSWORD=""
ENV POSTGRES_HOST=""
ENV POSTGRES_PORT=""

USER appuser

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--log-level", "info"]
