"""Client-cache headers for the public content API.

Every response the reader asks for was recomputed from scratch, every time: the
library carried no ``Cache-Control`` at all. The catalogue changes on a deploy or
an admin action, not per request, so a reader paging back to a shelf they were
just on re-ran the whole query.

**Why there is no ETag here.** An ETag keyed on ``content_digest()`` is the
obvious move — the digest is baked at image build and changes exactly when the
shipped content does. It is also wrong, and quietly so. An admin can publish a
book, approve a translation, or take a language live **without a deploy**, and
none of that moves the digest. A conditional request would then keep answering
``304 Not Modified`` against an unchanged digest *forever*, so the reader would
never see the change until the next release. That is a worse failure than no
caching, because it is unbounded and invisible.

Keying on the data instead would need a cheap "max updated_at across content",
and the columns are not there: Book, Sermon, Plan and the two translation tables
carry ``updated_at``, but Author, Chapter, Topic and Language do not — which is
precisely the set an admin edits. Adding them is a migration and a separate
change.

So this ships the half that is correct on its own: a short ``max-age`` bounds
staleness to seconds and cannot get stuck, and ``stale-while-revalidate`` lets a
client show the cached copy while it refreshes. When those columns exist,
conditional requests can be added on top without revisiting any of this.

``public`` is deliberate and was checked, not assumed: nothing in the public
views or serializers reads ``request.user``, so no response varies by reader and
a shared cache cannot leak one reader's view to another. Anything that DOES vary
per reader lives under ``/api/reading/`` behind ``IsAuthenticated`` and must
never use this mixin.
"""

from __future__ import annotations

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


class PublicContentCacheMixin:
    """Add ``Cache-Control`` to successful GET/HEAD responses.

    Applied per view rather than as middleware so that adding an endpoint is a
    decision: a view that starts varying by reader must not silently inherit
    ``public`` caching. The reading and admin APIs deliberately do not use it.
    """

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        # Only cache successful reads. An error is not the catalogue, and
        # caching a 404 for a minute would outlive the import that fixes it.
        if request.method in ("GET", "HEAD") and response.status_code == 200:
            response["Cache-Control"] = CACHE_CONTROL
        return response
