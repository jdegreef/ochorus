"""The year-long devotionals' daily entries — ``library/daily_readings.py``.

The days are read off the body by shape, so the gate that matters is the
fixture one: every shipped edition of every dated book must yield twelve
months of in-range, strictly increasing days. The API tests pin the day page's
payload (/api/library/books/<slug>/daily/<MM-DD>/) and the Today shelf's
(/api/library/daily/<MM-DD>/).
"""

from __future__ import annotations

import calendar
import json
from pathlib import Path

from django.core.management import call_command
from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase

from emails.plan_reminders import _reading_title, day_path

from . import daily_readings
from .daily_readings import DATED_BOOKS, DatedBook, blocks, month_entries, parse_date
from .models import Author, Book, Chapter, Plan, PlanDay
from .plan_seed import DAILY_PLANS
from .quote_blocks import served_block_texts

BOOKS_DIR = Path(__file__).parent / "fixtures" / "content" / "books"

#: Dates the source itself lacks; the reader is shown the day before. Listed so
#: a NEW gap — an import or a correction eating a day — fails here instead.
KNOWN_GAPS = {
    "days-of-heaven-upon-earth": {(2, 29)},
    "thoughts-for-the-quiet-hour": {(2, 29), (10, 3)},
    "our-daily-walk": {(9, 22)},
}


H3 = DatedBook()
CHEQUE = DATED_BOOKS["cheque-book"]


def _month_body(days):
    return "".join(f"<h3>January {d}</h3><p>Text for day {d}.</p><p>More {d}.</p>" for d in days)


def _entries(body, spec=H3):
    return month_entries(blocks(body), spec)


class FixtureGateTests(SimpleTestCase):
    def test_every_dated_edition_has_a_whole_year(self):
        for slug, spec in DATED_BOOKS.items():
            files = sorted(BOOKS_DIR.glob(f"{slug}.*.json"))
            self.assertTrue(files, f"{slug}: no fixture file")
            for path in files:
                rows = json.loads(path.read_text(encoding="utf-8"))
                bodies = {r["fields"]["order"]: r["fields"]["body_html"] for r in rows[1:]}
                with self.subTest(edition=path.name):
                    missing = set()
                    for month in range(1, 13):
                        body = bodies.get(daily_readings.chapter_order(slug, month), "")
                        els = blocks(body)
                        # The index is taken on the stored body; the reader counts
                        # the served one. Annotation must not add or drop a block.
                        self.assertEqual(len(els), len(served_block_texts(body)), f"month {month}")
                        days = [e.day for e in month_entries(els, spec)]
                        self.assertEqual(days, sorted(set(days)), f"month {month} out of order")
                        last = calendar.monthrange(daily_readings._LEAP, month)[1]
                        self.assertTrue(days and days[-1] <= last, f"month {month}: {days[-1:]}")
                        missing |= {(month, d) for d in range(1, last + 1)} - {
                            (month, d) for d in days
                        }
                    self.assertEqual(missing, KNOWN_GAPS.get(slug, set()))


