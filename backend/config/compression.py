"""Compress the API's responses (gzip), except where compression could leak a secret.

Nothing compressed the API's JSON before this: WhiteNoise compresses only the
static files it serves, and Django's GZipMiddleware was not installed. A chapter
or sermon body is the bulk of what a reader downloads, and that HTML-in-JSON
shrinks to about a quarter, which matters most on the slow mobile networks many
readers use. If Render's proxy was already compressing, nothing changes: the
proxy passes an encoded response through as it is.

BREACH, the reason Django leaves compression opt-in: a response that carries a
secret AND reflects attacker-chosen text lets the attacker guess the secret byte
by byte from the compressed size. The reader API carries no secrets in its
bodies (the Supabase token lives in the client and travels only as a request
header), but the Django admin's HTML embeds a CSRF token on every form. So the
admin is never compressed, and nor is the admin dashboard's API
(/api/admin/...), whose JSON holds readers' email addresses next to search
text the caller chose. Django's own middleware also randomises the gzip
filename field to blunt the attack; this keeps that.
"""

from __future__ import annotations

from django.middleware.gzip import GZipMiddleware

# ONLY BROWSERS. A request without an ``Origin`` is a server: the web build's
# prerender crawl, its build scripts, Render's health check. The crawl's
# Node fetch (undici) crashed the whole build on gzip bodies (`assert(!this.paused)`
# in undici's parser, CI 2026-11-24), and a server on the same host or network
# gains nothing from compression anyway. Every reader call carries ``Origin``:
# the site is on another origin than the API, and the apps send their fixed
# Capacitor origins.

# Paths whose responses can hold a secret: a CSRF token in a Django admin form,
# or private reader data in the admin dashboard's API.
UNCOMPRESSED_PREFIXES = ("/admin/", "/api/admin/")


class ApiGZipMiddleware(GZipMiddleware):
    def process_response(self, request, response):
        if request.path.startswith(UNCOMPRESSED_PREFIXES):
            return response
        if not request.headers.get("Origin"):
            return response
        return super().process_response(request, response)
