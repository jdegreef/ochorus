"""Whose words? — the daily quotation game (library.quote_game + its endpoint)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Quote
from .quote_game import (
    CHOICES,
    GAME_EPOCH,
    PoolQuote,
    Writer,
    choices_for,
    puzzle_number,
    quote_for_day,
)

BEFORE = GAME_EPOCH - timedelta(days=30)
#: A server clock well past the early puzzles, so the tests can play them.
LATER = datetime(2027, 6, 1, tzinfo=UTC)


def day(n: int) -> date:
    """Puzzle No. n's date."""
    return GAME_EPOCH + timedelta(days=n - 1)


class ScheduleTests(SimpleTestCase):
    def test_numbering_starts_at_the_epoch(self):
        self.assertEqual(puzzle_number(GAME_EPOCH), 1)
        self.assertEqual(puzzle_number(day(42)), 42)
        self.assertIsNone(quote_for_day([PoolQuote("a", BEFORE)], GAME_EPOCH - timedelta(days=1)))
        self.assertIsNone(quote_for_day([], GAME_EPOCH))

    def test_a_date_always_gets_the_same_quote(self):
        pool = [PoolQuote(f"q{i}", BEFORE) for i in range(30)]
        picks = [quote_for_day(pool, day(n)) for n in range(1, 100)]
        self.assertEqual(picks, [quote_for_day(list(reversed(pool)), day(n)) for n in range(1, 100)])

    def test_a_cycle_deals_every_quote_once(self):
        pool = [PoolQuote(f"q{i}", BEFORE) for i in range(25)]
        for cycle in range(3):
            picks = [quote_for_day(pool, day(cycle * 25 + n)) for n in range(1, 26)]
            self.assertEqual(sorted(picks), sorted(q.slug for q in pool), f"cycle {cycle}")

    def test_cycles_are_dealt_in_different_orders(self):
        pool = [PoolQuote(f"q{i}", BEFORE) for i in range(25)]
        first = [quote_for_day(pool, day(n)) for n in range(1, 26)]
        second = [quote_for_day(pool, day(25 + n)) for n in range(1, 26)]
        self.assertNotEqual(first, second)

    def test_no_quote_on_two_days_running(self):
        pool = [PoolQuote(f"q{i}", BEFORE) for i in range(3)]
        picks = [quote_for_day(pool, day(n)) for n in range(1, 300)]
        self.assertFalse([n for n in range(1, len(picks)) if picks[n] == picks[n - 1]])

    def test_no_writer_two_days_running(self):
        # One writer with a fifth of the pool (Spurgeon's real share is about a
        # sixth): still never back to back, across deals too.
        pool = [PoolQuote(f"s{i}", BEFORE, "spurgeon") for i in range(5)] + [
            PoolQuote(f"o{i}", BEFORE, f"other{i % 5}") for i in range(20)
        ]
        by = {q.slug: q.author for q in pool}
        picks = [by[quote_for_day(pool, day(n))] for n in range(1, 251)]
        self.assertFalse([n for n in range(1, len(picks)) if picks[n] == picks[n - 1]])
        # …and each deal is still every quote once.
        self.assertEqual(
            sorted(quote_for_day(pool, day(n)) for n in range(26, 51)), sorted(by)
        )

    def test_a_new_quote_waits_for_the_next_cycle(self):
        pool = [PoolQuote(f"q{i}", BEFORE) for i in range(20)]
        before = [quote_for_day(pool, day(n)) for n in range(1, 21)]
        # Added on day 5: the deal under way is untouched…
        grown = [*pool, PoolQuote("new", day(5))]
        self.assertEqual([quote_for_day(grown, day(n)) for n in range(1, 21)], before)
        # …and the next one deals it.
        self.assertIn("new", [quote_for_day(grown, day(20 + n)) for n in range(1, 22)])

    def test_a_pool_created_after_the_epoch_is_dealt_whole(self):
        # A fresh database: every row joined "today", after the epoch.
        pool = [PoolQuote(f"q{i}", day(300)) for i in range(5)]
        picks = [quote_for_day(pool, day(n)) for n in range(1, 6)]
        self.assertEqual(sorted(picks), sorted(q.slug for q in pool))


