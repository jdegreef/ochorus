"""The deploy-time scans must fetch only what they read — and still write right.

Three passes over the whole corpus run on every deploy, and each hauled columns
it never looked at. That is the allocation class behind the 2026-08-14 OOM, and
it grows with the library.

The risk in fixing it is the fix itself: deferring a column that a save() path
turns out to need would blank it. So these tests assert BOTH halves — that the
heavy columns are no longer selected, and that a correction applied through a
deferred load still lands with body_text correctly re-derived.
"""

from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Author, Book, Chapter, Sermon

HEAVY = ("body_html", "body_text", "search_vector")


def _selected(queryset) -> set[str]:
    """The column names a queryset's SQL actually selects."""
    sql = str(queryset.query)
    select = sql[sql.index("SELECT") + 6 : sql.index(" FROM ")]
    return {part.strip().split(".")[-1].strip('"') for part in select.split(",")}


class DeployScanColumnTests(TestCase):
    """Assert the SQL the COMMANDS issue, not a queryset rebuilt in the test.

    An earlier draft of these built `Chapter.objects.defer(...)` here and
    checked it — which asserts Django's defer(), not this change, and passed
    against the unfixed code. Running the real command and reading the captured
    queries is the only version that can fail for the right reason.
    """

    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(
            book=self.book, order=1, title="One", body_html="<p>Some prose.</p>"
        )
        Sermon.objects.create(
            author=self.author,
            slug="s",
            language="en",
            title="S",
            body_html="<p>More prose.</p>",
        )

    @staticmethod
    def _is_read(sql: str) -> bool:
        """A query that READS chapters, on either backend.

        Not simply `startswith("SELECT")`. These commands stream with
        `.iterator(chunk_size=...)`, and on POSTGRES that opens a server-side
        cursor — so the captured statement is `DECLARE ... CURSOR FOR SELECT`,
        which a SELECT-prefix filter drops on the floor. SQLite has no
        server-side cursors and issues a plain SELECT, so a prefix filter passes
        locally and finds nothing in CI. It did exactly that.
        """
        head = sql.lstrip().upper()
        return head.startswith("SELECT") or head.startswith("DECLARE")

    def _chapter_selects(self, *command):
        with CaptureQueriesContext(connection) as captured:
            call_command(*command, stdout=StringIO())
        return [
            q["sql"]
            for q in captured.captured_queries
            if self._is_read(q["sql"]) and "library_chapter" in q["sql"]
        ]

    def test_corrections_scan_never_selects_the_tsvector_or_derived_text(self):
        selects = self._chapter_selects("apply_body_corrections")
        self.assertTrue(selects, "the command issued no chapter SELECT")
        for sql in selects:
            self.assertNotIn("search_vector", sql)
            self.assertNotIn("body_text", sql)
        self.assertTrue(
            any("body_html" in sql for sql in selects),
            "it must still read the body it rewrites",
        )

    def test_citation_scan_never_selects_the_body_html_or_tsvector(self):
        selects = self._chapter_selects("index_citations")
        self.assertTrue(selects, "the command issued no chapter SELECT")
        for sql in selects:
            self.assertNotIn("search_vector", sql)
            self.assertNotIn("body_html", sql)
        self.assertTrue(any("body_text" in sql for sql in selects))

    def test_drift_query_fetches_only_what_it_compares(self):
        """The per-book chapter read seed_books' drift check actually issues.

        The drift check now reads one book's chapters at a time (no whole-corpus
        prefetch), but must still select only the columns it compares — order,
        title, body_html — never the tsvector or derived text.
        """
        from library.management.commands.seed_books import chapter_drift_reason

        fixture_chapters = [
            {
                "book": [self.book.slug, "en"],
                "order": 1,
                "title": "One",
                "body_html": "<p>Some prose.</p>",
            }
        ]
        with CaptureQueriesContext(connection) as captured:
            chapter_drift_reason(self.book, fixture_chapters)
        chapter_selects = [
            q["sql"]
            for q in captured.captured_queries
            if self._is_read(q["sql"]) and "library_chapter" in q["sql"]
        ]
        self.assertTrue(chapter_selects, "the drift check issued no chapter query")
        for sql in chapter_selects:
            self.assertNotIn("search_vector", sql)
            self.assertNotIn("body_text", sql)


class CorrectionsStillWriteCorrectlyTests(TestCase):
    """A deferred load must not cost the command its correctness.

    ``Chapter.save()`` assigns ``body_text``, which un-defers it so it IS
    written; ``word_count`` is never deferred and is written the same way;
    ``search_vector`` stays deferred and is refreshed by fts's own UPDATE. This
    proves that rather than assuming it.

    ``word_count`` is here because this command is where its drift was actually
    manufactured: on a fresh build it rewrites the bodies of 30 chapters and a
    sermon, and while nothing re-derived the count, nine of them came out of
    the deploy describing a body they no longer had — with nothing later in the
    chain to repair it (``backfill_word_count`` fills only zeros).
    """

    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author, slug="humility", language="en", title="Humility"
        )

    def test_a_page_number_is_stripped_and_body_text_re_derived(self):
        chapter = Chapter.objects.create(
            book=self.book,
            order=1,
            title="One",
            # strip_trailing_pagenum removes a bare 1-3 digit number stuck to
            # the end of the body directly after terminal punctuation — the
            # next section's number absorbed at the chapter boundary. A number
            # in its own paragraph is NOT that shape and is left alone.
            body_html="<p>The grace of humility. 17</p>",
        )
        call_command("apply_body_corrections", stdout=StringIO())

        chapter.refresh_from_db()
        self.assertEqual(chapter.body_html, "<p>The grace of humility.</p>")
        # The derived columns must match the corrected HTML, not the old one.
        self.assertIn("The grace of humility.", chapter.body_text)
        self.assertNotIn("17", chapter.body_text)
        # Five words went in; the stripped page number is not one of them.
        self.assertEqual(chapter.word_count, 4)

    def test_an_untouched_chapter_keeps_its_derived_text(self):
        chapter = Chapter.objects.create(
            book=self.book, order=2, title="Two", body_html="<p>Nothing to fix here.</p>"
        )
        before = Chapter.objects.get(pk=chapter.pk)
        call_command("apply_body_corrections", stdout=StringIO())
        after = Chapter.objects.get(pk=chapter.pk)
        self.assertEqual(after.body_text, before.body_text)
        self.assertEqual(after.word_count, before.word_count)

    def test_sermons_take_the_same_path(self):
        """Sermons stream deferred too, and their writes must survive it.

        The sermon loop applies only `apply_body_corrections` (the chapter loop
        additionally strips trailing page numbers), so this uses the rejoin rule
        that runs for EVERY work rather than a chapter-only transform.
        """
        sermon = Sermon.objects.create(
            author=self.author,
            slug="humility-sermon",
            language="en",
            title="On Humility",
            body_html="<p>A humil- ity deeper than words.</p>",
        )
        call_command("apply_body_corrections", stdout=StringIO())
        sermon.refresh_from_db()
        self.assertEqual(sermon.body_html, "<p>A humil-ity deeper than words.</p>")
        # The derived columns follow the corrected HTML, not the old one.
        self.assertIn("humil-ity", sermon.body_text)
        self.assertNotIn("humil- ity", sermon.body_text)
        # The rejoin fused two half-words, so the count must drop by one.
        self.assertEqual(sermon.word_count, 5)
