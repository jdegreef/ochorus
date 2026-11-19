"""A Bible chapter's "Most quoted in the classics" row (`quoted_verses`).

What is worth pinning: the ranking counts DISTINCT citing chapters (the graph's
own measure, not raw repetitions), a verse is listed only when its scripture
page was really built, and every chapter that is not a Bible chapter — another
book, the introduction, the conclusion — carries an empty row.
"""

from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Series
from .scripture_graph import QUOTED_VERSES, VERSE_FLOOR, current_pages

#: verse of Romans 8 → how many distinct chapters of the work cite it.
SPREAD = {28: 7, 1: 6, 31: VERSE_FLOOR, 38: VERSE_FLOOR - 1}


class QuotedVersesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="a", name="A Writer")
        works = Book.objects.create(author=author, slug="w", language="en", title="A Work")
        for order in range(1, max(SPREAD.values()) + 1):
            refs = [f"Romans 8:{v}" for v, n in SPREAD.items() if order <= n]
            # Chapter 1 returns to 8:31 again and again: still one voice, so
            # 8:31 must not outrank 8:1 on repetition.
            if order == 1:
                refs += ["Romans 8:31"] * 6
            Chapter.objects.create(
                book=works,
                order=order,
                title=f"Chapter {order}",
                body_html="<p>" + " and then ".join(f"see {r}" for r in refs) + ".</p>",
            )
        call_command("index_citations", "--all", verbosity=0)
        series = Series.objects.create(slug="the-bible", title="The Bible")
        self.romans = Book.objects.create(
            author=author, slug="romans", language="en", title="Romans",
            series=series, series_position=45,
        )
        # Introduction, Romans 1-16, conclusion — as build_owb_book sets it.
        for order, title in [(1, "Introduction"), (2, "Romans 1"), (9, "Romans 8"), (18, "Conclusion")]:
            Chapter.objects.create(book=self.romans, order=order, title=title, body_html="<p>Text.</p>")

    def _row(self, slug, order):
        res = self.client.get(f"/api/library/books/{slug}/chapters/{order}/")
        self.assertEqual(res.status_code, 200)
        return res.data["quoted_verses"]

    def test_ranked_by_distinct_citing_chapters(self):
        row = self._row("romans", 9)
        self.assertEqual([(q["verse"], q["count"]) for q in row], [(28, 7), (1, 6), (31, VERSE_FLOOR)])
        self.assertEqual(
            row[0],
            {
                "verse": 28,
                "reference": "Romans 8:28",
                "count": 7,
                "page": {"book": "romans", "chapter": 8, "verse": 28},
            },
        )

    def test_only_verses_with_a_built_page(self):
        # 8:38 is quoted, but under the verse floor: no page, so no entry.
        row = self._row("romans", 9)
        self.assertNotIn(38, [q["verse"] for q in row])
        built = {(p["book"], p["chapter"], p["verse"]): p["citing_count"] for p in current_pages()}
        for q in row:
            page = q["page"]
            key = (page["book"], page["chapter"], page["verse"])
            self.assertIn(key, built)
            # The count is the one the verse page publishes about itself.
            self.assertEqual(q["count"], built[key])
            res = self.client.get(f"/api/library/scripture/romans/8/{page['verse']}/")
            self.assertEqual(res.status_code, 200)

    def test_a_chapter_nobody_quotes_has_an_empty_row(self):
        self.assertEqual(self._row("romans", 2), [])

    def test_introduction_and_conclusion_have_none(self):
        for order in (1, 18):
            self.assertEqual(self._row("romans", order), [])

    def test_any_other_book_has_none(self):
        self.assertEqual(self._row("w", 1), [])

    def test_the_row_is_capped(self):
        works = Book.objects.get(slug="w", language="en")
        for chapter in works.chapters.all():
            extra = " ".join(f"see Romans 8:{v} here." for v in range(2, 2 + QUOTED_VERSES))
            chapter.body_html = chapter.body_html.replace("</p>", f" {extra}</p>")
            chapter.save()
        call_command("index_citations", "--all", verbosity=0)
        row = self._row("romans", 9)
        self.assertEqual(len(row), QUOTED_VERSES)
        self.assertEqual(row[0]["verse"], 2)  # cited by all 7, ties in verse order

    def test_the_batch_agrees_with_the_single_endpoint(self):
        res = self.client.get("/api/library/books/romans/chapters/?language=en")
        self.assertEqual(res.status_code, 200)
        for chapter in res.data:
            self.assertEqual(chapter["quoted_verses"], self._row("romans", chapter["order"]))
