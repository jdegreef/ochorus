"""The admin audit trail: what it records, and that nothing escapes it.

The coverage test is the important one. A mixin that has to be remembered is a
mixin that will be forgotten — the same lesson RLS taught this codebase, where
nineteen tables were missed precisely because six were done by hand and nothing
checked. So this walks the real URL conf, finds every admin view with a write
method, and fails on any that is not audited, naming it and the fix.
"""

from __future__ import annotations

from django.test import TestCase, override_settings
from django.urls import get_resolver
from rest_framework.test import APIClient

from accounts.permissions import IsAdminEmail

from .audit import WRITE_METHODS, AdminAudited, AdminNotAudited
from .models import AdminAction, Author, Book, Language, ReviewOutcome


def _admin_write_views() -> list[tuple[str, type]]:
    """Every admin-gated view in the URL conf that can change something.

    Read off the resolver rather than a hand-kept list, which is the whole
    point: a new endpoint appears here the moment it is routed.
    """
    found: dict[str, type] = {}

    def walk(patterns, prefix=""):
        for p in patterns:
            if hasattr(p, "url_patterns"):
                walk(p.url_patterns, prefix + str(p.pattern))
                continue
            cls = getattr(p.callback, "cls", None)
            if cls is None:
                continue
            if IsAdminEmail not in (getattr(cls, "permission_classes", None) or []):
                continue
            if not any(hasattr(cls, m.lower()) for m in WRITE_METHODS):
                continue
            found[f"{cls.__module__}.{cls.__name__}"] = cls

    walk(get_resolver().url_patterns)
    return sorted(found.items())


class AdminAuditCoverageTests(TestCase):
    def test_every_admin_write_endpoint_is_audited(self):
        missing = [
            name
            for name, cls in _admin_write_views()
            if not issubclass(cls, (AdminAudited, AdminNotAudited))
        ]
        self.assertEqual(
            missing,
            [],
            "These admin endpoints can change something and record nothing.\n"
            "Add the mixin and say what it touched:\n"
            + "\n".join(
                f"    class {n.rsplit('.', 1)[-1]}(AdminAudited, APIView):\n"
                f"        audit_action = AdminAction.Action.<...>\n"
                f"        def audit_entry(self, request, response): ...\n"
                for n in missing
            ),
        )

    def test_an_exemption_has_to_say_why(self):
        """An unexplained exemption is indistinguishable from a forgotten one."""
        unexplained = [
            name
            for name, cls in _admin_write_views()
            if issubclass(cls, AdminNotAudited) and not (cls.audit_exempt or "").strip()
        ]
        self.assertEqual(unexplained, [], "set `audit_exempt` to the reason")

    def test_the_walk_actually_finds_endpoints(self):
        """Guard the guard: a resolver walk that silently matches nothing would
        make the test above pass for every future endpoint too."""
        found = _admin_write_views()
        self.assertGreaterEqual(len(found), 6, f"only found {[n for n, _ in found]}")


@override_settings(DEBUG=True)
class AdminAuditRecordingTests(TestCase):
    """What actually lands in the log, driven through the real endpoints."""

    def setUp(self):
        self.client = APIClient()
        # The built-in six are seeded by migration, so this adopts the real row
        # rather than colliding with it.
        self.lang, _ = Language.objects.update_or_create(
            code="sw",
            defaults={"name": "Swahili", "native_name": "Kiswahili"},
        )

    def test_a_threshold_change_records_who_what_and_the_new_bar(self):
        res = self.client.patch(
            "/api/admin/languages/sw/thresholds/", {"min_books": 3}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        row = AdminAction.objects.get()
        self.assertEqual(row.action, AdminAction.Action.LANGUAGE_THRESHOLDS)
        self.assertEqual(row.target, "language:sw")
        # The field that moved and its new value — and nothing else, so the
        # answer isn't buried in five thresholds nobody touched.
        self.assertEqual(row.detail, {"min_books": 3})

    def test_a_rejected_request_records_nothing(self):
        """A log that shows attempts as changes is worse than no log."""
        res = self.client.patch(
            "/api/admin/languages/sw/thresholds/", {"min_books": -1}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(AdminAction.objects.exists())

    def test_an_unknown_target_records_nothing(self):
        res = self.client.patch(
            "/api/admin/languages/zz/thresholds/", {"min_books": 1}, format="json"
        )
        self.assertEqual(res.status_code, 404)
        self.assertFalse(AdminAction.objects.exists())

    def test_a_read_records_nothing(self):
        """One row per dashboard refresh would bury the events worth finding."""
        self.client.get("/api/admin/languages/")
        self.client.get("/api/admin/stats/")
        self.assertFalse(AdminAction.objects.exists())

    def test_creating_an_author_records_the_author(self):
        res = self.client.post(
            "/api/admin/authors/", {"name": "Amy Carmichael"}, format="json"
        )
        self.assertEqual(res.status_code, 201)
        row = AdminAction.objects.get()
        self.assertEqual(row.action, AdminAction.Action.AUTHOR_CREATE)
        # Read back the slug the endpoint actually minted: `_unique_author_slug`
        # suffixes a name already taken, and asserting a literal would make this
        # depend on what else is in the database.
        self.assertEqual(row.target, f"author:{res.data['slug']}")
        self.assertEqual(row.detail["name"], "Amy Carmichael")

    def test_a_review_decision_and_its_undo_are_two_different_actions(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(
            author=author,
            slug="humility",
            language="sw",
            title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        decide = self.client.post(
            "/api/admin/review-queue/",
            {"kind": "book", "slug": "humility", "language": "sw", "outcome": "approved"},
            format="json",
        )
        self.assertEqual(decide.status_code, 200)
        undo = self.client.delete(
            "/api/admin/review-queue/?kind=book&slug=humility&language=sw"
        )
        self.assertEqual(undo.status_code, 200)

        actions = list(AdminAction.objects.order_by("at").values_list("action", flat=True))
        self.assertEqual(
            actions,
            [AdminAction.Action.REVIEW_DECIDE, AdminAction.Action.REVIEW_UNDO],
        )
        # ReviewOutcome keeps the decision; this keeps the fact that it happened
        # AND that it was taken back — which the outcome row no longer shows.
        self.assertFalse(ReviewOutcome.objects.exists())
        decided = AdminAction.objects.get(action=AdminAction.Action.REVIEW_DECIDE)
        self.assertEqual(decided.target, "book:humility:sw")
        self.assertEqual(decided.detail["outcome"], "approved")
        self.assertEqual(decided.detail["decided"], 1)

    def test_the_log_is_ordered_newest_first(self):
        self.client.post("/api/admin/authors/", {"name": "One"}, format="json")
        self.client.post("/api/admin/authors/", {"name": "Two"}, format="json")
        self.assertEqual(
            [r.detail["name"] for r in AdminAction.objects.all()], ["Two", "One"]
        )
