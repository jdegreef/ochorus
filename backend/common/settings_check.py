"""Startup configuration validation, kept pure so it's unit-testable.

`config.settings` calls this in non-DEBUG deployments to refuse to start with
missing/unsafe critical config, surfacing the problem at boot instead of as a
confusing runtime error.
"""

from __future__ import annotations

_INSECURE_KEY_PREFIX = "django-insecure-"


def missing_required_config(
    *, secret_key: str, database_url: str, supabase_url: str
) -> list[str]:
    """Return the names of required settings that are absent or unsafe for a
    real deployment. An empty list means the configuration is good to start."""
    missing: list[str] = []
    if not secret_key or secret_key.startswith(_INSECURE_KEY_PREFIX):
        missing.append("DJANGO_SECRET_KEY (unset or still the insecure dev default)")
    if not database_url:
        missing.append("DATABASE_URL (a Postgres URL; SQLite is dev-only)")
    if not supabase_url:
        missing.append("SUPABASE_URL (needed to validate Supabase JWTs)")
    return missing
