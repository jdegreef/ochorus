"""Client-cache headers for the public content API.

Every response the reader asks for was recomputed from scratch, every time: the
library carried no ``Cache-Control`` at all. The catalogue changes on a deploy or
an admin action, not per request, so a reader paging back to a shelf they were
just on re-ran the whole query.

**The ETag** is keyed on the pair that together cover *every* way reader-visible
content changes: ``content_digest()`` (baked at image build, moves when the
shipped repo content does) AND ``ContentRevision`` (bumped by the content-changed
channel whenever an admin publishes, approves, or takes a language live — the
mutations a deploy-only digest can't see, ``library/invalidation``). A digest-only
tag was the trap this module used to avoid: it would answer ``304`` against an
unchanged digest *forever* after an admin publish. Adding the revision removes
the trap — a conditional request stops matching the moment content changes.

The tag also folds in the request's full path, so it is **per-URL**: a client
holding the ``/books`` tag can never be told ``304`` for ``/authors``. The check
runs in ``dispatch``, *before* the queryset, so a matching conditional request is
answered without touching the database — the win that matters for a compute-bound
origin, on top of the body it no longer re-transmits every ``max-age``.

``max-age`` + ``stale-while-revalidate`` still bound staleness and cannot get
stuck; the ETag lets a revalidation after that window return ``304`` instead of
the whole shelf.

**One gap, the same one the rebuild has.** A change made DIRECTLY in the database
— the documented urgent copyright pull (``seed_sermons``), or a manual SQL fix —
bumps neither the digest (no deploy) nor the revision (no API call), so the ETag
would keep answering ``304`` against it, just as the prerendered reader would
stay stale. Run ``manage.py bump_content_revision`` after such a change: it bumps
the revision (busting every ETag) and fires the rebuild, closing both.

``public`` is deliberate and was checked, not assumed: nothing in the public
views or serializers reads ``request.user``, so no response varies by reader and
a shared cache cannot leak one reader's view to another. Anything that DOES vary
per reader lives under ``/api/reading/`` behind ``IsAuthenticated`` and must
never use this mixin.
"""

from __future__ import annotations

import hashlib

from django.http import HttpResponseNotModified
from django.utils.http import parse_etags

#: How long a client may reuse a response without asking again. Short on
#: purpose: an admin who publishes a book should see it in the reader in about a
#: minute, not after a cache expiry measured in hours.
MAX_AGE = 60

#: How long a stale copy may be shown WHILE a refresh runs in the background.
#: Ten minutes, because showing the previous shelf for a moment is much better
#: than showing a spinner, and the refresh lands before the reader notices.
STALE_WHILE_REVALIDATE = 600

CACHE_CONTROL = (
    f"public, max-age={MAX_AGE}, stale-while-revalidate={STALE_WHILE_REVALIDATE}"
)


def content_etag(request) -> str:
    """A weak, per-URL ETag over (path, content digest, content revision).

    Weak (``W/``) because it marks a content *version*, not a byte-identical body.
    Per-URL because a conditional request must only 304 against the same resource
    the client cached. The digest covers repo-borne content (deploys); the
    revision covers admin-borne content (publish/approve/go-live) — see the module
    docstring. Imports are local to keep this module import-cheap and avoid a
    cycle through models."""
    from .content_fixtures import content_digest
    from .models import ContentRevision

    material = f"{request.get_full_path()}|{content_digest()}|{ContentRevision.current()}"
    return 'W/"' + hashlib.sha256(material.encode()).hexdigest()[:16] + '"'


def _if_none_match(request, etag: str) -> bool:
    header = request.META.get("HTTP_IF_NONE_MATCH")
    if not header:
        return False
    # Django's parser handles the comma list, whitespace, and the `*` wildcard
    # ("304 if any representation exists"), which a plain split would miss.
    candidates = parse_etags(header)
    return "*" in candidates or etag in candidates


class PublicContentCacheMixin:
    """Add ``Cache-Control`` + a conditional ``ETag`` to public GET/HEAD reads.

    Applied per view rather than as middleware so that adding an endpoint is a
    decision: a view that starts varying by reader must not silently inherit
    ``public`` caching. The reading and admin APIs deliberately do not use it.
    """

    def dispatch(self, request, *args, **kwargs):
        # Conditional GET: when the client already holds this content version,
        # answer 304 BEFORE running the queryset (the origin is compute-bound).
        # The tag is only computed when a validator is present, so an ordinary
        # first request pays nothing extra here — finalize_response tags it once.
        if request.method in ("GET", "HEAD") and request.META.get("HTTP_IF_NONE_MATCH"):
            etag = content_etag(request)
            if _if_none_match(request, etag):
                not_modified = HttpResponseNotModified()
                not_modified["ETag"] = etag
                not_modified["Cache-Control"] = CACHE_CONTROL
                return not_modified
        return super().dispatch(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        # Only cache successful reads. An error is not the catalogue, and
        # caching a 404 for a minute would outlive the import that fixes it.
        if request.method in ("GET", "HEAD") and response.status_code == 200:
            response["Cache-Control"] = CACHE_CONTROL
            response["ETag"] = content_etag(request)
        return response
