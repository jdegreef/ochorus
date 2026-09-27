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
# One worker with four threads, not separate worker processes. Each worker
# process holds its own copy of Django (~170 MB baseline on the 512 MB plan), so
# with two of them the prerender crawl pushed memory to 90-100% for hours at a
# time, and the instance was OOM-killed (exit 137) on 2026-09-26, as on
# 2026-09-10 and 2026-08-14. Threads share one copy. Measured locally over a full
# web build: 1x4 used ~40% less memory than 2 workers (median 356 vs 599 MB, peak
# 668 vs 894 MB, macOS accounting) with the same build time. On 0.5 CPU two
# processes never ran Python in parallel anyway; threads still overlap the waits
# on Supabase round trips. `--preload` with 2 workers was measured too and saved
# nothing. Django gives each thread its own DB connection, so up to 4 persistent
# ones.
#
# --max-requests recycles the worker after ~500 requests. CPython retains freed
# memory pages, so occasional large allocations ratchet RSS toward the plan limit
# over a process's lifetime; recycling resets the ratchet with a clean handover
# instead of an OOM kill. With one worker, requests queue in the listen backlog
# while its replacement boots (they wait, they don't fail).
CMD ["sh", "-c", "uv run gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --timeout 120 --max-requests 500 --max-requests-jitter 100"]
