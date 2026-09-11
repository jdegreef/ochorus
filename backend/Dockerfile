# Production image for the Ochorus API. Portable across Render, Fly.io, etc.
FROM python:3.12-slim

# Fast, reproducible installs with uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Run as a non-root user. Neither gunicorn nor the preDeploy `manage.py release`
# needs root, and dropping it narrows what any Django/dependency RCE can reach.
#
# Three things make the unprivileged user actually work here:
#   * HOME is set explicitly — Docker does NOT adjust HOME on a USER switch, and
#     `uv run` (used by CMD and by Render's preDeployCommand) wants a writable
#     cache dir under it;
#   * /app is owned by the user, so `uv sync` can create .venv and collectstatic
#     can write staticfiles/;
#   * COPY uses --chown so the copied tree is owned by the user rather than root.
ENV HOME=/home/app
RUN useradd --create-home --home-dir /home/app --uid 10001 app \
    && mkdir -p /app \
    && chown app:app /app
WORKDIR /app
USER app

# Install dependencies first (cached unless the lockfile changes).
COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application code and finish the install.
COPY --chown=app:app . .
RUN uv sync --frozen --no-dev

# Collect static files at build time (no database needed).
ENV DJANGO_DEBUG=false
RUN DJANGO_SECRET_KEY=build-time-only uv run python manage.py collectstatic --noinput

# Bake the reader-content digest so /api/health/ can serve it as a file read.
# Computing it walks ~90 MB of fixtures and seed data — 8s cold, and the first
# request a fresh container serves IS Render's liveness probe. Done here, from
# the same immutable content the image ships, it cannot be stale.
RUN DJANGO_SECRET_KEY=build-time-only uv run python manage.py content_version --write

EXPOSE 8000

# Migrations run once per deploy via Render's preDeployCommand (see render.yaml),
# not on container start. The host provides $PORT.
#
# 2 workers, not 3. Each worker's baseline RSS is ~170 MB, so a third worker put
# steady-state memory around 60-80% of the 512 MB plan with almost no headroom —
# and every deploy's zero-downtime overlap (two instances briefly live) plus the
# per-request body serialization then tipped an instance over into an OOM restart
# (2026-09-10; the 2026-08-14 OOM is the same ratchet). Two workers drop the
# baseline by one worker's RSS and still suit the 0.5-CPU plan (3 was already
# CPU-oversubscribed). If a bigger plan is adopted later, raise this with it.
#
# --max-requests recycles each worker after ~500 requests (jitter so the workers
# never restart together). CPython retains freed memory pages, so occasional
# large allocations ratchet worker RSS toward the plan limit over a process's
# lifetime; recycling resets the ratchet with a clean handover instead of an OOM
# kill. It mitigates the ratchet but does not eliminate it — the worker count is
# the primary control.
CMD ["sh", "-c", "uv run gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --max-requests 500 --max-requests-jitter 100"]
