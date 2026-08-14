# Production image for the Ochorus API. Portable across Render, Fly.io, etc.
FROM python:3.12-slim

# Fast, reproducible installs with uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (cached unless the lockfile changes).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application code and finish the install.
COPY . .
RUN uv sync --frozen --no-dev

# Collect static files at build time (no database needed).
ENV DJANGO_DEBUG=false
RUN DJANGO_SECRET_KEY=build-time-only uv run python manage.py collectstatic --noinput

EXPOSE 8000

# Migrations run once per deploy via Render's preDeployCommand (see render.yaml),
# not on container start. The host provides $PORT.
#
# --max-requests recycles each worker after ~500 requests (jitter so the three
# workers never restart together). CPython retains freed memory pages, so
# occasional large allocations ratchet worker RSS toward the 512MB plan limit
# over a process's lifetime (OOM restart, 2026-08-14); recycling resets the
# ratchet with a clean handover instead of an OOM kill.
CMD ["sh", "-c", "uv run gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120 --max-requests 500 --max-requests-jitter 100"]