class ParsingTests(SimpleTestCase):
    def test_entries_run_from_marker_to_marker(self):
        entries = _entries(_month_body([1, 2, 3]))
        self.assertEqual([(e.day, e.start, e.end) for e in entries], [(1, 0, 3), (2, 3, 6), (3, 6, 9)])
        self.assertEqual(entries[0].label, "January 1")
        self.assertEqual(entries[0].excerpt, "Text for day 1.")

    def test_a_heading_without_a_number_is_not_a_day(self):
        body = "<h3>Dedication</h3><p>Sweet friends.</p>" + _month_body([1])
        self.assertEqual([e.day for e in _entries(body)], [1])

    def test_a_verse_reference_is_not_a_marker(self):
        body = "<h3>January 1</h3><p>x</p><h3>John 3:16</h3><p>y</p>"
        self.assertEqual([e.end for e in _entries(body)], [4])

    def test_the_cheque_books_shape(self):
        body = (
            "<p>Jan. 1</p> <h3>THE BIBLE'S FIRST PROMISE</h3> <p>\"And I will put enmity.\" Gen. 3:15</p>"
            "<p>Jan. 2</p> <h3>FROM CONQUEST TO REST</h3> <p>Rest.</p>"
        )
        first = _entries(body, CHEQUE)[0]
        self.assertEqual((first.label, first.heading), ("Jan. 1", "The Bible's First Promise"))
        self.assertEqual(first.excerpt, '"And I will put enmity." Gen. 3:15')

    def test_the_day_page_body_leaves_out_the_heading(self):
        body = "<p>Jan. 1</p> <h3>A PROMISE</h3> <p>Verse.</p><p>Jan. 2</p>"
        entry = _entries(body, CHEQUE)[0]
        self.assertEqual(entry.body_start, 2)
        self.assertEqual(str(blocks(body)[entry.body_start]), "<p>Verse.</p>")

    def test_a_poems_line_breaks_are_spaces(self):
        body = "<h3>January 1</h3><p>Lord, what I once had done<br/>Had I been true</p>"
        self.assertEqual(_entries(body)[0].excerpt, "Lord, what I once had done Had I been true")

    def test_a_bold_title_line_is_the_heading(self):
        body = "<h3>January 1</h3><p><b>MAKING A FRESH START</b></p><p>We can all start afresh!</p>"
        entry = _entries(body, DATED_BOOKS["our-daily-walk"])[0]
        self.assertEqual((entry.heading, entry.excerpt), ("Making a Fresh Start", "We can all start afresh!"))
        split = "<h3>January 1</h3><p><b>MAKING A</b> <b>FRESH START</b></p><p>Text.</p>"
        self.assertEqual(_entries(split, DATED_BOOKS["our-daily-walk"])[0].heading, "Making a Fresh Start")
        half = "<h3>January 1</h3><p><b>Lord,</b> keep me.</p>"
        self.assertEqual(_entries(half, DATED_BOOKS["our-daily-walk"])[0].heading, "")
        # Only where the book sets its titles that way: elsewhere a bold line
        # is the day's text.
        self.assertEqual(_entries(body)[0].heading, "")

    def test_an_uncased_script_is_left_alone(self):
        body = "<h3>ጃንዋሪ 1</h3><h4>እንደ ገና መጀመር</h4><p>ሁላችንም</p>"
        self.assertEqual(_entries(body)[0].heading, "እንደ ገና መጀመር")

    def test_dates(self):
        self.assertEqual(parse_date("02-29"), (2, 29))
        for bad in ("2-9", "13-01", "02-30", "00-10", "today", ""):
            self.assertIsNone(parse_date(bad), bad)

    def test_neighbours_wrap_the_year(self):
        self.assertEqual(daily_readings.neighbours(1, 1), ("12-31", "01-02"))
        self.assertEqual(daily_readings.neighbours(2, 28), ("02-27", "02-29"))
        self.assertEqual(daily_readings.neighbours(12, 31), ("12-30", "01-01"))
        self.assertEqual(daily_readings.neighbours(12, 1), ("11-30", "12-02"))
        self.assertEqual(daily_readings.neighbours(3, 1), ("02-29", "03-02"))


class _DatedBooks:
    """A dated book in the test DB: twelve month chapters, a marker a day."""

    def setUp(self):
        super().setUp()
        self.author = Author.objects.create(slug="a-b-simpson", name="A. B. Simpson")

    def book(self, slug="days-of-heaven-upon-earth", language="en", *, missing=frozenset({(2, 29)})):
        book = Book.objects.create(
            author=self.author, slug=slug, language=language, title=f"{slug} {language}"
        )
        for month in range(1, 13):
            last = calendar.monthrange(daily_readings._LEAP, month)[1]
            Chapter.objects.create(
                book=book,
                order=daily_readings.chapter_order(slug, month),
                title=calendar.month_name[month],
                body_html=_month_body(d for d in range(1, last + 1) if (month, d) not in missing),
            )
        return book


