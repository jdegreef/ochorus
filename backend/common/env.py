"""Small, defensive normalizers for environment-provided values."""

from __future__ import annotations

from urllib.parse import urlsplit


def origin_url(value: str) -> str:
    """Reduce a URL to its origin (``scheme://host[:port]``), dropping any
    path, query or fragment.

    A Supabase *project* URL is an origin (``https://<ref>.supabase.co``). The
    dashboard also shows the REST endpoint (``…/rest/v1``) and other paths, and
    pasting one of those into ``SUPABASE_URL`` silently breaks JWKS key
    discovery — the auth layer appends ``/auth/v1/.well-known/jwks.json`` to it,
    so ``…/rest/v1`` yields a 404 and every token is rejected. Normalizing to the
    origin makes the setting tolerant of that mistake.
    """
    value = (value or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    # No scheme (e.g. "host/rest/v1") — keep the host, drop any trailing path.
    return value.split("/", 1)[0]
