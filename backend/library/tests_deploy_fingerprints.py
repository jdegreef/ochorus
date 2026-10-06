"""The release's change detectors (library/deploy_fingerprints).

What matters is that a skipped row is one that genuinely didn't need the step:
the SQL and Python hashes agree, a second run touches nothing, and a body that
moves by ANY path (a queryset ``.update()``, which no save() hook sees) or a
change to the rules themselves brings it back.
"""

from __future__ import annotations

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from . import translation_staleness as ts
from .deploy_fingerprints import keyed_md5, keyed_md5_hex
from .models import Author, Book, Chapter, Sermon


def _run_corrections(*args) -> str:
    out = StringIO()
    call_command("apply_body_corrections", *args, stdout=out)
    return out.getvalue()


class KeyedMd5Tests(TestCase):
    def test_sql_and_python_agree(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="b", language="en", title="B")
        # Non-ASCII on purpose: SQL md5() hashes the UTF-8 bytes, as Python must.
        body = "<p>Grâce — “humility”, 謙遜.</p>"
        Chapter.objects.create(book=book, order=1, title="", body_html=body)
        sql = (
            Chapter.objects.annotate(k=keyed_md5("v1", "title", "body_html"))
            .values_list("k", flat=True)
            .get()
        )
        self.assertEqual(sql, keyed_md5_hex("v1", "", body))
        self.assertNotEqual(sql, keyed_md5_hex("v2", "", body))


class IncrementalCorrectionsTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        self.chapter = Chapter.objects.create(
            book=self.book, order=1, title="One", body_html="<p>Clean prose.</p>"
        )
        self.sermon = Sermon.objects.create(
            author=author, slug="s", language="en", title="S", body_html="<p>Clean.</p>"
        )

    def test_a_second_run_checks_nothing(self):
        self.assertIn("(2 bodies checked)", _run_corrections())
        self.assertIn("(0 bodies checked)", _run_corrections())

    def test_a_body_changed_behind_saves_back_is_corrected_next_run(self):
        _run_corrections()
        # .update() bypasses save(), exactly like a data migration does.
        Chapter.objects.filter(pk=self.chapter.pk).update(
            body_html="<p>The grace of humility. 17</p>"
        )
        out = _run_corrections()
        self.assertIn("(1 bodies checked)", out)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.body_html, "<p>The grace of humility.</p>")
        # And the corrected body is now settled: nothing left to check.
        self.assertIn("(0 bodies checked)", _run_corrections())

    def test_new_rules_recheck_every_body(self):
        _run_corrections()
        with mock.patch(
            "library.management.commands.apply_body_corrections.source_version",
            return_value="different-rules",
        ):
            self.assertIn("(2 bodies checked)", _run_corrections())

    def test_all_ignores_the_keys(self):
        _run_corrections()
        self.assertIn("(2 bodies checked)", _run_corrections("--all"))


class IncrementalDigestTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        self.en = Book.objects.create(author=author, slug="humility", language="en", title="H")
        self.sw = Book.objects.create(
            author=author, slug="humility", language="sw", title="U",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        for book, body in ((self.en, "<p>Pride</p>"), (self.sw, "<p>Kiburi</p>")):
            Chapter.objects.create(book=book, order=1, title="One", body_html=body)
        ts.refresh("book")

    def _texts_read(self) -> set[int]:
        with mock.patch.object(ts, "_row_digests", wraps=ts._row_digests) as spy:
            ts.refresh("book")
        return spy.call_args.args[1]

    def test_an_unchanged_corpus_reads_no_text(self):
        self.assertEqual(self._texts_read(), set())

    def test_only_the_moved_book_is_read_and_its_translation_goes_stale(self):
        Chapter.objects.filter(book=self.en).update(body_html="<p>Pride and fall</p>")
        self.assertEqual(self._texts_read(), {self.en.pk})
        self.assertEqual(ts.stale_languages("book"), {"humility": ["sw"]})

    def test_a_typography_only_edit_is_read_once_and_stays_current(self):
        Chapter.objects.filter(book=self.en).update(body_html="<p>Pride</p> ")
        self.assertEqual(self._texts_read(), {self.en.pk})
        self.assertEqual(ts.stale_languages("book"), {})
        self.assertEqual(self._texts_read(), set())
