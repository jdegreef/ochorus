"""Two read paths whose SHAPE was the problem, not their indexes.

The plans shelf fetched each card's chapters three times over — total words,
where the plan starts, the cover strip — once per plan, so the cost grew with
the shelf (a 3N+1), and the detail page resolved the same chapters a fourth time
for its day list.

The authors page joined `books`, `sermons` and `translations` all at once. Those
reverse joins fan out multiplicatively — Spurgeon's 5 books × 13 sermons is 65
intermediate rows for one author — and surviving that needed `Count(distinct)`
plus a trailing `.distinct()`, which made Postgres GROUP BY and de-duplicate
over every selected column, `bio` and `bio_html` included: the full biography
HTML of every author, hashed and sorted, on a page the prerender crawl requests
once per locale.

These assert the shape directly, because "it got faster" is not a thing a test
can hold, and query COUNT alone would not have caught the authors problem — that
query was always one query; it was one bad query.
"""

from __future__ import annotations

import re

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Author, AuthorTranslation, Book, Chapter, Plan, PlanDay, Sermon


def _outer_statement(sql: str) -> str:
    """The SQL with every parenthesised subquery elided.

    A correlated subquery legitimately GROUPs BY the correlating key; what
    matters is whether the OUTER query does.
    """
    depth, out = 0, []
    for ch in sql:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


class PlanShelfQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray")
        for n in range(3):
            book = Book.objects.create(
                author=cls.author,
                slug=f"book-{n}",
                language="en",
                title=f"Book {n}",
                is_published=True,
            )
            for order in (1, 2):
                Chapter.objects.create(
                    book=book,
                    order=order,
                    title=f"Ch {order}",
                    body_html="<p>Some words here.</p>",
                )

    @staticmethod
    def _make_plan(slug, days):
        plan = Plan.objects.create(
            slug=slug, language="en", title=slug, is_published=True
        )
        for day, (book_slug, order) in enumerate(days, start=1):
            PlanDay.objects.create(
                plan=plan, day=day, book_slug=book_slug, chapter_order=order
            )
        return plan

    def _shelf_queries(self):
        with CaptureQueriesContext(connection) as captured:
            res = APIClient().get(reverse("plan-list"))
        self.assertEqual(res.status_code, 200)
        return len(captured.captured_queries), res.data

    def test_the_shelf_cost_does_not_grow_with_the_number_of_plans(self):
        self._make_plan("one", [("book-0", 1), ("book-1", 2)])
        first, _ = self._shelf_queries()

        for n in range(2, 8):
            self._make_plan(f"plan-{n}", [("book-0", 1), ("book-2", 2)])
        grown, data = self._shelf_queries()

        self.assertEqual(len(data), 7)
        self.assertLessEqual(
            grown,
            first,
            f"seven plans cost {grown} queries against {first} for one — "
            "each card is still resolving its own chapters",
        )

    def test_the_cards_still_say_what_they_said(self):
        """The N+1 went; the numbers must not."""
        self._make_plan("one", [("book-0", 1), ("book-1", 2)])
        _, data = self._shelf_queries()
        card = data[0]
        self.assertEqual(card["day_count"], 2)
        self.assertGreater(card["total_words"], 0)
        self.assertEqual(card["day_one"]["book_title"], "Book 0")
        self.assertEqual(card["day_one"]["chapter_title"], "Ch 1")
        self.assertEqual([c["slug"] for c in card["covers"]], ["book-0", "book-1"])

    def test_the_detail_page_resolves_its_chapters_once(self):
        plan = self._make_plan("one", [("book-0", 1), ("book-1", 2)])
        with CaptureQueriesContext(connection) as captured:
            res = APIClient().get(reverse("plan-detail", args=[plan.slug]))
        self.assertEqual(res.status_code, 200)
        chapter_reads = [
            q for q in captured.captured_queries if "library_chapter" in q["sql"]
        ]
        self.assertLessEqual(
            len(chapter_reads),
            1,
            "the day list and the card fields fetched the same chapters twice",
        )
        self.assertEqual(len(res.data["days"]), 2)
        self.assertEqual(res.data["days"][0]["book_title"], "Book 0")


class AuthorListQueryShapeTests(TestCase):
    """Shape, not count: this was always ONE query — it was one bad query."""

    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(
            slug="ch", name="Charles Spurgeon", bio="A bio."
        )
        AuthorTranslation.objects.create(
            author=cls.author, language="es", bio="Una biografía."
        )
        for n in range(5):
            Book.objects.create(
                author=cls.author,
                slug=f"b-{n}",
                language="en",
                title=f"B{n}",
                is_published=True,
            )
        for n in range(13):
            Sermon.objects.create(
                author=cls.author,
                slug=f"s-{n}",
                language="en",
                title=f"S{n}",
                is_published=True,
            )

    def _queryset_sql(self, language="en"):
        """The SQL the endpoint actually issues for the author list.

        Captured from a real request rather than rebuilt from the view class:
        reconstructing a DRF view by hand asserts the reconstruction as much as
        the code, and it broke the moment the view needed more than a request.
        """
        with CaptureQueriesContext(connection) as captured:
            res = APIClient().get(reverse("author-list"), {"language": language})
        self.assertEqual(res.status_code, 200)
        author_reads = [
            q["sql"]
            for q in captured.captured_queries
            if "library_author" in q["sql"] and "library_authortranslation" not in q["sql"][:60]
        ]
        self.assertTrue(author_reads, "the endpoint issued no author query")
        # The widest one is the list query; the rest are the prefetch.
        return max(author_reads, key=len)

    def test_the_outer_query_no_longer_de_duplicates(self):
        outer = _outer_statement(self._queryset_sql())
        self.assertNotIn("DISTINCT", outer)

    def test_the_biography_text_never_reaches_a_group_by(self):
        """The specific cost: hashing every author's bio_html to de-duplicate."""
        outer = _outer_statement(self._queryset_sql())
        self.assertNotIn("GROUP BY", outer)

    def test_the_reverse_joins_are_gone(self):
        """Three joins fanning out multiplicatively — 5 books x 13 sermons."""
        outer = _outer_statement(self._queryset_sql())
        self.assertEqual(len(re.findall(r"\bJOIN\b", outer)), 0)

    def test_the_counts_are_still_right(self):
        """A fan-out that Count(distinct) was compensating for; prove it stayed fixed."""
        res = APIClient().get(reverse("author-list"))
        self.assertEqual(res.status_code, 200)
        row = next(r for r in res.data if r["slug"] == "ch")
        self.assertEqual(row["book_count"], 5)
        self.assertEqual(row["sermon_count"], 13)

    def test_an_author_with_only_a_translated_bio_still_appears(self):
        """The Exists() replaced a join; it must select the same authors."""
        Author.objects.create(slug="bio-only", name="Bio Only", bio="")
        AuthorTranslation.objects.create(
            author=Author.objects.get(slug="bio-only"),
            language="es",
            bio="Sólo biografía.",
        )
        res = APIClient().get(reverse("author-list"), {"language": "es"})
        self.assertIn("bio-only", [r["slug"] for r in res.data])

    def test_an_author_with_nothing_in_this_language_is_absent(self):
        Author.objects.create(slug="empty", name="Empty", bio="")
        res = APIClient().get(reverse("author-list"), {"language": "sw"})
        self.assertNotIn("empty", [r["slug"] for r in res.data])
