"""Triage of unanswered searches: deciding, undoing, scope, and reopening."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AdminCapability as C
from accounts.models import AdminGrant
from accounts.models import AdminVerb as V

from .models import AdminAction, SearchDecision, SearchQueryLog
from .search_triage import REOPEN_GRACE

VERIFIED = {"email_verified": True}
DECIDE = "/api/admin/search-decisions/decide/"


def miss(query, language="es", days_ago=0):
    row = SearchQueryLog.objects.create(query=query, language=language, result_count=0)
    SearchQueryLog.objects.filter(pk=row.pk).update(
        created_at=timezone.now() - timedelta(days=days_ago)
    )


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class SearchTriageTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.super = User.objects.create(username="uid-super", email="super@ochorus.com")
        self.la = User.objects.create(username="uid-la", email="la@ochorus.com")
        self.client = APIClient()

    def as_super(self):
        self.client.force_authenticate(user=self.super, token=VERIFIED)

    def as_language_admin(self, languages="es", verb=V.ACT):
        AdminGrant.objects.create(
            email="la@ochorus.com", capability=C.TRANSLATE, verb=verb, languages=languages
        )
        AdminGrant.objects.create(
            email="la@ochorus.com", capability=C.REPORTING, verb=V.VIEW, languages=languages
        )
        self.client.force_authenticate(user=self.la, token=VERIFIED)

    def decide(self, query, outcome, language="es", **extra):
        return self.client.post(
            DECIDE, {"query": query, "language": language, "outcome": outcome, **extra}, format="json"
        )

    def unanswered(self):
        res = self.client.get("/api/admin/search-stats/")
        return {
            (lang["code"], q["query"]): q
            for lang in res.data["unanswered_by_language"]
            for q in lang["queries"]
        }

    def test_a_decided_query_leaves_the_open_list(self):
        miss("reavivamiento")
        miss("esperando en dios")
        self.as_super()
        self.assertIn(("es", "reavivamiento"), self.unanswered())

        res = self.decide("  Reavivamiento ", "wanted", note="no Spanish revival books yet")
        self.assertEqual(res.status_code, 201)
        open_now = self.unanswered()
        self.assertNotIn(("es", "reavivamiento"), open_now)
        self.assertIn(("es", "esperando en dios"), open_now)
        # Stored folded, with who and why, and audited.
        d = SearchDecision.objects.get()
        self.assertEqual((d.query, d.decided_by, d.note), ("reavivamiento", "super@ochorus.com", "no Spanish revival books yet"))
        self.assertEqual(AdminAction.objects.get().action, AdminAction.Action.SEARCH_DECIDE)

    def test_deciding_again_replaces_the_outcome_and_undo_reopens(self):
        miss("c s lewis", language="en")
        self.as_super()
        self.decide("c s lewis", "wanted", language="en")
        self.assertEqual(self.decide("c s lewis", "out_of_scope", language="en").status_code, 200)
        self.assertEqual(SearchDecision.objects.get().outcome, "out_of_scope")

        res = self.client.delete(f"{DECIDE}?query=c%20s%20lewis&language=en")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(SearchDecision.objects.exists())
        self.assertIn(("en", "c s lewis"), self.unanswered())
        self.assertEqual(
            self.client.delete(f"{DECIDE}?query=c%20s%20lewis&language=en").status_code, 404
        )

    def test_list_reports_what_happened_since(self):
        self.as_super()
        self.decide("reavivamiento", "wanted")
        miss("reavivamiento")
        miss("reavivamiento")
        SearchQueryLog.objects.create(query="Reavivamiento", language="es", result_count=4)
        miss("reavivamiento", language="pt")  # another language's search
        [row] = self.client.get("/api/admin/search-decisions/").data["decisions"]
        self.assertEqual((row["searches_since"], row["misses_since"]), (3, 2))
        self.assertEqual(row["outcome_label"], "Wanted")
        self.assertFalse(row["reopened"])  # wanted never reopens: misses are expected

    def test_a_translation_that_keeps_missing_reopens_after_the_grace_period(self):
        self.as_super()
        self.decide("esperando en dios", "translate", target="book:waiting-on-god")
        SearchDecision.objects.update(decided_at=timezone.now() - REOPEN_GRACE - timedelta(days=3))
        miss("esperando en dios", days_ago=5)  # inside the grace period: proves nothing
        self.assertNotIn(("es", "esperando en dios"), self.unanswered())
        miss("esperando en dios", days_ago=1)
        miss("esperando en dios", days_ago=0)
        row = self.unanswered()[("es", "esperando en dios")]
        self.assertTrue(row["reopened"]["reopened"])
        self.assertEqual(row["reopened"]["target"], "book:waiting-on-god")

    def test_bad_input_is_refused(self):
        self.as_super()
        self.assertEqual(self.decide("ab", "wanted").status_code, 400)
        self.assertEqual(self.decide("reavivamiento", "delete_everything").status_code, 400)
        self.assertEqual(self.decide("reavivamiento", "wanted", language="").status_code, 400)

    def test_language_admin_triages_only_their_language(self):
        self.as_language_admin(languages="es")
        self.assertEqual(self.decide("reavivamiento", "wanted").status_code, 201)
        self.assertEqual(self.decide("grace", "wanted", language="fr").status_code, 403)
        SearchDecision.objects.create(
            query="grâce", language="fr", outcome="wanted", decided_at=timezone.now()
        )
        listed = self.client.get("/api/admin/search-decisions/").data["decisions"]
        self.assertEqual([d["language"] for d in listed], ["es"])

    def test_queueing_a_translation_stays_super_admin_only(self):
        self.as_language_admin(languages="es")
        self.assertEqual(self.decide("esperando en dios", "translate").status_code, 403)
        self.assertFalse(SearchDecision.objects.exists())

    def test_a_language_admin_cannot_replace_or_undo_a_queued_translation(self):
        SearchDecision.objects.create(
            query="esperando en dios", language="es", outcome="translate",
            target="book:waiting-on-god", decided_at=timezone.now(),
        )
        self.as_language_admin(languages="es")
        self.assertEqual(self.decide("esperando en dios", "out_of_scope").status_code, 403)
        self.assertEqual(
            self.client.delete(f"{DECIDE}?query=esperando%20en%20dios&language=es").status_code, 403
        )
        self.assertEqual(SearchDecision.objects.get().outcome, "translate")

    def test_the_language_total_counts_only_what_is_still_open(self):
        for _ in range(3):
            miss("reavivamiento")
        miss("esperando en dios")
        self.as_super()
        self.decide("reavivamiento", "wanted")
        res = self.client.get("/api/admin/search-stats/")
        [es] = res.data["unanswered_by_language"]
        self.assertEqual(es["total"], 1)

    def test_a_suggest_grant_can_look_but_not_decide(self):
        self.as_language_admin(languages="es", verb=V.SUGGEST)
        self.assertEqual(self.decide("reavivamiento", "wanted").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/search-decisions/").status_code, 200)


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class SearchRulesTests(TestCase):
    """Synonyms and pins: the two outcomes that change what readers get back."""

    def setUp(self):
        from .models import Author, Book, Chapter

        User = get_user_model()
        self.super = User.objects.create(username="uid-super", email="super@ochorus.com")
        self.client = APIClient()
        author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        self.book = Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(
            book=self.book, order=1, title="The Glory of the Creature",
            body_html="<p>Humility is the place of entire dependence on God.</p>",
        )

    def search(self, q, **extra):
        res = self.client.get("/api/library/search/", {"q": q, "language": "en", **extra})
        self.assertEqual(res.status_code, 200)
        return res.data

    def decide(self, query, outcome, target, language="en"):
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        res = self.client.post(
            DECIDE,
            {"query": query, "language": language, "outcome": outcome, "target": target},
            format="json",
        )
        self.client.force_authenticate(user=None)
        return res

    def test_a_synonym_runs_the_search_on_its_word_and_says_so(self):
        self.assertEqual(self.search("meekness")["results"], [])
        self.assertEqual(self.decide("Meekness", "synonym", " Humility ").status_code, 201)
        data = self.search("meekness")
        self.assertEqual(data["query"], "meekness")
        self.assertEqual(data["searched_for"], "humility")
        self.assertIn("humility", {h.get("book_slug") for h in data["results"]})
        # Logged as the reader's own word, now answered.
        self.assertGreater(SearchQueryLog.objects.get(query="meekness", result_count__gt=0).result_count, 0)
        # One-way: the synonym's word is untouched.
        self.assertNotIn("searched_for", self.search("humility"))

    def test_a_pin_leads_the_results_once(self):
        before = self.search("dependence")["results"]
        self.assertTrue(before)
        self.assertEqual(self.decide("dependence", "pinned", "book:humility").status_code, 201)
        results = self.search("dependence")["results"]
        self.assertEqual((results[0]["type"], results[0]["book_slug"], results[0]["pinned"]), ("book", "humility", True))
        self.assertEqual(sum(1 for h in results if h["type"] == "book"), 1)

    def test_a_pin_to_an_unpublished_page_does_nothing(self):
        self.assertEqual(self.decide("dependence", "pinned", "book:humility").status_code, 201)
        type(self.book).objects.filter(pk=self.book.pk).update(is_published=False)
        self.assertFalse(any(h.get("pinned") for h in self.search("dependence")["results"]))

    def test_rules_do_not_apply_inside_a_scope(self):
        self.decide("meekness", "synonym", "humility")
        data = self.search("meekness", **{"in": "author:andrew-murray"})
        self.assertNotIn("searched_for", data)

    def test_bad_synonyms_and_pins_are_refused(self):
        self.assertEqual(self.decide("meekness", "synonym", "Meekness").status_code, 400)
        self.assertEqual(self.decide("meekness", "synonym", "").status_code, 400)
        self.assertEqual(self.decide("dependence", "pinned", "book:no-such-book").status_code, 400)
        self.assertEqual(self.decide("dependence", "pinned", "chapter:humility").status_code, 400)
        self.assertEqual(self.decide("dependence", "pinned", "book:humility", language="es").status_code, 400)
        self.assertFalse(SearchDecision.objects.exists())

    def test_a_synonym_that_still_misses_reopens_at_once(self):
        self.decide("meekness", "synonym", "nothing-matches-this")
        self.search("meekness")
        self.search("meekness")
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        [row] = self.client.get("/api/admin/search-decisions/").data["decisions"]
        self.assertTrue(row["reopened"])

    def test_a_pin_reports_opens_and_leaves_the_unopened_list(self):
        from .models import SearchClickLog

        for _ in range(3):
            self.search("dependence")
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        unopened = self.client.get("/api/admin/search-stats/").data["unopened_queries"]
        self.assertIn({"query": "dependence", "language": "en", "count": 3}, unopened)

        self.decide("dependence", "pinned", "book:humility")
        SearchClickLog.objects.create(query="Dependence", language="en", result_type="book", position=1)
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        res = self.client.get("/api/admin/search-stats/")
        self.assertNotIn("dependence", [r["query"] for r in res.data["unopened_queries"]])
        [row] = self.client.get("/api/admin/search-decisions/").data["decisions"]
        self.assertEqual((row["opens_since"], row["reopened"]), (1, False))

    def test_the_admin_preview_searches_without_logging_or_rules(self):
        self.decide("meekness", "synonym", "humility")
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        res = self.client.get("/api/admin/search-preview/", {"q": "meekness", "language": "en"})
        self.assertEqual((res.status_code, res.data["results"]), (200, []))
        res = self.client.get("/api/admin/search-preview/", {"q": "humility", "language": "en"})
        self.assertTrue(res.data["results"])
        self.assertFalse(SearchQueryLog.all_rows.exists())

    def test_a_pin_leads_its_facet_page_and_counts_in_its_total(self):
        from .models import Author, Book

        other = Book.objects.create(
            author=Author.objects.get(), slug="absolute-surrender", language="en",
            title="Absolute Surrender",
        )
        self.decide("dependence", "pinned", f"book:{other.slug}")
        data = self.search("dependence")
        self.assertEqual(data["results"][0]["book_slug"], other.slug)
        # "dependence" matches only chapter text, so the pinned book is the one
        # book: its group's total counts it.
        self.assertEqual(data["totals"]["book"], 1)
        page = self.search("dependence", type="book")
        self.assertEqual(page["results"][0]["book_slug"], other.slug)
        self.assertTrue(page["results"][0]["pinned"])

    def test_a_pin_whose_page_goes_reopens(self):
        self.decide("dependence", "pinned", "book:humility")
        self.book.is_published = False
        self.book.save()
        self.search("dependence")
        self.search("dependence")
        self.client.force_authenticate(user=self.super, token=VERIFIED)
        [row] = self.client.get("/api/admin/search-decisions/").data["decisions"]
        self.assertTrue(row["reopened"])

    def test_the_audit_log_records_where_readers_were_sent(self):
        self.decide("meekness", "synonym", "humility")
        action = AdminAction.objects.get()
        self.assertEqual((action.target, action.detail), ("en:meekness", {"outcome": "synonym", "to": "humility"}))
