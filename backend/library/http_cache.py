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
The frontend leans on this too: page loads send ``/api/library/`` reads
WITHOUT the reader's token (``isPublicLibraryRead`` in ``frontend/src/lib/api.ts``),
so a library view that began reading the user would silently see everyone as
anonymous.
"""

from __future__ import annotations

import contextlib
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

#: What a CDN in front of the API may do (``CDN-Cache-Control``, RFC 9213:
#: Cloudflare, Fastly and Akamai read it before ``Cache-Control`` and do not
#: pass it on to the browser). The same minute as the browser, so an admin's
#: change still reaches readers in about a minute, but WITHOUT
#: ``stale-while-revalidate``: an edge that served a stale copy while it
#: refreshed would hand the reader's prerender build (which reads this API minutes
#: after a change fires the rebuild) last version's shelf, and bake it into the
#: static pages. A browser may show a stale shelf for a moment; a build must not.
#: Inert until a CDN sits in front of the API (docs/api-edge-cache.md).
EDGE_CACHE_CONTROL = f"public, max-age={MAX_AGE}"


def set_cache_headers(response) -> None:
    """The browser's and the edge's cache headers on a public content read."""
    response["Cache-Control"] = CACHE_CONTROL
    response["CDN-Cache-Control"] = EDGE_CACHE_CONTROL


def content_etag(request, *, release: bool = False) -> str:
    """A weak, per-URL ETag over (path, content digest, content revision) —
    and, with ``release``, the deployed commit, for a view whose response SHAPE
    is code (the EPUB's bytes, a hub that gains a field): a deploy that only
    changes code moves neither the digest nor the revision, so without it a
    returning reader's cached body, field missing, would keep answering 304.

    Weak (``W/``) because it marks a content *version*, not a byte-identical body.
    Per-URL because a conditional request must only 304 against the same resource
    the client cached. The digest covers repo-borne content (deploys); the
    revision covers admin-borne content (publish/approve/go-live) — see the module
    docstring. Imports are local to keep this module import-cheap and avoid a
    cycle through models."""
    from .content_fixtures import content_digest
    from .models import ContentRevision

    # Once per request: the response cache asks for the same tag on lookup and
    # on store, and a query-budgeted view must not pay the revision read twice.
    memo = getattr(request, "_content_etags", None)
    if memo is None:
        memo = {}
        with contextlib.suppress(AttributeError):  # refuses attributes: no memo
            request._content_etags = memo
    if release in memo:
        return memo[release]
    material = f"{request.get_full_path()}|{content_digest()}|{ContentRevision.current()}"
    if release:
        from django.conf import settings

        material += f"|{settings.RELEASE_COMMIT}"
    memo[release] = 'W/"' + hashlib.sha256(material.encode()).hexdigest()[:16] + '"'
    return memo[release]


def _if_none_match(request, etag: str) -> bool:
    header = request.META.get("HTTP_IF_NONE_MATCH")
    if not header:
        return False
    # Django's parser handles the comma list, whitespace, and the `*` wildcard
    # ("304 if any representation exists"), which a plain split would miss.
    candidates = parse_etags(header)
    return "*" in candidates or etag in candidates


#: The cache alias the rendered bodies of ``response_cache`` views live in
#: (``config/settings.py``): file-based, on the instance's disk.
RESPONSE_CACHE = "responses"


def _response_key(request) -> str:
    """The cache key for one rendered response: the release-tracking ETag (path,
    content digest, admin revision, deployed commit), plus the calendar year,
    which ``rights.py`` folds into what a card says (public-domain terms)."""
    from datetime import date

    return f"body:{date.today().year}:{content_etag(request, release=True)}"


def _enabled() -> bool:
    """False when the alias is a DummyCache (the test suite), so a disabled
    cache costs no key computation at all."""
    from django.core.cache import caches
    from django.core.cache.backends.dummy import DummyCache

    return not isinstance(caches[RESPONSE_CACHE], DummyCache)


def _cacheable_renderer(response) -> bool:
    renderer = getattr(response, "accepted_renderer", None)
    return bool(renderer) and getattr(renderer, "media_type", "").startswith("application/json")


class PublicContentCacheMixin:
    """Add ``Cache-Control`` + a conditional ``ETag`` to public GET/HEAD reads.

    Applied per view rather than as middleware so that adding an endpoint is a
    decision: a view that starts varying by reader must not silently inherit
    ``public`` caching. The reading and admin APIs deliberately do not use it.

    ``etag_tracks_release``: also key the ETag to the deployed commit
    (``content_etag(release=True)``), for a view whose response shape changes
    with code rather than content.
    """

    etag_tracks_release = False

    #: Also keep this view's rendered JSON in the on-disk ``responses`` cache,
    #: under the content key, so it is built once per deploy or admin publish
    #: instead of once per worker. The worker recycles every ~500 requests, and
    #: each fresh one rebuilt the big lists from rows: 30-100 MB and seconds
    #: apiece under the web build's crawl (``[memory]`` log, 2026-11-19).
    #: Opt in only for a view whose body is a pure function of its URL and the
    #: content: nothing per reader, per day or random.
    response_cache = False

    def dispatch(self, request, *args, **kwargs):
        # Conditional GET: when the client already holds this content version,
        # answer 304 BEFORE running the queryset (the origin is compute-bound).
        # The tag is only computed when a validator is present, so an ordinary
        # first request pays nothing extra here — finalize_response tags it once.
        if request.method in ("GET", "HEAD") and request.META.get("HTTP_IF_NONE_MATCH"):
            etag = content_etag(request, release=self.etag_tracks_release)
            if _if_none_match(request, etag):
                not_modified = HttpResponseNotModified()
                not_modified["ETag"] = etag
                set_cache_headers(not_modified)
                return not_modified
        if self.response_cache and _enabled() and request.method in ("GET", "HEAD"):
            hit = _cached_body(request)
            if hit is not None:
                return hit
        return super().dispatch(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        # Only cache successful reads. An error is not the catalogue, and
        # caching a 404 for a minute would outlive the import that fixes it.
        if request.method in ("GET", "HEAD") and response.status_code == 200:
            set_cache_headers(response)
            response["ETag"] = content_etag(request, release=self.etag_tracks_release)
            if self.response_cache and _enabled() and _cacheable_renderer(response):
                _store_body(request, response)
        return response


def _cached_body(request):
    """A stored response for this request's content key, or None."""
    from django.core.cache import caches
    from django.http import HttpResponse

    try:
        stored = caches[RESPONSE_CACHE].get(_response_key(request))
    except Exception:  # noqa: BLE001 -- a broken cache is a miss, never an error
        return None
    if not stored:
        return None
    content_type, body, etag = stored
    response = HttpResponse(body, content_type=content_type)
    set_cache_headers(response)
    response["ETag"] = etag
    return response


def _store_body(request, response) -> None:
    from django.core.cache import caches

    response.render()
    # A full disk or a broken cache must not fail the read.
    with contextlib.suppress(Exception):
        caches[RESPONSE_CACHE].set(
            _response_key(request),
            (response["Content-Type"], response.content, response["ETag"]),
        )
