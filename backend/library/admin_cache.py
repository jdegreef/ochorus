"""The admin's shared memo — one cache alias and the two read patterns on it.

The admin's slow reads are of two kinds, and each wants a different rule:

* **Derived from content** (the dashboard stats, the audit scan): correct until
  content changes. Keyed on ``ContentRevision``, so a publish, an import or an
  approval (all of which call ``invalidation.mark_content_changed``) misses on
  the very next request; the timeout bounds what the revision can't see — an
  edit from the SQL editor or a management command.
* **Read from GitHub** (the translation and content-edit queues): correct for a
  minute or two, and sometimes unavailable. :func:`read_through` keeps a fresh
  copy for ``fresh_seconds`` and a last-good copy for a day, so a GitHub outage
  shows the last queue it saw (marked stale) instead of a 502 after a 15-second
  timeout on every page that asks.

The alias is ``"admin"`` (``config/settings.py``): on disk, so it survives the
worker's recycle every ~500 requests, and a dummy under test like the others.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import requests
from django.core.cache import caches
from django.utils import timezone

ALIAS = "admin"

#: How long a failed read is answered from the last-good copy before GitHub is
#: tried again — so an outage costs one timeout a minute, not one per page load.
RETRY_AFTER_FAILURE = 60
#: How long a last-good copy is kept to fall back on.
KEEP_LAST_GOOD = 24 * 3600


def admin_cache():
    return caches[ALIAS]


def revision_key(name: str) -> str:
    """``name`` under the current content revision — misses once content moves."""
    from .models import ContentRevision

    return f"{name}:rev{ContentRevision.current()}"


def revision_memo(
    name: str, compute: Callable[[], Any], *, timeout: int, refresh: bool = False
) -> Any:
    """``compute()``, memoised under the content revision; ``refresh`` recomputes
    and overwrites (a Refresh / Re-run button)."""
    key = revision_key(name)
    cache = admin_cache()
    if not refresh:
        hit = cache.get(key)
        if hit is not None:
            return hit
    value = compute()
    cache.set(key, value, timeout)
    return value


class Read:
    """One answer from :func:`read_through`: the value, when it was fetched, and
    whether it is a last-good copy served because the fetch failed."""

    __slots__ = ("value", "read_at", "stale")

    def __init__(self, value: Any, read_at: datetime, stale: bool = False):
        self.value = value
        self.read_at = read_at
        self.stale = stale


def read_through(key: str, fetch: Callable[[], Any], *, fresh_seconds: int) -> Read:
    """``fetch()`` reused for ``fresh_seconds``, falling back to the last good
    copy when it raises ``requests.RequestException``.

    Re-raises only when there is nothing to fall back on (a cold cache during an
    outage) — the caller then answers its usual "GitHub is unreachable"."""
    cache = admin_cache()
    fresh = cache.get(f"{key}:fresh")
    if fresh is not None:
        value, read_at, stale = fresh
        return Read(value, read_at, stale)
    try:
        value = fetch()
    except requests.RequestException:
        good = cache.get(f"{key}:good")
        if good is None:
            raise
        value, read_at = good
        # Remember the failure briefly, so the next page load doesn't wait on the
        # same timeout; the last-good copy answers meanwhile.
        cache.set(f"{key}:fresh", (value, read_at, True), RETRY_AFTER_FAILURE)
        return Read(value, read_at, stale=True)
    now = timezone.now()
    cache.set(f"{key}:fresh", (value, now, False), fresh_seconds)
    cache.set(f"{key}:good", (value, now), KEEP_LAST_GOOD)
    return Read(value, now)


def forget(key: str) -> None:
    """Drop the fresh copy (after a write the next read must see); the last-good
    copy stays as the outage fallback."""
    admin_cache().delete(f"{key}:fresh")
