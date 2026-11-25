"""The admin's GitHub reads — reused for a minute or two, and survivable.

The translation and content-edit queues are GitHub issues, read over a
paginated API with a 15-second timeout per page. :func:`read_through` reuses a
read for ``fresh_seconds`` and keeps it for a day, so every admin page that
shows the queue shares one read — and a GitHub outage shows the last queue it
saw (marked stale) instead of a 502 after a timeout on every page that asks.

(The admin's content-derived memos — dashboard stats, the audit scan — use
``invalidation.revision_cached`` on the same alias.)

The alias is ``"admin"`` (``config/settings.py``): on disk, so it survives the
worker's recycle every ~500 requests, and a dummy under test like the others.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, NamedTuple

import requests
from django.core.cache import caches
from django.utils import timezone

ALIAS = "admin"

#: How long a failed read is answered from the last-good copy before GitHub is
#: tried again — so an outage costs one timeout a minute, not one per page load.
RETRY_AFTER_FAILURE = 60
#: How long a read is kept to fall back on.
KEEP_LAST_GOOD = 24 * 3600
#: Held in place of a value when a fetch failed with nothing to fall back on.
_FAILED = "__fetch_failed__"


class Read(NamedTuple):
    """One answer from :func:`read_through`: the value, when it was fetched, and
    whether it is a last-good copy served because the fetch failed."""

    value: Any
    read_at: datetime
    stale: bool = False


def read_through(key: str, fetch: Callable[[], Any], *, fresh_seconds: int) -> Read:
    """``fetch()`` reused for ``fresh_seconds``, falling back to the last good
    read when it raises ``requests.RequestException``.

    One entry per key, ``(value, read_at, until, stale)``, kept for a day: it
    answers until ``until`` (``stale`` when that window follows a failed fetch),
    and is the fallback after. With nothing to fall back on (a cold cache during
    an outage) it raises — and remembers that for ``RETRY_AFTER_FAILURE`` too,
    so the caller's "GitHub is unreachable" costs one timeout a minute, not one
    per page load."""
    cache = caches[ALIAS]
    now = timezone.now()
    held = cache.get(key)
    if held is not None and held[0] == _FAILED:
        if now < held[2]:
            raise requests.ConnectionError(f"{key}: failed within the last minute")
        held = None  # the marker has expired: there is still nothing to fall back on
    if held is not None:
        value, read_at, until, stale = held
        if until and now < until:
            return Read(value, read_at, stale)
    try:
        value = fetch()
    except requests.RequestException:
        # Remember the failure briefly, so the next page load doesn't wait on the
        # same timeout; the last-good copy (if any) answers meanwhile.
        retry = now + timedelta(seconds=RETRY_AFTER_FAILURE)
        if held is None:
            cache.set(key, (_FAILED, None, retry, True), RETRY_AFTER_FAILURE)
            raise
        value, read_at = held[:2]
        cache.set(key, (value, read_at, retry, True), KEEP_LAST_GOOD)
        return Read(value, read_at, stale=True)
    cache.set(
        key, (value, now, now + timedelta(seconds=fresh_seconds), False), KEEP_LAST_GOOD
    )
    return Read(value, now)


def forget(key: str) -> None:
    """Make the next read go to GitHub (after a write it must see); the held copy
    stays as the outage fallback."""
    cache = caches[ALIAS]
    held = cache.get(key)
    if held is not None and held[0] == _FAILED:
        cache.delete(key)
    elif held is not None:
        cache.set(key, (*held[:2], None, held[3]), KEEP_LAST_GOOD)
