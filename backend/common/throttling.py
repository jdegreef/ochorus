"""Throttle bases shared across apps.

The counters live in their own cache alias rather than the default one. Keeping
rate-limiter state out of the application cache matters in both directions — a
cache flush must not hand out fresh quota, and a throttle must not evict
application data — and it gives the test suite a seam it badly needs.

Without that seam, throttle state is process-global and leaks between tests: the
anonymous search throttle keys on the client address, every test request comes
from 127.0.0.1, and the suite makes ~90 search requests, so they all land in one
60-second bucket. Nothing fails today; it fails the week someone adds a few more
search assertions, in an unrelated test, for no visible reason. Under
``manage.py test`` the alias is a dummy cache, so that cannot happen. The tests
that assert a throttle actually fires patch a real cache back in, so the
behaviour stays proven — just not ambient.
"""

from __future__ import annotations

from django.core.cache import caches
from rest_framework.throttling import UserRateThrottle


class ScopedCacheThrottle(UserRateThrottle):
    """A ``UserRateThrottle`` counting in the dedicated ``throttle`` cache.

    ``UserRateThrottle`` rather than ``AnonRateThrottle``: the latter exempts
    authenticated requests by design, and the reader's ``apiFetch`` sends a
    Supabase token whenever there is one — so an "anonymous" throttle would
    cover nobody who had signed up. This keys on the account when there is one
    and the client address otherwise, which is the population that needs
    bounding either way.
    """

    cache = caches["throttle"]
