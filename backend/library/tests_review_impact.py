"""Reader-impact ranking of the review queue (library.review_impact).

Native reviewers are few and the queue holds hundreds of editions, so the
default order is what readers actually read: measured readers of the edition,
else the English edition's readers scaled by the language's share of readers.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AdminCapability, AdminGrant, AdminVerb, UserProfile
from reading.models import ReadingProgress

from .models import Author, Book, Chapter, Sermon
from .review_impact import RECENT_DAYS, WINDOW_DAYS, activity, edition_impact

User = get_user_model()
VERIFIED = {"email_verified": True}


def _reader(locale="en"):
    return UserProfile.objects.create(
        user=User.objects.create(username=str(uuid.uuid4())),
        supabase_uid=uuid.uuid4(),
        locale=locale,
    )


def _read(profile, slug, language, *, kind="book", days_ago=0):
    p = ReadingProgress.objects.create(profile=profile, kind=kind, book_slug=slug, language=language)
    if days_ago:
        # updated_at is auto_now: backdate past save().
        ReadingProgress.objects.filter(pk=p.pk).update(updated_at=timezone.now() - timedelta(days=days_ago))
    return p


class EditionImpactTests(TestCase):
    def test_measured_readers_with_recent_counted_twice(self):
        _read(_reader("sw"), "humility", "sw")  # recent: counts 2
        _read(_reader("sw"), "humility", "sw", days_ago=RECENT_DAYS + 5)  # window only: 1
        _read(_reader("sw"), "humility", "sw", days_ago=WINDOW_DAYS + 5)  # outside: 0
        out, _ = edition_impact([("book", "humility", "sw")])
        imp = out[("book", "humility", "sw")]
        self.assertEqual((imp["readers"], imp["readers_recent"]), (2, 1))
        self.assertEqual(imp["score"], activity(2, 1))
        self.assertEqual(imp["basis"], "readers")

    def test_no_data_falls_back_to_english_times_language_share(self):
        # Four active readers: three English-site, one Swahili-site → sw share ¼.
        for _ in range(3):
            _read(_reader("en"), "humility", "en")  # en edition: 3 recent → 6
        _read(_reader("sw"), "other-book", "sw")
        out, share = edition_impact([("book", "humility", "sw")])
        self.assertAlmostEqual(share["sw"], 0.25)
        imp = out[("book", "humility", "sw")]
        self.assertEqual(imp["basis"], "estimate")
        self.assertEqual(imp["en_score"], 6)
        self.assertEqual(imp["score"], 1.5)

    def test_a_measured_reader_beats_the_projection_basis(self):
        for _ in range(3):
            _read(_reader("en"), "humility", "en")
        _read(_reader("sw"), "humility", "sw", days_ago=RECENT_DAYS + 1)
        imp = edition_impact([("book", "humility", "sw")])[0][("book", "humility", "sw")]
        self.assertEqual((imp["basis"], imp["score"]), ("readers", 1.0))

    def test_no_signal_at_all_is_zero(self):
        imp = edition_impact([("sermon", "nobody", "sw")])[0][("sermon", "nobody", "sw")]
        self.assertEqual((imp["score"], imp["basis"]), (0.0, "none"))

    def test_kinds_do_not_bleed_into_each_other(self):
        # A sermon and a book may share a slug; progress is keyed by kind too.
        _read(_reader("sw"), "waiting", "sw", kind="sermon")
        out, _ = edition_impact([("book", "waiting", "sw"), ("sermon", "waiting", "sw")])
        self.assertEqual(out[("book", "waiting", "sw")]["readers"], 0)
        self.assertEqual(out[("sermon", "waiting", "sw")]["readers"], 1)

    def test_two_queries_whatever_the_size(self):
        for i in range(15):
            _read(_reader("sw"), f"book-{i}", "sw")
        editions = [("book", f"book-{i}", lang) for i in range(15) for lang in ("sw", "es", "pt")]
        with self.assertNumQueries(2):
            edition_impact(editions)


@override_settings(DEBUG=False, ADMIN_EMAILS={"super@ochorus.com"})
class ReviewQueueImpactTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("admin-review-queue")
        author = Author.objects.create(slug="am", name="Andrew Murray")
        # Three Swahili books and one Spanish sermon awaiting review, created
        # oldest-first in the order impact should NOT follow.
        for slug in ("quiet", "middling", "popular"):
            for lang, st in (("en", Book.SourceType.PUBLIC_DOMAIN), ("sw", Book.SourceType.AI_UNREVIEWED)):
                b = Book.objects.create(author=author, slug=slug, language=lang, title=f"{slug} {lang}", source_type=st)
                Chapter.objects.create(book=b, order=1, title="One", body_html="<p>x</p>")
        Sermon.objects.create(
            author=author, slug="possibilities", language="es", title="Posibilidades",
            body_html="<p>uno</p>", source_type=Book.SourceType.AI_UNREVIEWED,
        )
        for _ in range(3):
            _read(_reader("sw"), "popular", "sw")
        _read(_reader("sw"), "middling", "sw")
        # "quiet" has no Swahili readers but one English one → an estimate below
        # every measured edition.
        _read(_reader("en"), "quiet", "en")

        cls.superu = User.objects.create(username=str(uuid.uuid4()), email="super@ochorus.com")
        cls.sw_reviewer = User.objects.create(username=str(uuid.uuid4()), email="sw-rev@ochorus.com")
        AdminGrant.objects.create(
            email="sw-rev@ochorus.com", capability=AdminCapability.REVIEW,
            verb=AdminVerb.VIEW, languages="sw", role_label="reviewer",
        )
        cls.stranger = User.objects.create(username=str(uuid.uuid4()), email="reader@example.com")

    def _get(self, user, **params):
        c = APIClient()
        c.force_authenticate(user=user, token=VERIFIED)
        return c.get(self.url, params)

    def test_default_order_is_reader_impact(self):
        data = self._get(self.superu, language="sw").json()
        self.assertEqual([r["slug"] for r in data["results"]], ["popular", "middling", "quiet"])
        top = data["results"][0]["impact"]
        self.assertEqual((top["basis"], top["readers"], top["score"]), ("readers", 3, 6.0))
        self.assertEqual(data["results"][2]["impact"]["basis"], "estimate")
        self.assertIn("explanation", data["impact"])
        self.assertEqual(data["impact"]["window_days"], WINDOW_DAYS)

    def test_oldest_sort_still_available(self):
        data = self._get(self.superu, language="sw", sort="oldest").json()
        self.assertEqual([r["slug"] for r in data["results"]], ["quiet", "middling", "popular"])

    def test_next_n_is_the_top_of_the_impact_order(self):
        data = self._get(self.superu, language="sw", next=2, sort="oldest").json()
        self.assertEqual([r["slug"] for r in data["results"]], ["popular", "middling"])
        self.assertEqual((data["next"], data["filtered"], data["pages"]), (2, 2, 1))

    def test_next_is_capped_and_tolerates_junk(self):
        self.assertEqual(self._get(self.superu, next=10_000).json()["next"], 50)
        self.assertEqual(self._get(self.superu, next="ten").json()["next"], 0)

    def test_a_scoped_reviewer_sees_only_their_languages_scores(self):
        res = self._get(self.sw_reviewer)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual({r["language"] for r in data["results"]}, {"sw"})
        self.assertLessEqual(set(data["impact"]["language_share"]), {"sw"})

    def test_non_admins_are_refused(self):
        self.assertEqual(self._get(self.stranger).status_code, 403)
        self.assertIn(APIClient().get(self.url).status_code, (401, 403))

    def test_queries_do_not_grow_with_readers(self):
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self._get(self.superu, language="sw").status_code, 200)
            return len(ctx.captured_queries)

        before = count()
        for i in range(20):
            _read(_reader("sw"), "popular" if i % 2 else f"elsewhere-{i}", "sw")
        with self.assertNumQueries(before):
            self.assertEqual(self._get(self.superu, language="sw").status_code, 200)
