"""A work can't be saved with a title that shows a reader nothing.

A Spurgeon book reached production with a blank title: the admin coverage
matrix drew it as just its author's name, still offering to queue translations
of it. The fixture gate (tests_fixture) only covers content from the fixture,
and some forty other paths write these rows, so the rule lives in the models'
save() for every work the matrix lists (Book, Sermon, Plan, Article). These
tests pin it there, the import endpoint's matching 400, and the coverage API's
`untitled` flag the page reads instead of judging blankness itself.

Invisible characters are written as escapes on purpose: a literal zero-width
space reads as "" here and an editor may silently drop it.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .models import Article, Author, Book, Plan, Sermon
from .text import is_blank_title

ZWSP, BOM, WJ, SHY, RLM, HANGUL_FILLER = "​", "﻿", "⁠", "­", "‏", "ㅤ"
# Each renders as nothing; all but the first three survive str.strip().
BLANKS = ("", "   ", "\n\t", ZWSP, f" {BOM} ", ZWSP + WJ + SHY, RLM, HANGUL_FILLER)
CHAPTER = {"title": "One", "html": "<p>Consider the grace of humility, and the Lord who taught it.</p>"}


class IsBlankTitleTests(SimpleTestCase):
    def test_invisible_titles_are_blank(self):
        for t in (*BLANKS, None):
            with self.subTest(t=repr(t)):
                self.assertTrue(is_blank_title(t))

    def test_real_titles_are_not(self):
        for t in ("Humility", " Abide in Christ ", "É", f"{ZWSP}Grace", "الله"):
            with self.subTest(t=repr(t)):
                self.assertFalse(is_blank_title(t))


class SaveGuardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray")

    def test_a_blank_title_is_refused_on_every_listed_work(self):
        makers = {
            "book": lambda t: Book.objects.create(author=self.author, slug="b", language="en", title=t),
            "sermon": lambda t: Sermon.objects.create(
                author=self.author, slug="s", language="en", title=t, body_html="<p>x</p>"
            ),
            "plan": lambda t: Plan.objects.create(slug="p", language="en", title=t),
            "article": lambda t: Article.objects.create(slug="a", language="en", h1=t, body_html="<p>x</p>"),
        }
        for kind, make in makers.items():
            for t in BLANKS:
                with self.subTest(kind=kind, t=repr(t)), self.assertRaises(ValidationError):
                    make(t)
        self.assertFalse(Book.objects.exists() or Sermon.objects.exists())
        self.assertFalse(Plan.objects.exists() or Article.objects.exists())

    def test_retitling_to_blank_is_refused(self):
        book = Book.objects.create(author=self.author, slug="b", language="en", title="Humility")
        book.title = ZWSP
        with self.assertRaises(ValidationError):
            book.save()
        with self.assertRaises(ValidationError):
            book.save(update_fields=["title"])

    def test_a_legacy_blank_row_stays_saveable(self):
        """A row that was ALREADY blank (written before the guard) must not
        wedge: the release step re-saves sermons whole (apply_body_corrections),
        and refusing there would fail every deploy until the data was fixed by
        hand. Only a title BECOMING blank is refused."""
        sermon = Sermon.objects.create(
            author=self.author, slug="s", language="en", title="Abide", body_html="<p>x</p>"
        )
        Sermon.objects.filter(pk=sermon.pk).update(title="")
        sermon.refresh_from_db()
        sermon.body_html = "<p>y</p>"
        sermon.save()  # unscoped, title unchanged: passes
        sermon.is_published = False
        sermon.save(update_fields=["is_published"])  # scoped: passes
        sermon.title = "Abide"
        sermon.save()  # and the fix goes through
        self.assertEqual(Sermon.objects.get(pk=sermon.pk).title, "Abide")


@override_settings(DEBUG=True)
class ImportRefusesBlankTitlesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.create(slug="am", name="Andrew Murray")

    def _publish(self, **payload):
        base = {"kind": "book", "author_slug": "am", "chapters": [CHAPTER]}
        return APIClient().post("/api/admin/import/publish/", {**base, **payload}, format="json")

    def test_an_invisible_title_is_a_400_not_a_book(self):
        res = self._publish(title=ZWSP * 2)
        self.assertEqual(res.status_code, 400)
        self.assertIn("title", res.data["detail"].lower())

    def test_a_title_visible_only_past_the_cut_is_a_400_not_a_500(self):
        """Titles are stored as their first 300 characters; the check is made
        on what's stored."""
        res = self._publish(title=ZWSP * 300 + "Grace")
        self.assertEqual(res.status_code, 400)

    def test_a_non_string_title_is_a_400_not_a_junk_title(self):
        for title in (["Humility"], {"en": "x"}, True, 7):
            with self.subTest(title=title):
                self.assertEqual(self._publish(title=title).status_code, 400)

    def test_non_string_fields_are_a_400_not_a_500(self):
        self.assertEqual(self._publish(title="T", language=5).status_code, 400)
        self.assertEqual(self._publish(title="T", author_slug=1).status_code, 400)

    def test_nothing_was_created(self):
        self._publish(title=ZWSP)
        self.assertFalse(Book.objects.exists())


@override_settings(DEBUG=True)
class CoverageFlagsUntitledRowsTests(TestCase):
    def test_the_api_marks_a_blank_titled_row(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(author=author, slug="good", language="en", title="Humility")
        bad = Book.objects.create(author=author, slug="bad", language="en", title="Abide")
        Book.objects.filter(pk=bad.pk).update(title=ZWSP)  # a legacy row, past the guard
        rows = {r["slug"]: r for r in APIClient().get("/api/admin/coverage/").data["books"]}
        self.assertTrue(rows["bad"].get("untitled"))
        self.assertNotIn("untitled", rows["good"])
