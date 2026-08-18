# AGENTS.md

Django 5.2 LTS + DRF backend for **KaazDaak**, a Bangladeshi gig-work platform. Roles: `hirer` (employer) and `kaazbir` (worker). No README exists; this file is the primary doc.

## Commands

- Env: python-decouple reads `.env`. Copy `.env.example` → `.env`. When running on the host (not docker), set `POSTGRES_HOST=localhost` — the example value `db` is a docker service name.
- Tests: `pytest` — configured in `pyproject.toml` with `--ds=config.settings.development --reuse-db`. This means the suite runs against **Postgres + Redis**, which must be running (CI provides `postgres:16` + `redis:7` services). Fast DB-free runs: `pytest --ds=config.settings.testing` (sqlite + locmem cache; `config/settings/testing.py` exists but is NOT the default). Use `--create-db` after changing models/migrations because of `--reuse-db`.
- CI (gates on push/PR to main, develop, feature/*, auth):
  - `black --check .`
  - `isort --check-only .`
  - `flake8 . --max-line-length=88 --extend-ignore=E203`
  - `pytest --cov=apps --cov-report=xml --cov-fail-under=70` (70% coverage gate)
  - `bandit -r apps/ -ll` and `safety check -r requirements/production.txt`
- Dev stack: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up` (runserver, code mounted via `builder` target). Migrations are run by `docker/entrypoint.sh`, web container only.

## Architecture

- `config/` = project package; settings split across `base.py` / `development.py` / `testing.py` / `production.py` (default: development). Celery app is `config/celery.py`, loaded via `config/__init__.py`.
- `apps/` = local apps, must be registered as `apps.*` in `INSTALLED_APPS`: `core` (abstract `TimestampedModel`/`SoftDeleteModel`), `common` (response/pagination/exception helpers), `users` (auth).
- `AUTH_USER_MODEL = users.User`: custom UUID-pk, username-based user with optional email/phone; migration history here is sensitive (entrypoint comment warns about `InconsistentMigrationHistory`).
- API mounted under `config/urls.py`: `/api/health/`, `/api/v1/auth/` (users URLs). New apps' routes go in `config/urls.py`.
- DRF defaults: SimpleJWT auth, `IsAuthenticated` permission, pagination via `apps.common.pagination.StandardResultsPagination`, custom error handler, throttle scopes `otp_resend` (3/hour) and `login` (10/minute).

## Conventions & gotchas

- Every API response uses a uniform envelope. Success: `apps.common.responses.success_response(...)` → `{success, message, data}`. Errors: the custom exception handler → `{success: False, error, message, status_code}`. Use these helpers; don't hand-roll responses (a few views already hand-roll error dicts for throttling/verification edge cases).
- `apps/users/tests/factories.py` `UserFactory` is broken (passes the password as the `username` positional arg; `role="general"` is not a valid choice) and is unused. Write test fixtures with `User.objects.create_user(...)` directly, as the existing tests do.
- BD phone numbers: validated against `BD_PHONE_REGEX` and normalized to `+88` prefix via `apps/users/validators.py::normalize_bd_phone`. Always compare/look up by the normalized form.
- OTP codes are stored as SHA-256 hashes; plaintext only ever appears in the email body (tests extract it from `mail.outbox`).
- Lint style: black (line-length 88), isort with black profile, flake8 ignoring E203 — config in `pyproject.toml`.
- Commit messages follow conventional style from git history (`feat:`, `fix:`, `style:`...).
- Deploy: CD runs on CI success to `main` → builds `ghcr.io` images tagged by SHA → SCP `docker-compose.yml` + `nginx.conf` to an Azure VM → `docker compose pull/up`, then `migrate` and `collectstatic` in the web container.