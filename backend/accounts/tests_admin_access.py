"""Scoped admin access — the AdminGrant model, live enforcement through
RequireCapability, /api/auth/me exposure, and the admin_grants command.

Enforcement is exercised with DEBUG off (no loopback bypass) and a granted
account that is NOT on the ADMIN_EMAILS allowlist — the whole point of the
feature. A verified token is supplied via force_authenticate(token=...), which
sets request.auth the way SupabaseJWTAuthentication would.
"""

from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import AdminCapability as C
from accounts.models import AdminGrant, UserProfile
from accounts.models import AdminVerb as V

User = get_user_model()
VERIFIED = {"email_verified": True}


class AdminGrantModelTests(TestCase):
    def test_verb_ladder_and_language_scope(self):
        g = AdminGrant.objects.create(email="a@b.com", capability=C.REVIEW, verb=V.ACT, languages="es")
        # act satisfies act / suggest / view; not approve.
        self.assertTrue(AdminGrant.allows("a@b.com", C.REVIEW, V.VIEW, "es"))
        self.assertTrue(AdminGrant.allows("a@b.com", C.REVIEW, V.ACT, "es"))
        self.assertFalse(AdminGrant.allows("a@b.com", C.REVIEW, V.APPROVE, "es"))
        # wrong language, wrong capability, blank email.
        self.assertFalse(AdminGrant.allows("a@b.com", C.REVIEW, V.ACT, "pt"))
        self.assertFalse(AdminGrant.allows("a@b.com", C.PUBLISH, V.ACT, "es"))
        self.assertFalse(AdminGrant.allows("", C.REVIEW, V.VIEW, "es"))
        # a non-language-scoped action (language=None) is covered by any grant.
        self.assertTrue(AdminGrant.allows("a@b.com", C.REVIEW, V.ACT, None))
        _ = g

    def test_all_languages_sentinel(self):
        AdminGrant.objects.create(email="a@b.com", capability=C.PUBLISH, verb=V.ACT, languages="*")
        self.assertTrue(AdminGrant.allows("a@b.com", C.PUBLISH, V.ACT, "sw"))
        self.assertTrue(AdminGrant.allows("a@b.com", C.PUBLISH, V.ACT, "any-code"))

    def test_email_is_normalised(self):
        AdminGrant.objects.create(email="a@b.com", capability=C.AUDIT, verb=V.VIEW)
        self.assertTrue(AdminGrant.allows("A@B.com", C.AUDIT, V.VIEW))


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class RequireCapabilityEnforcementTests(TestCase):
    """Live gate, DEBUG off. /admin/stats needs reporting:view; /admin/users needs users:view."""

    def setUp(self):
        self.client = APIClient()
        self.helper = User.objects.create(username="uid-helper", email="helper@ochorus.com")
        self.superu = User.objects.create(username="uid-super", email="super@ochorus.com")

    def test_super_admin_passes_everything(self):
        self.client.force_authenticate(user=self.superu, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/stats/").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/users/").status_code, 200)

    def test_grant_opens_exactly_its_capability(self):
        AdminGrant.objects.create(email="helper@ochorus.com", capability=C.REPORTING, verb=V.VIEW)
        self.client.force_authenticate(user=self.helper, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/stats/").status_code, 200)  # reporting:view
        self.assertEqual(self.client.get("/api/admin/users/").status_code, 403)  # users, not granted

    def test_no_grant_and_not_super_is_denied(self):
        self.client.force_authenticate(user=self.helper, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/stats/").status_code, 403)

    def test_grant_needs_a_verified_token(self):
        AdminGrant.objects.create(email="helper@ochorus.com", capability=C.REPORTING, verb=V.VIEW)
        # Authenticated, but the token does not assert the email is verified.
        self.client.force_authenticate(user=self.helper, token={"email_verified": False})
        self.assertEqual(self.client.get("/api/admin/stats/").status_code, 403)

    def test_anonymous_is_denied(self):
        # 401 (no credentials) or 403 (credentials, no access) — both are "no".
        self.assertIn(self.client.get("/api/admin/stats/").status_code, (401, 403))


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class MeRolesTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_super_admin_me_reports_all(self):
        # /api/auth/me builds a UserProfile whose supabase_uid is a UUIDField, so
        # the username (the Supabase `sub`) must be a real UUID here.
        u = User.objects.create(username="11111111-1111-1111-1111-111111111111", email="super@ochorus.com")
        self.client.force_authenticate(user=u, token=VERIFIED)
        data = self.client.get("/api/auth/me/").data
        self.assertTrue(data["is_admin"])
        self.assertTrue(data["is_super_admin"])
        self.assertEqual(data["roles"], ["super_admin"])
        self.assertEqual(data["scopes"], "all")

    def test_granted_user_me_reports_scopes(self):
        u = User.objects.create(username="22222222-2222-2222-2222-222222222222", email="helper@ochorus.com")
        AdminGrant.objects.create(
            email="helper@ochorus.com", capability=C.REVIEW, verb=V.ACT,
            languages="es,pt", role_label="reviewer",
        )
        self.client.force_authenticate(user=u, token=VERIFIED)
        data = self.client.get("/api/auth/me/").data
        self.assertTrue(data["is_admin"] is False)
        self.assertEqual(data["roles"], ["reviewer"])
        scope = next(s for s in data["scopes"] if s["capability"] == C.REVIEW)
        self.assertEqual(scope["verb"], V.ACT)
        self.assertEqual(scope["languages"], ["es", "pt"])


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class ScopeEnforcementTests(TestCase):
    """Regression guards for the fail-open the security review caught: a
    language-scoped reviewer must not act on — or even see — another language,
    including via the batch review POST that carries language per item."""

    def setUp(self):
        from library.models import Author, Book, Chapter

        self.Book = Book
        self.client = APIClient()
        self.helper = User.objects.create(
            username="33333333-3333-3333-3333-333333333333", email="es@ochorus.com"
        )
        AdminGrant.objects.create(email="es@ochorus.com", capability=C.REVIEW, verb=V.ACT, languages="es")
        author = Author.objects.create(slug="am", name="Andrew Murray")
        self.es = Book.objects.create(
            author=author, slug="humility", language="es", title="Humildad",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Chapter.objects.create(book=self.es, order=1, title="Uno", body_html="<p>x</p>")
        self.pt = Book.objects.create(
            author=author, slug="humility", language="pt", title="Humildade",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Chapter.objects.create(book=self.pt, order=1, title="Um", body_html="<p>x</p>")
        self.client.force_authenticate(user=self.helper, token=VERIFIED)

    def test_batch_decision_cannot_touch_an_out_of_scope_language(self):
        # The exact CRITICAL: a batch item in pt, no top-level language field.
        self.client.post(
            "/api/admin/review-queue/",
            {"items": [{"kind": "book", "slug": "humility", "language": "pt"}], "outcome": "approved"},
            format="json",
        )
        self.pt.refresh_from_db()
        self.assertEqual(self.pt.source_type, self.Book.SourceType.AI_UNREVIEWED)  # NOT flipped

    def test_in_scope_language_is_recorded(self):
        from library.models import ReviewOutcome

        self.client.post(
            "/api/admin/review-queue/",
            {"items": [{"kind": "book", "slug": "humility", "language": "es"}], "outcome": "approved"},
            format="json",
        )
        # In scope → the decision is recorded. This reviewer holds review:act (not
        # approve), so it's PROVISIONAL: recorded but not yet flipped — an approver
        # confirms the flip (see tests_provisional_review).
        outcome = ReviewOutcome.objects.get(kind="book", slug="humility", language="es")
        self.assertTrue(outcome.is_provisional)
        self.es.refresh_from_db()
        self.assertEqual(self.es.source_type, self.Book.SourceType.AI_UNREVIEWED)

    def test_get_queue_is_filtered_to_the_reviewers_languages(self):
        res = self.client.get("/api/admin/review-queue/")
        langs = {r["language"] for r in res.data["results"]}
        self.assertIn("es", langs)
        self.assertNotIn("pt", langs)

    def test_publish_without_a_resolvable_language_fails_closed(self):
        # HIGH: a language-scoped publish endpoint must deny when no language is
        # given rather than defaulting into English.
        AdminGrant.objects.create(email="es@ochorus.com", capability=C.PUBLISH, verb=V.ACT, languages="sw")
        res = self.client.post("/api/admin/import/publish/", {"kind": "book", "title": "X"}, format="json")
        self.assertEqual(res.status_code, 403)


class AdminGrantsCommandTests(TestCase):
    def _run(self, *args):
        out = StringIO()
        call_command("admin_grants", *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_grant_role_creates_the_preset_rows(self):
        self._run("grant", "--email", "r@ochorus.com", "--role", "reviewer", "--languages", "es,pt")
        rows = AdminGrant.objects.filter(email="r@ochorus.com")
        self.assertTrue(rows.exists())
        self.assertTrue(all(r.role_label == "reviewer" for r in rows))
        review = rows.get(capability=C.REVIEW)
        self.assertEqual(review.verb, V.ACT)
        self.assertEqual(review.languages, "es,pt")

    def test_language_admin_gets_a_read_only_language_cockpit(self):
        # The language_admin preset grants LANGUAGE_ADMIN at VIEW — so a language
        # admin can open /admin/languages/<code> — but NOT the act/approve levers
        # (thresholds/settings/create are :act, go-live is :approve), which stay
        # super admin. Guards the preset intent so a future edit can't silently
        # drop the cockpit or over-grant the destructive levers.
        self._run("grant", "--email", "la@ochorus.com", "--role", "language_admin", "--languages", "lg")
        grant = AdminGrant.objects.get(email="la@ochorus.com", capability=C.LANGUAGE_ADMIN)
        self.assertEqual(grant.verb, V.VIEW)
        self.assertTrue(grant.satisfies(V.VIEW))
        self.assertFalse(grant.satisfies(V.ACT))
        self.assertFalse(grant.satisfies(V.APPROVE))
        self.assertTrue(grant.covers_language("lg"))
        self.assertFalse(grant.covers_language("es"))

    def test_revoke_removes_grants(self):
        AdminGrant.objects.create(email="r@ochorus.com", capability=C.REVIEW, verb=V.ACT)
        self._run("revoke", "--email", "r@ochorus.com")
        self.assertFalse(AdminGrant.objects.filter(email="r@ochorus.com").exists())

    @override_settings(ADMIN_EMAILS={"super@ochorus.com"})
    def test_cannot_grant_to_a_super_admin(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self._run("grant", "--email", "super@ochorus.com", "--role", "reviewer")


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class LanguageAdminRestrictionTests(TestCase):
    """The founder decision (2026-09-21): a language admin (any non-super admin)
    reviews content but does not queue translations, import documents, run the
    reader-email section, or see reader emails in the clear. Each lever is gated
    server-side, not merely hidden in the SPA — this exercises the gate."""

    def setUp(self):
        self.client = APIClient()
        self.super = User.objects.create(username="uid-super", email="super@ochorus.com")
        self.la = User.objects.create(username="uid-la", email="la@ochorus.com")

    def _as_super(self):
        self.client.force_authenticate(user=self.super, token=VERIFIED)

    def _as_language_admin(self, *pairs):
        """Authenticate as a non-super admin holding the given (capability, verb)
        grants — a language admin as far as the app is concerned."""
        for cap, verb in pairs:
            AdminGrant.objects.create(email="la@ochorus.com", capability=cap, verb=verb, languages="*")
        self.client.force_authenticate(user=self.la, token=VERIFIED)

    # --- Queueing translation work: super-admin-only ---------------------------
    def test_language_admin_cannot_queue_translations(self):
        # A TRANSLATE/act grant does NOT let a language admin file a job — the POST
        # is reserved to a super admin. (GET is separately language-scoped and
        # already fails closed for a request that names no language, so a scoped
        # grantee doesn't reach the queue list either; the reservation here is the
        # POST guard added in admin_views/jobs.py.)
        self._as_language_admin((C.TRANSLATE, V.ACT))
        res = self.client.post(
            "/api/admin/translation-jobs/",
            {"type": "book", "slug": "x", "language": "es"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_super_admin_may_queue(self):
        self._as_super()
        # The permission passes for a super admin; junk input then fails
        # validation (400) rather than the 403 a language admin hits — proof the
        # gate, not the payload, is what stops the language admin.
        res = self.client.post(
            "/api/admin/translation-jobs/", {"type": "nonsense"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    # --- Import documents: super-admin-only -----------------------------------
    def test_import_is_super_admin_only(self):
        # A PUBLISH grant used to open the import picker; now it does not.
        self._as_language_admin((C.PUBLISH, V.ACT))
        self.assertEqual(self.client.get("/api/admin/import/languages/").status_code, 403)

    def test_super_admin_reaches_import(self):
        self._as_super()
        self.assertEqual(self.client.get("/api/admin/import/languages/").status_code, 200)

    # --- Reader-email broadcast section: super-admin-only ----------------------
    def test_emails_section_is_super_admin_only(self):
        # REPORTING (which every role preset holds) used to open the metrics view.
        self._as_language_admin((C.REPORTING, V.VIEW))
        self.assertEqual(self.client.get("/api/admin/email-metrics/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/broadcasts/").status_code, 403)

    def test_super_admin_reaches_emails(self):
        self._as_super()
        self.assertEqual(self.client.get("/api/admin/email-metrics/").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/broadcasts/").status_code, 200)


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class LanguageAdminManualTests(TestCase):
    """The language-admin manual PDF endpoint — reachable by any admin, denied to
    a signed-in non-admin.

    Its own class on purpose (mirrors AdminManualTests): the reachable test streams
    a real FileResponse and closes it, which fires ``request_finished`` →
    ``close_old_connections()`` and drops this test's DB connection. On Postgres
    that breaks any test that runs AFTER it in the same class (the next ``setUp``
    hits a closed connection), so the file-serving test is kept last (alphabetical
    order puts 'reachable' after 'denied') with nothing following it — exactly how
    AdminManualTests stays green on the Postgres CI run."""

    def setUp(self):
        self.client = APIClient()
        self.la = User.objects.create(username="uid-manual-la", email="la@ochorus.com")

    def test_manual_denied_without_admin_access(self):
        # Signed in, verified, but holds no grant and is not super.
        self.client.force_authenticate(user=self.la, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/language-manual/").status_code, 403)

    def test_manual_reachable_by_any_admin(self):
        # A scoped grant (REPORTING/view, which every role preset holds) reaches it.
        AdminGrant.objects.create(
            email="la@ochorus.com", capability=C.REPORTING, verb=V.VIEW, languages="*"
        )
        self.client.force_authenticate(user=self.la, token=VERIFIED)
        res = self.client.get("/api/admin/language-manual/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        if hasattr(res, "streaming_content"):
            res.close()


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class ReaderEmailMaskingTests(TestCase):
    """Reader emails are PII: a super admin sees them in the clear; a scoped USERS
    grantee (a language admin) gets them masked at the source, across every users
    payload — so the SPA's reveal toggle has nothing to reveal."""

    def setUp(self):
        import uuid

        self.client = APIClient()
        self.super = User.objects.create(username="uid-super2", email="super@ochorus.com")
        self.la = User.objects.create(username="uid-la2", email="la@ochorus.com")
        AdminGrant.objects.create(email="la@ochorus.com", capability=C.USERS, verb=V.VIEW, languages="*")
        # A reader whose address the users payloads will carry.
        self.reader_uid = uuid.uuid4()
        UserProfile.objects.create(
            user=User.objects.create(username=str(self.reader_uid)),
            supabase_uid=self.reader_uid,
            email="reader@example.com",
        )

    def test_super_admin_sees_cleartext(self):
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        recent = self.client.get("/api/admin/users/").data["recent"]
        self.assertEqual(recent[0]["email"], "reader@example.com")
        row = self.client.get("/api/admin/users/directory/").data["results"][0]
        self.assertEqual(row["email"], "reader@example.com")
        detail = self.client.get(f"/api/admin/users/{self.reader_uid}/").data
        self.assertEqual(detail["profile"]["email"], "reader@example.com")

    def test_language_admin_sees_masked(self):
        self.client.force_authenticate(user=self.la, token=VERIFIED)
        recent = self.client.get("/api/admin/users/").data["recent"]
        self.assertNotEqual(recent[0]["email"], "reader@example.com")
        self.assertIn("•", recent[0]["email"])
        self.assertTrue(recent[0]["email"].endswith("@example.com"))
        row = self.client.get("/api/admin/users/directory/").data["results"][0]
        self.assertIn("•", row["email"])
        detail = self.client.get(f"/api/admin/users/{self.reader_uid}/").data
        self.assertIn("•", detail["profile"]["email"])

    def test_directory_csv_masks_for_language_admin(self):
        self.client.force_authenticate(user=self.la, token=VERIFIED)
        res = self.client.get("/api/admin/users/directory/?fmt=csv")
        body = res.content.decode()
        self.assertNotIn("reader@example.com", body)
        self.assertIn("@example.com", body)  # still the masked form

    def test_language_admin_cannot_search_the_cleartext_email(self):
        # The directory search must not be a cleartext oracle: "reader" is the
        # local part (not present in the masked form), so a non-super search on it
        # finds nothing, while a super admin's search still matches.
        self.client.force_authenticate(user=self.la, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/users/directory/?q=reader").data["total"], 0)
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        self.assertEqual(self.client.get("/api/admin/users/directory/?q=reader").data["total"], 1)

    def test_language_admin_sorts_do_not_crash_and_stay_masked(self):
        # Every sort must work for a non-super caller — including the ones whose
        # ordering carries an F()-expression tiebreak ('seen', 'active') that the
        # email-stripping list comprehension filters over. Guards a refactor of
        # SORTS from silently reintroducing an email-ordered oracle or a crash.
        self.client.force_authenticate(user=self.la, token=VERIFIED)
        for sort in ("recent", "seen", "active", "name"):
            res = self.client.get(f"/api/admin/users/directory/?sort={sort}")
            self.assertEqual(res.status_code, 200, sort)
            self.assertIn("•", res.data["results"][0]["email"])
