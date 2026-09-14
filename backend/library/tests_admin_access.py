"""Coverage guard for the scoped admin gate.

The sibling of ``tests_audit``: it walks the real URL conf and fails the build if
any ``/api/admin/*`` view ships without a valid capability declaration, so a new
admin endpoint can't quietly land ungated (deny-all) or mis-gated. This is the
single source of truth that "every admin route has a policy" is enforced by a
test, not by remembering.
"""

from __future__ import annotations

from django.test import SimpleTestCase
from django.urls import get_resolver

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import RequireCapability

_VALID_CAPS = set(AdminCapability.values)
_VALID_VERBS = set(AdminVerb.values)
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _admin_views():
    """Every routed view under ``api/admin/``, as (route, view class)."""
    found = {}

    def walk(patterns, prefix=""):
        for p in patterns:
            if hasattr(p, "url_patterns"):
                walk(p.url_patterns, prefix + str(p.pattern))
                continue
            route = prefix + str(p.pattern)
            cls = getattr(p.callback, "cls", None)
            if cls is not None and route.startswith("api/admin/"):
                found[route] = cls

    walk(get_resolver().url_patterns)
    return sorted(found.items())


class AdminAccessCoverageTests(SimpleTestCase):
    def test_the_walk_finds_the_admin_surface(self):
        # Guard the guard — a walk that matches nothing would pass everything.
        self.assertGreaterEqual(len(_admin_views()), 20, "URL walk found almost no admin routes")

    def test_every_admin_view_declares_a_valid_capability(self):
        problems = []
        for route, cls in _admin_views():
            gate = getattr(cls, "permission_classes", None) or []
            if RequireCapability not in gate:
                problems.append(f"{route} ({cls.__name__}): not gated by RequireCapability")
                continue
            cap = getattr(cls, "admin_capability", None)
            if cap not in _VALID_CAPS:
                problems.append(f"{route} ({cls.__name__}): bad/missing admin_capability {cap!r}")
            verbs = getattr(cls, "admin_verbs", None) or {}
            single = getattr(cls, "admin_verb", None)
            declared = set(verbs.values()) | ({single} if single else set())
            if not declared or not declared <= _VALID_VERBS:
                problems.append(f"{route} ({cls.__name__}): bad/missing verb(s) {declared!r}")
        self.assertEqual(problems, [], "\n".join(["Admin views with a bad access policy:", *problems]))

    def test_write_methods_require_at_least_act(self):
        """A view that mutates must not be gated at merely 'view'/'suggest' for its
        write method — a category error that would let a viewer change things."""
        lax = []
        for route, cls in _admin_views():
            if RequireCapability not in (getattr(cls, "permission_classes", None) or []):
                continue
            verbs = getattr(cls, "admin_verbs", None) or {}
            for method in _WRITE_METHODS:
                if not hasattr(cls, method.lower()):
                    continue
                verb = verbs.get(method, getattr(cls, "admin_verb", None))
                # 'suggest' is allowed on a write method: filing a job is a POST
                # that changes nothing live. Only 'view' is the category error.
                if verb == AdminVerb.VIEW:
                    lax.append(f"{route} ({cls.__name__}).{method}: gated at 'view'")
        self.assertEqual(lax, [], "\n".join(["Mutating methods gated too weakly:", *lax]))
