"""Keep the API for Ochorus's own clients: the reader, the phone apps, the build.

What this is, and what it is not
--------------------------------
The reader is a static site whose browser calls this API directly, so anything
the reader can fetch, a visitor can fetch too: open the network tab, copy the
request. There is no secret a browser can hold that a person at that browser
can't read. So this is NOT access control — the library's content is public on
the reader's own pages, and private data is already gated by the Supabase token
(``accounts``) and the admin gates. It is a fence, raising the bar from "point
a script at api.ochorus.com" to "deliberately forge the headers a browser sends
from ochorus.com", and that bar is what turns casual scrapers, other sites
embedding our API, and generic bots away. The rest is the edge's job (rate
limits, bot management — docs/api-access.md).

How a request gets through (any one is enough)
----------------------------------------------
* ``Origin`` is one of ``CORS_ALLOWED_ORIGINS`` (or this API's own origin).
  Every cross-origin ``fetch`` a browser makes sends it and a page cannot
  change it — that covers the reader on ochorus.com, the iOS / Android apps
  (their fixed Capacitor origins) and Googlebot's renderer, which runs the
  reader's JavaScript like any browser.
* No ``Origin``, but a ``Referer`` from one of those origins: a same-origin GET
  (browsers omit ``Origin`` there) or a plain link.
* ``X-Ochorus-Key`` matches one of ``API_SERVICE_KEYS``: the web build's
  prerender crawl and its build scripts, which are servers, send no ``Origin``,
  and are the only callers that can keep a secret. Kept in a PRIVATE env var on
  the web service, never a ``PUBLIC_`` one (those are baked into the bundle).
* The path is exempt (``EXEMPT``): reached by things that are not our pages —
  Render's health check and the build's release gate, Resend's signed webhook,
  the unsubscribe links in an email, a downloaded EPUB.

Modes (``API_GUARD_MODE``)
--------------------------
``off`` does nothing; ``report`` lets everything through and logs what
``enforce`` would refuse (``ochorus.api_guard`` logger), so production can be
watched for a day before any request is turned away; ``enforce`` answers 403.
Production defaults to ``report`` — the build only sends its key once
``OCHORUS_API_KEY`` is set on ochorus-web, so enforcing before that would fail
the next deploy's prerender.
"""

from __future__ import annotations

import contextlib
import hmac
import logging
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger("ochorus.api_guard")

HEADER = "X-Ochorus-Key"
_META_KEY = "HTTP_X_OCHORUS_KEY"

# Paths reached by callers that are not our pages. Each needs a reason.
EXEMPT = re.compile(
    r"^/api/(?:"
    # Render's health check, uptime monitors, and the web build's release gate
    # (frontend/scripts/await-api-release.mjs) — liveness + a content digest.
    r"health/"
    # Resend's webhook (Svix-signed), and the unsubscribe / preferences links an
    # email client opens — token-gated, and a mail app sends no Origin.
    r"|emails/"
    # A book's EPUB: a download link, not a fetch. Referrer settings can strip
    # the Referer, and the file is the free download the page offers anyway.
    r"|library/books/[^/]+/download\.epub$"
    r")"
)


def _origin(url: str) -> str:
    """``scheme://host[:port]`` of a URL, lower-cased; '' if it has none."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return ""
    if not parts.scheme or not parts.netloc:
        return ""
    return f"{parts.scheme}://{parts.netloc}".lower()


def _allowed_origins() -> set[str]:
    return {o.rstrip("/").lower() for o in settings.CORS_ALLOWED_ORIGINS}


def _has_service_key(request) -> bool:
    sent = request.META.get(_META_KEY, "")
    if not sent:
        return False
    return any(
        hmac.compare_digest(sent.encode(), key.encode())
        for key in settings.API_SERVICE_KEYS
    )


def refusal_reason(request) -> str | None:
    """Why the guard would turn this request away, or None if it may pass."""
    path = request.path
    if not path.startswith("/api/") or EXEMPT.match(path):
        return None
    if request.method == "OPTIONS":  # a CORS preflight; CorsMiddleware answers it
        return None
    if _has_service_key(request):
        return None
    allowed = _allowed_origins()
    # This API's own origin (a same-origin caller). A disallowed Host raises;
    # Django refuses that request on its own.
    with contextlib.suppress(Exception):
        allowed.add(_origin(request.build_absolute_uri("/")))
    origin = request.META.get("HTTP_ORIGIN", "")
    if origin:
        return (
            None if origin.rstrip("/").lower() in allowed else f"origin {origin[:100]}"
        )
    referer = request.META.get("HTTP_REFERER", "")
    if referer:
        return (
            None if _origin(referer) in allowed else f"referer {_origin(referer)[:100]}"
        )
    if request.META.get(_META_KEY):
        return "wrong service key"
    return "no origin, referer or service key"


class ApiGuardMiddleware:
    """See the module docstring. Sits right after CorsMiddleware, so a refusal
    still carries the CORS headers a browser needs to read it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        mode = settings.API_GUARD_MODE
        if mode != "off":
            reason = refusal_reason(request)
            if reason:
                logger.warning(
                    "api_guard %s %s %s (%s) ua=%r",
                    "refused" if mode == "enforce" else "would refuse",
                    request.method,
                    request.path,
                    reason,
                    request.META.get("HTTP_USER_AGENT", "")[:120],
                )
                if mode == "enforce":
                    return JsonResponse(
                        {"detail": "This API serves Ochorus's own apps only."},
                        status=403,
                    )
        return self.get_response(request)