class ChoiceTests(SimpleTestCase):
    WRITERS = [
        Writer("spurgeon", 1834),
        Writer("moody", 1837),
        Writer("ryle", 1816),
        Writer("murray", 1828),
        Writer("bounds", 1835),
        Writer("muller", 1805),
        Writer("augustine", 354),
        Writer("kempis", 1380),
        Writer("unknown", None),
    ]

    def test_the_answer_is_among_four_distinct_writers(self):
        for n in range(1, 40):
            offered = choices_for(self.WRITERS[0], self.WRITERS, day(n))
            self.assertEqual(len(offered), CHOICES)
            self.assertEqual(len(set(offered)), CHOICES)
            self.assertIn("spurgeon", offered)

    def test_decoys_come_from_the_answers_era(self):
        seen = set()
        for n in range(1, 60):
            seen.update(choices_for(self.WRITERS[0], self.WRITERS, day(n)))
        # The six nearest in era (the five Victorians, then Müller and à Kempis):
        # never Augustine, and never a writer with no dates to place them.
        self.assertNotIn("augustine", seen)
        self.assertNotIn("unknown", seen)

    def test_the_right_answer_moves_around(self):
        places = {
            choices_for(self.WRITERS[0], self.WRITERS, day(n)).index("spurgeon")
            for n in range(1, 40)
        }
        self.assertEqual(places, set(range(CHOICES)))

    def test_too_few_writers(self):
        self.assertIsNone(choices_for(self.WRITERS[0], self.WRITERS[:3], GAME_EPOCH))


class QuoteGameApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.writers = []
        for i, (slug, born) in enumerate(
            [("a", 1830), ("b", 1835), ("c", 1840), ("d", 1820), ("e", 1810)]
        ):
            w = Author.objects.create(
                slug=slug, name=f"Writer {slug.upper()}", birth_year=born,
                photo_url=f"https://example.org/{slug}.jpg",
            )
            book = Book.objects.create(author=w, slug=f"bk-{slug}", language="en", title=f"Work {i}")
            ch = Chapter.objects.create(
                book=book, order=1, title="One", body_html="<p>A line.</p>"
            )
            Quote.objects.create(
                slug=f"q-{slug}", author=w, text=f"Line by {slug}.", chapter=ch,
                paragraph=0, reviewed=True,
            )
            self.writers.append((w, ch))

    def get(self, d):
        return self.client.get(f"/api/library/quotes/game/{d}/")

    def test_the_payload(self):
        res = self.get(GAME_EPOCH.isoformat())
        self.assertEqual(res.status_code, 200)
        data = res.data
        self.assertEqual(data["number"], 1)
        self.assertEqual(data["date"], GAME_EPOCH.isoformat())
        slugs = [c["slug"] for c in data["choices"]]
        self.assertEqual(len(slugs), CHOICES)
        self.assertIn(data["answer"], slugs)
        # The quote is the answer's, and carries its source as every quote does.
        self.assertEqual(data["quote"]["slug"], f"q-{data['answer']}")
        self.assertEqual(data["quote"]["source"]["kind"], "chapter")
        self.assertTrue(all(c["photo_url"] for c in data["choices"]))
        # Same date, same puzzle.
        self.assertEqual(self.get(GAME_EPOCH.isoformat()).data, data)

    def test_only_reviewed_quotes_by_writers_with_portraits(self):
        Quote.objects.filter(author__slug__in=["b", "c"]).update(reviewed=False)
        Author.objects.filter(slug="d").update(photo_url="")
        # a and e remain: too few writers to offer four faces.
        self.assertEqual(self.get(GAME_EPOCH.isoformat()).status_code, 404)
        Quote.objects.filter(author__slug__in=["b", "c"]).update(reviewed=True)
        seen = set()
        for n in range(1, 9):
            with mock.patch("django.utils.timezone.now", return_value=LATER):
                data = self.get(day(n).isoformat()).data
            seen.add(data["answer"])
            self.assertNotIn("d", [c["slug"] for c in data["choices"]])
        self.assertEqual(seen, {"a", "b", "c", "e"})

    def test_out_of_range_and_malformed_dates(self):
        today = timezone.now().date()
        for d in (
            (GAME_EPOCH - timedelta(days=1)).isoformat(),
            (today + timedelta(days=2)).isoformat(),
            "11-11",
            "not-a-date",
        ):
            with self.subTest(d=d):
                self.assertEqual(self.get(d).status_code, 404)
        self.assertEqual(self.get((today + timedelta(days=1)).isoformat()).status_code, 200)

    def test_a_quote_created_mid_cycle_does_not_change_today(self):
        # Every row was created "now", after the epoch — so the first deal is
        # the whole pool. A sixth writer added later must not reshuffle it once
        # the earlier rows predate the cycle.
        Quote.objects.update(created_at=datetime(2026, 1, 1, tzinfo=UTC))
        first = self.get(GAME_EPOCH.isoformat()).data["quote"]["slug"]
        w = Author.objects.create(slug="f", name="Writer F", birth_year=1831, photo_url="https://x/f.jpg")
        book = Book.objects.create(author=w, slug="bk-f", language="en", title="Work F")
        ch = Chapter.objects.create(book=book, order=1, title="One", body_html="<p>A line.</p>")
        Quote.objects.create(slug="q-f", author=w, text="Line by f.", chapter=ch, paragraph=0, reviewed=True)
        self.assertEqual(self.get(GAME_EPOCH.isoformat()).data["quote"]["slug"], first)
