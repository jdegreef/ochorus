"""The dashboard's trends endpoint (``/api/admin/trends/``): the reader pulse,
Level 1 progress per language, and the AI-translation review backlog."""

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    Author,
    Book,
    Language,
    LanguageHealthSnapshot,
    ReviewOutcome,
    SearchQueryLog,
    Sermon,
)

AI_UNREVIEWED = Book.SourceType.AI_UNREVIEWED


@override_settings(DEBUG=True)
class AdminTrendsTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        now = timezone.now()
        # Two unreviewed Swahili books, one older; one already reviewed.
        old = Book.objects.create(
            author=self.author,
            slug="old",
            language="sw",
            title="Zamani",
            source_type=AI_UNREVIEWED,
        )
        Book.objects.create(
            author=self.author,
            slug="new",
            language="sw",
            title="Mpya",
            source_type=AI_UNREVIEWED,
        )
        Book.objects.create(
            author=self.author,
            slug="done",
            language="sw",
            title="Imekamilika",
            source_type=Book.SourceType.AI_REVIEWED,
        )
        Book.objects.filter(pk=old.pk).update(created_at=now - timedelta(days=40))
        # A retired duplicate is waiting forever — never in the backlog.
        Book.objects.create(
            author=self.author,
            slug="lord-teach-us-to-pray-2",
            language="sw",
            title="Retired",
            source_type=AI_UNREVIEWED,
        )
        Sermon.objects.create(
            author=self.author,
            slug="s",
            language="es",
            title="Sermón",
            body_html="<p>x</p>",
            source_type=AI_UNREVIEWED,
        )
        # One confirmed approval this week; a provisional one doesn't count yet.
        ReviewOutcome.objects.create(
            kind="book",
            slug="done",
            language="sw",
            outcome=ReviewOutcome.Outcome.APPROVED,
            confirmed_at=now,
        )
        ReviewOutcome.objects.create(
            kind="book",
            slug="new",
            language="sw",
            outcome=ReviewOutcome.Outcome.APPROVED,
        )
        # Searches that found nothing: two this week, one the week before.
        for days in (1, 2, 9):
            log = SearchQueryLog.objects.create(
                query=f"q{days}", language="en", result_count=0
            )
            SearchQueryLog.objects.filter(pk=log.pk).update(
                created_at=now - timedelta(days=days)
            )
        SearchQueryLog.objects.create(query="found", language="en", result_count=3)

    def get(self):
        res = APIClient().get("/api/admin/trends/")
        self.assertEqual(res.status_code, 200, res.content)
        return res.data

    def test_review_backlog(self):
        review = self.get()["review"]
        self.assertEqual(
            review["waiting"], 3
        )  # two books + one sermon, not the retired one
        self.assertEqual(
            (review["oldest"]["slug"], review["oldest"]["kind"]), ("old", "book")
        )
        self.assertEqual(len(review["weeks"]), 8)
        self.assertEqual(review["approved"][-1], 1)  # confirmed only
        # Every AI edition in the 8 charted weeks (56 days, so the 40-day-old
        # one counts), reviewed or not — but never the retired duplicate.
        self.assertEqual(sum(review["arrived"]), 4)

    def test_pulse_compares_the_last_seven_days_with_the_seven_before(self):
        zero = self.get()["pulse"]["zero_searches"]
        self.assertEqual((zero["d7"], zero["d7_prev"]), (2, 1))
        self.assertEqual(zero["d30"], 3)
        self.assertEqual(sum(zero["weekly"]), 3)

    def test_languages_carry_level1_review_share_and_health(self):
        LanguageHealthSnapshot.objects.create(
            language="sw",
            date=timezone.localdate() - timedelta(days=1),
            score_version=3,
            health=40,
            readiness=0.5,
            coverage=0.1,
            review=0.2,
            engagement=0.0,
        )
        rows = {r["code"]: r for r in self.get()["languages"]}
        self.assertNotIn("en", rows)  # the source language has no target
        sw = rows["sw"]
        self.assertEqual((sw["ai_translations"], sw["unreviewed"]), (3, 2))
        self.assertEqual(sw["reviewed_share"], round(1 / 3, 3))
        self.assertEqual(sw["health"], [40])
        self.assertIn("done", sw["level1"])
        # A language with no AI translations has no share, rather than 0%.
        no_ai = next(r for r in rows.values() if r["ai_translations"] == 0)
        self.assertIsNone(no_ai["reviewed_share"])

    def test_the_dashboard_never_writes_a_health_snapshot(self):
        before = LanguageHealthSnapshot.objects.count()
        self.get()
        self.assertEqual(LanguageHealthSnapshot.objects.count(), before)

    def test_source_language_is_never_listed(self):
        Language.objects.filter(code="en").update(is_source=True)
        self.assertNotIn("en", {r["code"] for r in self.get()["languages"]})