class DailyApiTests(_DatedBooks, TestCase):
    DAY = "/api/library/books/{}/daily/{}/?language={}"
    SHELF = "/api/library/daily/{}/?language={}"

    def test_the_day_page(self):
        self.book()
        res = self.client.get(self.DAY.format("days-of-heaven-upon-earth", "10-30", "en"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["book"]["slug"], "days-of-heaven-upon-earth")
        self.assertEqual((data["date"], data["requested"]), ("10-30", "10-30"))
        self.assertEqual((data["chapter"], data["paragraph"]), (10, 29 * 3))
        self.assertEqual((data["prev"], data["next"]), ("10-29", "10-31"))
        self.assertEqual(data["html"], "<p>Text for day 30.</p><p>More 30.</p>")

    def test_a_missing_day_is_the_day_before(self):
        self.book()
        data = self.client.get(self.DAY.format("days-of-heaven-upon-earth", "02-29", "en")).json()
        self.assertEqual((data["date"], data["requested"]), ("02-28", "02-29"))
        # Stepping runs from the date ASKED: from the shown 28th, "next" would
        # be the 29th again — a loop.
        self.assertEqual((data["prev"], data["next"]), ("02-28", "03-01"))

    def test_the_walk_back_crosses_the_year(self):
        self.book(missing={(1, 1), (2, 29)})
        data = self.client.get(self.DAY.format("days-of-heaven-upon-earth", "01-01", "en")).json()
        self.assertEqual((data["date"], data["chapter"]), ("12-31", 12))

    def test_a_gap_longer_than_a_week_is_not_bridged(self):
        self.book(missing={(10, d) for d in range(1, 32)})
        res = self.client.get(self.DAY.format("days-of-heaven-upon-earth", "10-30", "en"))
        self.assertEqual(res.status_code, 404)
        # Early in the month the week reaches back into the last one.
        data = self.client.get(self.DAY.format("days-of-heaven-upon-earth", "10-03", "en")).json()
        self.assertEqual(data["date"], "09-30")
        shelf = self.client.get(self.SHELF.format("10-30", "en")).json()
        self.assertEqual(shelf["readings"], [])

    def test_not_found(self):
        self.book()
        cases = [
            ("days-of-heaven-upon-earth", "02-30", "en"),
            ("days-of-heaven-upon-earth", "10-30", "es"),
            ("pilgrims-progress", "10-30", "en"),
        ]
        for slug, date, language in cases:
            with self.subTest(slug=slug, date=date, language=language):
                self.assertEqual(self.client.get(self.DAY.format(slug, date, language)).status_code, 404)

    def test_the_shelf_lists_this_languages_dated_books(self):
        self.book()
        self.book("morning-by-morning")
        self.book("morning-by-morning", "es")
        data = self.client.get(self.SHELF.format("10-30", "en")).json()
        slugs = sorted(r["book"]["slug"] for r in data["readings"])
        self.assertEqual(slugs, ["days-of-heaven-upon-earth", "morning-by-morning"])
        first = data["readings"][0]
        self.assertEqual((first["label"], first["excerpt"]), ("January 30", "Text for day 30."))
        self.assertNotIn("html", first)

    def test_the_book_detail_says_it_is_dated(self):
        self.book()
        Book.objects.create(author=self.author, slug="the-fourfold-gospel", language="en", title="x")
        detail = "/api/library/books/{}/?language=en"
        self.assertTrue(self.client.get(detail.format("days-of-heaven-upon-earth")).json()["daily"])
        self.assertFalse(self.client.get(detail.format("the-fourfold-gospel")).json()["daily"])


class DailyPlanTests(_DatedBooks, TestCase):
    """The year-long plans (plan_seed.DAILY_PLANS): seeded a day per dated entry,
    served with the entry's own title and length, and linked to the day page."""

    PLAN = "/api/library/plans/days-of-heaven-upon-earth-year/?language=en"

    def seed(self):
        call_command("seed_plans", verbosity=0)

    def test_every_devotional_plan_reads_a_dated_book(self):
        self.assertEqual(sorted(b for _, b, *_ in DAILY_PLANS if b not in DATED_BOOKS), [])

    def test_an_entry_date_is_never_on_an_article_day(self):
        plan = Plan.objects.create(slug="p", language="en", title="P")
        with self.assertRaises(IntegrityError):
            PlanDay.objects.create(plan=plan, day=1, article_slug="a", entry_date="01-01")

    def test_the_seed_makes_a_day_per_entry_january_first_sorted_last(self):
        older = Plan.objects.create(slug="older", language="en", title="Older", sort_order=40)
        self.book()
        self.seed()
        plan = Plan.objects.get(slug="days-of-heaven-upon-earth-year", language="en")
        days = list(plan.days.all())
        self.assertEqual(len(days), 365)  # the fixture's year: no 29 February
        self.assertEqual(
            [(d.day, d.chapter_order, d.entry_date) for d in (days[0], days[58], days[59])],
            [(1, 1, "01-01"), (59, 2, "02-28"), (60, 3, "03-01")],
        )
        # After the shelf, not ahead of it: a new plan on a live DB once got
        # the run's own count, 0.
        self.assertGreater(plan.sort_order, older.sort_order)
        self.seed()  # idempotent
        self.assertEqual(Plan.objects.filter(slug="days-of-heaven-upon-earth-year").count(), 1)

    def test_a_day_reads_its_entry_not_the_month(self):
        self.book()
        self.seed()
        data = self.client.get(self.PLAN).json()
        first = data["days"][0]
        self.assertEqual(
            (first["entry_date"], first["chapter_title"], first["word_count"]),
            ("01-01", "January 1", 6),  # "Text for day 1. More 1."
        )
        # The plan's length is its entries', not 365 months'.
        self.assertEqual(data["total_words"], 6 * 365)
        self.assertEqual(data["day_one"]["chapter_title"], "January 1")

    def test_the_book_names_its_plan_where_the_edition_has_one(self):
        self.book()
        detail = "/api/library/books/days-of-heaven-upon-earth/?language=en"
        self.assertEqual(self.client.get(detail).json()["daily_plan"], "")
        self.seed()
        self.assertEqual(
            self.client.get(detail).json()["daily_plan"], "days-of-heaven-upon-earth-year"
        )

    def test_the_reminder_email_links_the_day_page(self):
        self.book()
        self.seed()
        plan = Plan.objects.get(slug="days-of-heaven-upon-earth-year", language="en")
        day = plan.days.get(day=32)
        self.assertEqual(
            day_path(plan, day),
            "today/days-of-heaven-upon-earth/?d=02-01&plan=days-of-heaven-upon-earth-year&day=32",
        )
        # The helper's months all say "January"; 1 February's line is "January 1".
        self.assertEqual(_reading_title(day, "en"), "January 1")
