"""The Language Content Targets stay true to the catalogue.

Read straight off the fixture files (no database), so a renamed slug, an
unpublished work or a plan whose sources fall out of the set fails here, at the
PR that causes it, rather than as a silently shorter admin list.
"""

from __future__ import annotations

import json
from collections import Counter

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .admin_views.targets import level_summary
from .content_fixtures import (
    ARTICLES_DIR,
    AUTHORS_FILE,
    article_fixture_path,
    book_fixture_path,
    sermon_fixture_path,
)
from .content_targets import BIO_EXCEPTIONS, KINDS, LEVEL_1, LEVELS
from .corrections import COPYRIGHT_BLOCKED_SLUGS
from .models import Author, AuthorTranslation, Book
from .plan_seed import CURATED_PLANS, LAUNCH_PLANS, plan_sources


def _head(path) -> dict:
    """The work row (first row) of an English fixture file."""
    return json.loads(path.read_text())[0]["fields"]


def _plan_sources() -> dict[str, tuple[list[str], list[str]]]:
    out = {p[0]: ([p[1]], []) for p in LAUNCH_PLANS}
    out.update({p[0]: plan_sources(p[3]) for p in CURATED_PLANS})
    return out


class ContentTargetsTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authors = {r["fields"]["slug"]: r["fields"] for r in json.loads(AUTHORS_FILE.read_text())}
        cls.plans = _plan_sources()

    def test_no_slug_is_listed_twice(self):
        for level in LEVELS:
            for kind in KINDS:
                dupes = [s for s, n in Counter(level.slugs(kind)).items() if n > 1]
                self.assertEqual(dupes, [], f"{level.name} {kind}")

    def test_every_work_is_a_published_english_row(self):
        paths = {"books": book_fixture_path, "sermons": sermon_fixture_path, "articles": article_fixture_path}
        for level in LEVELS:
            for kind, path_for in paths.items():
                for slug in level.slugs(kind):
                    path = path_for(slug, "en")
                    self.assertTrue(path.exists(), f"{level.name} {kind}: no English {slug}")
                    self.assertTrue(_head(path)["is_published"], f"{level.name} {kind}: {slug} is unpublished")

    def test_nothing_under_copyright(self):
        for level in LEVELS:
            self.assertEqual(set(level.slugs("books")) & COPYRIGHT_BLOCKED_SLUGS, set(), level.name)

    def test_every_bio_is_an_author_with_an_english_bio(self):
        for level in LEVELS:
            for slug in level.slugs("bios"):
                self.assertIn(slug, self.authors, f"{level.name}: unknown author {slug}")
                self.assertTrue(self.authors[slug].get("bio_html"), f"{level.name}: {slug} has no English bio")

    def test_every_author_in_the_level_has_its_bio(self):
        """The closure rule: no author page in the set lacks its biography."""
        for level in LEVELS:
            bios = set(level.slugs("bios"))
            authors = {_head(book_fixture_path(s, "en"))["author"][0] for s in level.slugs("books")}
            authors |= {_head(sermon_fixture_path(s, "en"))["author"][0] for s in level.slugs("sermons")}
            imprints = {a for a in authors if self.authors[a].get("is_imprint")}
            missing = authors - bios - imprints - BIO_EXCEPTIONS
            self.assertEqual(missing, set(), f"{level.name}: authors without a bio in the level")

    def test_bio_exceptions_still_lack_an_english_bio(self):
        """An exception is temporary: once the bio is written, move it into the level."""
        for slug in BIO_EXCEPTIONS:
            self.assertFalse(self.authors[slug].get("bio_html"), f"{slug} has a bio now; add it to the level")

    def test_every_plan_draws_only_on_the_level(self):
        """``seed_plans`` builds a plan only where all its sources exist, so a plan
        whose sources sit outside the level could never be finished at it."""
        for level in LEVELS:
            books, articles = set(level.slugs("books")), set(level.slugs("articles"))
            for plan in level.plans:
                self.assertIn(plan, self.plans, f"{level.name}: unknown plan {plan}")
                need_books, need_articles = self.plans[plan]
                self.assertEqual(set(need_books) - books, set(), f"{level.name}: {plan} needs books")
                self.assertEqual(set(need_articles) - articles, set(), f"{level.name}: {plan} needs articles")

    def test_articles_dir_is_where_the_paths_point(self):
        # Guards the helper this file leans on, so a fixture-layout change fails
        # loudly here instead of every article check passing on missing files.
        self.assertTrue(any(ARTICLES_DIR.glob("*.en.json")))


@override_settings(DEBUG=True)
class TargetsProgressTests(TestCase):
    """What the admin counts as done against a level."""

    @classmethod
    def setUpTestData(cls):
        murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        for lang, published in (("en", True), ("sw", True), ("lg", False)):
            Book.objects.create(
                author=murray, slug="humility-2", language=lang, title="Humility", is_published=published
            )
        Book.objects.create(
            author=murray, slug="absolute-surrender", language="sw", title="Kujisalimisha",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Book.objects.create(author=murray, slug="not-in-the-level", language="sw", title="Elsewhere")
        AuthorTranslation.objects.create(author=murray, language="sw", bio_html="<p>Wasifu</p>", reviewed=True)
        # A blank bio is not a biography.
        AuthorTranslation.objects.create(author=murray, language="lg", bio_html="")

    def test_summary_counts_published_level_editions_only(self):
        summary = level_summary(LEVEL_1, ["sw", "lg"])
        self.assertEqual(summary["sw"]["done"], 3)  # two books + one bio
        self.assertEqual(summary["lg"]["done"], 0)  # unpublished book, blank bio
        self.assertEqual(summary["sw"]["total"], sum(len(LEVEL_1.slugs(k)) for k in KINDS))

    def test_language_page_reports_each_item(self):
        res = APIClient().get("/api/admin/languages/lg/targets/")
        self.assertEqual(res.status_code, 200)
        books = next(k for k in res.data["kinds"] if k["key"] == "books")
        items = {i["slug"]: i for g in books["groups"] for i in g["items"]}
        self.assertEqual(len(items), len(LEVEL_1.slugs("books")))
        self.assertEqual((items["humility-2"]["done"], items["humility-2"]["drafted"]), (False, True))
        self.assertEqual(items["humility-2"]["title"], "Humility")  # the English title

        sw = APIClient().get("/api/admin/languages/sw/targets/").data
        books = next(k for k in sw["kinds"] if k["key"] == "books")
        self.assertEqual((books["done"], books["reviewed"]), (2, 1))

    def test_a_missing_plan_names_what_it_waits_on(self):
        res = APIClient().get("/api/admin/languages/sw/targets/")
        plans = next(k for k in res.data["kinds"] if k["key"] == "plans")
        humility = next(i for i in plans["groups"][0]["items"] if i["slug"] == "humility-12-days")
        self.assertEqual(humility["waiting_on"], [])  # its one book is here; the plan text isn't
        prayer = next(i for i in plans["groups"][0]["items"] if i["slug"] == "school-of-prayer-31-days")
        self.assertEqual(prayer["waiting_on"], ["school-of-prayer"])
