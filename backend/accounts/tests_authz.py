"""Every write endpoint must gate on more than AllowAny.

The companion to ``tests_rls``: RLS proves no table is reachable by the anon
key; this proves no *write* view is reachable by an anonymous request.

DRF's default permission is ``AllowAny`` (``config.settings``), so FORGETTING
``permission_classes`` on a new POST/PUT/PATCH/DELETE view ships an open,
DB-mutating endpoint — and the audit-coverage walk in ``library.tests_audit``
cannot catch it, because that one only looks at views which ALREADY declare an
admin gate (``IsAdminEmail`` / ``RequireCapability``). A view shipped with the
bare default is invisible to it. This walk looks at *all* of them.

A genuinely public write is allowed, but only from the explicit exemption map
below and only with a stated reason — an unexplained exemption is
indistinguishable from a forgotten one (the lesson ``tests_rls`` and
``tests_audit`` were both built on).

SCOPE: this walks DRF views only — ``APIView`` subclasses and ``@api_view``
functions, whose write handlers are named ``post``/``put``/``patch``/``delete``
(the ``.callback.cls`` the walk reads off). That is every endpoint this API has;
there are no DRF ``ViewSet``s (whose write actions would be ``create``/
``update``/``destroy``) and no plain-Django mutating function views (which carry
no ``.cls``). Were either pattern ever introduced, this guard would not see it —
add coverage for it there, or (better) keep writing DRF views.
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import get_resolver
from rest_framework.permissions import AllowAny

from library.audit import WRITE_METHODS

#: ``<module>.<ClassName>`` → why this view may serve a write to an anonymous
#: caller. Keep the reason concrete: the next reader decides from it whether the
#: exemption is still earned.
PUBLIC_WRITE_EXEMPTIONS = {
    "library.views.SearchClickView": (
        "Public click log: an unauthenticated reader records which result they "
        "opened. Throttled (search-click) and JSON-only — the content-type "
        "forces a CORS preflight, closing the forged cross-origin <form> route "
        "— and it writes one capped row. See config.settings and library.views."
    ),
    "library.views.QuoteResolveView": (
        "Read-shaped POST: resolves a batch of saved-quote slugs to cards and "
        "writes NOTHING. POST only because the slug list is unbounded and "
        "belongs in the body, not the URL. Throttled and batch-capped to 200."
    ),
}


def _write_views() -> dict[str, type]:
    """Every routed view with a write handler, keyed by ``<module>.<ClassName>``.

    Read off the resolver rather than a hand-kept list — the whole point: a new
    write endpoint appears here the moment it is routed, before anyone has to
    remember it exists.
    """
    found: dict[str, type] = {}

    def walk(patterns):
        for p in patterns:
            if hasattr(p, "url_patterns"):
                walk(p.url_patterns)
                continue
            cls = getattr(p.callback, "cls", None)
            if cls is None:
                continue
            if not any(hasattr(cls, m.lower()) for m in WRITE_METHODS):
                continue
            found[f"{cls.__module__}.{cls.__name__}"] = cls

    walk(get_resolver().url_patterns)
    return found


def _is_open(cls) -> bool:
    """Can an anonymous request reach this view's write handler?

    DRF ANDs the permission classes, so the view is open only when EVERY class
    is ``AllowAny`` (or there are none — which, given DRF's default, is the same
    thing). One real gate anywhere in the list is enough to close it.
    """
    perms = getattr(cls, "permission_classes", None) or []
    return all(p is AllowAny for p in perms)


class WriteEndpointAuthorizationTests(TestCase):
    def test_no_write_endpoint_is_open_unless_explicitly_exempt(self):
        offenders = sorted(
            name
            for name, cls in _write_views().items()
            if _is_open(cls) and name not in PUBLIC_WRITE_EXEMPTIONS
        )
        self.assertEqual(
            offenders,
            [],
            "These views handle a write method (POST/PUT/PATCH/DELETE) but gate "
            "only on AllowAny — an anonymous caller can reach them and change "
            "data. Set permission_classes explicitly (IsAdminEmail / "
            "RequireCapability / IsAuthenticated); or, if the write is genuinely "
            "public, add the class to PUBLIC_WRITE_EXEMPTIONS with a reason:\n    "
            + "\n    ".join(offenders),
        )

    def test_every_exemption_still_names_an_open_write_view(self):
        """A stale exemption hides a later regression: were a listed view to gain
        a real gate (or stop being a write), its name lingering here would also
        silence a *different* future view that took its place. Keep the list a
        live inventory of what is actually open."""
        views = _write_views()
        stale = sorted(
            name
            for name in PUBLIC_WRITE_EXEMPTIONS
            if name not in views or not _is_open(views[name])
        )
        self.assertEqual(
            stale,
            [],
            "These exemptions no longer name an open write endpoint — remove "
            "them from PUBLIC_WRITE_EXEMPTIONS:\n    " + "\n    ".join(stale),
        )

    def test_the_walk_actually_finds_write_endpoints(self):
        """Guard the guard: a resolver walk that silently matched nothing would
        make the coverage test pass for every future endpoint too (the exact way
        tests_audit's own walk is guarded)."""
        found = _write_views()
        self.assertGreaterEqual(
            len(found), 20, f"only found {sorted(found)}"
        )
