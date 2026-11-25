"""``GET /api/build-facts/``: production's DB-owned facts, for the web build.

Option A of docs/build-without-prod-api.md ("the facts transport"). With
``OCHORUS_BUILD_API=local`` the web build seeds its own API from the checkout
and lays production's decisions over it (``apply_build_facts``): which languages
are live, what is published, review state, approved quotes and bios. This view
hands those over in one request at build start, so a web-only rebuild fired by
Go live or an approval sees the change it was fired for.

The document names unpublished slugs and review state, so it is not public:

* ``BUILD_FACTS_TOKEN`` unset (the default) → 404, as if the route were not
  there. Nothing is exposed until the token is configured on both services.
* The caller must send ``Authorization: Bearer <BUILD_FACTS_TOKEN>`` (the web
  service's ``OCHORUS_BUILD_FACTS_TOKEN``), compared in constant time. Anything
  else → 404 too, so the route can't be told apart from a missing one.

A plain Django view, not DRF: DRF would run SupabaseJWTAuthentication on the
bearer, and this token is not a JWT. Read-only (``export_facts`` runs about ten
SELECTs) and never cached.
"""

from __future__ import annotations

import hmac

from django.conf import settings
from django.http import Http404, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from library.build_facts import export_facts


def _authorized(request) -> bool:
    token = (getattr(settings, "BUILD_FACTS_TOKEN", "") or "").strip()
    if not token:
        return False
    scheme, _, sent = request.META.get("HTTP_AUTHORIZATION", "").partition(" ")
    if scheme.lower() != "bearer" or not sent.strip():
        return False
    return hmac.compare_digest(sent.strip().encode(), token.encode())


@require_GET
@never_cache
def build_facts(request):
    if not _authorized(request):
        raise Http404
    return JsonResponse(export_facts(), json_dumps_params={"ensure_ascii": False})
