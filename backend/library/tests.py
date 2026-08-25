import copy
import json
import os
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock, skipUnless

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from . import language_suggestions
from . import readiness as readiness_module
from . import search as search_module
from .ingest import clean_title
from .language_seed import SEED_LANGUAGES
from .languages import config as language_config
from .models import (
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Language,
    Plan,
    PlanDay,
    SearchClickLog,
    SearchQueryLog,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)
from .search import search_library
from .text import html_to_text
from .translation import (
    GLOSSARY_TERMS,
    Ref,
    fetch_chapter,
    missing_glossary_terms,
    verify_bible_code,
    verify_glossary,
)


class CleanTitleTests(TestCase):
    def test_allcaps_ccel_heading_becomes_title_case(self):
        self.assertEqual(clean_title("II. THE DIGNITY OF CHRIST"), "The Dignity of Christ")
        self.assertEqual(clean_title("XXXII. GOD A CONSUMING FIRE."), "God a Consuming Fire")

    def test_preserves_apostrophe_when_recasing(self):
        self.assertEqual(
            clean_title("VIII. CHRIST'S MERCIFUL AND FAITHFUL HELP"),
            "Christ's Merciful and Faithful Help",
        )

    def test_strips_roman_prefix_only_from_allcaps_heading(self):
        # ALL-CAPS CCEL heading: the redundant numeral is dropped.
        self.assertEqual(clean_title("IV. DRIFTING"), "Drifting")
        # Mixed-case numbered title (Murray's Humility) keeps its numeral, so its
        # chapter numbering survives a re-import.
        self.assertEqual(
            clean_title("I. Humility: The Glory of the Creature"),
            "I. Humility: The Glory of the Creature",
        )
        # A Bible-book title likewise keeps its numeral.
        self.assertEqual(clean_title("II. Timothy"), "II. Timothy")

    def test_preserves_roman_numeral_words_in_allcaps(self):
        self.assertEqual(clean_title("II CORINTHIANS"), "II Corinthians")
        self.assertEqual(clean_title("PSALM CXIX"), "Psalm CXIX")

    def test_ordinals_not_miscapitalised(self):
        self.assertEqual(clean_title("THE 1ST AWAKENING"), "The 1st Awakening")

    def test_does_not_eat_personal_initials(self):
        # "D." is a roman-numeral char but this is a name, not a chapter prefix.
        self.assertEqual(clean_title("D. L. Moody (1837 – 1899)"), "D. L. Moody (1837 – 1899)")

    def test_bare_roman_numeral_left_alone(self):
        self.assertEqual(clean_title("IV"), "IV")

    def test_idempotent_on_clean_title(self):
        self.assertEqual(clean_title("The Dignity of Christ"), "The Dignity of Christ")


class HtmlToTextTests(TestCase):
    def test_strips_tags_and_keeps_block_boundaries(self):
        text = html_to_text("<p>First sentence.</p><p>Second one.</p>")
        self.assertEqual(text, "First sentence. Second one.")

    def test_unescapes_entities(self):
        self.assertEqual(html_to_text("<p>God&rsquo;s &amp; grace</p>"), "God’s & grace")


class ChapterBodyTextTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="a", name="Andrew Murray")
        self.book = Book.objects.create(author=author, slug="humility", title="Humility")

    def test_save_derives_body_text(self):
        ch = Chapter.objects.create(
            book=self.book, order=1, title="One", body_html="<p>Pride must die.</p>"
        )
        self.assertEqual(ch.body_text, "Pride must die.")

    def test_save_with_update_fields_keeps_body_text_in_step(self):
        ch = Chapter.objects.create(
            book=self.book, order=1, title="One", body_html="<p>Old.</p>"
        )
        ch.body_html = "<p>New text.</p>"
        ch.save(update_fields=["body_html"])
        ch.refresh_from_db()
        self.assertEqual(ch.body_text, "New text.")


class SearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        book = Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(
            book=book,
            order=1,
            title="The Glory of the Creature",
            body_html="<p>Humility is the place of entire dependence on God.</p>",
        )
        Chapter.objects.create(
            book=book,
            order=2,
            title="The Secret of Redemption",
            body_html="<p>Pride must die in you, or nothing of heaven can live in you.</p>",
        )
        unpublished = Book.objects.create(
            author=author, slug="hidden", language="en", title="Hidden", is_published=False
        )
        Chapter.objects.create(
            book=unpublished, order=1, title="X", body_html="<p>dependence secret</p>"
        )
        spurgeon = Author.objects.create(slug="charles-h-spurgeon", name="Charles H. Spurgeon")
        Sermon.objects.create(
            author=spurgeon,
            slug="the-ravens-cry",
            language="en",
            title="The Ravens' Cry",
            scripture_ref="Psalm 147:9",
            body_html="<p>He gives to the beast his food, and to the young ravens which cry.</p>",
        )
        Sermon.objects.create(
            author=spurgeon,
            slug="hidden-sermon",
            language="en",
            title="Hidden Sermon",
            body_html="<p>ravens unpublished</p>",
            is_published=False,
        )
        Topic.objects.create(
            slug="prayer",
            title="Prayer",
            description="Classics on communion with God.",
            is_published=True,
        )
        Plan.objects.create(
            slug="thirty-days",
            language="en",
            title="Thirty Days of Humility",
            description="A month with Andrew Murray.",
            is_published=True,
        )

    def search(self, q, language="en"):
        res = self.client.get(f"/api/library/search/?q={q}&language={language}")
        self.assertEqual(res.status_code, 200)
        return res.data["results"]

    def test_finds_body_text_with_highlight_markers(self):
        results = self.search("dependence")
        self.assertEqual(len(results), 1)
        hit = results[0]
        self.assertEqual(hit["book_slug"], "humility")
        self.assertEqual(hit["chapter_order"], 1)
        self.assertIn("⟦dependence⟧", hit["snippet"])

    def test_hits_carry_iso_date_for_newest_sort(self):
        # Every hit exposes a YYYY-MM-DD date (chapters borrow their book's) so
        # the client can offer a "newest" sort. A book match and a chapter match:
        results = self.search("humility")
        self.assertTrue(results)
        for hit in results:
            self.assertIn("date", hit)
            self.assertRegex(hit["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_short_query_returns_nothing(self):
        res = self.client.get("/api/library/search/?q=a")
        self.assertEqual(res.data["results"], [])

    def test_unpublished_books_excluded(self):
        slugs = {r["book_slug"] for r in self.search("dependence")}
        self.assertNotIn("hidden", slugs)

    def test_language_filter(self):
        self.assertEqual(self.search("dependence", language="fr"), [])

    def test_no_html_in_snippets(self):
        for hit in self.search("pride"):
            self.assertNotIn("<", hit["snippet"])

    def test_sermons_included_with_type(self):
        results = self.search("ravens")
        sermon_hits = [r for r in results if r["type"] == "sermon"]
        self.assertEqual(len(sermon_hits), 1)
        hit = sermon_hits[0]
        self.assertEqual(hit["sermon_slug"], "the-ravens-cry")
        self.assertEqual(hit["scripture_ref"], "Psalm 147:9")
        self.assertIn("ravens", hit["snippet"])

    def test_unpublished_sermons_excluded(self):
        slugs = {r.get("sermon_slug") for r in self.search("ravens")}
        self.assertNotIn("hidden-sermon", slugs)

    def test_chapter_hits_typed(self):
        results = self.search("dependence")
        self.assertEqual(results[0]["type"], "chapter")

    def test_book_entity_hit(self):
        hits = [r for r in self.search("Humility") if r["type"] == "book"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["book_slug"], "humility")
        self.assertEqual(hits[0]["author_name"], "Andrew Murray")

    def test_author_entity_hit(self):
        hits = [r for r in self.search("Murray") if r["type"] == "author"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["author_slug"], "andrew-murray")

    def test_topic_entity_hit(self):
        hits = [r for r in self.search("Prayer") if r["type"] == "topic"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["topic_slug"], "prayer")

    def test_plan_entity_hit(self):
        hits = [r for r in self.search("Thirty") if r["type"] == "plan"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["plan_slug"], "thirty-days")

    def test_entities_lead_over_passages(self):
        # A book/author/topic/plan match should rank above raw body-text hits.
        results = self.search("Humility")
        self.assertIn(results[0]["type"], {"book", "author", "topic", "plan"})

    def test_unpublished_author_excluded(self):
        # An author with nothing published in the language shouldn't surface.
        Author.objects.create(slug="ghost", name="Ghost Humility Writer")
        slugs = {r.get("author_slug") for r in self.search("Humility")}
        self.assertNotIn("ghost", slugs)

    def _raw(self, q, language="en"):
        res = self.client.get("/api/library/search/", {"q": q, "language": language})
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_suggests_on_misspelled_title(self):
        data = self._raw("humilty")
        self.assertEqual(data["results"], [])
        self.assertEqual(data.get("suggestion", "").lower(), "humility")

    def test_suggests_misspelled_author_surname(self):
        data = self._raw("Spurgen")
        self.assertEqual(data.get("suggestion", "").lower(), "spurgeon")

    def test_no_suggestion_when_results_found(self):
        data = self._raw("Humility")
        self.assertTrue(data["results"])
        self.assertNotIn("suggestion", data)

    def test_no_suggestion_for_gibberish(self):
        data = self._raw("zxqwvbn")
        self.assertEqual(data["results"], [])
        self.assertNotIn("suggestion", data)

    @skipUnless(connection.vendor == "postgresql", "Postgres-only FTS path")
    def test_postgres_stemming_and_ranking(self):
        # "depend" should stem-match "dependence" under the english config.
        results = self.search("depend")
        self.assertTrue(results)
        self.assertIn("⟦", results[0]["snippet"])


class ScriptureSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        a = Author.objects.create(slug="cs", name="Charles Spurgeon")
        Sermon.objects.create(
            author=a,
            slug="new-birth",
            language="en",
            title="The New Birth",
            scripture_ref="John 3:14-21",
            body_html="<p>You must be born from above.</p>",
        )
        Sermon.objects.create(
            author=a,
            slug="the-vine",
            language="en",
            title="The True Vine",
            scripture_ref="John 15:1-8",
            body_html="<p>Abide in me and bear much fruit.</p>",
        )

    def search(self, q, language="en"):
        res = self.client.get("/api/library/search/", {"q": q, "language": language})
        self.assertEqual(res.status_code, 200)
        return res.data["results"]

    def test_verse_inside_range_matches(self):
        # John 3:16 falls inside John 3:14-21 — matched by verse overlap, not text.
        slugs = {r.get("sermon_slug") for r in self.search("John 3:16")}
        self.assertIn("new-birth", slugs)
        self.assertNotIn("the-vine", slugs)

    def test_abbreviated_reference_matches(self):
        slugs = {r.get("sermon_slug") for r in self.search("Jn 3:16")}
        self.assertIn("new-birth", slugs)

    def test_chapter_reference_matches(self):
        slugs = {r.get("sermon_slug") for r in self.search("John 15")}
        self.assertIn("the-vine", slugs)
        self.assertNotIn("new-birth", slugs)

    def test_non_reference_query_uses_text_only(self):
        # A normal word query still works and pulls in nothing by verse logic.
        slugs = {r.get("sermon_slug") for r in self.search("abide")}
        self.assertIn("the-vine", slugs)

    def test_reference_hit_not_duplicated(self):
        # A sermon found by both text and verse overlap appears once.
        results = [r for r in self.search("John 15:1") if r.get("sermon_slug") == "the-vine"]
        self.assertEqual(len(results), 1)

    def test_ranked_order_is_the_scan_order_not_the_databases(self):
        """Winners are fetched with one ``pk__in`` query, which returns rows in
        whatever order the database likes — they have to be put back into the
        (sort_order, title) order the scan chose.

        Asserted on the function rather than through ``search_library``: end to
        end, "John 15" also matches both sermons' ``scripture_ref`` by full text,
        so on Postgres they arrive via the text path and the scripture path never
        ranks them at all. (SQLite's icontains fallback behaves differently,
        which is exactly the kind of difference an end-to-end order assertion
        would be pinning by accident.)
        """
        cs = Author.objects.get(slug="cs")
        Sermon.objects.create(
            author=cs, slug="fruit", language="en", title="A Sermon On Fruit",
            scripture_ref="John 15:5", sort_order=0, body_html="<p>Much fruit.</p>",
        )
        Sermon.objects.filter(slug="the-vine").update(sort_order=1)

        eligible = Sermon.objects.filter(is_published=True, language="en")
        hits = search_module._scripture_sermon_hits("John 15", eligible, [])
        self.assertEqual([h["sermon_slug"] for h in hits], ["fruit", "the-vine"])

        # And the scan's order wins over the database's, not the reverse: flip
        # sort_order and the same two rows come back the other way round.
        Sermon.objects.filter(slug="fruit").update(sort_order=2)
        hits = search_module._scripture_sermon_hits("John 15", eligible, [])
        self.assertEqual([h["sermon_slug"] for h in hits], ["the-vine", "fruit"])

    def test_reference_scan_does_not_load_every_sermon_body(self):
        # The reference test needs one short field per sermon, and only the
        # winners' text is ever shown. Iterating full instances dragged every
        # published sermon's body_html and tsvector into memory to read
        # scripture_ref off each — per keystroke, once the reader typed a digit.
        from django.test.utils import CaptureQueriesContext

        eligible = Sermon.objects.filter(is_published=True, language="en")
        with CaptureQueriesContext(connection) as captured:
            hits = search_module._scripture_sermon_hits("John 3:16", eligible, [])
        self.assertEqual([h["sermon_slug"] for h in hits], ["new-birth"])
        self.assertEqual(
            [q["sql"] for q in captured.captured_queries if "body_html" in q["sql"]],
            [],
            "the scripture scan still pulls sermon bodies out of the database",
        )


class SermonBodyTextTests(TestCase):
    def test_save_derives_body_text(self):
        author = Author.objects.create(slug="a", name="A")
        s = Sermon.objects.create(
            author=author, slug="s", title="S", body_html="<p>Hear my <b>cry</b>.</p>"
        )
        self.assertEqual(s.body_text, "Hear my cry.")


class SeedBooksTests(TestCase):
    def test_creates_missing_books_with_chapters_and_author(self):
        from django.core.management import call_command

        self.assertFalse(Book.objects.filter(slug="the-way-to-god").exists())
        call_command("seed_books", verbosity=0)
        book = Book.objects.get(slug="the-way-to-god", language="en")
        self.assertEqual(book.author.slug, "dwight-l-moody")
        self.assertGreaterEqual(book.chapter_count, 9)
        # Chapters created via save() so search text is derived.
        self.assertTrue(all(c.body_text for c in book.chapters.all()))
        # Idempotent: second run creates nothing new.
        before = Book.objects.count()
        call_command("seed_books", verbosity=0)
        self.assertEqual(Book.objects.count(), before)


class SeedBooksUpsertTests(TestCase):
    """The update branch: a fixture edit must reach an already-seeded DB.

    Each test starts from a seeded database standing in for prod, mutates a row
    to the state that predates a fixture edit, then runs seed_books again as
    "the next deploy". Seeding once for the class matters — a full seed is 98
    books and 1674 chapters, each derived through save().
    """

    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command

        call_command("seed_books", verbosity=0)

    def test_updates_changed_book_metadata(self):
        # The PR #355 regression: generate_covers set cover_url locally, the
        # value reached the fixture, and prod never saw it because seed_books
        # only created. Simulate a prod row that predates a fixture edit.
        from django.core.management import call_command

        book = Book.objects.get(slug="the-way-to-god", language="en")
        Book.objects.filter(pk=book.pk).update(
            cover_url="", description="stale", sort_order=999
        )

        call_command("seed_books", verbosity=0)  # the next deploy

        book.refresh_from_db()
        fixture = self._fixture_fields("the-way-to-god", "en")
        self.assertEqual(book.cover_url, fixture["cover_url"])
        self.assertEqual(book.description, fixture["description"])
        self.assertEqual(book.sort_order, fixture["sort_order"])

    def test_second_run_updates_nothing(self):
        # A no-op deploy must not touch a single row — updated_at is the tell.
        from django.core.management import call_command

        stamps = dict(Book.objects.values_list("pk", "updated_at"))
        call_command("seed_books", verbosity=0)
        self.assertEqual(dict(Book.objects.values_list("pk", "updated_at")), stamps)

    def test_seed_never_reverts_an_approved_translation(self):
        # source_type is create-only. It ships in the fixture as ai_unreviewed,
        # but once a native speaker approves a translation the review workflow
        # owns it — re-asserting the fixture value on the next deploy would
        # silently restore the "awaiting native review" badge and make
        # approve_translation useless.
        from django.core.management import call_command

        translated = Book.objects.filter(
            source_type=Book.SourceType.AI_UNREVIEWED
        ).first()
        self.assertIsNotNone(translated, "fixture has no AI-translated book")
        call_command(
            "approve_translation", translated.slug, language=translated.language, no_fixture=True
        )

        call_command("seed_books", verbosity=0)  # the next deploy

        translated.refresh_from_db()
        self.assertEqual(translated.source_type, Book.SourceType.AI_REVIEWED)

    def test_seed_never_republishes_an_unpublished_book(self):
        # is_published is create-only for the same reason as source_type: an
        # urgent unpublish (a copyright complaint) happens directly in the live
        # DB, and the fixture must not resurrect the book on the next deploy.
        from django.core.management import call_command

        book = Book.objects.get(slug="the-way-to-god", language="en")
        self.assertTrue(book.is_published)  # the fixture says published
        Book.objects.filter(pk=book.pk).update(is_published=False)

        call_command("seed_books", verbosity=0)  # the next deploy

        book.refresh_from_db()
        self.assertFalse(book.is_published)

    @skipUnless(connection.vendor == "postgresql", "Stored search vectors are Postgres-only")
    def test_retitle_rebuilds_chapter_search_vectors(self):
        # The update must go through Book.save(), whose hook rebuilds the
        # chapters' stored tsvectors; queryset.update() would leave them stale
        # (not NULL) and backfill_search_vectors would never notice. Asserted
        # on the production engine, where the vectors actually exist: after
        # seed_books applies a retitle, the OLD title must stop matching.
        from django.core.management import call_command

        from library import fts
        from library.search import search_library

        book = Book.objects.get(slug="the-way-to-god", language="en")
        # Put the DB in the "prod predates the fixture edit" state: a stale
        # title with search vectors consistently built from it.
        Book.objects.filter(pk=book.pk).update(title="Quixotical")
        book.refresh_from_db()
        fts.refresh_book_chapters(book)
        self.assertTrue(
            [h for h in search_library("Quixotical", "en") if h["type"] == "chapter"]
        )

        call_command("seed_books", verbosity=0)  # the next deploy

        self.assertEqual(
            [h for h in search_library("Quixotical", "en") if h["type"] == "chapter"], []
        )

    # --- author sync -------------------------------------------------------
    # An author's fields were create-only, so a biography written into
    # authors.json after the row existed never reached production; every such
    # correction shipped as a hand-written per-author migration (0049, 0051,
    # 0052, 0053). seed_books/seed_sermons now sync them, under a rule that can
    # only overwrite text the catalogs generated (library/author_sync).

    def _author(self):
        # An author whose fixture row carries a real biography.
        return Author.objects.get(slug="andrew-murray")

    def _fixture_bio(self, slug):
        from library.content_fixtures import authors_by_slug

        return authors_by_slug()[slug]["bio"]

    def test_a_catalog_stub_is_upgraded_to_the_real_biography(self):
        # The gap: an import created this author with catalog.py's one-liner,
        # and writing the real bio into authors.json never reached the row.
        from library.catalog import AUTHORS

        stub = AUTHORS["andrew-murray"].bio
        Author.objects.filter(slug="andrew-murray").update(bio=stub)

        call_command("seed_books", verbosity=0)  # the next deploy

        self.assertEqual(self._author().bio, self._fixture_bio("andrew-murray"))

    def test_an_author_with_no_book_or_sermon_is_synced_too(self):
        # The sync was first written inside the book loop, which silently
        # skipped the 9 biography-only authors — including the three migration
        # 0053 had to add by hand, i.e. exactly the case the feature is for.
        from library.content_fixtures import authors_by_slug, load_all_rows

        rows = load_all_rows()
        with_work = {
            r["fields"]["author"][0]
            for r in rows
            if r.get("model") in ("library.book", "library.sermon")
        }
        bookless = sorted(set(authors_by_slug(rows)) - with_work)
        self.assertTrue(bookless, "fixture no longer has a biography-only author")

        # These rows reach prod through the initial seed_if_empty loaddata (or a
        # migration like 0053) — seed_books only ever CREATES authors that have
        # a book, which is why the class's own seeding doesn't produce them.
        slug = bookless[0]
        Author.objects.create(slug=slug, name="Placeholder", bio="")

        call_command("seed_books", verbosity=0)

        self.assertEqual(Author.objects.get(slug=slug).bio, self._fixture_bio(slug))

    def _plant_stub_with_translations(self):
        from library.catalog import AUTHORS

        author = self._author()
        Author.objects.filter(pk=author.pk).update(bio=AUTHORS["andrew-murray"].bio)
        for lang, text in (("es", "Una biografía aprobada."),
                           ("sw", "Wasifu ulioidhinishwa.")):
            AuthorTranslation.objects.create(
                author=author, language=lang, bio=text, reviewed=True
            )
        return author

    def test_replacing_the_english_bio_flags_its_translations_stale(self):
        # A translation approved against the stub describes text that no longer
        # exists once the English is replaced, and nothing else records that.
        author = self._plant_stub_with_translations()

        call_command("seed_books", verbosity=0)

        self.assertEqual(
            sorted(
                AuthorTranslation.objects.filter(
                    author=author, source_stale=True
                ).values_list("language", flat=True)
            ),
            ["es", "sw"],
        )
        # Marked, not re-translated: the wording is untouched, and approval is
        # NOT cleared — see the release-order test below for why that matters.
        es = AuthorTranslation.objects.get(author=author, language="es")
        self.assertEqual(es.bio, "Una biografía aprobada.")
        self.assertTrue(es.reviewed)

    def test_the_full_release_order_preserves_approved_wording(self):
        # THE regression. Signalling staleness by clearing `reviewed` looks
        # right and destroys data: seed_author_translations reads `reviewed` as
        # "an approver owns this wording", and it runs LATER in the same release
        # (seed_books -> seed_sermons -> seed_author_translations). A re-gated
        # row loses that protection and the approver's text is replaced by the
        # repo's AI translation, in the same deploy, silently. Verified to
        # happen before source_stale was introduced.
        author = self._plant_stub_with_translations()

        call_command("seed_books", verbosity=0)
        call_command("seed_sermons", verbosity=0)
        call_command("seed_author_translations", verbosity=0)

        es = AuthorTranslation.objects.get(author=author, language="es")
        # The property that matters: the approver's words are still there.
        self.assertEqual(es.bio, "Una biografía aprobada.")
        self.assertTrue(es.source_stale)
        # `reviewed` may legitimately end up False here — seed_author_translations
        # fills the row's still-empty bio_html from the repo and re-gates for
        # review, which is its own pre-existing behaviour, not the sync's doing.
        # What must never happen is the bio text being replaced.

    def test_syncing_a_field_other_than_bio_flags_nothing_stale(self):
        # Only a REPLACED English bio invalidates a translation. This exercises
        # the `if "bio" in changed` guard specifically: clearing photo_url makes
        # the deploy sync SOMETHING (so sync_author doesn't return early) while
        # leaving the English bio alone, and approvals must survive that.
        author = self._author()
        Author.objects.filter(pk=author.pk).update(photo_url="")
        AuthorTranslation.objects.create(
            author=author, language="es", bio="Aprobada.", reviewed=True
        )

        call_command("seed_books", verbosity=0)

        author.refresh_from_db()
        self.assertTrue(author.photo_url, "photo_url should have been filled")
        es = AuthorTranslation.objects.get(author=author, language="es")
        self.assertFalse(es.source_stale)
        self.assertTrue(es.reviewed)

    def test_the_stale_flag_is_cleared_when_the_translation_is_rewritten(self):
        # A flag nothing clears is a counter that only grows: the dashboard's
        # stale count would never come back down and would stop meaning
        # anything. Every path that rewrites the wording, or approves it against
        # the current English, answers the flag.
        from library.catalog import AUTHORS

        author = self._author()
        Author.objects.filter(pk=author.pk).update(bio=AUTHORS["andrew-murray"].bio)
        # UNREVIEWED, so seed_author_translations owns the wording and will
        # rewrite `bio` from the repo files — the path that answers the flag.
        AuthorTranslation.objects.create(
            author=author, language="es", bio="Texto viejo.", reviewed=False
        )

        call_command("seed_books", verbosity=0)
        self.assertTrue(
            AuthorTranslation.objects.get(author=author, language="es").source_stale
        )

        call_command("seed_author_translations", verbosity=0)
        es = AuthorTranslation.objects.get(author=author, language="es")
        self.assertNotEqual(es.bio, "Texto viejo.")  # it really was rewritten
        self.assertFalse(es.source_stale)

    def test_approving_a_translation_clears_the_stale_flag(self):
        author = self._plant_stub_with_translations()
        call_command("seed_books", verbosity=0)
        AuthorTranslation.objects.filter(author=author).update(reviewed=False)

        call_command("approve_author_translation", language="es", verbosity=0)

        es = AuthorTranslation.objects.get(author=author, language="es")
        self.assertTrue(es.reviewed)
        self.assertFalse(es.source_stale)

    def test_a_retired_stub_wording_is_still_upgraded(self):
        # Recognition is by string equality, so rewording a stub would strand
        # every live row still carrying the old text — nothing else can upgrade
        # a non-empty bio. RETIRED_STUBS keeps those wordings recognisable; this
        # fails if one is ever deleted rather than retired.
        from library.author_sync import RETIRED_STUBS

        Author.objects.filter(slug="andrew-murray").update(bio=RETIRED_STUBS[0])

        call_command("seed_books", verbosity=0)

        self.assertEqual(self._author().bio, self._fixture_bio("andrew-murray"))

    def test_an_empty_bio_is_filled(self):
        Author.objects.filter(slug="andrew-murray").update(bio="")
        call_command("seed_books", verbosity=0)
        self.assertEqual(self._author().bio, self._fixture_bio("andrew-murray"))

    def test_reviewed_prose_is_never_overwritten(self):
        # THE constraint. Blind-syncing the fixture would close the gap and also
        # silently revert a hand edit or an approved translation — so anything
        # that isn't empty or a verbatim catalog stub wins over the fixture.
        edited = "A biography a human rewrote in the admin, after review."
        Author.objects.filter(slug="andrew-murray").update(bio=edited)

        call_command("seed_books", verbosity=0)

        self.assertEqual(self._author().bio, edited)

    def test_fill_only_fields_are_filled_but_not_overwritten(self):
        Author.objects.filter(slug="andrew-murray").update(photo_url="")
        call_command("seed_books", verbosity=0)
        filled = self._author().photo_url

        Author.objects.filter(slug="andrew-murray").update(photo_url="/custom.png")
        call_command("seed_books", verbosity=0)
        self.assertEqual(self._author().photo_url, "/custom.png")
        self.assertNotEqual(filled, "/custom.png")

    def test_a_no_op_deploy_changes_no_author(self):
        # Author has no updated_at, so snapshot the synced fields themselves.
        fields = ("slug", "bio", "bio_html", "photo_url", "birth_year", "death_year")
        before = list(Author.objects.order_by("slug").values_list(*fields))
        call_command("seed_books", verbosity=0)
        self.assertEqual(
            list(Author.objects.order_by("slug").values_list(*fields)), before
        )

    def _fixture_fields(self, slug, language):
        """The fixture's Book row for one work — its own file's first record.

        FileCoherenceTests pins that layout, so this reads one file instead of
        parsing all ~170 to find one row.
        """
        import json

        from library.content_fixtures import BOOKS_DIR, work_filename

        row = json.loads((BOOKS_DIR / work_filename(slug, language)).read_text())[0]
        self.assertEqual(row["model"], "library.book")
        return row["fields"]


class SeedBooksChapterDriftTests(TestCase):
    """seed_books syncs the Book row but not its chapters, so it emits a
    report-only warning when a book's stored chapters diverge from the fixture
    (a live-DB transform that never got a fixture regen). It must never mutate
    a chapter or fail — the deploy just gets a heads-up."""

    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command

        call_command("seed_books", verbosity=0)
        cls.book = Book.objects.filter(language="en").first()

    def _drift(self):
        # chapters_by_book keyed exactly as the command builds it.
        from library.content_fixtures import load_all_rows
        from library.management.commands.seed_books import chapter_drift

        chapters_by_book: dict = {}
        for r in load_all_rows():
            if r["model"] == "library.chapter":
                chapters_by_book.setdefault(
                    tuple(r["fields"]["book"]), []
                ).append(r["fields"])
        drifted = {
            b.slug: reason
            for b, reason in chapter_drift(
                Book.objects.prefetch_related("chapters"), chapters_by_book
            )
        }
        return drifted

    def test_faithful_seed_reports_no_drift(self):
        self.assertEqual(self._drift(), {})

    def test_missing_chapter_is_drift(self):
        self.book.chapters.order_by("-order").first().delete()
        self.assertIn("chapter(s) in DB", self._drift()[self.book.slug])

    def test_retitled_chapter_is_drift(self):
        c = self.book.chapters.first()
        Chapter.objects.filter(pk=c.pk).update(title="mangled")
        self.assertIn("title", self._drift()[self.book.slug])

    def test_edited_body_is_drift(self):
        c = self.book.chapters.first()
        Chapter.objects.filter(pk=c.pk).update(body_html="<p>tampered</p>")
        self.assertIn("body differs", self._drift()[self.book.slug])

    def test_reordered_chapters_report_the_odd_orders(self):
        # Same count, shifted order numbers — the message must name the orders,
        # not read "N vs N".
        last = self.book.chapters.order_by("-order").first()
        Chapter.objects.filter(pk=last.pk).update(order=last.order + 100)
        reason = self._drift()[self.book.slug]
        self.assertIn("order(s)", reason)
        self.assertIn(str(last.order + 100), reason)

    def test_warning_is_report_only_and_never_mutates_chapters(self):
        from django.core.management import call_command

        c = self.book.chapters.first()
        Chapter.objects.filter(pk=c.pk).update(body_html="<p>tampered</p>")
        out = StringIO()
        call_command("seed_books", stdout=out, stderr=out)
        # It warned…
        self.assertIn("Chapter drift", out.getvalue())
        self.assertIn(self.book.slug, out.getvalue())
        # …but did not "fix" the divergent chapter back to the fixture.
        c.refresh_from_db()
        self.assertEqual(c.body_html, "<p>tampered</p>")

    def test_drift_check_failure_never_aborts_the_seed(self):
        # The drift pass runs inside seed_books' @transaction.atomic handle(),
        # so a bug in this diagnostics-only code must not roll back a good seed
        # or fail the deploy — it's caught and reported, and the command still
        # succeeds (creating a book that was missing).
        from unittest.mock import patch

        from django.core.management import call_command

        self.book.delete()  # so this run has real work to commit
        out = StringIO()
        with patch(
            "library.management.commands.seed_books.chapter_drift",
            side_effect=RuntimeError("boom"),
        ):
            call_command("seed_books", stdout=out, stderr=out)
        self.assertIn("Chapter-drift check skipped", out.getvalue())
        # The seed itself committed despite the diagnostics blowing up.
        self.assertTrue(
            Book.objects.filter(slug=self.book.slug, language="en").exists()
        )


class SeedSermonsTests(TestCase):
    def test_creates_missing_authors_from_fixture(self):
        # Prod regression (2026-07-06): a sermon whose author has no books yet
        # (Moody) was silently skipped because the author row didn't exist.
        from django.core.management import call_command

        self.assertFalse(Author.objects.filter(slug="dwight-l-moody").exists())
        call_command("seed_sermons", verbosity=0)
        self.assertTrue(Author.objects.filter(slug="dwight-l-moody").exists())
        self.assertGreaterEqual(
            Sermon.objects.filter(author__slug="dwight-l-moody").count(), 5
        )
        self.assertGreaterEqual(Sermon.objects.count(), 18)

    def test_seeds_the_translation_badge_on_create(self):
        from django.core.management import call_command

        call_command("seed_sermons", verbosity=0)
        lg = Sermon.objects.get(slug="the-immutability-of-god", language="lg")
        self.assertEqual(lg.source_type, Book.SourceType.AI_UNREVIEWED)

    def test_seed_never_reverts_an_approved_translation(self):
        # source_type is create-only. It ships in the fixture as ai_unreviewed,
        # but once a native speaker approves a translation the review workflow
        # owns it — re-asserting the fixture value on the next deploy would
        # silently restore the "awaiting native review" badge and make
        # approve_sermon_translation useless.
        from django.core.management import call_command

        call_command("seed_sermons", verbosity=0)
        call_command("approve_sermon_translation", "the-immutability-of-god", language="lg", no_fixture=True)
        call_command("seed_sermons", verbosity=0)  # the next deploy
        lg = Sermon.objects.get(slug="the-immutability-of-god", language="lg")
        self.assertEqual(lg.source_type, Book.SourceType.AI_REVIEWED)

    def test_seed_never_republishes_an_unpublished_sermon(self):
        # is_published is create-only for the same reason as source_type: an
        # urgent unpublish happens directly in the live DB, and the fixture
        # (which still says is_published=True) must not resurrect the sermon on
        # the next deploy.
        from django.core.management import call_command

        call_command("seed_sermons", verbosity=0)
        sermon = Sermon.objects.filter(language="en").first()
        Sermon.objects.filter(pk=sermon.pk).update(is_published=False)
        call_command("seed_sermons", verbosity=0)  # the next deploy
        sermon.refresh_from_db()
        self.assertFalse(sermon.is_published)


class SeedAuthorTranslationsTests(TestCase):
    """The es/sw/lg author bios must survive a fresh-DB rebuild (the PR #204
    class of loss): they shipped only via guarded data migrations (0021/0023/
    0024) that no-op when authors are seeded after migrate, and
    AuthorTranslation has no fixture — the seed_author_translations release
    step is what recreates them."""

    def _create_authors(self):
        from library.management.commands.seed_author_translations import (
            language_dirs,
            read_bios,
        )

        for slug in {s for _, d in language_dirs() for s in read_bios(d)}:
            Author.objects.create(slug=slug, name=slug.replace("-", " ").title())

    def test_fills_all_languages_on_a_fresh_db(self):
        from django.core.management import call_command

        from library.management.commands.seed_author_translations import (
            language_dirs,
            read_bios,
        )

        self._create_authors()
        call_command("seed_author_translations", verbosity=0)
        dirs = language_dirs()
        self.assertGreaterEqual(len(dirs), 3)  # es, sw, lg at minimum
        for lang, d in dirs:
            bios = read_bios(d)
            rows = AuthorTranslation.objects.filter(language=lang).select_related(
                "author"
            )
            self.assertEqual(rows.count(), len(bios))
            for tr in rows:
                self.assertEqual(tr.bio, bios[tr.author.slug].get("bio", ""))
                self.assertEqual(tr.bio_html, bios[tr.author.slug].get("bio_html", ""))
                self.assertFalse(tr.reviewed)
        # One literal oracle, independent of read_bios (which fed the seed too).
        murray_es = AuthorTranslation.objects.get(
            author__slug="andrew-murray", language="es"
        )
        self.assertTrue(murray_es.bio.startswith("Andrew Murray hijo"))
        self.assertIn("<", murray_es.bio_html)

    def test_upserts_corrections_to_unreviewed_rows(self):
        # The repo data files are the source of truth while a row is
        # unreviewed (same contract as seed_sermons): a corrected bio committed
        # to <slug>.short.txt/<slug>.html must reach prod on the next deploy.
        from django.core.management import call_command

        self._create_authors()
        call_command("seed_author_translations", verbosity=0)
        tr = AuthorTranslation.objects.get(author__slug="andrew-murray", language="es")
        good_bio, good_html = tr.bio, tr.bio_html
        tr.bio, tr.bio_html = "stale", "<p>stale</p>"
        tr.save()
        call_command("seed_author_translations", verbosity=0)
        tr.refresh_from_db()
        self.assertEqual(tr.bio, good_bio)
        self.assertEqual(tr.bio_html, good_html)

    def test_idempotent_and_never_rewrites_an_approved_wording(self):
        # Once approve_author_translation flips reviewed=True the review
        # workflow owns the wording — the deploy step must not walk back the
        # flag or the text (same rule as seed_sermons's create-only
        # source_type).
        from django.core.management import call_command

        self._create_authors()
        call_command("seed_author_translations", verbosity=0)
        AuthorTranslation.objects.filter(language="es").update(
            reviewed=True, bio="Approver's wording."
        )
        before = list(
            AuthorTranslation.objects.values_list("bio", "bio_html", "reviewed")
        )
        call_command("seed_author_translations", verbosity=0)
        after = list(
            AuthorTranslation.objects.values_list("bio", "bio_html", "reviewed")
        )
        self.assertEqual(before, after)

    def test_reviewed_row_still_receives_a_later_shipped_field(self):
        # Migrations 0023/0024 filled still-empty fields even on reviewed rows
        # and re-gated review; the seed must keep that delivery path — an
        # approved short bio would otherwise block the long-form bio_html
        # batch forever.
        from django.core.management import call_command

        self._create_authors()
        call_command("seed_author_translations", verbosity=0)
        tr = AuthorTranslation.objects.get(author__slug="andrew-murray", language="sw")
        tr.bio, tr.bio_html, tr.reviewed = "Approved wording.", "", True
        tr.save()
        call_command("seed_author_translations", verbosity=0)
        tr.refresh_from_db()
        self.assertEqual(tr.bio, "Approved wording.")  # approver's text kept
        self.assertTrue(tr.bio_html)  # the empty field was delivered
        self.assertFalse(tr.reviewed)  # and the row re-gated for review

    def test_missing_author_is_a_soft_skip(self):
        # Translation data may land ahead of its author (like seed_topics's
        # soft slug-references) — the deploy must not fail on it.
        from django.core.management import call_command

        from library.management.commands.seed_author_translations import (
            language_dirs,
            read_bios,
        )

        n_langs = sum(
            1 for _, d in language_dirs() if "andrew-murray" in read_bios(d)
        )
        Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        call_command("seed_author_translations", verbosity=0)
        self.assertEqual(
            AuthorTranslation.objects.filter(author__slug="andrew-murray").count(),
            n_langs,
        )
        self.assertEqual(AuthorTranslation.objects.count(), n_langs)


class PlanTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="humility-2", language="en", title="Humility")
        for i in (1, 2):
            Chapter.objects.create(
                book=book, order=i, title=f"Ch {i}", body_html="<p>x</p>", word_count=100
            )
        plan = Plan.objects.create(slug="humility-12-days", language="en", title="Humility in 12 Days")
        for i in (1, 2):
            PlanDay.objects.create(plan=plan, day=i, book_slug="humility-2", chapter_order=i)
        Plan.objects.create(slug="hidden", language="en", title="X", is_published=False)

    def test_list_excludes_unpublished_and_counts_days(self):
        res = self.client.get("/api/library/plans/?language=en")
        self.assertEqual(res.status_code, 200)
        slugs = [p["slug"] for p in res.data]
        self.assertEqual(slugs, ["humility-12-days"])
        self.assertEqual(res.data[0]["day_count"], 2)
        # Total words across the plan's days (each stub chapter is one word).
        self.assertEqual(res.data[0]["total_words"], 200)

    def test_list_and_detail_expose_book_covers(self):
        # The plan draws from one distinct book → one cover descriptor, in
        # first-appearance order, on both the list and the detail response.
        lst = self.client.get("/api/library/plans/?language=en")
        self.assertEqual([c["title"] for c in lst.data[0]["covers"]], ["Humility"])
        detail = self.client.get("/api/library/plans/humility-12-days/?language=en")
        self.assertEqual([c["title"] for c in detail.data["covers"]], ["Humility"])

    def test_detail_resolves_chapter_titles(self):
        res = self.client.get("/api/library/plans/humility-12-days/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["days"][0]["chapter_title"], "Ch 1")
        self.assertEqual(res.data["days"][0]["book_title"], "Humility")
        self.assertEqual(res.data["days"][0]["word_count"], 100)

    def test_list_exposes_day_one_teaser(self):
        # The card leads with where the plan starts — day 1's book + chapter.
        res = self.client.get("/api/library/plans/?language=en")
        self.assertEqual(
            res.data[0]["day_one"],
            {"book_title": "Humility", "chapter_title": "Ch 1"},
        )

    def test_day_one_null_when_chapter_unresolved(self):
        # A locale where day 1's book isn't translated can't resolve the chapter;
        # the field degrades to null rather than erroring (mirrors covers/detail).
        Plan.objects.create(slug="humility-12-days", language="lg", title="Obwetoowaze")
        PlanDay.objects.create(
            plan=Plan.objects.get(slug="humility-12-days", language="lg"),
            day=1, book_slug="humility-2", chapter_order=1,
        )
        res = self.client.get("/api/library/plans/?language=lg")
        self.assertIsNone(res.data[0]["day_one"])

    def test_seed_plans_idempotent(self):
        from django.core.management import call_command
        call_command("seed_plans")
        call_command("seed_plans")
        self.assertEqual(Plan.objects.filter(slug="humility-12-days").count(), 1)

    def test_seed_plans_rebuilds_a_day_less_plan(self):
        # Simulate a previous run that created the Plan row but died before its
        # PlanDays landed (or an interrupted seed). The reconcile used to report
        # any existing row as "done", leaving it permanently empty; now it's
        # rebuilt with its days.
        from django.core.management import call_command

        plan = Plan.objects.get(slug="humility-12-days", language="en")
        plan.days.all().delete()
        self.assertEqual(plan.days.count(), 0)

        call_command("seed_plans")

        self.assertEqual(
            Plan.objects.filter(slug="humility-12-days", language="en").count(), 1
        )
        rebuilt = Plan.objects.get(slug="humility-12-days", language="en")
        self.assertEqual(rebuilt.days.count(), 2)

    def test_seed_plans_localizes_lg_prose_and_leaves_en(self):
        from django.core.management import call_command

        # humility-2 also exists in Luganda → seed creates a Luganda plan row.
        lg_book = Book.objects.create(
            author=Author.objects.get(slug="am"), slug="humility-2", language="lg", title="Obwetoowaze"
        )
        for i in (1, 2):
            Chapter.objects.create(book=lg_book, order=i, title=f"Ess {i}", body_html="<p>x</p>")
        call_command("seed_plans")

        en = Plan.objects.get(slug="humility-12-days", language="en")
        lg = Plan.objects.get(slug="humility-12-days", language="lg")
        self.assertEqual(en.title, "Humility in 12 Days")  # English row untouched
        self.assertEqual(lg.title, "Obwetoowaze mu Nnaku 12")  # Luganda title
        self.assertTrue(lg.description)  # Luganda description present

    def test_seed_plans_refreshes_stale_english_lg_row(self):
        # A Luganda plan row seeded earlier with English prose (prod's state)
        # is refreshed to Luganda on the next seed run.
        from django.core.management import call_command

        lg_book = Book.objects.create(
            author=Author.objects.get(slug="am"), slug="humility-2", language="lg", title="Obwetoowaze"
        )
        Chapter.objects.create(book=lg_book, order=1, title="Ess 1", body_html="<p>x</p>")
        stale = Plan.objects.create(
            slug="humility-12-days", language="lg", title="Humility in 12 Days", description="old"
        )
        # A real stale row (from an earlier seed run) has its days; give it one so
        # the prose-refresh path runs, not the day-less rebuild.
        PlanDay.objects.create(plan=stale, day=1, book_slug="humility-2", chapter_order=1)
        call_command("seed_plans")
        stale.refresh_from_db()
        self.assertEqual(stale.title, "Obwetoowaze mu Nnaku 12")

    def test_seed_plans_skips_a_language_with_no_prose(self):
        """A book shipping in a new language must NOT publish an English plan.

        This is the #819 defect at its source. `seed_plans` creates a plan row
        per language the source book is published in, so shipping a BOOK is what
        creates the plan — and the prose used to fall back to English, putting
        "Humility in 12 Days" on the Arabic plans page. Hindi has no
        data/plan_translations/hi.json, so no Hindi plan may appear.
        """
        from django.core.management import call_command

        hi_book = Book.objects.create(
            author=Author.objects.get(slug="am"),
            slug="humility-2",
            language="hi",
            title="विनम्रता",
        )
        Chapter.objects.create(book=hi_book, order=1, title="एक", body_html="<p>x</p>")
        call_command("seed_plans", verbosity=0)

        self.assertFalse(
            Plan.objects.filter(slug="humility-12-days", language="hi").exists(),
            "seed_plans created a Hindi plan with no Hindi prose — it would "
            "render the English title to a Hindi reader.",
        )
        # The languages that DO have prose are unaffected.
        self.assertTrue(Plan.objects.filter(slug="humility-12-days", language="en").exists())

    def test_seed_plans_leaves_an_existing_untranslated_row_alone(self):
        """A row created before this guard keeps its prose; deleting a published
        plan is a bigger decision than a seed step makes on its own."""
        from django.core.management import call_command

        hi_book = Book.objects.create(
            author=Author.objects.get(slug="am"), slug="humility-2", language="hi", title="विनम्रता"
        )
        Chapter.objects.create(book=hi_book, order=1, title="एक", body_html="<p>x</p>")
        legacy = Plan.objects.create(
            slug="humility-12-days", language="hi", title="Humility in 12 Days", description="old"
        )
        PlanDay.objects.create(plan=legacy, day=1, book_slug="humility-2", chapter_order=1)
        call_command("seed_plans", verbosity=0)

        legacy.refresh_from_db()
        self.assertEqual(legacy.title, "Humility in 12 Days")


class TopicTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        # Two works, both English + one with a Swahili translation.
        for slug, title in (("humility-2", "Humility"), ("prayer", "On Prayer Book")):
            b = Book.objects.create(author=author, slug=slug, language="en", title=title)
            Chapter.objects.create(book=b, order=1, title="One", body_html="<p>hello there</p>")
        Book.objects.create(author=author, slug="humility-2", language="sw", title="Unyenyekevu")

        self.topic = Topic.objects.create(slug="prayer", title="On Prayer", description="Pray.")
        # Curated order deliberately reversed vs. alphabetical, so ordering is testable.
        TopicBook.objects.create(topic=self.topic, book_slug="prayer", sort_order=0)
        TopicBook.objects.create(topic=self.topic, book_slug="humility-2", sort_order=1)
        TopicTranslation.objects.create(
            topic=self.topic, language="sw", title="Kuhusu Maombi"
        )
        # A topic with no member present in English → hidden from the EN shelf.
        empty = Topic.objects.create(slug="empty", title="Empty", sort_order=1)
        TopicBook.objects.create(topic=empty, book_slug="does-not-exist")
        # An unpublished topic is never listed.
        Topic.objects.create(slug="draft", title="Draft", is_published=False, sort_order=2)

    def test_list_localizes_and_hides_empty_and_unpublished(self):
        res = self.client.get("/api/library/topics/?language=en")
        self.assertEqual(res.status_code, 200)
        slugs = [t["slug"] for t in res.data]
        self.assertEqual(slugs, ["prayer"])  # empty + draft excluded
        self.assertEqual(res.data[0]["title"], "On Prayer")
        self.assertEqual(res.data[0]["book_count"], 2)

    def test_list_localized_title_falls_back_per_language(self):
        res = self.client.get("/api/library/topics/?language=sw")
        self.assertEqual(res.status_code, 200)
        # Swahili has a translation for the title...
        self.assertEqual(res.data[0]["title"], "Kuhusu Maombi")
        # ...but only humility-2 exists in Swahili, so the shelf shows one book.
        self.assertEqual(res.data[0]["book_count"], 1)

    def test_covers_carry_sermons_when_a_language_has_no_books(self):
        """A shelf whose members in this language are sermons still has art.

        `TopicListView` lists a topic that has books OR sermons, but `covers`
        only ever drew books — so a Spanish reader met a card reading
        "0 books · 5 sermons" above an empty band. It never showed in English,
        where every topic has at least three books; it showed in every other
        language, because sermon translation has outrun book translation.
        """
        author = Author.objects.get(slug="am")
        shelf = Topic.objects.create(slug="the-call", title="The Call", sort_order=3)
        TopicBook.objects.create(topic=shelf, book_slug="prayer")  # English only
        for i, slug in enumerate(("come-in", "free-grace")):
            Sermon.objects.create(
                author=author, slug=slug, language="sw", title=slug, body_html="<p>x</p>"
            )
            TopicSermon.objects.create(topic=shelf, sermon_slug=slug, sort_order=i)
        TopicTranslation.objects.create(topic=shelf, language="sw", title="Mwito")

        res = self.client.get("/api/library/topics/?language=sw")
        card = next(t for t in res.data if t["slug"] == "the-call")
        self.assertEqual(card["book_count"], 0)
        self.assertEqual(card["sermon_count"], 2)
        self.assertEqual(
            [(c["kind"], c["slug"]) for c in card["covers"]],
            [("sermon", "come-in"), ("sermon", "free-grace")],
            "a shelf with only sermons in this language must still carry tiles",
        )
        # The rule that actually broke: the listing rule and the drawing rule
        # live in different files and neither mentions the other. Anything the
        # endpoint returns has to have something to draw.
        for other in res.data:
            self.assertTrue(
                other["covers"],
                f"{other['slug']}: listed with {other['book_count']} books and "
                f"{other['sermon_count']} sermons, but nothing to draw",
            )

    def test_covers_put_books_first_and_cap_the_fan(self):
        """Books fill the fan, sermons take what is left, four tiles at most.

        Books first so a shelf that can fill the band with covers looks exactly
        as it did before sermons joined; the fan holds four because that is what
        `.cover-fan` lays out before it overflows.
        """
        author = Author.objects.get(slug="am")
        for i in range(3):
            Sermon.objects.create(
                author=author, slug=f"s{i}", language="en", title=f"S{i}", body_html="<p>x</p>"
            )
            TopicSermon.objects.create(topic=self.topic, sermon_slug=f"s{i}", sort_order=i)

        res = self.client.get("/api/library/topics/?language=en")
        covers = next(t for t in res.data if t["slug"] == "prayer")["covers"]
        self.assertEqual(
            [(c["kind"], c["slug"]) for c in covers],
            [("book", "prayer"), ("book", "humility-2"), ("sermon", "s0"), ("sermon", "s1")],
            "books first in curated order, sermons after, four tiles at most",
        )

    def test_detail_returns_members_in_curated_order(self):
        res = self.client.get("/api/library/topics/prayer/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([b["slug"] for b in res.data["books"]], ["prayer", "humility-2"])
        # Book cards carry their chapter counts (annotation wired through).
        self.assertEqual(res.data["books"][0]["chapter_count"], 1)

    def test_detail_unpublished_is_404(self):
        self.assertEqual(self.client.get("/api/library/topics/draft/").status_code, 404)

    def test_book_detail_lists_its_topics(self):
        res = self.client.get("/api/library/books/prayer/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["topics"], [{"slug": "prayer", "title": "On Prayer"}])

    def test_books_list_carries_topic_chips(self):
        # The shelf endpoint attaches each book's published topics (for the
        # topic filter) — both members here belong to the one topic.
        res = self.client.get("/api/library/books/?language=en")
        self.assertEqual(res.status_code, 200)
        by_slug = {b["slug"]: b for b in res.data}
        chip = [{"slug": "prayer", "title": "On Prayer"}]
        self.assertEqual(by_slug["prayer"]["topics"], chip)
        self.assertEqual(by_slug["humility-2"]["topics"], chip)

    def test_books_list_topic_chips_localize(self):
        res = self.client.get("/api/library/books/?language=sw")
        by_slug = {b["slug"]: b for b in res.data}
        self.assertEqual(
            by_slug["humility-2"]["topics"], [{"slug": "prayer", "title": "Kuhusu Maombi"}]
        )

    def test_author_detail_lists_topics(self):
        # The author page surfaces the topical shelves the author appears in.
        res = self.client.get("/api/library/authors/am/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["topics"], [{"slug": "prayer", "title": "On Prayer"}])

    def test_author_topics_localize(self):
        res = self.client.get("/api/library/authors/am/?language=sw")
        self.assertEqual(res.data["topics"], [{"slug": "prayer", "title": "Kuhusu Maombi"}])

    def test_author_topics_include_sermon_membership(self):
        # A topic reachable only via one of the author's sermons still shows.
        Sermon.objects.create(
            author=Author.objects.get(slug="am"), slug="on-waiting", language="en",
            title="On Waiting", body_html="<p>Wait on God.</p>",
        )
        waiting = Topic.objects.create(slug="waiting", title="On Waiting", sort_order=3)
        TopicSermon.objects.create(topic=waiting, sermon_slug="on-waiting")
        res = self.client.get("/api/library/authors/am/?language=en")
        slugs = {t["slug"] for t in res.data["topics"]}
        self.assertEqual(slugs, {"prayer", "waiting"})

    def test_seed_topics_idempotent_and_upserts_membership(self):
        from django.core.management import call_command
        call_command("seed_topics")
        call_command("seed_topics")
        self.assertEqual(Topic.objects.filter(slug="prayer").count(), 1)
        # The seed's curated prayer membership includes the-inner-chamber.
        self.assertTrue(
            TopicBook.objects.filter(
                topic__slug="prayer", book_slug="the-inner-chamber"
            ).exists()
        )

    def test_every_translated_language_covers_every_topic(self):
        """A translated language must cover ALL topics, not some.

        There is no English fallback: a topic missing from a language's file is
        omitted from that language's shelf list entirely. So a partial language
        silently ships a partial set of shelves — the same discipline as the
        per-language glossaries, which are pinned the same way. Reads
        ``data/topic_translations/<lang>.json`` through the loader.
        """
        from library.management.commands.seed_topics import TOPICS
        from library.topic_translations import topic_translations

        slugs = {t[0] for t in TOPICS}
        for lang, per_topic in topic_translations().items():
            with self.subTest(language=lang):
                self.assertEqual(
                    set(per_topic),
                    slugs,
                    f"{lang}: translated topics differ from the seeded topics",
                )
                for slug, pair in per_topic.items():
                    title, description = pair
                    self.assertTrue(title.strip(), f"{lang}/{slug}: empty title")
                    self.assertTrue(
                        description.strip(), f"{lang}/{slug}: empty description"
                    )

    def test_seed_topics_reverts_a_deleted_scripture_entry(self):
        """Removing an entry's scripture object un-ships the verse on redeploy.

        The files are authoritative in BOTH directions. The additive version of
        this upsert only wrote scripture when present, so a reviewer deleting a
        wrong verse from the language file would find it still rendering after
        every future deploy — while translate_topic's own success message
        promised the opposite.
        """
        from django.core.management import call_command

        call_command("seed_topics", verbosity=0)
        lg = TopicTranslation.objects.get(topic__slug="prayer", language="lg")
        self.assertTrue(lg.scripture_text)  # lg ships a verse for prayer

        from library import topic_translations as tt

        edited = copy.deepcopy(tt.raw_topic_translations())
        edited["lg"]["prayer"].pop("scripture")
        with mock.patch(
            "library.topic_translations.raw_topic_translations", return_value=edited
        ):
            call_command("seed_topics", verbosity=0)

        lg.refresh_from_db()
        self.assertEqual((lg.scripture_ref, lg.scripture_text), ("", ""))
        self.assertTrue(lg.title)  # the prose survives; only the verse reverts

    def test_seed_topics_translates_every_advertised_language(self):
        """es, sw, lg and pt all get real shelves — not English ones, and not none.

        Guards the regression this batch fixed: before these translations landed,
        /es and /sw had six shelves whose titles were English, and closing that
        leak emptied both pages until the prose existed.
        """
        from django.core.management import call_command

        call_command("seed_topics")
        topic = Topic.objects.get(slug="deeper-life")
        english = topic.title_for("en")
        for lang in ("es", "sw", "lg", "pt"):
            with self.subTest(language=lang):
                title = topic.title_for(lang)
                self.assertTrue(title, f"{lang}: no translated title")
                self.assertNotEqual(title, english, f"{lang}: title is the English")
                self.assertTrue(topic.is_translated_into(lang))

    def test_seed_topics_populates_lg_translations(self):
        from django.core.management import call_command

        call_command("seed_topics")
        topic = Topic.objects.get(slug="prayer")
        # An lg TopicTranslation is upserted, and it differs from the English.
        self.assertEqual(topic.title_for("en"), "On Prayer")
        self.assertEqual(topic.title_for("lg"), "Ku Kusaba")
        self.assertTrue(topic.description_for("lg"))
        self.assertNotEqual(topic.description_for("lg"), topic.description_for("en"))
        # Idempotent: a second run doesn't duplicate the translation row.
        call_command("seed_topics")
        self.assertEqual(
            TopicTranslation.objects.filter(topic=topic, language="lg").count(), 1
        )


class AuthorListTests(TestCase):
    """The Biographies shelf: anyone with a bio OR a book to read."""

    def setUp(self):
        self.client = APIClient()
        # Has books but no bio written yet (the R. A. Torrey case).
        bookish = Author.objects.create(slug="torrey", name="R. A. Torrey")
        Book.objects.create(author=bookish, slug="baptism", language="en", title="Baptism")
        # Has a bio but no books (a figure we tell the story of).
        Author.objects.create(slug="bunyan", name="John Bunyan", bio="A tinker who dreamed.")
        # Neither: nothing to show.
        Author.objects.create(slug="ghost", name="No One")
        # Books only in another language → nothing to open on the English shelf.
        other = Author.objects.create(slug="lg-only", name="Lg Only")
        Book.objects.create(author=other, slug="lg-book", language="lg", title="Ekitabo")
        # A house byline with books — not a person, so not on this shelf.
        imprint = Author.objects.create(slug="house", name="House Originals", is_imprint=True)
        Book.objects.create(author=imprint, slug="anthology", language="en", title="Anthology")

    def slugs(self, lang="en"):
        res = self.client.get(f"/api/library/authors/?language={lang}")
        self.assertEqual(res.status_code, 200)
        return [a["slug"] for a in res.data]

    def test_author_with_books_but_no_bio_is_listed(self):
        # Previously excluded by exclude(bio="") — an author with 5 books simply
        # vanished from the page that lists the library's writers.
        self.assertIn("torrey", self.slugs())

    def test_author_with_bio_but_no_books_is_listed(self):
        self.assertIn("bunyan", self.slugs())

    def test_author_with_neither_is_not_listed(self):
        self.assertNotIn("ghost", self.slugs())

    def test_books_only_in_another_language_do_not_carry_an_author(self):
        # No bio and no book a reader could open in this language → nothing to show.
        self.assertNotIn("lg-only", self.slugs("en"))
        # …but they are on their own language's shelf.
        self.assertIn("lg-only", self.slugs("lg"))

    def test_book_count_is_per_language(self):
        res = self.client.get("/api/library/authors/?language=en")
        torrey = next(a for a in res.data if a["slug"] == "torrey")
        self.assertEqual(torrey["book_count"], 1)

    def test_imprint_is_not_listed(self):
        # A house byline has books, but this shelf — and the schema.org
        # ItemList of Person it emits — is about people.
        self.assertNotIn("house", self.slugs())

    def test_fixture_flags_the_house_imprint(self):
        # The migration flags prod, but a fresh DB is loaded from the fixture
        # *after* migrate runs — so the flag has to ship in the fixture too.
        from library.content_fixtures import load_all_rows

        rows = load_all_rows()
        imprints = {
            r["fields"]["slug"]
            for r in rows
            if r.get("model") == "library.author" and r["fields"].get("is_imprint")
        }
        self.assertIn("ochorus-originals", imprints)


class SermonTranslationLabelTests(TestCase):
    """0036: AI translations were left labelled as public-domain originals."""

    def _relabel(self):
        import importlib

        from django.apps import apps as global_apps

        mod = importlib.import_module("library.migrations.0036_relabel_translated_sermons")
        mod.relabel_translations(global_apps, None)

    def setUp(self):
        self.a = Author.objects.create(slug="cs", name="C. Spurgeon")

    def _sermon(self, slug, language, **kw):
        return Sermon.objects.create(
            author=self.a, slug=slug, language=language, title=f"{slug} {language}",
            body_html="<p>some words here</p>", **kw
        )

    def test_relabels_only_genuine_translations(self):
        en = self._sermon("himself", "en")
        translated = self._sermon("himself", "lg")  # default: public_domain
        # A non-English sermon with no English sibling is a real original.
        original = self._sermon("okusaba", "lg")
        # An already-approved translation must never be downgraded.
        self._sermon("rest", "en")
        approved = self._sermon("rest", "lg", source_type=Book.SourceType.AI_REVIEWED)

        self._relabel()
        for s in (en, translated, original, approved):
            s.refresh_from_db()

        self.assertEqual(translated.source_type, Book.SourceType.AI_UNREVIEWED)
        self.assertEqual(en.source_type, Book.SourceType.PUBLIC_DOMAIN)
        self.assertEqual(original.source_type, Book.SourceType.PUBLIC_DOMAIN)
        self.assertEqual(approved.source_type, Book.SourceType.AI_REVIEWED)

    def test_is_idempotent(self):
        self._sermon("himself", "en")
        t = self._sermon("himself", "lg")
        self._relabel()
        self._relabel()
        t.refresh_from_db()
        self.assertEqual(t.source_type, Book.SourceType.AI_UNREVIEWED)

    def test_slug_collision_across_authors_is_not_a_translation(self):
        # slug is unique per language, not per author: a native-language
        # original may legitimately share a slug with an unrelated English
        # sermon. Matching on slug alone would brand a human's own work as
        # machine output.
        self._sermon("rest", "en")  # Spurgeon's English sermon
        other = Author.objects.create(slug="hb", name="Hannah Buyinza")
        native = Sermon.objects.create(
            author=other, slug="rest", language="lg", title="Okuwummula",
            body_html="<p>an original Luganda sermon</p>",
        )
        self._relabel()
        native.refresh_from_db()
        self.assertEqual(native.source_type, Book.SourceType.PUBLIC_DOMAIN)


class SermonNeighboursTests(TestCase):
    """Sequential prev/next through an author's sermon corpus (shelf order)."""

    def setUp(self):
        self.client = APIClient()
        self.a = Author.objects.create(slug="cs", name="C. Spurgeon")
        # Deliberately created out of order; shelf order is (sort_order, title).
        for slug, order, title in (
            ("gamma", 2, "Gamma"),
            ("alpha", 0, "Alpha"),
            ("beta", 1, "Beta"),
        ):
            Sermon.objects.create(
                author=self.a, slug=slug, language="en", title=title,
                sort_order=order, body_html="<p>words</p>",
            )
        # A sermon by another author must never be a neighbour.
        other = Author.objects.create(slug="dm", name="D. L. Moody")
        Sermon.objects.create(
            author=other, slug="delta", language="en", title="Delta",
            body_html="<p>x</p>",
        )
        # An unpublished sermon is skipped in the sequence.
        Sermon.objects.create(
            author=self.a, slug="hidden", language="en", title="Hidden",
            sort_order=1, body_html="<p>x</p>", is_published=False,
        )

    def _detail(self, slug):
        res = self.client.get(f"/api/library/sermons/{slug}/?language=en")
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_middle_has_both_neighbours(self):
        d = self._detail("beta")
        self.assertEqual(d["prev"], {"slug": "alpha", "title": "Alpha"})
        self.assertEqual(d["next"], {"slug": "gamma", "title": "Gamma"})

    def test_ends_are_null(self):
        self.assertIsNone(self._detail("alpha")["prev"])
        self.assertIsNone(self._detail("gamma")["next"])

    def test_neighbours_stay_within_author_and_published(self):
        # gamma's next would be the other author's "delta" if not scoped — it isn't.
        self.assertIsNone(self._detail("gamma")["next"])
        # beta's neighbours skip the unpublished "hidden".
        d = self._detail("beta")
        self.assertEqual(d["prev"]["slug"], "alpha")
        self.assertEqual(d["next"]["slug"], "gamma")


class SermonScriptureRefsTests(TestCase):
    """The scripture-index chip row: the sermon's text + body citations."""

    def setUp(self):
        self.client = APIClient()
        a = Author.objects.create(slug="cs", name="C. Spurgeon")
        Sermon.objects.create(
            author=a, slug="faith", language="en", title="Faith",
            scripture_ref="Mark 9:23",
            body_html=(
                "<p>Consider John 3:16 and what Romans 8:28 promises. "
                "As Mark 9:23 says again — and Jn 3:16 repeats — believe. "
                "Room 3:16 is not scripture.</p>"
            ),
        )

    def test_chips_lead_with_text_and_dedupe(self):
        res = self.client.get("/api/library/sermons/faith/?language=en")
        self.assertEqual(res.status_code, 200)
        refs = res.data["scripture_refs"]
        # The sermon's own text first; body citations deduped (Mark 9:23 again
        # and the Jn/John spellings collapse); non-references skipped.
        self.assertEqual(refs[0], "Mark 9:23")
        self.assertIn("John 3:16", refs)
        self.assertIn("Romans 8:28", refs)
        self.assertEqual(len(refs), 3)


class FixtureSourceDefectTests(SimpleTestCase):
    """Guard the fixture itself: a repaired source defect must stay repaired.

    A re-import or a fixture regen can quietly reinstate the original text, and
    these defects read as ordinary prose — nothing about "the name of God"
    looks broken unless you know the verse it is standing on. Written against
    the whole of `SOURCE_FIXES` rather than one book, so a repair registered
    later is guarded the day it ships: shipped text must be a fixed point of
    its own repair, in every language and in both stored fields.
    """

    def test_every_registered_source_fix_is_already_applied_to_the_fixture(self):
        from library.content_fixtures import load_all_rows
        from library.source_fixes import SOURCE_FIXES, apply_source_fixes

        chapters = [
            r["fields"] for r in load_all_rows() if r.get("model") == "library.chapter"
        ]
        checked = 0
        for (slug, order), _ in SOURCE_FIXES.items():
            editions = [
                c for c in chapters if c["book"][0] == slug and c["order"] == order
            ]
            self.assertTrue(
                editions,
                f"{slug} ch{order:02d} has no shipped chapter — did the numbering move?",
            )
            for chapter in editions:
                language = chapter["book"][1]
                for field in ("body_html", "body_text"):
                    # assertTrue, not assertEqual: these bodies run to tens of
                    # thousands of characters, and the useful thing on failure
                    # is which edition regressed, not a diff nobody can read.
                    self.assertTrue(
                        apply_source_fixes(slug, order, chapter[field]) == chapter[field],
                        f"{language} {slug} ch{order:02d} {field} ships with the "
                        f"uncorrected source text — the repair would still change it",
                    )
                checked += 1
        self.assertTrue(checked, "no source fixes registered — the guard is guarding nothing")


class FixtureSermonLabelTests(TestCase):
    """Guard the fixture itself: a shipped translation must carry its badge."""

    def test_no_translated_sermon_ships_as_public_domain(self):
        from library.content_fixtures import load_all_rows

        rows = load_all_rows()
        sermons = [r["fields"] for r in rows if r.get("model") == "library.sermon"]
        english = {s["slug"] for s in sermons if s["language"] == "en"}
        mislabelled = [
            f"{s['language']}/{s['slug']}"
            for s in sermons
            if s["language"] != "en"
            and s["slug"] in english
            and s.get("source_type", "public_domain") == "public_domain"
        ]
        self.assertEqual(mislabelled, [], "translated sermons must not ship as public_domain")


class RelatedBooksTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.murray = Author.objects.create(slug="am", name="Andrew Murray")
        other = Author.objects.create(slug="cs", name="Charles Spurgeon")

        def book(slug, author, title):
            b = Book.objects.create(author=author, slug=slug, language="en", title=title)
            Chapter.objects.create(book=b, order=1, title="One", body_html="<p>a b c</p>")
            return b

        # subject 'a' plus candidates. 'b' shares two topics, 'c' one, 'd' none
        # (but is by the same author), 'e' is unrelated (no topic, other author).
        book("a", self.murray, "A")
        book("b", other, "B")
        book("c", other, "C")
        book("d", self.murray, "D")  # same author, no shared topic
        book("e", other, "E")  # unrelated

        t1 = Topic.objects.create(slug="t1", title="T1")
        t2 = Topic.objects.create(slug="t2", title="T2")
        for slug in ("a", "b", "c"):
            TopicBook.objects.create(topic=t1, book_slug=slug)
        for slug in ("a", "b"):
            TopicBook.objects.create(topic=t2, book_slug=slug)

    def _related(self, slug="a", language="en"):
        res = self.client.get(f"/api/library/books/{slug}/?language={language}")
        self.assertEqual(res.status_code, 200)
        return [b["slug"] for b in res.data["related"]]

    def test_ranks_by_shared_topics_then_author(self):
        # b: 2 topics × 2 = 4; c: 1 topic × 2 = 2; d: same author = 1.
        self.assertEqual(self._related("a"), ["b", "c", "d"])

    def test_excludes_self_and_unrelated(self):
        related = self._related("a")
        self.assertNotIn("a", related)  # never suggest the book itself
        self.assertNotIn("e", related)  # no topic or author link

    def test_only_same_language_suggestions(self):
        # A Swahili copy of 'b' shares the slug but must not surface for English
        # 'a' — related is filtered to the requested language.
        Book.objects.create(author=self.murray, slug="b", language="sw", title="B sw")
        res = self.client.get("/api/library/books/a/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["related"])  # still finds the English matches
        self.assertEqual({b["language"] for b in res.data["related"]}, {"en"})

    def test_limited_to_six(self):
        big = Topic.objects.create(slug="big", title="Big")
        TopicBook.objects.create(topic=big, book_slug="a")
        for i in range(8):
            Book.objects.create(author=self.murray, slug=f"x{i}", language="en", title=f"X{i}")
            TopicBook.objects.create(topic=big, book_slug=f"x{i}")
        self.assertEqual(len(self._related("a")), 6)

    def test_no_topics_or_author_returns_empty(self):
        solo = Author.objects.create(slug="solo", name="Solo")
        b = Book.objects.create(author=solo, slug="solo-book", language="en", title="Solo")
        Chapter.objects.create(book=b, order=1, title="One", body_html="<p>x</p>")
        self.assertEqual(self._related("solo-book"), [])


class AvailableLanguagesTests(TestCase):
    """Detail endpoints report the locales a per-language work actually exists
    in, so the frontend advertises hreflang only for real translations (books,
    sermons, and plans have no English fallback — see hreflangFor)."""

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")

    def _book(self, slug, language, published=True):
        b = Book.objects.create(
            author=self.author, slug=slug, language=language,
            title=f"{slug} {language}", is_published=published,
        )
        Chapter.objects.create(book=b, order=1, title="One", body_html="<p>x</p>")
        return b

    def test_book_detail_lists_published_locales_sorted(self):
        self._book("humility", "en")
        self._book("humility", "sw")
        self._book("humility", "es")
        res = self.client.get("/api/library/books/humility/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["available_languages"], ["en", "es", "sw"])

    def test_book_detail_excludes_unpublished_and_modern_edition(self):
        self._book("humility", "en")
        self._book("humility", "lg", published=False)  # draft translation
        self._book("humility", "en-modern")  # in-page toggle, not a locale
        res = self.client.get("/api/library/books/humility/?language=en")
        self.assertEqual(res.data["available_languages"], ["en"])

    def test_chapter_detail_uses_the_books_locales(self):
        self._book("humility", "en")
        self._book("humility", "lg")
        res = self.client.get("/api/library/books/humility/chapters/1/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["available_languages"], ["en", "lg"])

    def test_sermon_detail_lists_published_locales(self):
        for lang in ("en", "lg"):
            Sermon.objects.create(
                author=self.author, slug="himself", language=lang,
                title=f"Himself {lang}", body_html="<p>x</p>",
            )
        Sermon.objects.create(
            author=self.author, slug="himself", language="sw",
            title="Himself sw", body_html="<p>x</p>", is_published=False,
        )
        res = self.client.get("/api/library/sermons/himself/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["available_languages"], ["en", "lg"])

    def test_plan_detail_lists_published_locales(self):
        for lang in ("en", "sw"):
            p = Plan.objects.create(slug="prayer", language=lang, title=f"Prayer {lang}")
            PlanDay.objects.create(plan=p, day=1, book_slug="humility", chapter_order=1)
        res = self.client.get("/api/library/plans/prayer/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["available_languages"], ["en", "sw"])


class AdminStatsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray", bio="Preacher.")
        Author.objects.create(slug="cs", name="Charles Spurgeon")  # no bio

        en = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        Chapter.objects.create(book=en, order=1, title="One", body_html="<p>one two three</p>")
        Chapter.objects.create(book=en, order=2, title="Two", body_html="<p>four five</p>")
        # A published Swahili AI translation and an unpublished English draft.
        Book.objects.create(
            author=author,
            slug="humility",
            language="sw",
            title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Book.objects.create(
            author=author, slug="secret", language="en", title="Draft", is_published=False
        )
        Sermon.objects.create(
            author=author, slug="all-of-grace", language="en", title="All of Grace",
            body_html="<p>grace</p>", word_count=120,
        )
        Plan.objects.create(slug="p1", language="en", title="Plan One")

    @override_settings(DEBUG=True)
    def test_totals_and_language_breakdown(self):
        res = self.client.get("/api/admin/stats/")
        self.assertEqual(res.status_code, 200)
        totals = res.data["totals"]
        self.assertEqual(totals["works"], 2)  # humility, secret
        self.assertEqual(totals["books"], 3)
        self.assertEqual(totals["published_books"], 2)
        self.assertEqual(totals["unpublished_books"], 1)
        self.assertEqual(totals["chapters"], 2)
        self.assertEqual(totals["authors"], 2)
        self.assertEqual(totals["authors_with_bio"], 1)
        self.assertEqual(totals["languages"], 2)

        langs = {row["code"]: row for row in res.data["languages"]}
        self.assertEqual(langs["en"]["books"], 2)
        self.assertEqual(langs["en"]["chapters"], 2)
        self.assertEqual(langs["sw"]["source_types"]["ai_unreviewed"], 1)
        # English comes first (owner language), then by book count.
        self.assertEqual(res.data["languages"][0]["code"], "en")

    @override_settings(DEBUG=True)
    def test_attention_flags(self):
        res = self.client.get("/api/admin/stats/")
        attn = res.data["attention"]
        self.assertEqual(attn["unpublished_books"], 1)
        self.assertEqual(attn["unreviewed_translations"], 1)
        self.assertEqual(attn["authors_without_bio"], 1)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_forbidden_without_admin_email(self):
        # Anonymous → 401 (authenticate), a signed-in non-admin would get 403.
        res = self.client.get("/api/admin/stats/")
        self.assertIn(res.status_code, (401, 403))

    @override_settings(DEBUG=True)
    def test_language_bios_count(self):
        # A translated long-form bio counts toward the language's bios tally.
        from .models import Author, AuthorTranslation

        murray = Author.objects.get(slug="am")
        murray.bio_html = "<p>Long English bio.</p>"
        murray.save(update_fields=["bio_html"])
        AuthorTranslation.objects.create(
            author=murray, language="sw", bio_html="<p>Wasifu.</p>", reviewed=True
        )
        langs = {row["code"]: row for row in self.client.get("/api/admin/stats/").data["languages"]}
        self.assertEqual(langs["en"]["bios"], 1)
        self.assertEqual(langs["sw"]["bios"], 1)


class AdminLanguageDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.murray = Author.objects.create(
            slug="am", name="Andrew Murray", bio="Preacher.", bio_html="<p>Bio.</p>"
        )
        # Two published English books; one translated to Swahili.
        for i, slug in enumerate(("humility", "abide", "with-christ")):
            b = Book.objects.create(
                author=self.murray, slug=slug, language="en", title=slug.title(),
                sort_order=i,
            )
            Chapter.objects.create(book=b, order=1, title="One", body_html="<p>x</p>")
        Book.objects.create(
            author=self.murray, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Sermon.objects.create(
            author=self.murray, slug="grace", language="en", title="Grace",
            body_html="<p>g</p>", word_count=10,
        )
        Plan.objects.create(slug="p1", language="en", title="Plan One")

    @override_settings(DEBUG=True)
    def test_present_and_todo_for_translation_language(self):
        res = self.client.get("/api/admin/languages/sw/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_source"])
        self.assertEqual(res.data["language"]["name"], "Swahili")

        # Present: the one translated book, nothing else yet.
        self.assertEqual([b["slug"] for b in res.data["books"]], ["humility"])
        self.assertEqual(res.data["sermons"], [])

        # Todo: highest-priority English books not yet in Swahili, by sort_order,
        # excluding the already-translated "humility".
        todo_slugs = [b["slug"] for b in res.data["todo"]["books"]]
        self.assertEqual(todo_slugs, ["abide", "with-christ"])
        self.assertEqual([s["slug"] for s in res.data["todo"]["sermons"]], ["grace"])
        self.assertEqual([p["slug"] for p in res.data["todo"]["plans"]], ["p1"])
        # Murray's bio isn't translated to Swahili yet → he's a bio todo.
        self.assertEqual([a["slug"] for a in res.data["todo"]["bios"]], ["am"])

        self.assertEqual(res.data["english_counts"]["books"], 3)

    @override_settings(DEBUG=True)
    def test_sermon_todo_round_robins_across_authors(self):
        # Five more Murray sermons would fill the todo list by sort_order alone;
        # the list should instead lead with one sermon per preacher and only
        # repeat an author once every preacher is represented.
        moody = Author.objects.create(slug="dm", name="Dwight Moody", bio="P.")
        for i, slug in enumerate(("m1", "m2", "m3", "m4", "m5"), start=1):
            Sermon.objects.create(
                author=self.murray, slug=slug, language="en", title=slug.upper(),
                body_html="<p>x</p>", word_count=10, sort_order=i,
            )
        Sermon.objects.create(
            author=moody, slug="fire", language="en", title="Fire",
            body_html="<p>f</p>", word_count=10, sort_order=99,
        )
        todo = self.client.get("/api/admin/languages/sw/").data["todo"]["sermons"]
        # Murray's best ("grace", sort_order 0), then Moody's only sermon despite
        # its low priority, then back to Murray's queue in order once Moody's is
        # exhausted. (Six candidates here, under TODO_LIMIT, so none are cut.)
        self.assertEqual(
            [s["slug"] for s in todo], ["grace", "fire", "m1", "m2", "m3", "m4", "m5"]
        )

    @override_settings(DEBUG=True)
    def test_bio_todo_ranks_by_how_much_the_author_carries(self):
        """The bio queue leads with the authors most of the library hangs off.

        A translated bio is what a reader reaches from any of that author's
        works, so it pays back in proportion to how many they have. Murray
        (3 books + 1 sermon here) must outrank an author with a single sermon,
        whatever the alphabet says.
        """
        prolific = Author.objects.create(
            slug="zz-many", name="Zebedee Many", bio="P.", bio_html="<p>b</p>"
        )
        for i, slug in enumerate(("z1", "z2", "z3", "z4"), start=1):
            Sermon.objects.create(
                author=prolific, slug=slug, language="en", title=slug.upper(),
                body_html="<p>x</p>", word_count=10, sort_order=i,
            )
        Author.objects.create(
            slug="aa-one", name="Aaron One", bio="P.", bio_html="<p>b</p>"
        )
        todo = self.client.get("/api/admin/languages/sw/").data["todo"]["bios"]
        # Zebedee (4 works) first, Murray (3 books + 1 sermon) — tied on total,
        # but books break the tie — then Aaron, who carries nothing, last
        # despite sorting first alphabetically.
        self.assertEqual([a["slug"] for a in todo], ["am", "zz-many", "aa-one"])
        self.assertEqual(todo[0]["book_count"], 3)
        self.assertEqual(todo[0]["sermon_count"], 1)
        self.assertEqual(todo[2]["book_count"], 0)

    @override_settings(DEBUG=True)
    def test_source_language_has_no_todo(self):
        res = self.client.get("/api/admin/languages/en/")
        self.assertTrue(res.data["is_source"])
        self.assertEqual(len(res.data["books"]), 3)
        self.assertEqual(res.data["todo"]["books"], [])
        self.assertEqual([a["slug"] for a in res.data["bios"]], ["am"])

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/languages/sw/")
        self.assertIn(res.status_code, (401, 403))


class AdminCoverageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(author=author, slug="humility", language="en", title="Humility", sort_order=0)
        Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED, sort_order=0,
        )
        Book.objects.create(author=author, slug="abide", language="en", title="Abide", sort_order=1)
        Sermon.objects.create(author=author, slug="grace", language="en", title="Grace", body_html="<p>g</p>")
        Plan.objects.create(slug="p1", language="es", title="Plan Uno")

    @override_settings(DEBUG=True)
    def test_matrix_shape_and_cells(self):
        res = self.client.get("/api/admin/coverage/")
        self.assertEqual(res.status_code, 200)

        # Columns are the union of all content languages, English first.
        codes = [lang["code"] for lang in res.data["languages"]]
        self.assertEqual(codes[0], "en")
        self.assertEqual(set(codes), {"en", "sw", "es"})

        books = {b["slug"]: b for b in res.data["books"]}
        # Canonical title comes from the English row; cells carry source_type.
        self.assertEqual(books["humility"]["title"], "Humility")
        self.assertEqual(books["humility"]["cells"]["en"], "public_domain")
        self.assertEqual(books["humility"]["cells"]["sw"], "ai_unreviewed")
        self.assertNotIn("es", books["humility"]["cells"])  # missing → absent
        # Rows ordered by sort_order.
        self.assertEqual([b["slug"] for b in res.data["books"]], ["humility", "abide"])

        self.assertEqual(res.data["sermons"][0]["cells"], {"en": "present"})
        self.assertEqual(res.data["plans"][0]["cells"], {"es": "present"})

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/coverage/")
        self.assertIn(res.status_code, (401, 403))


class AdminReviewQueueTests(TestCase):
    def setUp(self):
        from .models import AuthorTranslation

        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        # A reviewed book and a public-domain original should NOT appear.
        Book.objects.create(
            author=self.author, slug="abide", language="es", title="Permaneced",
            source_type=Book.SourceType.AI_REVIEWED,
        )
        Book.objects.create(author=self.author, slug="humility", language="en", title="Humility")
        self.tr = AuthorTranslation.objects.create(
            author=self.author, language="sw", bio_html="<p>Wasifu.</p>", reviewed=False
        )
        AuthorTranslation.objects.create(
            author=self.author, language="es", bio="Bio.", reviewed=True
        )  # reviewed → excluded

    @override_settings(DEBUG=True)
    def test_lists_only_unreviewed(self):
        # The payload is a single filtered/paged `results` list across all three
        # content types, not per-type arrays — sermons were invisible while the
        # shape was {books, bios}. See tests_review_queue for the full contract.
        res = self.client.get("/api/admin/review-queue/")
        self.assertEqual(res.status_code, 200)
        rows = res.data["results"]
        books = [r for r in rows if r["kind"] == "book"]
        bios = [r for r in rows if r["kind"] == "bio"]
        self.assertEqual([b["slug"] for b in books], ["humility"])
        self.assertEqual(books[0]["language"], "sw")
        self.assertEqual([b["language"] for b in bios], ["sw"])
        self.assertTrue(bios[0]["has_long"])

    @override_settings(DEBUG=True)
    def test_approve_book_flips_source_type(self):
        res = self.client.post(
            "/api/admin/review-queue/",
            {"kind": "book", "slug": "humility", "language": "sw"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)
        # It drops out of the queue afterwards.
        follow = self.client.get("/api/admin/review-queue/")
        self.assertEqual([r for r in follow.data["results"] if r["kind"] == "book"], [])

    @override_settings(DEBUG=True)
    def test_approve_bio_marks_reviewed(self):
        res = self.client.post(
            "/api/admin/review-queue/",
            {"kind": "bio", "slug": "am", "language": "sw"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.tr.refresh_from_db()
        self.assertTrue(self.tr.reviewed)

    @override_settings(DEBUG=True)
    def test_approve_public_domain_book_rejected(self):
        res = self.client.post(
            "/api/admin/review-queue/",
            {"kind": "book", "slug": "humility", "language": "en"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=True)
    def test_bad_payload_rejected(self):
        res = self.client.post(
            "/api/admin/review-queue/", {"kind": "book"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/review-queue/")
        self.assertIn(res.status_code, (401, 403))


class AdminAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(author=self.author, slug="humility", language="en", title="Humility")
        # ch1: generic title + doesn't end in terminal punctuation (mid-split, has next).
        Chapter.objects.create(book=self.book, order=1, title="Chapter I", body_html="<p>text runs on</p>", word_count=300)
        # ch2: empty chapter (also an order gap will exist since order 3 skipped).
        Chapter.objects.create(book=self.book, order=2, title="Real Title", body_html="", word_count=0)
        # ch4: starts lowercase (missing drop cap); order 3 is missing → gap.
        Chapter.objects.create(book=self.book, order=4, title="Good", body_html="<p>and so it began.</p>", word_count=200)
        # A book with no chapters at all.
        Book.objects.create(author=self.author, slug="empty", language="en", title="Empty Book")
        # A plan whose day points at a non-existent chapter.
        plan = Plan.objects.create(slug="p1", language="en", title="Plan One")
        PlanDay.objects.create(plan=plan, day=1, book_slug="humility", chapter_order=1)  # valid
        PlanDay.objects.create(plan=plan, day=2, book_slug="humility", chapter_order=99)  # broken

    @override_settings(DEBUG=True)
    def test_quality_checks(self):
        res = self.client.get("/api/admin/audit/")
        self.assertEqual(res.status_code, 200)
        q = res.data["quality"]
        gen = [(f["book"], f["order"]) for f in q["generic_titles"]["items"]]
        self.assertIn(("humility", 1), gen)
        mids = [(f["book"], f["order"]) for f in q["mid_sentence_splits"]["items"]]
        self.assertIn(("humility", 1), mids)  # order 1, has a later chapter, no terminal punct
        drops = [(f["book"], f["order"]) for f in q["missing_dropcap"]["items"]]
        self.assertIn(("humility", 4), drops)

    @override_settings(DEBUG=True)
    def test_integrity_checks(self):
        res = self.client.get("/api/admin/audit/")
        integ = res.data["integrity"]
        self.assertIn("empty", [b["book"] for b in integ["empty_books"]["items"]])
        self.assertIn(("humility", 2), [(c["book"], c["order"]) for c in integ["empty_chapters"]["items"]])
        gaps = {g["book"]: g["missing"] for g in integ["order_gaps"]["items"]}
        self.assertEqual(gaps.get("humility"), [3])
        broken = [(d["plan"], d["day"]) for d in integ["broken_plan_days"]["items"]]
        self.assertEqual(broken, [("p1", 2)])

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/audit/")
        self.assertIn(res.status_code, (401, 403))


class AdminEngagementTests(TestCase):
    def setUp(self):
        import uuid

        from django.contrib.auth import get_user_model

        from accounts.models import UserProfile
        from reading.models import ChapterMarks, ReadingProgress

        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        for i in (1, 2, 3):
            Chapter.objects.create(book=book, order=i, title=f"C{i}", body_html="<p>x</p>")
        Book.objects.create(author=author, slug="abide", language="en", title="Abide")

        User = get_user_model()
        self.p1 = UserProfile.objects.create(user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4())
        self.p2 = UserProfile.objects.create(user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4())

        # p1 finished humility (ch3 of 3) + started abide; p2 at humility ch1.
        ReadingProgress.objects.create(profile=self.p1, book_slug="humility", language="en", chapter_order=3)
        ReadingProgress.objects.create(profile=self.p2, book_slug="humility", language="en", chapter_order=1)
        ReadingProgress.objects.create(profile=self.p1, book_slug="abide", language="en", chapter_order=1)
        ChapterMarks.objects.create(
            profile=self.p1, book_slug="humility", language="en", chapter_order=1,
            marks=[{"id": "a", "p": 0, "s": 0, "e": 5}],
        )

    @override_settings(DEBUG=True)
    def test_overview_and_rollups(self):
        res = self.client.get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        ov = res.data["overview"]
        self.assertEqual(ov["readers"], 2)
        self.assertEqual(ov["total_users"], 2)
        self.assertEqual(ov["active_7d"], 2)
        self.assertEqual(ov["readers_with_marks"], 1)
        self.assertEqual(ov["marked_chapters"], 1)

        most = {b["slug"]: b for b in res.data["most_read"]}
        self.assertEqual(most["humility"]["readers"], 2)
        self.assertEqual(most["humility"]["finishers"], 1)  # only p1 reached ch3
        self.assertEqual(most["abide"]["readers"], 1)

        self.assertEqual(res.data["most_marked"][0]["slug"], "humility")
        by_lang = {r["code"]: r["readers"] for r in res.data["by_language"]}
        self.assertEqual(by_lang["en"], 2)
        # 8 weekly buckets; this week has activity.
        self.assertEqual(len(res.data["weekly_active"]), 8)
        self.assertEqual(res.data["weekly_active"][-1]["readers"], 2)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/engagement/")
        self.assertIn(res.status_code, (401, 403))


class AdminUsersTests(TestCase):
    def setUp(self):
        import uuid

        from django.contrib.auth import get_user_model

        from accounts.models import UserProfile
        from reading.models import ReadingProgress

        self.client = APIClient()
        User = get_user_model()

        def mk(locale="en", theme="paper"):
            u = User.objects.create(username=str(uuid.uuid4()))
            return UserProfile.objects.create(
                user=u, supabase_uid=uuid.uuid4(), locale=locale, theme=theme
            )

        self.p1 = mk("en", "dark")
        self.p2 = mk("sw", "paper")
        self.p3 = mk("en", "paper")  # dormant (no progress)
        ReadingProgress.objects.create(profile=self.p1, book_slug="humility", language="en")
        ReadingProgress.objects.create(profile=self.p2, book_slug="humility", language="sw")

    @override_settings(DEBUG=True)
    def test_users_analytics(self):
        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["total"], 3)
        self.assertEqual(res.data["with_activity"], 2)
        self.assertEqual(res.data["dormant"], 1)
        self.assertEqual(res.data["signups_7d"], 3)

        by_locale = {r["code"]: r["count"] for r in res.data["by_locale"]}
        self.assertEqual(by_locale["en"], 2)
        self.assertEqual(by_locale["sw"], 1)
        by_theme = {r["theme"]: r["count"] for r in res.data["by_theme"]}
        self.assertEqual(by_theme["paper"], 2)
        self.assertEqual(by_theme["dark"], 1)

        self.assertEqual(len(res.data["weekly_signups"]), 12)
        self.assertEqual(res.data["weekly_signups"][-1]["count"], 3)  # all signed up this week

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/users/")
        self.assertIn(res.status_code, (401, 403))


class AdminBookDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        en = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        # ch1 has a next and doesn't end in punctuation → mid-split (+ no drop cap);
        # ch2 has a generic title and ends fine.
        Chapter.objects.create(book=en, order=1, title="Real", body_html="<p>runs on</p>", word_count=300)
        Chapter.objects.create(book=en, order=2, title="Chapter II", body_html="<p>All is well.</p>", word_count=200)
        Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )

    @override_settings(DEBUG=True)
    def test_book_detail_across_languages(self):
        res = self.client.get("/api/admin/books/humility/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["title"], "Humility")
        self.assertEqual(res.data["author"]["slug"], "am")

        langs = {lang["code"]: lang for lang in res.data["languages"]}
        self.assertEqual(res.data["languages"][0]["code"], "en")  # English first
        self.assertEqual(langs["en"]["word_count"], 500)
        chapters = {c["order"]: c for c in langs["en"]["chapters"]}
        self.assertIn("mid-split", chapters[1]["flags"])
        self.assertIn("generic-title", chapters[2]["flags"])
        self.assertNotIn("mid-split", chapters[2]["flags"])  # last chapter, no next
        self.assertEqual(langs["sw"]["source_type"], "ai_unreviewed")

    @override_settings(DEBUG=True)
    def test_unknown_slug_404(self):
        res = self.client.get("/api/admin/books/nope/")
        self.assertEqual(res.status_code, 404)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/books/humility/")
        self.assertIn(res.status_code, (401, 403))


class AdminExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray", bio="x")
        b = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        Chapter.objects.create(book=b, order=1, title="One", body_html="<p>x</p>", word_count=100)
        Sermon.objects.create(author=author, slug="grace", language="en", title="Grace", body_html="<p>g</p>", word_count=50)
        Plan.objects.create(slug="p1", language="en", title="Plan One")

    @override_settings(DEBUG=True)
    def test_json_inventory(self):
        res = self.client.get("/api/admin/export/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["books"][0]["chapters"], 1)
        self.assertEqual(res.data["books"][0]["words"], 100)
        self.assertEqual(res.data["sermons"][0]["slug"], "grace")
        self.assertEqual(res.data["plans"][0]["slug"], "p1")
        self.assertEqual(res.data["authors"][0]["has_bio"], True)

    @override_settings(DEBUG=True)
    def test_csv_inventory(self):
        res = self.client.get("/api/admin/export/?fmt=csv")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", res["Content-Disposition"])
        body = res.content.decode()
        self.assertIn("type,slug,language,title", body)
        self.assertIn("book,humility,en,Humility", body)
        self.assertIn("sermon,grace,en,Grace", body)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/export/")
        self.assertIn(res.status_code, (401, 403))


class ScriptureTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_annotate_wraps_valid_references_only(self):
        from library.scripture import annotate_references

        html = "<p>As John 3:16 says, and see Romans 8:28. But Room 3:16 is not.</p>"
        out = annotate_references(html)
        self.assertIn('<a class="scripture-ref" data-ref="John 3:16">John 3:16</a>', out)
        self.assertIn('data-ref="Romans 8:28"', out)
        self.assertNotIn('data-ref="Room 3:16"', out)  # not a real book
        self.assertIn("Room 3:16 is not", out)

    def test_annotate_skips_attributes_and_existing_anchors(self):
        from library.scripture import annotate_references

        # Reference inside an existing <a> must not be double-wrapped.
        html = '<p><a href="/x">John 3:16</a></p>'
        self.assertEqual(annotate_references(html).count("<a"), 1)
        self.assertEqual(annotate_references(""), "")

    def test_lookup_endpoint_returns_asv_text(self):
        res = self.client.get("/api/library/scripture/?ref=John 3:16")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["reference"], "John 3:16")
        self.assertEqual(res.data["verses"][0]["number"], 16)
        self.assertIn("God so loved the world", res.data["verses"][0]["text"])
        self.assertEqual(res.data["version"], "American Standard Version")

    def test_lookup_endpoint_range(self):
        res = self.client.get("/api/library/scripture/?ref=Romans 8:28-29")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["verses"]), 2)

    def test_lookup_endpoint_bad_and_missing(self):
        self.assertEqual(self.client.get("/api/library/scripture/").status_code, 400)
        self.assertEqual(
            self.client.get("/api/library/scripture/?ref=Nope 1:1").status_code, 404
        )

    def test_sermon_body_references_are_annotated(self):
        author = Author.objects.create(slug="cs-scrip", name="Charles Spurgeon")
        Sermon.objects.create(
            author=author,
            slug="faith-and-life",
            language="en",
            title="Faith and Life",
            body_html="<p>Consider Hebrews 11:1 and take heart.</p>",
            sort_order=1,
        )
        res = self.client.get("/api/library/sermons/faith-and-life/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertIn(
            '<a class="scripture-ref" data-ref="Hebrews 11:1">Hebrews 11:1</a>',
            res.data["body_html"],
        )
        # The reader header needs the author's portrait.
        self.assertIn("author_photo", res.data)


class _FakeUsage:
    input_tokens = 120
    output_tokens = 240


class _FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]
        self.usage = _FakeUsage()


class _FakeStream:
    def __init__(self, message):
        self._message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._message


class _FakeMessages:
    """Stands in for anthropic client.messages — stream() for the body,
    create() for the structured scripture-ref call."""

    def stream(self, **kwargs):
        return _FakeStream(
            _FakeMessage(
                "<chapter_title>El Nuevo Nacimiento</chapter_title>"
                "<chapter_body><p>Debéis nacer de nuevo.</p></chapter_body>"
            )
        )

    def create(self, **kwargs):
        return _FakeMessage('{"reference": "Juan 3:3"}')


class _FakeClient:
    def __init__(self, *a, **k):
        self.messages = _FakeMessages()


class _FakeModernMessages:
    """Stands in for the client used by the contemporize careful pass: returns a
    modernized chapter in the same <chapter_title>/<chapter_body> wrapper."""

    def stream(self, **kwargs):
        return _FakeStream(
            _FakeMessage(
                "<chapter_title>Of Humility</chapter_title>"
                "<chapter_body><p>You must be born again.</p></chapter_body>"
            )
        )


class _FakeModernClient:
    def __init__(self, *a, **k):
        self.messages = _FakeModernMessages()


from unittest.mock import patch  # noqa: E402


# No Bible API network. Returns a minimal valid chapter rather than None: the
# translate_* preflight (verify_bible_code) treats an unresolvable code as fatal,
# and these tests exercise the translation flow, not a broken configuration.
@patch(
    "library.translation.fetch_chapter",
    return_value={"reference": "John 3", "verses": [{"number": 3, "text": "…"}]},
)
@patch(
    "library.management.commands.translate_sermon.anthropic.Anthropic",
    new=_FakeClient,
)
class SermonTranslationTests(TestCase):
    def setUp(self):
        from django.core.management import call_command  # noqa: F401

        self.author = Author.objects.create(slug="cs", name="Charles Spurgeon")
        self.source = Sermon.objects.create(
            author=self.author,
            slug="the-new-birth",
            language="en",
            title="The New Birth",
            scripture_ref="John 3:3",
            body_html="<p>You must be born again.</p>",
            sort_order=4,
        )

    def _translate(self, language="es"):
        from django.core.management import call_command

        call_command("translate_sermon", "the-new-birth", language=language)

    def test_creates_ai_unreviewed_translation(self, _fetch):
        self._translate("es")
        s = Sermon.objects.get(slug="the-new-birth", language="es")
        self.assertEqual(s.source_type, "ai_unreviewed")
        self.assertEqual(s.title, "El Nuevo Nacimiento")
        self.assertIn("Debéis nacer de nuevo", s.body_html)
        self.assertEqual(s.scripture_ref, "Juan 3:3")
        self.assertEqual(s.author, self.author)
        self.assertEqual(s.sort_order, 4)
        self.assertTrue(s.is_published)

    def test_derives_body_text_and_word_count(self, _fetch):
        self._translate("es")
        s = Sermon.objects.get(slug="the-new-birth", language="es")
        self.assertEqual(s.body_text, "Debéis nacer de nuevo.")
        self.assertGreater(s.word_count, 0)

    def test_idempotent_without_force(self, _fetch):
        self._translate("es")
        self._translate("es")  # second run should skip, not duplicate
        self.assertEqual(
            Sermon.objects.filter(slug="the-new-birth", language="es").count(), 1
        )

    def test_unknown_slug_errors(self, _fetch):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("translate_sermon", "nope", language="es")

    def test_approve_flips_to_reviewed(self, _fetch):
        from django.core.management import call_command

        self._translate("es")
        call_command("approve_sermon_translation", "the-new-birth", language="es", no_fixture=True)
        s = Sermon.objects.get(slug="the-new-birth", language="es")
        self.assertEqual(s.source_type, "ai_reviewed")

    def test_approve_rejects_public_domain_original(self, _fetch):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("approve_sermon_translation", "the-new-birth", language="en", no_fixture=True)


class AdminTranslationJobsTests(TestCase):
    """The admin translation queue: buttons → GitHub issues (mocked GitHub)."""

    @classmethod
    def setUpTestData(cls):
        author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        Book.objects.create(
            author=author,
            slug="the-inner-chamber",
            language="en",
            title="The Inner Chamber",
        )
        Book.objects.create(
            author=author,
            slug="the-inner-chamber",
            language="lg",
            title="Ekisenge Eky'omunda",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Sermon.objects.create(
            author=author, slug="himself", language="en", title="Himself",
            body_html="<p>x</p>", word_count=10,
        )
        # An English plan and an author with a long-form bio, so plan/bio jobs
        # have real English sources to resolve against.
        Plan.objects.create(slug="humility-12-days", language="en", title="Humility in 12 Days")
        author.bio_html = "<p>A long-form biography.</p>"
        author.save(update_fields=["bio_html"])

    def setUp(self):
        self.client = APIClient()

    @staticmethod
    def _issue(title, labels=("translation-job",), number=7):
        return {
            "title": title,
            "labels": [{"name": name} for name in labels],
            "html_url": f"https://github.com/o/r/issues/{number}",
            "number": number,
            "created_at": "2026-07-16T00:00:00Z",
        }

    @override_settings(DEBUG=True)
    def test_get_unconfigured(self):
        res = self.client.get("/api/admin/translation-jobs/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, {"configured": False, "jobs": []})

    @override_settings(DEBUG=True)
    def test_post_unconfigured_is_503(self):
        res = self.client.post(
            "/api/admin/translation-jobs/",
            {"type": "book", "slug": "humility", "language": "lg"},
            format="json",
        )
        self.assertEqual(res.status_code, 503)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_validation(self):
        from unittest.mock import patch

        cases = [
            ({"type": "essay", "slug": "humility", "language": "lg"}, 400),  # unknown type
            ({"type": "book", "slug": "humility", "language": "en"}, 400),  # source language
            ({"type": "book", "slug": "humility", "language": "xx"}, 400),  # unknown code
            ({"type": "book", "slug": "nope", "language": "lg"}, 404),  # no English source
            ({"type": "book", "slug": "the-inner-chamber", "language": "lg"}, 409),  # exists
            ({"type": "plan", "slug": "nope", "language": "lg"}, 404),  # no English plan
            ({"type": "bio", "slug": "nope", "language": "lg"}, 404),  # no author with a bio
            ({"type": "topic", "slug": "nope", "language": "lg"}, 404),  # no such shelf
        ]
        with patch("library.admin_views.jobs.requests"):
            for body, expected in cases:
                res = self.client.post("/api/admin/translation-jobs/", body, format="json")
                self.assertEqual(res.status_code, expected, body)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_creates_issue(self):
        from unittest.mock import MagicMock, patch

        with patch("library.admin_views.jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
            created = self._issue("[translation] book:humility -> lg")
            gh.post.return_value = MagicMock(
                json=lambda: created, raise_for_status=lambda: None
            )
            res = self.client.post(
                "/api/admin/translation-jobs/",
                {"type": "book", "slug": "humility", "language": "lg"},
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["created"])
        self.assertEqual(res.data["job"]["slug"], "humility")
        self.assertEqual(res.data["job"]["state"], "queued")
        # The issue was filed with the deterministic title + queue label.
        payload = gh.post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "[translation] book:humility -> lg")
        self.assertEqual(payload["labels"], ["translation-job"])
        self.assertIn("Humility", payload["body"])

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_creates_plan_and_bio_issues(self):
        from unittest.mock import MagicMock, patch

        for type_, slug, marker in (
            ("plan", "humility-12-days", "Humility in 12 Days"),
            ("bio", "andrew-murray", "Andrew Murray"),
        ):
            title = f"[translation] {type_}:{slug} -> lg"
            with patch("library.admin_views.jobs.requests") as gh:
                gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
                gh.post.return_value = MagicMock(
                    json=lambda t=title: self._issue(t), raise_for_status=lambda: None
                )
                res = self.client.post(
                    "/api/admin/translation-jobs/",
                    {"type": type_, "slug": slug, "language": "lg"},
                    format="json",
                )
            self.assertEqual(res.status_code, 201, type_)
            self.assertEqual(res.data["job"]["type"], type_)
            payload = gh.post.call_args.kwargs["json"]
            self.assertEqual(payload["title"], title)
            self.assertIn(marker, payload["body"])

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_duplicate_returns_existing(self):
        from unittest.mock import MagicMock, patch

        existing = self._issue("[translation] book:humility -> lg")
        with patch("library.admin_views.jobs.requests") as gh:
            gh.get.return_value = MagicMock(
                json=lambda: [existing], raise_for_status=lambda: None
            )
            res = self.client.post(
                "/api/admin/translation-jobs/",
                {"type": "book", "slug": "humility", "language": "lg"},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["created"])
        gh.post.assert_not_called()

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_get_lists_jobs_with_state(self):
        from unittest.mock import MagicMock, patch

        issues = [
            self._issue("[translation] book:humility -> lg"),
            self._issue(
                "[translation] sermon:himself -> sw",
                labels=("translation-job", "in-progress"),
                number=8,
            ),
            self._issue("unrelated issue", number=9),  # ignored: not a job title
        ]
        with patch("library.admin_views.jobs.requests") as gh:
            gh.get.return_value = MagicMock(
                json=lambda: issues, raise_for_status=lambda: None
            )
            res = self.client.get("/api/admin/translation-jobs/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["configured"])
        self.assertEqual(len(res.data["jobs"]), 2)
        self.assertEqual(res.data["jobs"][0]["state"], "queued")
        self.assertEqual(res.data["jobs"][1]["state"], "in_progress")

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/translation-jobs/")
        self.assertIn(res.status_code, (401, 403))


class ContemporizeLightTests(TestCase):
    """The deterministic light modernization pass (no model, no key)."""

    def test_pronoun_and_verb_phrases(self):
        from library.contemporize import modernize_light

        self.assertEqual(modernize_light("Thou art mine."), "You are mine.")
        self.assertEqual(modernize_light("What hast thou done?"), "What have you done?")
        self.assertEqual(
            modernize_light("He hath spoken; he cometh."), "He has spoken; he comes."
        )
        self.assertEqual(modernize_light("shew me thy ways"), "show me your ways")

    def test_case_is_preserved(self):
        from library.contemporize import modernize_light

        self.assertEqual(modernize_light("Thou knowest"), "You know")
        self.assertEqual(modernize_light("thou knowest"), "you know")

    def test_unlisted_words_and_html_untouched(self):
        from library.contemporize import modernize_light

        # A modern homograph ("art" the noun) and the HTML tags must survive.
        self.assertEqual(
            modernize_light("<p>the fine art of prayer</p>"),
            "<p>the fine art of prayer</p>",
        )
        self.assertEqual(modernize_light("<em>God is love</em>"), "<em>God is love</em>")


class ContemporizeCommandTests(TestCase):
    """The light-mode command end to end: creates an en-modern edition."""

    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author,
            slug="humility",
            language="en",
            title="Humility",
            source_type=Book.SourceType.PUBLIC_DOMAIN,
            sort_order=3,
        )
        Chapter.objects.create(
            book=self.book,
            order=1,
            title="Thou Art Called",
            body_html="<p>Thou hast been called; walk thou humbly.</p>",
        )

    def _run(self, **kw):
        from django.core.management import call_command

        call_command("contemporize_book", "humility", **kw)

    def test_light_creates_modern_edition(self):
        self._run()  # default mode is light
        mb = Book.objects.get(slug="humility", language="en-modern")
        self.assertEqual(mb.source_type, "ai_unreviewed")
        self.assertEqual(mb.author, self.author)
        ch = mb.chapters.get(order=1)
        self.assertIn("You have been called", ch.body_html)
        self.assertNotIn("Thou", ch.body_html)
        self.assertNotIn("Thou", ch.title)
        self.assertIn("You are", ch.title)
        self.assertGreater(ch.word_count, 0)
        self.assertTrue(ch.body_text)  # derived on save

    def test_original_english_is_untouched(self):
        self._run()
        en = Chapter.objects.get(
            book__slug="humility", book__language="en", order=1
        )
        self.assertIn("Thou hast", en.body_html)

    def test_idempotent_without_force(self):
        self._run()
        self._run()
        self.assertEqual(
            Book.objects.filter(slug="humility", language="en-modern").count(), 1
        )
        self.assertEqual(
            Chapter.objects.filter(
                book__slug="humility", book__language="en-modern"
            ).count(),
            1,
        )

    def test_rejects_non_public_domain_source(self):
        from django.core.management.base import CommandError

        self.book.source_type = Book.SourceType.AI_UNREVIEWED
        self.book.save(update_fields=["source_type"])
        with self.assertRaises(CommandError):
            self._run()

    def test_approve_flips_modern_edition_to_reviewed(self):
        from django.core.management import call_command

        self._run()
        call_command("approve_translation", "humility", language="en-modern", no_fixture=True)
        mb = Book.objects.get(slug="humility", language="en-modern")
        self.assertEqual(mb.source_type, "ai_reviewed")

    def test_new_chapters_regate_an_approved_edition(self):
        # Approve the modern edition, then add a chapter to the English source
        # and re-run: the new chapter is unreviewed AI text, so the edition must
        # drop back to ai_unreviewed rather than silently staying "approved".
        from django.core.management import call_command

        self._run()
        call_command("approve_translation", "humility", language="en-modern", no_fixture=True)
        Chapter.objects.create(
            book=self.book,
            order=2,
            title="A Second Call",
            body_html="<p>Thou shalt walk humbly still.</p>",
        )

        self._run()  # no --force; only the new chapter 2 is contemporized

        mb = Book.objects.get(slug="humility", language="en-modern")
        self.assertEqual(mb.source_type, "ai_unreviewed")
        self.assertEqual(mb.chapters.count(), 2)

    def test_no_regate_when_nothing_new_is_translated(self):
        # Re-running with no new chapters must NOT walk back an approval.
        from django.core.management import call_command

        self._run()
        call_command("approve_translation", "humility", language="en-modern", no_fixture=True)
        self._run()  # nothing to do — chapter 1 already exists
        mb = Book.objects.get(slug="humility", language="en-modern")
        self.assertEqual(mb.source_type, "ai_reviewed")

    def test_api_exposes_modern_edition_flags(self):
        # Before an edition exists, the English book advertises none.
        res = self.client.get("/api/library/books/humility/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["has_modern_edition"])
        self.assertFalse(res.data["is_modern_edition"])

        # After contemporizing, the English book advertises it and the modern
        # row identifies itself.
        self._run()
        res = self.client.get("/api/library/books/humility/?language=en")
        self.assertTrue(res.data["has_modern_edition"])
        self.assertFalse(res.data["is_modern_edition"])

        res = self.client.get("/api/library/books/humility/?language=en-modern")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_modern_edition"])
        self.assertTrue(res.data["has_modern_edition"])
        # The chapter endpoint carries the same flags for the reader toggle.
        ch = self.client.get(
            "/api/library/books/humility/chapters/1/?language=en-modern"
        )
        self.assertTrue(ch.data["is_modern_edition"])


@patch(
    "library.management.commands.contemporize_book.anthropic.Anthropic",
    new=_FakeModernClient,
)
class ContemporizeCarefulTests(TestCase):
    """The model-backed careful mode, with a stubbed Anthropic client."""

    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author,
            slug="humility",
            language="en",
            title="Humility",
            source_type=Book.SourceType.PUBLIC_DOMAIN,
        )
        Chapter.objects.create(
            book=self.book,
            order=1,
            title="Of Humility",
            body_html="<p>Thou must be born again.</p>",
        )

    def test_careful_uses_model_output(self):
        from django.core.management import call_command

        call_command("contemporize_book", "humility", mode="careful")
        ch = Book.objects.get(slug="humility", language="en-modern").chapters.get(order=1)
        self.assertIn("You must be born again", ch.body_html)
        self.assertEqual(ch.book.source_type, "ai_unreviewed")


class ContentQAFixesTests(TestCase):
    """The 2026-07 QA body corrections (also enforced on every re-import)."""

    def test_nav_strip_spares_prose_and_scripture(self):
        """The trailing-nav strip must not eat "back to" / "return to" prose.

        Both phrases are ordinary English and this runs over sermons, so the
        pattern requires a navigation target AND last-element position. An
        earlier, looser version stripped all three of the negative cases below
        — two of which are scripture (Joel 2:13, Zechariah 1:3). Silent content
        loss: no error, just a missing line.
        """
        from library.management.commands.import_sermons import extract_web_sermon

        def body(fragment):
            html = f"<html><body><div>{fragment}</div></body></html>"
            return extract_web_sermon(html, "A Sermon")

        # Navigation goes.
        self.assertNotIn(
            "BOOTH INDEX",
            body("<p>...they SHALL.</p><b>Back to BOOTH INDEX Page</b>"),
        )
        # Prose and scripture stay.
        for keep in (
            "<p>Back to our text, then, and see what the Apostle means.</p>",
            "<p>Return to the Lord thy God, for he is gracious and merciful.</p>",
            "<p>Return to me, saith the Lord of hosts.</p>",
        ):
            self.assertIn(keep.split(">")[1][:24], body(keep))

    def test_blessed_adversity_transcription_slips(self):
        """The sermon corrections survive the small-caps unwrap they depend on.

        In Gutenberg #23438 the typo is markup, not text: the source reads
        ``S<small>HEPERD</small>``, so the literal string "SHEPERD" appears
        nowhere in the raw HTML. The replacement only matches because
        ``clean_fragment`` unwraps <small> first. Pin that dependency — if the
        sanitizer stops unwrapping, or PG re-transcribes with <span
        class="smcap">, the pair would no-op silently and the typo would come
        back on the next re-import with no error.
        """
        from library.corrections import apply_body_corrections
        from library.ingest import clean_fragment

        raw = (
            "<p>The believer who has taken the L<small>ORD</small> as his "
            "S<small>HEPERD</small>, can assuredly say that days of prosperity "
            "aso are full of blessing.</p>"
        )
        h = apply_body_corrections("blessed-adversity", 1, clean_fragment(raw))
        self.assertIn("as his SHEPHERD", h)
        self.assertNotIn("SHEPERD,", h)
        self.assertIn("days of prosperity also", h)

    def test_sermon_slug_never_takes_a_book_dropcap(self):
        """A sermon must not inherit a book's drop-cap letter by slug collision.

        Sermons pass ``order=None`` precisely so the drop-cap lookup misses:
        Book.slug and Sermon.slug are independently unique, so the two
        namespaces could collide, and a stray capital injected at the head of a
        sermon would be silent.
        """
        from library.corrections import BODY_CORRECTIONS, apply_body_corrections

        slug = next(
            (k for k, v in BODY_CORRECTIONS.items() if v.get("dropcap_letters")),
            None,
        )
        if slug is None:
            self.skipTest("no drop-cap entries to test against")
        body = "<p>alone at the beginning of a sermon.</p>"
        self.assertEqual(apply_body_corrections(slug, None, body), body)

    def test_corrections_have_no_duplicate_slugs(self):
        """A repeated slug key silently discards the first entry.

        Python keeps the last value for a duplicated key in a dict literal, so
        adding a second block for a book that already has one drops every
        correction in the original — with no error, and nothing to see in a
        diff that only shows the added lines. That happened while adding the
        drop-cap repairs; this is the guard.
        """
        import ast

        source = (Path(__file__).resolve().parent / "corrections.py").read_text()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Dict):
                target, value = node.target, node.value
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                target, value = node.targets[0], node.value
            else:
                continue
            if not isinstance(target, ast.Name):
                continue
            keys = [k.value for k in value.keys if isinstance(k, ast.Constant)]
            self.assertEqual(
                sorted(keys),
                sorted(set(keys)),
                f"{target.id} has a duplicated key, which silently drops the "
                f"earlier entry: {sorted(k for k in set(keys) if keys.count(k) > 1)}",
            )

    def test_inner_chamber_dashes_and_full_stop(self):
        from library.corrections import apply_body_corrections

        h = apply_body_corrections(
            "the-inner-chamber",
            5,
            "<p>practising the scales- only practice makes perfect- set yourself "
            "to learn thoroughly and to apply the needed first lessons</p>",
        )
        self.assertIn("the scales — only practice", h)
        self.assertIn("makes perfect — set", h)
        self.assertTrue(h.rstrip().endswith("apply the needed first lessons.</p>"))

    def test_unselfishness_ch22_full_stop(self):
        from library.corrections import apply_body_corrections

        self.assertIn(
            "filled me with joy.</p>",
            apply_body_corrections(
                "the-unselfishness-of-god", 22, "<p>read in the spirit — filled me with joy</p>"
            ),
        )

    def test_teens_heading_unfused_from_body(self):
        from library.corrections import apply_body_corrections

        h = apply_body_corrections(
            "the-body-of-christ-teens",
            1,
            "<p>Understanding the Life God Gives Us When God saves you, He does…</p>",
        )
        self.assertTrue(
            h.startswith("<h3>Understanding the Life God Gives Us</h3><p>When God saves you,")
        )

    def test_things_as_they_are_preface_rebuild(self):
        import importlib.util
        from pathlib import Path

        p = Path(__file__).resolve().parent / "migrations" / "0039_content_qa_fixes.py"
        spec = importlib.util.spec_from_file_location("m0038", str(p))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        # A sample carrying the Foreword signature, an Illustrations plate-list,
        # every glossary term jammed to its definition, and the title-page block.
        gloss = " ".join(f"{t}Def{i}." for i, t in enumerate(m.GLOSSARY_TERMS))
        body = (
            "<p>Foreword body.</p> EUGENE STOCK.<br/> "
            "<hr/><h3>Illustrations</h3>An Old Brahman A Potter at his Wheel "
            f"<hr/><h3>Glossary</h3>{gloss} "
            "<hr/><h3>Things as They Are</h3><h3>MISSION WORK IN SOUTHERN INDIA</h3> <hr/>"
        )
        out = m._rebuild_things_as_they_are_preface(body)
        self.assertIsNotNone(out)
        self.assertNotIn("Illustrations", out)
        self.assertNotIn("MISSION WORK IN SOUTHERN INDIA", out)
        self.assertIn("<p>— Eugene Stock</p>", out)
        # One clean entry per glossary term, no jammed "TermDef".
        self.assertEqual(out.count("<p><i>"), len(m.GLOSSARY_TERMS))
        self.assertIn("<p><i>Vishnu</i> — Def", out)
        # Idempotent: a second pass finds nothing to rebuild.
        self.assertIsNone(m._rebuild_things_as_they_are_preface(out))


@skipUnless(connection.vendor == "postgresql", "Stored search vectors are Postgres-only")
class StoredSearchVectorTests(TestCase):
    """The stored tsvector machinery (library/fts.py + migrations 0040/0041).

    Only runs on the Postgres CI leg / prod-shaped databases — SQLite search
    never reads search_vector.
    """

    def setUp(self):
        self.author = Author.objects.create(slug="john-wesley", name="John Wesley")
        self.book = Book.objects.create(
            author=self.author, slug="perfection", language="en",
            title="A Plain Account of Christian Perfection",
        )
        self.chapter = Chapter.objects.create(
            book=self.book, order=1, title="The Circumcision of the Heart",
            body_html="<p>Prayer is the lifting up of the heart to God.</p>",
        )
        self.sermon = Sermon.objects.create(
            author=self.author, slug="the-almost-christian", language="en",
            title="The Almost Christian", scripture_ref="Acts 26:28",
            body_html="<p>He runs the race that is set before him.</p>",
        )

    def _search(self, q, language="en"):
        from .search import search_library

        return search_library(q, language)

    def test_save_populates_vectors(self):
        self.chapter.refresh_from_db()
        self.sermon.refresh_from_db()
        self.assertIsNotNone(self.chapter.search_vector)
        self.assertIsNotNone(self.sermon.search_vector)

    def test_gin_indexes_exist(self):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes WHERE indexname IN "
                "('library_chapter_search_vector_gin', 'library_sermon_search_vector_gin')"
            )
            names = {row[0] for row in cur.fetchall()}
        self.assertEqual(
            names,
            {"library_chapter_search_vector_gin", "library_sermon_search_vector_gin"},
        )

    def test_author_name_baked_into_passage_vectors(self):
        # Recall parity with the old query-time vector: an author-name term
        # ANDed with a body term must still match the passage row itself.
        chapter_hits = [h for h in self._search("wesley prayer") if h["type"] == "chapter"]
        self.assertTrue(chapter_hits)
        sermon_hits = [h for h in self._search("wesley race") if h["type"] == "sermon"]
        self.assertTrue(sermon_hits)

    def test_english_config_stems(self):
        # body says "runs"; english config stems "running" to match it.
        hits = [h for h in self._search("running") if h["type"] == "sermon"]
        self.assertTrue(hits)

    def test_backfill_covers_fixture_loaded_rows(self):
        from django.core.management import call_command

        # bulk_create bypasses save(), like loaddata does on deploy.
        Chapter.objects.bulk_create([
            Chapter(book=self.book, order=2, title="On Zeal",
                    body_html="<p>x</p>", body_text="Let zeal be guided by knowledge."),
        ])
        self.assertFalse(
            any(h["type"] == "chapter" and "zeal" in h["snippet"].lower()
                for h in self._search("zeal"))
        )
        call_command("backfill_search_vectors", verbosity=0)
        self.assertTrue(
            any(h["type"] == "chapter" for h in self._search("zeal"))
        )

    def test_author_rename_cascades_into_work_vectors(self):
        # Author.save() ripples the new name into chapter + sermon vectors.
        self.author.name = "Juan Wesley"
        self.author.save()
        self.assertTrue(
            any(h["type"] == "chapter" for h in self._search("juan prayer"))
        )
        self.assertTrue(
            any(h["type"] == "sermon" for h in self._search("juan race"))
        )

    def test_book_retitle_cascades_into_chapter_vectors(self):
        self.book.title = "A Candid Account"
        self.book.save()
        self.assertTrue(
            any(h["type"] == "chapter" for h in self._search("candid prayer"))
        )

    def test_backfill_all_refreshes_after_save_bypassing_rename(self):
        from django.core.management import call_command

        # A queryset.update() rename bypasses the save cascade — vectors go
        # stale (documented edge)…
        Author.objects.filter(pk=self.author.pk).update(name="Juan Wesley")
        self.assertFalse(
            any(h["type"] == "chapter" for h in self._search("juan prayer"))
        )
        # …and --all is the documented remedy.
        call_command("backfill_search_vectors", "--all", verbosity=0)
        self.assertTrue(
            any(h["type"] == "chapter" for h in self._search("juan prayer"))
        )


class SermonBookFacetTests(TestCase):
    def test_scripture_book_derivation(self):
        from .scripture import book_of

        self.assertEqual(book_of("Malachi 3:6"), ("Malachi", 39))
        self.assertEqual(book_of("1 Peter 2:7"), ("1 Peter", 60))
        self.assertIsNone(book_of("Malaki 3:6"))  # localized ref: facet-less
        self.assertIsNone(book_of(""))

    def test_sermon_list_carries_book_facet(self):
        from rest_framework.test import APIClient

        author = Author.objects.create(slug="s", name="S")
        Sermon.objects.create(
            author=author, slug="x", language="en", title="X",
            scripture_ref="Malachi 3:6", body_html="<p>w</p>",
        )
        res = APIClient().get("/api/library/sermons/?language=en")
        row = next(r for r in res.data if r["slug"] == "x")
        self.assertEqual(row["scripture_book"], "Malachi")
        self.assertEqual(row["scripture_book_order"], 39)

    def test_sermon_list_carries_created_at(self):
        # The Atom feed orders newest-first by when a work was added; the sermon
        # list must expose created_at for that (books already do).
        from rest_framework.test import APIClient

        author = Author.objects.create(slug="s", name="S")
        Sermon.objects.create(
            author=author, slug="x", language="en", title="X", body_html="<p>w</p>"
        )
        res = APIClient().get("/api/library/sermons/?language=en")
        row = next(r for r in res.data if r["slug"] == "x")
        self.assertIn("created_at", row)
        self.assertTrue(row["created_at"])


class SearchLogTests(TestCase):
    """The anonymous search-query log + its admin analytics endpoint."""

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        book = Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(
            book=book, order=1, title="The Glory of the Creature",
            body_html="<p>Humility is the place of entire dependence on God.</p>",
        )

    def search(self, q, language="en"):
        return self.client.get(f"/api/library/search/?q={q}&language={language}")

    def test_search_is_logged(self):
        res = self.search("humility")
        self.assertEqual(res.status_code, 200)
        row = SearchQueryLog.objects.get()
        self.assertEqual(row.query, "humility")
        self.assertEqual(row.language, "en")
        self.assertGreater(row.result_count, 0)
        self.assertFalse(row.suggested)

    def test_zero_result_query_logged_with_suggestion_flag(self):
        res = self.search("humilty")  # typo → did-you-mean fires
        self.assertEqual(res.status_code, 200)
        # Pin the behaviour, not the implementation: the typo must actually
        # produce a hint, and the log row must record that it did.
        self.assertIn("suggestion", res.data)
        row = SearchQueryLog.objects.get()
        self.assertEqual(row.result_count, 0)
        self.assertTrue(row.suggested)

    def test_short_query_not_logged(self):
        self.search("h")
        self.assertEqual(SearchQueryLog.objects.count(), 0)

    def test_logging_failure_never_breaks_search(self):
        from unittest.mock import patch

        with patch.object(
            SearchQueryLog.objects, "create", side_effect=RuntimeError("db down")
        ):
            res = self.search("humility")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["results"])

    def test_trim_command_prunes_old_rows_only(self):
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        self.search("humility")  # fresh row
        old = SearchQueryLog.objects.create(
            query="ancient", language="en", result_count=0
        )
        SearchQueryLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=200)
        )
        call_command("trim_search_log", verbosity=0)
        remaining = list(SearchQueryLog.objects.values_list("query", flat=True))
        self.assertEqual(remaining, ["humility"])

    @override_settings(DEBUG=True)
    def test_admin_search_stats_aggregates(self):
        for q in ("humility", "humility", "Humility", "grace", "gr"):
            self.search(q)
        res = self.client.get("/api/admin/search-stats/")
        self.assertEqual(res.status_code, 200)
        ov = res.data["overview"]["30d"]
        self.assertEqual(ov["searches"], 5)
        # Case folds: humility×3 is one distinct query.
        self.assertEqual(ov["distinct_queries"], 3)
        top = {r["query"]: r["count"] for r in res.data["top_queries"]}
        self.assertEqual(top.get("humility"), 3)
        # Zero-result list holds the misses; the 2-char fragment is filtered out.
        zero = [r["query"] for r in res.data["zero_result_queries"]]
        self.assertIn("grace", zero)
        self.assertNotIn("gr", zero)
        self.assertEqual(res.data["by_language"][0]["code"], "en")
        self.assertEqual(res.data["by_language"][0]["name"], "English")
        # Zero-filled calendar series: always exactly 14 days, today last.
        self.assertEqual(len(res.data["daily"]), 14)
        self.assertEqual(res.data["daily"][-1]["searches"], 5)
        self.assertEqual(res.data["daily"][0]["searches"], 0)

    def test_language_param_truncated_to_field_length(self):
        # Postgres raises DataError past varchar(10); SQLite wouldn't catch it.
        self.search("humility", language="en-Latn-US-x-nonsense")
        row = SearchQueryLog.objects.get()
        self.assertEqual(row.language, "en-Latn-US")

    @override_settings(DEBUG=True)
    def test_unanswered_queries_are_split_by_language(self):
        # The global zero-result list mixes a Swahili gap with an English one,
        # and neither can be queued from it — a translation job targets ONE
        # language. So the report also carries the same misses per language.
        for _ in range(3):
            SearchQueryLog.objects.create(query="toba", language="sw", result_count=0)
        SearchQueryLog.objects.create(query="grace", language="en", result_count=0)
        SearchQueryLog.objects.create(query="humility", language="sw", result_count=7)

        res = self.client.get("/api/admin/search-stats/")
        self.assertEqual(res.status_code, 200)
        rows = {r["code"]: r for r in res.data["unanswered_by_language"]}
        self.assertEqual(rows["sw"]["name"], "Swahili")
        self.assertEqual(rows["sw"]["total"], 3)
        self.assertEqual(rows["sw"]["queries"], [{"query": "toba", "count": 3}])
        # A language whose searches all found something never appears.
        self.assertEqual([q["query"] for q in rows["en"]["queries"]], ["grace"])
        # Both sections of the report count a language's misses the same way —
        # they come from the same rows, so they cannot drift apart.
        totals = {r["code"]: r["zero"] for r in res.data["by_language"]}
        self.assertEqual({c: r["total"] for c, r in rows.items()},
                         {c: totals[c] for c in rows})

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_admin_search_stats_requires_admin(self):
        res = self.client.get("/api/admin/search-stats/")
        self.assertIn(res.status_code, (401, 403))


class SearchGapTests(TestCase):
    """Nobody found this — does it exist somewhere to translate FROM?

    The follow-up to the zero-result list, and what turns a gap into a job. It
    is an ADMIN planning signal: readers are never offered another language's
    results, because a language shows what it has.
    """

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        book = Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(
            book=book, order=1, title="The Glory of the Creature",
            body_html="<p>Humility is the place of entire dependence on God.</p>",
        )
        # Only live languages are searched, and the fixture's statuses are not
        # this test's subject — pin them. Saved rather than .update()d so the
        # post_save receiver drops the language display cache.
        for lang in Language.objects.filter(code__in=("en", "sw")):
            lang.status = Language.Status.LIVE
            lang.save(update_fields=["status"])

    def gap(self, q, language):
        return self.client.get(
            f"/api/admin/search-gap/?q={q}&language={language}"
        )

    @override_settings(DEBUG=True)
    def test_reports_where_the_content_already_exists(self):
        res = self.gap("humility", "sw")
        self.assertEqual(res.status_code, 200)
        rows = {r["code"]: r for r in res.data["elsewhere"]}
        self.assertIn("en", rows)
        self.assertGreater(rows["en"]["matches"], 0)
        # Broken down by type, so "one book" and "forty chapters" are different
        # sizes of job.
        self.assertIn("book", rows["en"]["by_type"])
        # The language that was searched is never listed against itself.
        self.assertNotIn("sw", rows)

    @override_settings(DEBUG=True)
    def test_nothing_anywhere_means_translation_will_not_help(self):
        # The distinction the whole endpoint exists to draw: this is a work to
        # acquire, not a work to translate.
        res = self.gap("theosis", "sw")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["elsewhere"], [])

    @override_settings(DEBUG=True)
    def test_a_missing_or_trivial_query_is_rejected(self):
        self.assertEqual(self.gap("humility", "").status_code, 400)
        self.assertEqual(self.gap("h", "sw").status_code, 400)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        self.assertIn(self.gap("humility", "sw").status_code, (401, 403))


class CitationIndexTests(TestCase):
    def _book(self, slug="cite-book", language="en"):
        author = Author.objects.create(slug=f"a-{slug}", name="A")
        return Book.objects.create(author=author, slug=slug, language=language, title=slug)

    def test_extract_citations_spans_and_dedupe(self):
        from .scripture import extract_citations

        cites = extract_citations(
            "See John 3:16 and again John 3:16; also 1 Cor 13:4-7. Room 5:1 is not a book."
        )
        by_ref = {c["ref"]: c for c in cites}
        self.assertEqual(set(by_ref), {"John 3:16", "1 Cor 13:4-7"})
        self.assertEqual(by_ref["John 3:16"]["count"], 2)
        j = by_ref["John 3:16"]
        self.assertEqual(j["start"], j["end"])  # single verse
        c = by_ref["1 Cor 13:4-7"]
        self.assertEqual(c["end"] - c["start"], 3)  # four-verse span

    def test_index_command_incremental_and_reindex_on_save(self):
        from django.core.management import call_command

        book = self._book()
        ch = Chapter.objects.create(
            book=book, order=1, title="T", body_html="<p>As John 3:16 says.</p>"
        )
        call_command("index_citations")
        self.assertEqual(ch.citations.count(), 1)
        stamped = Chapter.objects.get(pk=ch.pk).citations_indexed_at
        self.assertIsNotNone(stamped)

        # Second run touches nothing (stamp set).
        call_command("index_citations")
        self.assertEqual(
            Chapter.objects.get(pk=ch.pk).citations_indexed_at, stamped
        )

        # A body edit clears the stamp; next run re-indexes.
        ch.refresh_from_db()
        ch.body_html = "<p>Now Romans 8:28 instead.</p>"
        ch.save()
        self.assertIsNone(Chapter.objects.get(pk=ch.pk).citations_indexed_at)
        call_command("index_citations")
        refs = list(ch.citations.values_list("ref_text", flat=True))
        self.assertEqual(refs, ["Romans 8:28"])

    def test_search_finds_citing_chapters_by_overlap(self):
        from django.core.management import call_command

        book = self._book()
        Chapter.objects.create(
            book=book, order=1, title="Exact",
            body_html="<p>For God so loved the world (John 3:16).</p>",
        )
        Chapter.objects.create(
            book=book, order=2, title="Range",
            body_html="<p>The whole discourse (John 3:1-21) rewards study.</p>",
        )
        Chapter.objects.create(
            book=book, order=3, title="Other",
            body_html="<p>Psalm 23:1 comforts.</p>",
        )
        # Unpublished + wrong-language rows must not leak into results.
        hidden = self._book(slug="hidden-book")
        hidden.is_published = False
        hidden.save()
        Chapter.objects.create(
            book=hidden, order=1, title="H", body_html="<p>John 3:16 too.</p>"
        )
        lg = self._book(slug="cite-book-lg", language="lg")
        Chapter.objects.create(
            book=lg, order=1, title="L", body_html="<p>John 3:16 in lg body.</p>"
        )
        call_command("index_citations")

        from .search import search_library

        results = search_library("John 3:16", "en")
        chapter_hits = [
            (r["book_slug"], r["chapter_order"])
            for r in results
            if r["type"] == "chapter"
        ]
        self.assertIn(("cite-book", 1), chapter_hits)
        self.assertIn(("cite-book", 2), chapter_hits)  # range overlap
        self.assertNotIn(("cite-book", 3), chapter_hits)
        self.assertNotIn(("hidden-book", 1), chapter_hits)
        self.assertNotIn(("cite-book-lg", 1), chapter_hits)
        # exact citation ranks before the wide range, snippet is marker-wrapped
        exact = next(r for r in results if r.get("chapter_order") == 1)
        self.assertIn("⟦John 3:16⟧", exact["snippet"])
        self.assertLess(
            chapter_hits.index(("cite-book", 1)), chapter_hits.index(("cite-book", 2))
        )

    def test_multi_reference_query_uses_exact_intersection(self):
        """"John 3:16 and Romans 8:28" must not match everything in between."""
        from django.core.management import call_command

        book = self._book(slug="span-book")
        Chapter.objects.create(
            book=book, order=1, title="True1",
            body_html="<p>See John 3:16 for the promise.</p>",
        )
        Chapter.objects.create(
            book=book, order=2, title="True2",
            body_html="<p>And Romans 8:28 for the assurance.</p>",
        )
        # Falls inside min..max of the two references but overlaps neither.
        Chapter.objects.create(
            book=book, order=3, title="Between",
            body_html="<p>Acts 2:38 stands between them.</p>",
        )
        call_command("index_citations")

        from .search import search_library

        hits = [
            (r["book_slug"], r["chapter_order"])
            for r in search_library("John 3:16 and Romans 8:28", "en")
            if r["type"] == "chapter"
        ]
        self.assertIn(("span-book", 1), hits)
        self.assertIn(("span-book", 2), hits)
        self.assertNotIn(("span-book", 3), hits)

    def test_full_book_name_with_period_is_not_whole_book(self):
        """"Matthew. 1:23" must index one verse, not 28 chapters."""
        from .scripture import extract_citations

        cites = extract_citations("the words in Matthew. 1:23, well known.")
        self.assertEqual(len(cites), 1)
        self.assertEqual(cites[0]["start"], cites[0]["end"])  # single verse
        self.assertEqual(cites[0]["start"], 40001023)

    def test_bare_book_name_skips_citation_lead(self):
        """"Matthew" is a text query, not a whole-book citation sweep."""
        from django.core.management import call_command

        book = self._book(slug="matt-citer")
        Chapter.objects.create(
            book=book, order=1, title="C",
            body_html="<p>Matthew 5:3 opens the sermon.</p>",
        )
        call_command("index_citations")

        from .search import _base_querysets, _scripture_chapter_hits

        eligible = _base_querysets("en")["chapter"]
        self.assertEqual(_scripture_chapter_hits("Matthew", eligible), [])
        self.assertEqual(len(_scripture_chapter_hits("Matthew 5:3", eligible)), 1)


class LocalizedAuthorBioTests(TestCase):
    """The author mini-bio must follow the requested language everywhere.

    It shipped English on every localized book page: the nested
    AuthorSerializer returned the raw model field, and the book views never
    put `language` in the serializer context. Both halves are covered here.
    """

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(
            slug="gareth-evans", name="Gareth Evans", bio="An itinerant pastor."
        )
        AuthorTranslation.objects.create(
            author=self.author, language="lg", bio="Musumba atambulatambula."
        )
        for lang, title in (("en", "He Holds My Tomorrows"), ("lg", "Akwata Ennaku Zange")):
            book = Book.objects.create(
                author=self.author, slug="tomorrows", language=lang, title=title
            )
            Chapter.objects.create(book=book, order=1, title="One", body_html="<p>x</p>")
        Sermon.objects.create(
            author=self.author, slug="a-sermon", language="lg", title="Okubuulira",
            body_html="<p>y</p>",
        )

    def test_book_detail_bio_is_localized(self):
        res = self.client.get("/api/library/books/tomorrows/?language=lg")
        self.assertEqual(res.data["author"]["bio"], "Musumba atambulatambula.")

    def test_book_list_bio_is_localized(self):
        res = self.client.get("/api/library/books/?language=lg")
        self.assertEqual(res.data[0]["author"]["bio"], "Musumba atambulatambula.")

    def test_sermon_list_bio_is_localized(self):
        res = self.client.get("/api/library/sermons/?language=lg")
        self.assertEqual(res.data[0]["author"]["bio"], "Musumba atambulatambula.")

    def test_english_is_unaffected(self):
        res = self.client.get("/api/library/books/tomorrows/?language=en")
        self.assertEqual(res.data["author"]["bio"], "An itinerant pastor.")

    def test_untranslated_language_is_blank_not_english(self):
        # A language with no AuthorTranslation renders NO bio. Serving the
        # English original here is the leak this rule exists to prevent: a
        # reader who asked for Swahili must never be handed English prose.
        Book.objects.create(
            author=self.author, slug="tomorrows", language="sw", title="Kesho"
        )
        res = self.client.get("/api/library/books/tomorrows/?language=sw")
        self.assertEqual(res.data["author"]["bio"], "")

    def test_admin_surfaces_can_still_opt_into_the_original(self):
        # The fallback isn't deleted, just off by default: coverage and admin
        # views need to see what English text exists in order to queue it for
        # translation.
        self.assertEqual(self.author.bio_for("sw"), "")
        self.assertEqual(
            self.author.bio_for("sw", fallback=True), "An itinerant pastor."
        )

    def test_language_resolves_from_the_request_without_view_context(self):
        # The regression guard: a serializer used by a view that never sets
        # context["language"] still localizes, because Localized falls back to
        # the request's own ?language=.
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        from library.serializers import AuthorSerializer

        request = Request(APIRequestFactory().get("/api/library/books/?language=lg"))
        data = AuthorSerializer(self.author, context={"request": request}).data
        self.assertEqual(data["bio"], "Musumba atambulatambula.")

    def _translation_queries(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return [q for q in ctx.captured_queries if "authortranslation" in q["sql"].lower()]

    def _add_books(self, n, *, author=None, offset=0):
        for i in range(offset, offset + n):
            Book.objects.create(
                author=author
                or Author.objects.create(slug=f"a{i}", name=f"A{i}", bio="x"),
                slug=f"b{i}", language="lg", title=f"B{i}",
            )

    def _add_sermons(self, n, *, author=None, offset=0):
        for i in range(offset, offset + n):
            Sermon.objects.create(
                author=author
                or Author.objects.create(slug=f"s-a{i}", name=f"SA{i}", bio="x"),
                slug=f"s{i}", language="lg", title=f"S{i}", body_html="<p>x</p>",
            )

    def test_bio_rendering_costs_a_constant_number_of_queries(self):
        """Every path that renders a bio per row must prefetch translations.

        Asserts invariance as the payload grows (not an absolute count, which
        unrelated fixture changes would flip). Each case grows the rows THAT
        endpoint actually renders — otherwise the assertion passes vacuously,
        which is how the first version of this test missed a real N+1.
        """
        cases = [
            # (url, grow more of what this endpoint renders)
            ("/api/library/books/?language=lg", lambda n, off: self._add_books(n, offset=off)),
            ("/api/library/sermons/?language=lg", lambda n, off: self._add_sermons(n, offset=off)),
            # The author page lists that author's own books + sermons; book
            # detail's "related" shelf is same-author too.
            (
                "/api/library/authors/gareth-evans/?language=lg",
                lambda n, off: (
                    self._add_books(n, author=self.author, offset=off),
                    self._add_sermons(n, author=self.author, offset=off),
                ),
            ),
            (
                "/api/library/books/tomorrows/?language=lg",
                lambda n, off: self._add_books(n, author=self.author, offset=off),
            ),
        ]
        for url, grow in cases:
            with self.subTest(url=url):
                grow(2, 0)
                small = len(self._translation_queries(url))
                grow(4, 2)
                self.assertEqual(
                    len(self._translation_queries(url)), small,
                    f"{url} issues a translations query per row",
                )
                Book.objects.exclude(slug="tomorrows").delete()
                Sermon.objects.exclude(slug="a-sermon").delete()
                Author.objects.exclude(slug="gareth-evans").delete()


class DiscoveryQuickWinsTests(TestCase):
    """Popular-searches endpoint, sermon topic chips, and biographies-list
    sermon_count / has_long_bio — the discovery quick-wins."""

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(
            slug="cs", name="Charles Spurgeon", bio="short", bio_html="<p>long life</p>"
        )
        self.book = Book.objects.create(
            author=self.author, slug="morning", language="en", title="Morning by Morning"
        )
        Chapter.objects.create(book=self.book, order=1, title="Jan 1", body_html="<p>x</p>")
        self.sermon = Sermon.objects.create(
            author=self.author, slug="ravens-cry", language="en",
            title="The Raven's Cry", scripture_ref="Psalm 147:9", body_html="<p>y</p>",
        )
        self.topic = Topic.objects.create(slug="prayer", title="On Prayer", is_published=True)
        TopicSermon.objects.create(topic=self.topic, sermon_slug="ravens-cry")

    def test_sermon_detail_exposes_topic_chips(self):
        res = self.client.get("/api/library/sermons/ravens-cry/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["topics"], [{"slug": "prayer", "title": "On Prayer"}])

    def test_unpublished_topic_not_shown_on_sermon(self):
        self.topic.is_published = False
        self.topic.save(update_fields=["is_published"])
        res = self.client.get("/api/library/sermons/ravens-cry/?language=en")
        self.assertEqual(res.data["topics"], [])

    def test_biographies_list_carries_sermon_count_and_long_bio_flag(self):
        res = self.client.get("/api/library/authors/?language=en")
        row = next(a for a in res.data if a["slug"] == "cs")
        self.assertEqual(row["book_count"], 1)
        self.assertEqual(row["sermon_count"], 1)
        self.assertTrue(row["has_long_bio"])

    def test_sermon_only_author_appears_on_biographies_list(self):
        # An author with only a sermon (no book, no bio) is still library
        # content and must not be filtered out or read as empty.
        a = Author.objects.create(slug="mo", name="D. L. Moody", bio="")
        Sermon.objects.create(
            author=a, slug="sowing", language="en", title="Sowing", body_html="<p>z</p>"
        )
        res = self.client.get("/api/library/authors/?language=en")
        row = next((x for x in res.data if x["slug"] == "mo"), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["sermon_count"], 1)
        self.assertFalse(row["has_long_bio"])

    def test_book_count_not_inflated_by_sermon_join(self):
        # Two annotations over two relations must each stay distinct — a naive
        # double LEFT JOIN would multiply the counts.
        Book.objects.create(author=self.author, slug="evening", language="en", title="Evening")
        res = self.client.get("/api/library/authors/?language=en")
        row = next(a for a in res.data if a["slug"] == "cs")
        self.assertEqual(row["book_count"], 2)
        self.assertEqual(row["sermon_count"], 1)

    def _log(self, query, times, language="en", result_count=5):
        for _ in range(times):
            SearchQueryLog.objects.create(
                query=query, language=language, result_count=result_count
            )

    def test_popular_searches_is_aggregate_and_private(self):
        # Enough DISTINCT recurring queries to clear MIN_DISTINCT, so the
        # section is allowed to render at all.
        self._log("Prayer", 6)
        self._log("holiness", 5)
        self._log("revival", 5)
        self._log("faith", 5)
        # A one-off never surfaces — no single reader's query can leak.
        SearchQueryLog.objects.create(query="my secret note", language="en", result_count=4)
        # Neither does a query that recurs but stays under MIN_COUNT.
        self._log("almost", 4)
        # A frequent ZERO-result query never does either (only useful queries).
        self._log("missing", 9, result_count=0)
        # Wrong language is scoped out.
        self._log("oracion", 6, language="es")

        res = self.client.get("/api/library/popular-searches/?language=en")
        self.assertEqual(res.status_code, 200)
        # Case-folded, most frequent first; the private, sub-threshold,
        # zero-result and wrong-language rows are all absent.
        self.assertEqual(res.data["queries"], ["prayer", "faith", "holiness", "revival"])

    def test_popular_searches_empty_when_sparse(self):
        res = self.client.get("/api/library/popular-searches/?language=en")
        self.assertEqual(res.data["queries"], [])

    def test_popular_searches_hidden_until_enough_distinct_queries(self):
        # Two heavily-repeated queries still aren't a "popular" list — this is
        # the young-site case, where a couple of dev searches were surfacing as
        # the whole section. Below MIN_DISTINCT the endpoint returns nothing.
        self._log("gareth", 20)
        self._log("john 3:16", 20)
        res = self.client.get("/api/library/popular-searches/?language=en")
        self.assertEqual(res.data["queries"], [])


class LanguageSeedTableTests(SimpleTestCase):
    """Guards on the repo's seed table; see library/language_seed.py."""

    def test_every_language_is_fully_configured(self):
        for code, cfg in SEED_LANGUAGES.items():
            with self.subTest(language=code):
                for field in ("name", "native", "bible", "bible_label", "glossary"):
                    self.assertTrue(cfg.get(field), f"{code}: empty {field}")

    def test_glossaries_cover_the_shared_term_set(self):
        for code, cfg in SEED_LANGUAGES.items():
            with self.subTest(language=code):
                self.assertEqual(
                    set(cfg["glossary"]), set(GLOSSARY_TERMS),
                    f"{code}: glossary terms differ from GLOSSARY_TERMS",
                )

    @skipUnless(
        os.environ.get("CHECK_BIBLE_CODES"), "network check; CHECK_BIBLE_CODES=1 to run"
    )
    def test_bible_codes_resolve_against_take_root(self):
        # Goes through fetch_chapter — the same call scripture_context makes on a
        # real job — so this proves the codes work for the path that uses them,
        # not for a URL the test built itself. Opt-in so CI stays hermetic:
        #   CHECK_BIBLE_CODES=1 uv run python manage.py test \
        #     library.tests.LanguageSeedTableTests
        for code, cfg in SEED_LANGUAGES.items():
            with self.subTest(language=code, bible=cfg["bible"]):
                data = fetch_chapter(cfg["bible"], Ref("JHN", 1))
                self.assertTrue(
                    data and data.get("verses"),
                    f"{code}: {cfg['bible']} returned no verses",
                )


class TranslationPreflightTests(TestCase):
    """The checks every translate_* command runs before spending money.

    They read the REGISTRY now, not a dict in the tree — which is what lets a
    language added from the admin be translated at all, and also means these
    tests need a database.
    """

    def test_verify_bible_code_raises_when_the_code_does_not_resolve(self):
        # Mocked so it stays hermetic — what matters is that a non-resolving
        # code RAISES rather than letting the job proceed and quietly drop all
        # scripture.
        with mock.patch("library.translation.fetch_chapter", return_value=None):
            with self.assertRaises(ValueError) as ctx:
                verify_bible_code("pt")
        self.assertIn("scripture would be silently omitted", str(ctx.exception))

    def test_verify_bible_code_passes_when_verses_come_back(self):
        with mock.patch(
            "library.translation.fetch_chapter", return_value={"verses": [{"number": 1}]}
        ):
            verify_bible_code("pt")  # must not raise

    def test_verify_glossary_raises_on_a_half_filled_glossary(self):
        lang = Language.objects.get(code="pt")
        lang.glossary = {"grace": "graça"}
        lang.save(update_fields=["glossary"])
        with self.assertRaises(ValueError) as ctx:
            verify_glossary("pt")
        self.assertIn("justification", str(ctx.exception))

    def test_verify_glossary_passes_for_a_seeded_language(self):
        verify_glossary("pt")  # must not raise

    def test_an_unknown_language_is_a_clear_error_not_a_key_error(self):
        with self.assertRaises(ValueError) as ctx:
            language_config("xx")
        self.assertIn("Unknown language", str(ctx.exception))

    def test_the_source_language_is_not_a_translation_target(self):
        with self.assertRaises(ValueError):
            language_config("en")

    def test_missing_glossary_terms_ignores_blank_values(self):
        # A term present but empty is not a term — it would render as nothing in
        # the prompt, which is the same failure as leaving it out.
        self.assertIn("grace", missing_glossary_terms({"grace": "   "}))


class NoSourceLanguageLeakTests(TestCase):
    """The rule: a reader who asks for a non-source language is never handed
    source-language prose.

    Rather than pinning each field one at a time, this seeds every translatable
    prose field with a distinctive English sentinel, translates NOTHING into
    Swahili, then sweeps the public API in Swahili and asserts no sentinel comes
    back. A new serializer field that forgets the rule fails here without anyone
    having to remember to extend this test.
    """

    # Distinctive enough that a substring hit is a real leak, not a coincidence.
    BIO = "ZZQ-ENGLISH-BIO-SENTINEL"
    BIO_HTML = "ZZQ-ENGLISH-BIOHTML-SENTINEL"
    TOPIC_TITLE = "ZZQ-ENGLISH-TOPICTITLE-SENTINEL"
    TOPIC_DESC = "ZZQ-ENGLISH-TOPICDESC-SENTINEL"
    TOPIC_SCRIPT_REF = "ZZQ-ENGLISH-SCRIPTREF-SENTINEL"
    TOPIC_SCRIPT_TEXT = "ZZQ-ENGLISH-SCRIPTTEXT-SENTINEL"

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(
            slug="jane-doe",
            name="Jane Doe",
            bio=self.BIO,
            bio_html=f"<p>{self.BIO_HTML}</p>",
        )
        # Something to read in Swahili, so the author and shelf are not filtered
        # out for emptiness — this test is about prose, not about presence.
        self.sw_book = Book.objects.create(
            author=self.author,
            slug="kitabu",
            language="sw",
            title="Kitabu Changu",
            description="Maelezo ya Kiswahili.",
            is_published=True,
        )
        Chapter.objects.create(
            book=self.sw_book, order=1, title="Sura", body_html="<p>Maandishi.</p>"
        )
        self.topic = Topic.objects.create(
            slug="maombi",
            title=self.TOPIC_TITLE,
            description=self.TOPIC_DESC,
            scripture_ref=self.TOPIC_SCRIPT_REF,
            scripture_text=self.TOPIC_SCRIPT_TEXT,
            is_published=True,
        )
        TopicBook.objects.create(topic=self.topic, book_slug="kitabu")

    def _sentinels(self):
        return [
            self.BIO,
            self.BIO_HTML,
            self.TOPIC_TITLE,
            self.TOPIC_DESC,
            self.TOPIC_SCRIPT_REF,
            self.TOPIC_SCRIPT_TEXT,
        ]

    def _public_urls(self):
        return [
            "/api/library/authors/?language=sw",
            "/api/library/authors/jane-doe/?language=sw",
            "/api/library/books/?language=sw",
            "/api/library/books/kitabu/?language=sw",
            "/api/library/books/kitabu/chapters/1/?language=sw",
            "/api/library/sermons/?language=sw",
            "/api/library/plans/?language=sw",
            "/api/library/topics/?language=sw",
            "/api/library/topics/maombi/?language=sw",
            "/api/library/search/?q=Kitabu&language=sw",
            "/api/library/search/?q=Jane&language=sw",
        ]

    def test_no_english_prose_reaches_a_swahili_reader(self):
        for url in self._public_urls():
            res = self.client.get(url)
            self.assertIn(
                res.status_code, (200, 404), msg=f"{url} returned {res.status_code}"
            )
            if res.status_code != 200:
                continue
            body = res.content.decode()
            for sentinel in self._sentinels():
                self.assertNotIn(
                    sentinel,
                    body,
                    msg=(
                        f"English prose leaked into a Swahili response.\n"
                        f"  endpoint: {url}\n"
                        f"  leaked:   {sentinel}\n"
                        "A field with no Swahili translation must render as "
                        "absent, not as the English original."
                    ),
                )

    def test_english_readers_still_get_the_english_prose(self):
        # The counterpart guard: closing the leak must not blank out English.
        # The shelf needs an English book on it too — TopicListView has always
        # hidden a shelf with nothing to read in the requested language.
        Book.objects.create(
            author=self.author,
            slug="my-book",
            language="en",
            title="My Book",
            is_published=True,
        )
        TopicBook.objects.create(topic=self.topic, book_slug="my-book")

        res = self.client.get("/api/library/authors/jane-doe/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.BIO, res.content.decode())

        res = self.client.get("/api/library/topics/?language=en")
        self.assertIn(self.TOPIC_TITLE, res.content.decode())

    def test_topic_available_languages_drives_hreflang(self):
        # A shelf 404s in a locale with no translated title, so it must not be
        # advertised there — this field is what the page's hreflang is built from.
        res = self.client.get("/api/library/topics/maombi/?language=en")
        self.assertEqual(res.data["available_languages"], ["en"])

        TopicTranslation.objects.create(
            topic=self.topic, language="sw", title="Maombi"
        )
        res = self.client.get("/api/library/topics/maombi/?language=en")
        self.assertEqual(res.data["available_languages"], ["en", "sw"])

    def test_untranslated_topic_is_absent_from_its_locale(self):
        # Omitted from the shelf list...
        res = self.client.get("/api/library/topics/?language=sw")
        self.assertEqual(res.data, [])
        # ...and its page does not exist there either, rather than rendering
        # with a blank title.
        res = self.client.get("/api/library/topics/maombi/?language=sw")
        self.assertEqual(res.status_code, 404)

    def test_a_translated_field_is_served_in_that_language(self):
        # And the leak fix must not break the case translation exists for.
        AuthorTranslation.objects.create(
            author=self.author, language="sw", bio="Wasifu wa Kiswahili."
        )
        TopicTranslation.objects.create(
            topic=self.topic, language="sw", title="Maombi", description="Maelezo."
        )
        res = self.client.get("/api/library/authors/jane-doe/?language=sw")
        self.assertIn("Wasifu wa Kiswahili.", res.content.decode())

        res = self.client.get("/api/library/topics/?language=sw")
        body = res.content.decode()
        self.assertIn("Maombi", body)
        self.assertNotIn(self.TOPIC_TITLE, body)


class TopicTranslationJobTests(TestCase):
    """The `topic` job type: queueing a shelf for translation.

    Topics were the one content type the queue couldn't express, which is why
    the es/sw/pt shelves had to be written by hand. This covers the plumbing
    that makes them queueable like everything else.
    """

    def setUp(self):
        self.client = APIClient()
        self.topic = Topic.objects.create(
            slug="prayer",
            title="On Prayer",
            description="Learning to pray.",
            scripture_ref="Jeremiah 33:3",
            scripture_text="Call unto me, and I will answer thee.",
            is_published=True,
        )

    def test_topic_is_an_accepted_job_type(self):
        from library.admin_views.jobs import _TITLE_RE, JOB_TYPES

        self.assertIn("topic", JOB_TYPES)
        # The title is the job's identity and what the worker parses, so the
        # regex has to accept the new type too — a JOB_TYPES-only change would
        # file issues the queue then couldn't read back.
        m = _TITLE_RE.match("[translation] topic:prayer -> sw")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("topic", "prayer", "sw"))

    def test_resolve_source_reports_untranslated_then_translated(self):
        from library.admin_views.jobs import _resolve_source

        title, byline, exists = _resolve_source("topic", "prayer", "sw")
        self.assertIn("On Prayer", title)
        self.assertIsNone(byline)
        self.assertFalse(exists)

        # A row with a blank title does NOT count: a shelf is visible in a
        # language only once it has a title, so a titleless row is still a job.
        tr = TopicTranslation.objects.create(topic=self.topic, language="sw", title="")
        _, _, exists = _resolve_source("topic", "prayer", "sw")
        self.assertFalse(exists)

        tr.title = "Kuhusu Maombi"
        tr.save()
        _, _, exists = _resolve_source("topic", "prayer", "sw")
        self.assertTrue(exists)

    def test_resolve_source_ignores_unpublished_shelves(self):
        from library.admin_views.jobs import _resolve_source

        self.topic.is_published = False
        self.topic.save()
        self.assertIsNone(_resolve_source("topic", "prayer", "sw"))


class AdminLanguageTopicsTests(TestCase):
    """The admin language page's topic lists — present vs hidden."""

    def setUp(self):
        self.client = APIClient()
        for i, (slug, title) in enumerate(
            [("prayer", "On Prayer"), ("holy-spirit", "The Holy Spirit")]
        ):
            Topic.objects.create(
                slug=slug, title=title, description="d", is_published=True, sort_order=i
            )
        TopicTranslation.objects.create(
            topic=Topic.objects.get(slug="prayer"),
            language="sw",
            title="Kuhusu Maombi",
            description="d",
        )

    def _get(self, code):
        from unittest.mock import patch

        with patch("accounts.permissions.IsAdminEmail.has_permission", return_value=True):
            return self.client.get(f"/api/admin/languages/{code}/")

    def test_present_and_todo_split_by_translated_title(self):
        res = self._get("sw")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([t["slug"] for t in res.data["topics"]], ["prayer"])
        # The translated title is shown, not the English one.
        self.assertEqual(res.data["topics"][0]["title"], "Kuhusu Maombi")
        self.assertEqual([t["slug"] for t in res.data["todo"]["topics"]], ["holy-spirit"])

    def test_english_lists_every_shelf_and_has_no_todo(self):
        res = self._get("en")
        self.assertEqual(
            [t["slug"] for t in res.data["topics"]], ["prayer", "holy-spirit"]
        )
        self.assertEqual(res.data["todo"]["topics"], [])


class FetchVerseTextTests(SimpleTestCase):
    """`fetch_verse_text` — the guard that keeps a shelf's verse authentic.

    A topic quotes one verse verbatim, so the wording must come from that
    language's Bible. Every failure path must return "" so the caller ships no
    verse rather than a paraphrase (translate_topic warns and moves on).
    """

    def _chapter(self, verses):
        return {"reference": "Jeremías 33", "verses": verses}

    def test_returns_the_requested_verse(self):
        from library import translation as m

        with mock.patch.object(
            m,
            "fetch_chapter",
            return_value=self._chapter(
                [
                    {"number": 2, "text": "Asi dice Jehová..."},
                    {"number": 3, "text": "Clama a mí, y te responderé."},
                ]
            ),
        ):
            self.assertEqual(
                m.fetch_verse_text("rv1858", "Jeremiah 33:3"),
                "Clama a mí, y te responderé.",
            )

    def test_blank_when_the_verse_is_not_in_the_chapter(self):
        from library import translation as m

        with mock.patch.object(
            m, "fetch_chapter", return_value=self._chapter([{"number": 1, "text": "x"}])
        ):
            self.assertEqual(m.fetch_verse_text("rv1858", "Jeremiah 33:3"), "")

    def test_blank_on_an_unparseable_or_missing_reference(self):
        from library import translation as m

        with mock.patch.object(m, "fetch_chapter", return_value=None) as fetch:
            self.assertEqual(m.fetch_verse_text("rv1858", "not a reference"), "")
            fetch.assert_not_called()  # nothing to fetch
            self.assertEqual(m.fetch_verse_text("rv1858", ""), "")

    def test_blank_when_the_api_fails(self):
        from library import translation as m

        with mock.patch.object(m, "fetch_chapter", return_value=None):
            self.assertEqual(m.fetch_verse_text("rv1858", "Jeremiah 33:3"), "")


class TranslateTopicCommandTests(TestCase):
    """`translate_topic` — the pipeline behind the queue's `topic` job."""

    def setUp(self):
        self.topic = Topic.objects.create(
            slug="prayer",
            title="On Prayer",
            description="Learning to pray.",
            scripture_ref="Jeremiah 33:3",
            scripture_text="Call unto me, and I will answer thee.",
            is_published=True,
        )

    def _run(self, *args, **kwargs):
        # The command WRITES data/topic_translations/<lang>.json (that file is
        # the delivery path), so every run is pointed at a throwaway dir — a
        # test that touched the real repo data would pollute the working tree.
        out = StringIO()
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.written_dir = tmp
        with mock.patch("library.topic_translations.DATA_DIR", tmp):
            call_command("translate_topic", *args, stdout=out, stderr=out, **kwargs)
        return out.getvalue()

    def test_dry_run_touches_nothing(self):
        out = self._run("--language", "sw", "--dry-run")
        self.assertIn("prayer", out)
        self.assertFalse(TopicTranslation.objects.exists())

    def test_translates_title_and_description_and_writes_the_language_file(self):
        meta = {"title": "Kuhusu Maombi", "description": "Kujifunza kuomba."}
        with mock.patch("library.management.commands.translate_topic.verify_bible_code"), \
             mock.patch("library.management.commands.translate_topic.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value=meta,
             ):
            out = self._run("--language", "sw")

        tr = TopicTranslation.objects.get(topic=self.topic, language="sw")
        self.assertEqual(tr.title, "Kuhusu Maombi")
        self.assertEqual(tr.description, "Kujifunza kuomba.")
        # Scripture is opt-in, so it stays empty on a prose-only run.
        self.assertEqual(tr.scripture_text, "")
        # The shelf is now visible in Swahili — the whole point.
        self.assertTrue(self.topic.is_translated_into("sw"))
        # And the delivery file was written — it, not the DB row, is what
        # survives a deploy — with the translated prose in it.
        written = json.loads((self.written_dir / "sw.json").read_text(encoding="utf-8"))
        self.assertEqual(written["prayer"]["title"], "Kuhusu Maombi")
        self.assertEqual(written["prayer"]["description"], "Kujifunza kuomba.")
        self.assertNotIn("scripture", written["prayer"])  # prose-only run
        self.assertIn("sw.json", out)

    def test_scripture_uses_the_bible_and_never_the_model(self):
        meta = {"title": "Kuhusu Maombi", "description": "d"}
        with mock.patch("library.management.commands.translate_topic.verify_bible_code"), \
             mock.patch("library.management.commands.translate_topic.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value=meta,
             ), \
             mock.patch(
                 "library.management.commands.translate_topic.fetch_verse_text",
                 return_value="Niite, nami nitakujibu.",
             ), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_scripture_ref",
                 return_value="Yeremia 33:3",
             ):
            self._run("--language", "sw", "--scripture")

        tr = TopicTranslation.objects.get(topic=self.topic, language="sw")
        self.assertEqual(tr.scripture_text, "Niite, nami nitakujibu.")
        self.assertEqual(tr.scripture_ref, "Yeremia 33:3")

    def test_unfetchable_verse_ships_empty_rather_than_paraphrased(self):
        meta = {"title": "Kuhusu Maombi", "description": "d"}
        with mock.patch("library.management.commands.translate_topic.verify_bible_code"), \
             mock.patch("library.management.commands.translate_topic.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value=meta,
             ), \
             mock.patch(
                 "library.management.commands.translate_topic.fetch_verse_text",
                 return_value="",
             ) , \
             mock.patch(
                 "library.management.commands.translate_topic.translate_scripture_ref"
             ) as ref:
            out = self._run("--language", "sw", "--scripture")

        tr = TopicTranslation.objects.get(topic=self.topic, language="sw")
        self.assertEqual(tr.scripture_text, "")
        # The reference isn't translated either — a citation with no text under
        # it is worse than none, and the model is never asked to supply wording.
        ref.assert_not_called()
        self.assertIn("without a verse", out)

    def test_already_translated_is_skipped_unless_forced(self):
        TopicTranslation.objects.create(
            topic=self.topic, language="sw", title="Kuhusu Maombi", description="d"
        )
        with mock.patch(
            "library.management.commands.translate_topic.translate_topic_meta"
        ) as meta:
            self._run("--language", "sw")
            meta.assert_not_called()

        with mock.patch("library.management.commands.translate_topic.verify_bible_code"), \
             mock.patch("library.management.commands.translate_topic.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value={"title": "Mpya", "description": "mpya"},
             ) as meta:
            self._run("--language", "sw", "--force")
            meta.assert_called_once()
        self.assertEqual(
            TopicTranslation.objects.get(topic=self.topic, language="sw").title, "Mpya"
        )


class LanguageRegistrySeedTests(TestCase):
    """`seed_languages` — identity refreshes, the switch and the bar do not.

    This is the trap backend/CLAUDE.md warns about and that has bitten this
    codebase before: the seed re-runs on EVERY deploy, so any field a workflow
    owns after creation must be create-only. For languages that means `status`
    (an admin launched it), the thresholds (an admin tuned them), `went_live_at`
    and `notes`. If those were in the update set, the first deploy after a launch
    would silently put the language back to draft.
    """

    def test_seed_creates_every_configured_language(self):
        Language.objects.all().delete()
        call_command("seed_languages")
        codes = set(Language.objects.values_list("code", flat=True))
        # English (the source) plus every translation target.
        self.assertEqual(codes, {"en", "es", "sw", "lg", "pt", "ar", "hi", "uk"})

        en = Language.objects.get(code="en")
        self.assertTrue(en.is_source)
        self.assertEqual(en.bible_code, "")  # nothing to translate scripture into

        ar = Language.objects.get(code="ar")
        self.assertTrue(ar.rtl, "Arabic is right-to-left")
        self.assertFalse(ar.is_source)
        self.assertTrue(ar.bible_code, "a target language needs a Bible")
        # The glossary rides on the row now — it is what a translate_* command
        # reads, so a seeded language must arrive with a complete one.
        self.assertEqual(missing_glossary_terms(ar.glossary), [])

    def test_seed_is_idempotent(self):
        call_command("seed_languages")
        before = Language.objects.count()
        call_command("seed_languages")
        self.assertEqual(Language.objects.count(), before)

    def test_a_deploy_never_walks_back_a_launch_or_a_tuned_bar(self):
        call_command("seed_languages")
        ar = Language.objects.get(code="ar")
        # An admin launches Arabic and tunes its bar down for a beachhead run.
        ar.status = Language.Status.LIVE
        ar.min_books = 1
        ar.min_bios = 0
        ar.notes = "beachhead launch"
        ar.save()

        call_command("seed_languages")  # i.e. the next deploy

        ar.refresh_from_db()
        self.assertEqual(ar.status, Language.Status.LIVE, "the deploy un-launched it")
        self.assertEqual(ar.min_books, 1, "the deploy reset a tuned threshold")
        self.assertEqual(ar.min_bios, 0)
        self.assertEqual(ar.notes, "beachhead launch")

    def test_a_deploy_does_refresh_identity(self):
        # The other half: identity IS the repo's, so a correction ships.
        call_command("seed_languages")
        lg = Language.objects.get(code="lg")
        lg.name = "Wrong Name"
        lg.native_name = "Wrong"
        lg.save()

        call_command("seed_languages")

        lg.refresh_from_db()
        self.assertEqual(lg.name, "Luganda")
        self.assertEqual(lg.native_name, "Luganda")

    def test_a_deploy_repairs_a_repo_language_glossary(self):
        # Identity includes the glossary, so a term corrected in the repo ships
        # — and a row someone hand-edited in the database is put back.
        call_command("seed_languages")
        lg = Language.objects.get(code="lg")
        lg.glossary = {"grace": "wrong"}
        lg.save(update_fields=["glossary"])

        call_command("seed_languages")

        lg.refresh_from_db()
        self.assertEqual(missing_glossary_terms(lg.glossary), [])
        self.assertEqual(lg.glossary["grace"], SEED_LANGUAGES["lg"]["glossary"]["grace"])


class LanguageEntryTests(TestCase):
    """`_language_entry` now reads the registry rather than a hardcoded map."""

    def setUp(self):
        from library import languages

        languages.invalidate()

    def test_names_come_from_the_registry(self):
        from library.languages import entry

        self.assertEqual(entry("sw")["name"], "Swahili")
        self.assertEqual(entry("sw")["native_name"], "Kiswahili")

    def test_arabic_is_no_longer_bare_codes(self):
        # The old LANGUAGE_NAMES map had no Arabic, so an Arabic row rendered as
        # "ar / ar". That was the concrete cost of a fourth source of truth.
        from library.languages import entry

        ar = entry("ar")
        self.assertEqual(ar["name"], "Arabic")
        self.assertNotEqual(ar["native_name"], "ar")
        self.assertTrue(ar["rtl"])

    def test_an_unknown_code_degrades_to_itself(self):
        from library.languages import entry

        self.assertEqual(entry("zz")["name"], "zz")

    def test_editing_a_row_invalidates_the_cache(self):
        from library.languages import entry

        self.assertEqual(entry("lg")["name"], "Luganda")
        lang = Language.objects.get(code="lg")
        lang.name = "Ganda"
        lang.save()
        # The signal in library/languages.py drops the cache, so a rename shows
        # up without a restart.
        self.assertEqual(entry("lg")["name"], "Ganda")

    def test_live_codes_reads_status_from_the_database(self):
        from library.languages import live_codes

        self.assertIn("es", live_codes())
        self.assertNotIn("ar", live_codes())  # draft

        ar = Language.objects.get(code="ar")
        ar.status = Language.Status.LIVE
        ar.save()
        self.assertIn("ar", live_codes())


class LanguageListEndpointTests(TestCase):
    """`/api/library/languages/` — intent AND inventory, plus the build's view."""

    def setUp(self):
        self.client = APIClient()
        from library import languages

        languages.invalidate()
        self.author = Author.objects.create(slug="a", name="A")
        for lang in ("en", "es"):
            Book.objects.create(
                author=self.author, slug="b", language=lang, title="T", is_published=True
            )

    def test_reader_list_needs_both_live_status_and_books(self):
        codes = [r["code"] for r in self.client.get("/api/library/languages/").data]
        self.assertEqual(codes, ["en", "es"])

        # Swahili is live in the registry but has no book here yet — the reader's
        # picker must not offer a language with nothing to open.
        self.assertNotIn("sw", codes)

        # And a language with books but NOT live stays out: this is the guard the
        # old books-only rule lacked, which is how pt got advertised while empty.
        Book.objects.create(
            author=self.author, slug="b", language="ar", title="T", is_published=True
        )
        codes = [r["code"] for r in self.client.get("/api/library/languages/").data]
        self.assertNotIn("ar", codes)

    def test_all_returns_every_live_language_for_the_build(self):
        # The build asks for intent, not inventory: a live locale still filling
        # up must be prerendered and advertised.
        codes = [r["code"] for r in self.client.get("/api/library/languages/?all=1").data]
        self.assertEqual(codes, ["en", "es", "sw", "lg", "pt"])
        self.assertNotIn("ar", codes)  # draft

    def test_going_live_changes_what_the_build_is_told(self):
        ar = Language.objects.get(code="ar")
        ar.status = Language.Status.LIVE
        ar.save()
        codes = [r["code"] for r in self.client.get("/api/library/languages/?all=1").data]
        self.assertIn("ar", codes)

    def test_entries_carry_the_flags_the_reader_needs(self):
        ar = Language.objects.get(code="ar")
        ar.status = Language.Status.LIVE
        ar.save()
        rows = {r["code"]: r for r in self.client.get("/api/library/languages/?all=1").data}
        self.assertTrue(rows["ar"]["rtl"], "the reader needs to know to flip direction")
        self.assertFalse(rows["es"]["rtl"])
        self.assertTrue(rows["en"]["is_source"])


class ReadinessReportTests(TestCase):
    """`readiness.report` — the computed answer to "can this language go live?"."""

    def setUp(self):
        self.es = Language.objects.get(code="es")
        self.en = Language.objects.get(code="en")
        self.author = Author.objects.create(slug="a", name="A", bio="An English bio.")

    def _report(self, lang, bible=None):
        """A report with the Bible check stubbed out.

        Two reasons, both learned the hard way. The Bible check makes a live call
        to the Take Root API, so leaving it real would (a) make this suite depend
        on a third party being up — a hidden network dependency in a unit test —
        and (b) make results differ by environment: it passes in CI, which has
        network, and reports `unknown` in a sandbox that doesn't. A test that
        changes verdict with its surroundings isn't testing the code.
        """
        stub = bible or readiness_module.Check(
            "bible", "Bible", readiness_module.PASS, "stubbed"
        )
        with mock.patch.object(readiness_module, "_bible_check", return_value=stub):
            return readiness_module.report(lang)

    def test_the_source_language_skips_translation_checks(self):
        # Unstubbed on purpose: this asserts the real skip logic, and for the
        # source language `_bible_check` returns early — before any network call
        # — so it's safe to run for real here.
        r = readiness_module.report(self.en)
        by_key = {c.key: c for c in r.checks}
        for key in ("bible", "glossary", "ui"):
            self.assertEqual(by_key[key].status, "skipped", key)

    def test_a_failing_count_blocks_and_says_what_is_missing(self):
        self.es.min_books = 3
        self.es.save()
        books = {c.key: c for c in self._report(self.es).checks}["books"]
        self.assertEqual(books.status, "fail")
        self.assertEqual(books.current, 0)
        self.assertEqual(books.required, 3)
        self.assertIn("needs 3", books.detail)

    def test_zero_disables_a_check_rather_than_failing_it(self):
        self.es.min_books = 0
        self.es.save()
        books = {c.key: c for c in self._report(self.es).checks}["books"]
        self.assertEqual(books.status, "skipped")
        self.assertFalse(books.blocking)

    def test_meeting_the_bar_passes(self):
        self.es.min_books = 1
        self.es.min_bios = 0
        self.es.require_all_topics = False
        self.es.save()
        Book.objects.create(
            author=self.author, slug="b", language="es", title="T", is_published=True
        )
        books = {c.key: c for c in self._report(self.es).checks}["books"]
        self.assertEqual(books.status, "pass")

    def test_unknown_does_not_block_readiness(self):
        # Bible and interface strings can be unanswerable where they're asked —
        # no network, or an API container that can't see the frontend. Treating
        # that as failure would block a launch for an unrelated reason; the
        # interface rule is enforced at build time instead.
        #
        # The unknown is INJECTED rather than induced by the environment: an
        # earlier version of this test just asserted "some check is unknown",
        # which held in a sandbox with no network and failed in CI, where the
        # Bible check really does resolve.
        self.es.min_books = 0
        self.es.min_bios = 0
        self.es.min_plans = 0
        self.es.require_all_topics = False
        self.es.save()
        unreachable = readiness_module.Check(
            "bible", "Bible", readiness_module.UNKNOWN, "Could not reach the Bible API."
        )
        r = self._report(self.es, bible=unreachable)
        self.assertIn("unknown", {c.status for c in r.checks})
        self.assertTrue(r.ready, "an unanswerable check must not block")

    def test_a_genuinely_bad_bible_does_block(self):
        # The counterpart: `unknown` is forgiving, `fail` is not.
        self.es.min_books = 0
        self.es.min_bios = 0
        self.es.min_plans = 0
        self.es.require_all_topics = False
        self.es.save()
        bad = readiness_module.Check(
            "bible", "Bible", readiness_module.FAIL, "Bible code 'nope' returned no verses."
        )
        r = self._report(self.es, bible=bad)
        self.assertFalse(r.ready)
        self.assertEqual([c.key for c in r.blockers], ["bible"])

    def test_untranslated_topics_block_when_required(self):
        Topic.objects.create(slug="t", title="T", description="d", is_published=True)
        self.es.require_all_topics = True
        self.es.save()
        topics = {c.key: c for c in self._report(self.es).checks}["topics"]
        self.assertEqual(topics.status, "fail")
        self.assertIn("hidden in this language", topics.detail)

    def test_bios_count_either_short_or_long_form(self):
        self.es.min_bios = 1
        self.es.save()
        AuthorTranslation.objects.create(author=self.author, language="es", bio_html="<p>x</p>")
        bios = {c.key: c for c in self._report(self.es).checks}["bios"]
        self.assertEqual(bios.status, "pass")


class AdminLanguageReadinessEndpointTests(TestCase):
    """The admin readiness report and the editable bar."""

    def setUp(self):
        self.client = APIClient()

    def _patch_perm(self):
        """Admin permission AND a stubbed Bible check.

        The readiness endpoint calls the live Take Root API. Stubbing it here
        keeps these tests hermetic — otherwise the suite fails whenever that
        third party is unreachable, which has nothing to do with this endpoint.
        """
        from unittest.mock import patch

        perm = patch("accounts.permissions.IsAdminEmail.has_permission", return_value=True)
        bible = mock.patch.object(
            readiness_module,
            "_bible_check",
            return_value=readiness_module.Check(
                "bible", "Bible", readiness_module.PASS, "stubbed"
            ),
        )

        class _Both:
            def __enter__(self):
                perm.start()
                bible.start()
                return self

            def __exit__(self, *exc):
                bible.stop()
                perm.stop()
                return False

        return _Both()

    def test_report_lists_checks_and_current_thresholds(self):
        with self._patch_perm():
            res = self.client.get("/api/admin/languages/ar/readiness/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("checks", res.data)
        self.assertIn("min_books", res.data["thresholds"])
        self.assertEqual(res.data["status"], "draft")

    def test_unknown_language_is_404(self):
        with self._patch_perm():
            self.assertEqual(
                self.client.get("/api/admin/languages/zz/readiness/").status_code, 404
            )
            self.assertEqual(
                self.client.patch(
                    "/api/admin/languages/zz/thresholds/", {"min_books": 1}, format="json"
                ).status_code,
                404,
            )

    def test_editing_the_bar_changes_the_verdict(self):
        with self._patch_perm():
            before = self.client.get("/api/admin/languages/ar/readiness/").data
            self.assertIn("books", before["blocking"])

            # Every countable bar, not just the ones that happen to block today:
            # the point is that lowering the bar clears blockers, and pinning
            # that to the current defaults makes the test fail whenever a
            # default changes for unrelated reasons (min_plans just did).
            res = self.client.patch(
                "/api/admin/languages/ar/thresholds/",
                {
                    "min_books": 0,
                    "min_bios": 0,
                    "min_plans": 0,
                    "min_sermons": 0,
                    "require_all_topics": False,
                },
                format="json",
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data["thresholds"]["min_books"], 0)

            after = self.client.get("/api/admin/languages/ar/readiness/").data
        self.assertEqual(after["blocking"], [], "lowering the bar should clear blockers")

    def test_threshold_validation(self):
        cases = [
            ({"min_books": -1}, 400),
            ({"min_books": "lots"}, 400),
            ({}, 400),  # nothing to update
            ({"min_books": 2}, 200),
        ]
        with self._patch_perm():
            for body, expected in cases:
                res = self.client.patch(
                    "/api/admin/languages/es/thresholds/", body, format="json"
                )
                self.assertEqual(res.status_code, expected, body)

    def test_status_cannot_be_changed_through_the_thresholds_endpoint(self):
        # Launching is the go-live action's job — it re-runs the checks. A
        # thresholds PATCH must never be a back door to going live.
        with self._patch_perm():
            res = self.client.patch(
                "/api/admin/languages/ar/thresholds/",
                {"status": "live", "min_books": 1},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("status", res.data["updated"])
        self.assertEqual(Language.objects.get(code="ar").status, "draft")

    def test_readiness_requires_admin(self):
        # Anonymous gets 401 (no credentials); a signed-in non-admin would get
        # 403. Either way the endpoint is closed — these are admin surfaces that
        # expose content counts and can change a launch bar.
        self.assertIn(
            self.client.get("/api/admin/languages/es/readiness/").status_code, (401, 403)
        )
        self.assertIn(
            self.client.patch(
                "/api/admin/languages/es/thresholds/", {"min_books": 1}, format="json"
            ).status_code,
            (401, 403),
        )


class GoLiveTests(TestCase):
    """Taking a language live: re-check, record, trigger the rebuild.

    The two halves are asserted separately throughout. "Recorded as live" and
    "readers can see it" are different facts — the reader is a prerendered static
    site — and a launch whose deploy failed is a real state that must stay
    visible rather than collapsing into one success flag.
    """

    def setUp(self):
        self.client = APIClient()
        self.ar = Language.objects.get(code="ar")

    def _perm_and_ready(self, ready=True):
        """Admin permission, a stubbed Bible check, and a chosen readiness verdict."""
        from unittest.mock import patch

        perm = patch("accounts.permissions.IsAdminEmail.has_permission", return_value=True)
        checks = [] if ready else [
            readiness_module.Check("books", "Books", readiness_module.FAIL, "0 books — needs 5.")
        ]
        # Patched on the readiness module itself, which is what golive imports —
        # `from . import readiness` then `readiness.report(...)`, so the lookup
        # happens at call time and this stub is what golive sees.
        rep = mock.patch.object(
            readiness_module, "report", return_value=readiness_module.Report("ar", checks)
        )

        class _Ctx:
            def __enter__(self):
                perm.start()
                rep.start()
                return self

            def __exit__(self, *exc):
                rep.stop()
                perm.stop()
                return False

        return _Ctx()

    def test_not_ready_is_refused_with_its_blockers(self):
        with self._perm_and_ready(ready=False):
            res = self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertFalse(res.data["launched"])
        self.assertEqual(res.data["reason"], "not_ready")
        self.assertEqual(res.data["readiness"]["blocking"], ["books"])
        # And crucially it did NOT launch.
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "draft")

    def test_force_launches_past_failing_checks_and_says_so(self):
        with self._perm_and_ready(ready=False):
            res = self.client.post(
                "/api/admin/languages/ar/go-live/", {"force": True}, format="json"
            )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["launched"])
        self.assertTrue(res.data["forced"], "an override must be recorded as one")
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "live")

    def test_a_ready_language_launches_and_is_stamped(self):
        with self._perm_and_ready(ready=True):
            res = self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
        self.assertEqual(res.status_code, 200)
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "live")
        self.assertIsNotNone(self.ar.went_live_at)
        self.assertFalse(res.data["forced"])

    def test_relaunching_keeps_the_original_went_live_at(self):
        # Re-running the action (e.g. to retrigger a deploy) must not rewrite when
        # the language became public.
        with self._perm_and_ready(ready=True):
            self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
            self.ar.refresh_from_db()
            first = self.ar.went_live_at
            res = self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.went_live_at, first)
        self.assertTrue(res.data["already_live"])

    def test_an_unconfigured_deploy_hook_is_reported_not_hidden(self):
        with self.settings(RENDER_WEB_DEPLOY_HOOK=""):
            with self._perm_and_ready(ready=True):
                res = self.client.post("/api/admin/languages/ar/go-live/", {}, format="json")
        self.assertTrue(res.data["launched"])
        self.assertEqual(res.data["deploy"]["status"], "not_configured")
        self.assertIn("won't see it", res.data["deploy"]["detail"])

    def test_a_failing_deploy_hook_does_not_undo_the_launch(self):
        # The status flip already happened; losing it because the hook 500'd would
        # be worse than a launch that needs a manual deploy.
        with self.settings(RENDER_WEB_DEPLOY_HOOK="https://hook.example/deploy"):
            with self._perm_and_ready(ready=True):
                with mock.patch(
                    "library.golive.requests.post",
                    side_effect=__import__("requests").RequestException("boom"),
                ):
                    res = self.client.post(
                        "/api/admin/languages/ar/go-live/", {}, format="json"
                    )
        self.assertTrue(res.data["launched"])
        self.assertEqual(res.data["deploy"]["status"], "failed")
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, "live")

    def test_the_deploy_hook_is_fired_when_configured(self):
        with self.settings(RENDER_WEB_DEPLOY_HOOK="https://hook.example/deploy"):
            with self._perm_and_ready(ready=True):
                with mock.patch("library.golive.requests.post") as post:
                    post.return_value = mock.Mock(ok=True, status_code=200)
                    res = self.client.post(
                        "/api/admin/languages/ar/go-live/", {}, format="json"
                    )
                    post.assert_called_once_with("https://hook.example/deploy", timeout=20)
        self.assertEqual(res.data["deploy"]["status"], "triggered")

    def test_english_cannot_be_launched(self):
        from unittest.mock import patch

        with patch("accounts.permissions.IsAdminEmail.has_permission", return_value=True):
            res = self.client.post("/api/admin/languages/en/go-live/", {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_go_live_requires_admin(self):
        self.assertIn(
            self.client.post("/api/admin/languages/ar/go-live/", {}, format="json").status_code,
            (401, 403),
        )


class DeployCheckTests(TestCase):
    """"Did it ship?" — the question `status` cannot answer."""

    def setUp(self):
        self.client = APIClient()

    def _perm(self):
        from unittest.mock import patch

        return patch("accounts.permissions.IsAdminEmail.has_permission", return_value=True)

    def test_unknown_without_a_site_url_rather_than_a_guess(self):
        with self.settings(PUBLIC_SITE_URL=""):
            with self._perm():
                res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "unknown")

    def test_deployed_when_the_locale_is_in_the_live_sitemap(self):
        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get") as get:
                    get.return_value = mock.Mock(
                        ok=True, text="<url><loc>https://ochorus.test/ar/books/</loc></url>"
                    )
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "deployed")

    def test_pending_when_the_build_has_not_caught_up(self):
        with self.settings(PUBLIC_SITE_URL="https://ochorus.test"):
            with self._perm():
                with mock.patch("library.golive.requests.get") as get:
                    get.return_value = mock.Mock(
                        ok=True, text="<url><loc>https://ochorus.test/es/books/</loc></url>"
                    )
                    res = self.client.get("/api/admin/languages/ar/deploy-check/")
        self.assertEqual(res.data["status"], "pending")


class AdminDashboardLanguageListTests(TestCase):
    """Every registry language is listed, whether or not it has content.

    The chicken-and-egg this fixes: the Translate buttons live on the
    per-language page, and the dashboard is how you reach it. Listing only
    languages that already had content meant a language with nothing in it was
    unreachable — so there was no way to queue the work that would give it
    content. Arabic sat fully wired and invisible.
    """

    def setUp(self):
        self.client = APIClient()

    def _rows(self):
        from unittest.mock import patch

        with patch("accounts.permissions.IsAdminEmail.has_permission", return_value=True):
            return {r["code"]: r for r in self.client.get("/api/admin/stats/").data["languages"]}

    def test_a_language_with_no_content_is_still_listed(self):
        rows = self._rows()
        self.assertIn("ar", rows, "a registry language must be reachable before it has content")
        self.assertEqual(rows["ar"]["books"], 0)
        self.assertEqual(rows["ar"]["sermons"], 0)
        # And it carries its real name, not a bare code — the registry supplies it.
        self.assertEqual(rows["ar"]["name"], "Arabic")

    def test_every_registry_language_appears(self):
        rows = self._rows()
        for code in Language.objects.values_list("code", flat=True):
            self.assertIn(code, rows, code)

    def test_a_content_language_with_no_registry_row_still_appears(self):
        # e.g. the "en-modern" pseudo-language: content exists under a code the
        # registry doesn't model, and hiding it would lose it from the inventory.
        author = Author.objects.create(slug="a", name="A")
        Book.objects.create(
            author=author, slug="b", language="en-modern", title="T", is_published=True
        )
        self.assertIn("en-modern", self._rows())


# A deliberately FICTIONAL language for the admin-created path. It used to be
# Hindi, which collided the moment Hindi became a real seeded language: these
# tests assert an admin-created row can be edited, and a repo-defined one is
# correctly refused with 409. "zz" is unassigned in ISO 639 and will never be a
# real target, so the fixture cannot be overtaken again. Pinned below.
INVENTED = {
    "code": "zz",
    "name": "Testish",
    "native_name": "Testish",
    "bible_code": "irvhin",  # any code the verifier accepts; mocked in these tests
    "bible_label": "Stand-in Version",
    "glossary": {t: f"zz-{t}" for t in GLOSSARY_TERMS},
}


class InventedLanguageFixtureTests(SimpleTestCase):
    def test_the_fixture_language_is_not_a_real_one(self):
        """If this ever fails, the admin-created tests are silently asserting
        against a repo-defined language and will start returning 409."""
        from library.language_seed import SEED_LANGUAGES

        self.assertNotIn(INVENTED["code"], SEED_LANGUAGES)


class AdminAddLanguageTests(TestCase):
    """"Add a language" — the endpoint that starts a new language.

    The point of these tests is the thing that made the feature worth building:
    a language created here must be *translatable*, not merely listed. So the
    row is checked through `language_config` — the same accessor a translate_*
    command reads — rather than only by field.
    """

    def setUp(self):
        self.client = APIClient()

    def _admin(self, verses=True, reachable=True):
        """Admin permission plus a stubbed Bible API.

        Both are stubbed because the endpoint deliberately makes a live call: a
        wrong Bible code silently drops scripture from every translation, so it
        is checked at creation rather than discovered during a paid job.
        """
        from unittest.mock import patch

        perm = patch("accounts.permissions.IsAdminEmail.has_permission", return_value=True)
        fetch = patch(
            "library.admin_views.content.fetch_chapter",
            return_value={"verses": [{"number": 1, "text": "…"}]} if verses else None,
        )
        api = patch.object(readiness_module, "api_reachable", return_value=reachable)

        class _All:
            def __enter__(self):
                for p in (perm, fetch, api):
                    p.start()
                return self

            def __exit__(self, *exc):
                for p in (api, fetch, perm):
                    p.stop()
                return False

        return _All()

    def _post(self, payload=None, **kw):
        with self._admin(**kw):
            return self.client.post("/api/admin/languages/", payload or INVENTED, format="json")

    def test_creating_a_language_makes_it_translatable(self):
        from library import languages as languages_module

        res = self._post()
        self.assertEqual(res.status_code, 201, res.data)
        languages_module.invalidate()

        lang = Language.objects.get(code="zz")
        self.assertEqual(lang.status, Language.Status.DRAFT, "creating is not launching")
        self.assertFalse(lang.is_source)

        # The real test: the translator can read its config off the new row.
        cfg = language_config("zz")
        self.assertEqual(cfg["bible"], INVENTED["bible_code"])
        self.assertEqual(set(cfg["glossary"]), set(GLOSSARY_TERMS))
        verify_glossary("zz")  # must not raise

    def test_a_new_language_is_immediately_reachable_in_the_admin(self):
        from unittest.mock import patch

        from library import languages as languages_module

        self._post()
        languages_module.invalidate()
        with patch("accounts.permissions.IsAdminEmail.has_permission", return_value=True):
            rows = {r["code"] for r in self.client.get("/api/admin/stats/").data["languages"]}
        self.assertIn("zz", rows)

    def test_a_new_language_is_not_advertised_to_readers(self):
        # Created as draft, so the build's live-locale list must not pick it up.
        self._post()
        res = self.client.get("/api/library/languages/")
        self.assertNotIn("zz", [r["code"] for r in res.data])

    def test_duplicate_code_is_rejected(self):
        self.assertEqual(self._post(dict(INVENTED, code="pt")).status_code, 409)

    def test_a_malformed_code_is_rejected(self):
        for bad in ("", "H", "english", "hi_IN", "../etc"):
            with self.subTest(code=bad):
                self.assertEqual(self._post(dict(INVENTED, code=bad)).status_code, 400)

    def test_the_code_is_normalised(self):
        self.assertEqual(self._post(dict(INVENTED, code=" ZZ ")).status_code, 201)
        self.assertTrue(Language.objects.filter(code="zz").exists())

    def test_a_partial_glossary_is_rejected(self):
        payload = dict(INVENTED, glossary={"grace": "अनुग्रह"})
        res = self._post(payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("justification", res.data["detail"])
        self.assertFalse(Language.objects.filter(code="hi").exists())

    def test_an_unknown_glossary_term_is_rejected(self):
        payload = dict(INVENTED, glossary=dict(INVENTED["glossary"], predestination="x"))
        res = self._post(payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("predestination", res.data["detail"])

    def test_names_are_required(self):
        self.assertEqual(self._post(dict(INVENTED, native_name="  ")).status_code, 400)
        self.assertEqual(self._post(dict(INVENTED, name="")).status_code, 400)

    def test_a_bible_code_is_required(self):
        self.assertEqual(self._post(dict(INVENTED, bible_code="")).status_code, 400)

    def test_a_bible_code_that_does_not_resolve_is_rejected(self):
        res = self._post(verses=False)
        self.assertEqual(res.status_code, 400)
        self.assertIn("no verses", res.data["detail"])
        self.assertFalse(Language.objects.filter(code="hi").exists())

    def test_an_unreachable_bible_api_does_not_block_creation(self):
        # "We couldn't ask" is not "the code is wrong" — the readiness check asks
        # again later, and refusing here would make our egress a gate on adding
        # a language.
        res = self._post(verses=False, reachable=False)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertFalse(res.data["bible_verified"])
        self.assertIn("Could not reach", res.data["bible_note"])

    def test_the_response_says_what_still_has_to_happen(self):
        res = self._post()
        joined = " ".join(res.data["next_steps"])
        self.assertIn("messages/zz.json", joined, "the UI catalogue gap must be stated")
        self.assertIn("Go live", joined)


class AdminLanguageSettingsTests(TestCase):
    """Editing a language's identity — and refusing to pretend for repo rows."""

    def setUp(self):
        self.client = APIClient()
        self.helper = AdminAddLanguageTests()
        self.helper.client = self.client

    def _patch(self, code, payload, **kw):
        with self.helper._admin(**kw):
            return self.client.patch(
                f"/api/admin/languages/{code}/settings/", payload, format="json"
            )

    def _create_invented(self):
        with self.helper._admin():
            return self.client.post("/api/admin/languages/", INVENTED, format="json")

    def test_an_admin_created_language_can_be_edited(self):
        self._create_invented()
        res = self._patch("zz", {"bible_label": "IRV (2019)", "rtl": False})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(Language.objects.get(code="zz").bible_label, "IRV (2019)")

    def test_a_repo_defined_language_is_refused_rather_than_silently_reverted(self):
        res = self._patch("pt", {"name": "Portugues"})
        self.assertEqual(res.status_code, 409)
        self.assertIn("language_seed.py", res.data["detail"])
        self.assertEqual(Language.objects.get(code="pt").name, "Portuguese")

    def test_a_partial_glossary_cannot_be_saved_later_either(self):
        self._create_invented()
        res = self._patch("zz", {"glossary": {"grace": "अनुग्रह"}})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            set(Language.objects.get(code="zz").glossary), set(GLOSSARY_TERMS)
        )

    def test_a_bible_code_change_is_verified_too(self):
        self._create_invented()
        res = self._patch("zz", {"bible_code": "nope"}, verses=False)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Language.objects.get(code="zz").bible_code, INVENTED["bible_code"])

    def test_unknown_language_is_404(self):
        self.assertEqual(self._patch("zz", {"name": "X"}).status_code, 404)

    def test_the_deploy_leaves_an_admin_created_language_alone(self):
        # The other half of the create-only rule: the seed re-asserts identity
        # for languages IT defines. A language the admin invented isn't in the
        # seed table, so nothing about it may be rewritten by a deploy.
        self._create_invented()
        self._patch("zz", {"name": "Hindi (India)"})
        call_command("seed_languages")
        self.assertEqual(Language.objects.get(code="zz").name, "Hindi (India)")


class UiCatalogueCheckTests(TestCase):
    """Where the interface-strings check gets its answer.

    This check used to be permanently `unknown` in production — the catalogues
    live in frontend/messages/ and the API image is built from backend/ alone —
    so the deployed admin could never say whether a language's interface was
    done. The frontend now generates a summary into backend/, and a dev checkout
    still prefers the real files.
    """

    def setUp(self):
        self.lang = Language.objects.get(code="ar")

    def _check(self):
        return readiness_module._ui_check(self.lang)

    def _no_frontend(self):
        return mock.patch.object(readiness_module, "_messages_dir", return_value=None)

    def _summary_file(self, payload: dict) -> Path:
        path = Path(tempfile.mkdtemp()) / "ui_catalogues.json"
        path.write_text(json.dumps(payload), "utf-8")
        return path

    def test_the_committed_summary_answers_when_the_frontend_is_not_visible(self):
        # i.e. the deployed API. Arabic's catalogue is complete, so this is the
        # case that used to report "unknown" and now reports the truth.
        with self._no_frontend():
            check = self._check()
        self.assertEqual(check.status, readiness_module.PASS, check.detail)
        self.assertEqual(check.current, check.required)
        self.assertGreater(check.required, 100, "a plausible catalogue size")

    def test_an_incomplete_catalogue_fails_with_a_count(self):
        summary = {"base_keys": 100, "locales": {"ar": {"present": 88, "missing": []}}}
        with self._no_frontend():
            with mock.patch(
                "library.readiness.CATALOGUE_SUMMARY", self._summary_file(summary)
            ):
                check = self._check()
        self.assertEqual(check.status, readiness_module.FAIL)
        self.assertEqual((check.current, check.required), (88, 100))
        self.assertIn("12 string(s)", check.detail)

    def test_a_language_absent_from_the_summary_is_absent_not_unknown(self):
        # A language nobody has started an interface for has zero strings — that
        # is a fact, and it should block a launch rather than shrug.
        summary = {"base_keys": 100, "locales": {"es": {"present": 100, "missing": []}}}
        with self._no_frontend():
            with mock.patch(
                "library.readiness.CATALOGUE_SUMMARY", self._summary_file(summary)
            ):
                check = self._check()
        self.assertEqual(check.status, readiness_module.FAIL)
        self.assertEqual((check.current, check.required), (0, 100))

    def test_no_source_at_all_is_unknown(self):
        with self._no_frontend():
            with mock.patch(
                "library.readiness.CATALOGUE_SUMMARY", Path("/nonexistent/x.json")
            ):
                check = self._check()
        self.assertEqual(check.status, readiness_module.UNKNOWN)

    def test_a_dev_checkout_prefers_the_real_catalogues(self):
        # The summary is a courier, not an authority: where the files themselves
        # are readable they win, so a developer mid-edit sees their own state
        # rather than whatever was last committed.
        msgs = Path(tempfile.mkdtemp())
        (msgs / "en.json").write_text(json.dumps({"a": "1", "b": "2"}), "utf-8")
        (msgs / "ar.json").write_text(json.dumps({"a": "١"}), "utf-8")
        stale = {"base_keys": 999, "locales": {"ar": {"present": 999, "missing": []}}}
        with mock.patch.object(readiness_module, "_messages_dir", return_value=msgs):
            with mock.patch(
                "library.readiness.CATALOGUE_SUMMARY", self._summary_file(stale)
            ):
                check = self._check()
        self.assertEqual(check.status, readiness_module.FAIL)
        self.assertEqual((check.current, check.required), (1, 2))

    def test_the_committed_summary_is_shaped_the_way_the_reader_expects(self):
        # Guards the courier itself: the file is generated by an npm script in
        # the other half of the repo, so nothing in Python fails if its shape
        # changes — this does.
        data = json.loads(readiness_module.CATALOGUE_SUMMARY.read_text("utf-8"))
        self.assertEqual(data["base_locale"], "en")
        self.assertGreater(data["base_keys"], 100)
        for code in ("en", "ar", "es", "sw", "lg", "pt"):
            self.assertIn(code, data["locales"], code)
            self.assertIn("present", data["locales"][code])


class PlanThresholdTests(TestCase):
    """The reading-plan bar — the one threshold whose default was wrong.

    `min_plans` shipped at 0 because of a claim that no non-English language had
    a published plan. It came from a database with `seed_plans` unrun; every live
    language has them. These pin both halves of the correction: what a new
    language inherits, and what the check does with it.
    """

    def _report(self, lang):
        # Bible stubbed for the same reason as ReadinessReportTests — a real call
        # makes the verdict depend on whether the sandbox has network.
        with mock.patch.object(
            readiness_module,
            "_bible_check",
            return_value=readiness_module.Check(
                "bible", "Bible", readiness_module.PASS, "stubbed"
            ),
        ):
            return {c.key: c for c in readiness_module.report(lang).checks}

    def test_a_new_language_must_have_a_translated_plan(self):
        # The model default, which is what a language created from the admin gets.
        fresh = Language.objects.create(code="hi", name="Hindi", native_name="हिन्दी")
        self.assertEqual(fresh.min_plans, 1)

    def test_the_migration_left_launched_languages_alone(self):
        # A live language's bar is a record of what it cleared, not a decision
        # still open, so the correction deliberately skipped those rows.
        for code in ("es", "sw", "lg", "pt"):
            self.assertEqual(Language.objects.get(code=code).min_plans, 0, code)

    def test_the_migration_raised_the_unlaunched_one(self):
        self.assertEqual(Language.objects.get(code="ar").min_plans, 1)

    def test_no_plan_fails_the_check(self):
        lang = Language.objects.get(code="es")
        lang.min_plans = 1
        lang.save(update_fields=["min_plans"])
        check = self._report(lang)["plans"]
        self.assertEqual(check.status, readiness_module.FAIL)
        self.assertEqual((check.current, check.required), (0, 1))

    def test_a_published_plan_clears_it(self):
        lang = Language.objects.get(code="es")
        lang.min_plans = 1
        lang.save(update_fields=["min_plans"])
        Plan.objects.create(
            slug="p", language="es", title="Un plan", is_published=True
        )
        self.assertEqual(self._report(lang)["plans"].status, readiness_module.PASS)

    def test_an_unpublished_plan_does_not_count(self):
        # Readiness asks what a reader can reach, not what exists in a table.
        lang = Language.objects.get(code="es")
        lang.min_plans = 1
        lang.save(update_fields=["min_plans"])
        Plan.objects.create(slug="p", language="es", title="Un plan", is_published=False)
        self.assertEqual(self._report(lang)["plans"].status, readiness_module.FAIL)

    def test_zero_still_disables_the_check(self):
        lang = Language.objects.get(code="es")
        lang.min_plans = 0
        lang.save(update_fields=["min_plans"])
        self.assertEqual(self._report(lang)["plans"].status, readiness_module.SKIPPED)


class LanguageSuggestionTests(SimpleTestCase):
    """The shortlist behind "Add a language".

    Its value is entirely in what it rules out and how it orders — a suggestion
    with no Bible would propose an untranslatable language, and an order that
    ignores reach buries the languages worth doing first.
    """

    CATALOG = [
        {"code": "cus", "name": "Chinese Union", "language_code": "zh-hans",
         "language_name": "Chinese", "direction": "ltr", "is_public_domain": True,
         "license": "Public Domain"},
        {"code": "irvhin", "name": "Indian Revised Version", "language_code": "hi",
         "language_name": "Hindi", "direction": "ltr", "is_public_domain": False,
         "license": "CC BY 4.0"},
        {"code": "arb-vd", "name": "Van Dyck", "language_code": "ar",
         "language_name": "Arabic", "direction": "rtl", "is_public_domain": True,
         "license": "Public Domain"},
        {"code": "tischendorf", "name": "Tischendorf", "language_code": "grc",
         "language_name": "Greek", "direction": "ltr", "is_public_domain": True,
         "license": "Public Domain"},
        {"code": "nostudy", "name": "Whatever", "language_code": "xx",
         "language_name": "Unlisted", "direction": "ltr", "is_public_domain": True,
         "license": "Public Domain"},
    ]

    def _suggest(self, **kw):
        with mock.patch("library.language_suggestions._translations", return_value=self.CATALOG):
            return language_suggestions.suggestions(**kw)

    def test_orders_by_reach_not_licence(self):
        # Hindi's Bible is CC-BY and Arabic's is public domain, but Hindi reaches
        # far more people — an earlier cut sorted by licence and buried it.
        codes = [s["code"] for s in self._suggest()]
        self.assertEqual(codes[:3], ["zh-hans", "hi", "ar"])

    def test_excludes_languages_already_added(self):
        codes = [s["code"] for s in self._suggest(existing={"hi", "ar"})]
        self.assertNotIn("hi", codes)
        self.assertNotIn("ar", codes)

    def test_excludes_ancient_and_liturgical_source_languages(self):
        # Koine Greek is in the catalogue as a SOURCE text; nobody reads a
        # devotional library in it.
        self.assertNotIn("grc", [s["code"] for s in self._suggest()])

    def test_excludes_languages_with_no_reference_entry(self):
        # No native name and no reach figure means we cannot fill the form.
        self.assertNotIn("xx", [s["code"] for s in self._suggest()])

    def test_carries_everything_the_form_needs(self):
        hi = next(s for s in self._suggest() if s["code"] == "hi")
        self.assertEqual(hi["name"], "Hindi")
        self.assertEqual(hi["native_name"], "हिन्दी")
        self.assertEqual(hi["bible"], "irvhin")
        self.assertTrue(hi["attribution_required"])
        self.assertFalse(hi["rtl"])
        self.assertTrue(next(s for s in self._suggest() if s["code"] == "ar")["rtl"])

    def test_disambiguates_names_the_catalogue_gets_wrong(self):
        zh = next(s for s in self._suggest() if s["code"] == "zh-hans")
        self.assertEqual(zh["name"], "Chinese (Simplified)")

    def test_degrades_to_empty_when_take_root_is_unreachable(self):
        # The admin page must still load; a missing picker beats a 500.
        with mock.patch("library.language_suggestions._translations", return_value=[]):
            self.assertEqual(language_suggestions.suggestions(), [])


class SearchTotalsAndPagingTests(TestCase):
    """What the merged list is a sample OF, and how to get the rest.

    The page used to render "30 results" for a query matching hundreds of
    passages, because MAX_RESULTS and the per-type CAPS truncated silently.
    These cover the two halves of the fix: an honest count, and a way past the
    cap — including that sorting now orders ALL matches rather than the handful
    the client happened to hold.
    """

    LOTS = 25  # comfortably past CAPS["chapter"]=20 and PAGE_SIZE=20

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="a", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author, slug="b", language="en", title="Abiding"
        )
        # Titles run OPPOSITE to chapter order on purpose: the natural (relevance)
        # order is by chapter order, so a title sort that only reordered the page
        # it was given would still look right if the two agreed. They must not.
        for i in range(1, self.LOTS + 1):
            Chapter.objects.create(
                book=self.book,
                order=i,
                title=f"Chapter {self.LOTS - i + 1:02d}",
                body_html=f"<p>Abide in prayer, number {i}.</p>",
            )

    def test_the_merged_list_is_still_capped(self):
        # Unchanged behaviour — the fix is to describe the cap, not remove it.
        hits = search_library("prayer", "en")
        chapters = [h for h in hits if h["type"] == "chapter"]
        self.assertEqual(len(chapters), search_module.CAPS["chapter"])

    def test_counts_exceed_what_the_page_returns(self):
        counts, capped = search_module.count_by_type("prayer", "en")
        self.assertEqual(counts["chapter"], self.LOTS)
        self.assertGreater(counts["chapter"], search_module.CAPS["chapter"])
        self.assertFalse(capped["chapter"])

    def test_counts_stop_at_the_ceiling_and_say_so(self):
        with mock.patch.object(search_module, "COUNT_CEILING", 5):
            counts, capped = search_module.count_by_type("prayer", "en")
        self.assertEqual(counts["chapter"], 5)
        self.assertTrue(capped["chapter"], "a truncated count must be marked")

    def test_a_type_with_no_matches_is_absent_rather_than_zero(self):
        counts, _ = search_module.count_by_type("prayer", "en")
        self.assertNotIn("plan", counts)

    def test_counts_use_the_same_filter_as_the_results(self):
        # An unpublished book must not inflate the count past what a reader can
        # reach — the failure mode of computing counts from a second query.
        hidden = Book.objects.create(
            author=self.author, slug="h", language="en", title="H", is_published=False
        )
        Chapter.objects.create(book=hidden, order=1, title="X", body_html="<p>prayer</p>")
        counts, _ = search_module.count_by_type("prayer", "en")
        self.assertEqual(counts["chapter"], self.LOTS)

    def test_paging_reaches_past_the_cap(self):
        first = search_module.page_by_type("prayer", "en", "chapter", offset=0, limit=20)
        second = search_module.page_by_type("prayer", "en", "chapter", offset=20, limit=20)
        self.assertEqual(len(first), 20)
        self.assertEqual(len(second), self.LOTS - 20)
        keys = {(h["book_slug"], h["chapter_order"]) for h in first + second}
        self.assertEqual(len(keys), self.LOTS, "pages must not overlap or skip")

    def test_sorting_orders_every_match_not_just_the_page(self):
        """The point of moving sort off the client.

        "Chapter 01" is the LAST chapter in reading order, so it is nowhere near
        the first page by relevance. Asking for the first five by title must
        surface it — which is only possible if the sort ran over all 25 matches
        in the database rather than over a page already chosen by rank.
        """
        page = search_module.page_by_type(
            "prayer", "en", "chapter", offset=0, limit=5, sort="title"
        )
        self.assertEqual(
            [h["chapter_title"] for h in page][:3],
            ["Chapter 01", "Chapter 02", "Chapter 03"],
        )
        # And the relevance page really does start elsewhere, or the above proves
        # nothing.
        natural = search_module.page_by_type("prayer", "en", "chapter", limit=5)
        self.assertEqual(natural[0]["chapter_title"], f"Chapter {self.LOTS:02d}")

    def test_an_unknown_type_is_empty_not_an_error(self):
        self.assertEqual(search_module.page_by_type("prayer", "en", "nope"), [])

    # --- endpoint -------------------------------------------------------------

    def test_the_response_carries_the_real_totals(self):
        res = self.client.get("/api/library/search/?q=prayer")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["totals"]["chapter"], self.LOTS)
        self.assertFalse(res.data["totals_capped"]["chapter"])
        self.assertEqual(res.data["page_size"], search_module.PAGE_SIZE)

    def test_type_param_returns_only_that_type(self):
        res = self.client.get("/api/library/search/?q=prayer&type=chapter&offset=20")
        self.assertEqual(res.data["type"], "chapter")
        self.assertEqual(res.data["offset"], 20)
        self.assertTrue(all(h["type"] == "chapter" for h in res.data["results"]))
        self.assertEqual(len(res.data["results"]), self.LOTS - 20)

    def test_paging_is_not_logged_as_a_search(self):
        # Otherwise "show more" would inflate the popular-queries report, which
        # is meant to count what readers ASKED, not how far they scrolled.
        SearchQueryLog.objects.all().delete()
        self.client.get("/api/library/search/?q=prayer")
        self.client.get("/api/library/search/?q=prayer&type=chapter&offset=20")
        self.assertEqual(SearchQueryLog.objects.count(), 1)

    def test_a_hostile_offset_is_clamped(self):
        res = self.client.get("/api/library/search/?q=prayer&type=chapter&offset=999999")
        self.assertEqual(res.status_code, 200)
        self.assertLessEqual(res.data["offset"], 500)

    def test_a_junk_sort_falls_back_to_relevance(self):
        res = self.client.get("/api/library/search/?q=prayer&type=chapter&sort=drop%20table")
        self.assertEqual(res.data["sort"], "relevance")

    def test_a_junk_offset_does_not_500(self):
        res = self.client.get("/api/library/search/?q=prayer&type=chapter&offset=abc")
        self.assertEqual(res.status_code, 200)


class SearchScopeTests(TestCase):
    """Searching inside one author, topic or book.

    A scope is a *place in the library*. The contract worth pinning is that it
    narrows everything together — the list, the counts and the "show more"
    pages — because a count computed against a wider filter than the results is
    worse than no count at all.
    """

    def setUp(self):
        self.client = APIClient()
        murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        spurgeon = Author.objects.create(slug="spurgeon", name="C. H. Spurgeon")

        self.humility = Book.objects.create(
            author=murray, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(
            book=self.humility, order=1, title="Dependence",
            body_html="<p>Humility is the place of entire dependence on God.</p>",
        )
        abide = Book.objects.create(
            author=murray, slug="abide", language="en", title="Abide in Christ"
        )
        Chapter.objects.create(
            book=abide, order=1, title="The Vine",
            body_html="<p>Humility is the root of abiding.</p>",
        )
        grace = Book.objects.create(
            author=spurgeon, slug="all-of-grace", language="en", title="All of Grace"
        )
        Chapter.objects.create(
            book=grace, order=1, title="To You",
            body_html="<p>Humility before a holy God.</p>",
        )
        Sermon.objects.create(
            author=spurgeon, slug="the-blood", language="en", title="The Blood",
            body_html="<p>Humility at the cross.</p>",
        )

        topic = Topic.objects.create(slug="deeper-life", title="The Deeper Life")
        TopicBook.objects.create(topic=topic, book_slug="humility")
        TopicSermon.objects.create(topic=topic, sermon_slug="the-blood")

    def search(self, scope=None, q="humility"):
        url = f"/api/library/search/?q={q}"
        if scope:
            url += f"&in={scope}"
        return self.client.get(url)

    def slugs(self, res, kind="chapter"):
        key = {"chapter": "book_slug", "book": "book_slug", "sermon": "sermon_slug"}[kind]
        return {h[key] for h in res.data["results"] if h["type"] == kind}

    def test_unscoped_search_sees_the_whole_library(self):
        # The control: without this the scoped assertions prove nothing.
        self.assertEqual(
            self.slugs(self.search()), {"humility", "abide", "all-of-grace"}
        )

    def test_an_author_scope_keeps_only_that_author(self):
        res = self.search("author:andrew-murray")
        self.assertEqual(self.slugs(res), {"humility", "abide"})
        self.assertEqual(res.data["scope"], {
            "kind": "author", "slug": "andrew-murray", "label": "Andrew Murray",
        })

    def test_a_book_scope_keeps_only_that_book(self):
        res = self.search("book:humility")
        self.assertEqual(self.slugs(res), {"humility"})

    def test_a_topic_scope_follows_the_shelf(self):
        # Topic membership is by slug and spans books AND sermons.
        res = self.search("topic:deeper-life")
        self.assertEqual(self.slugs(res), {"humility"})
        self.assertEqual(self.slugs(res, "sermon"), {"the-blood"})

    def test_the_counts_are_scoped_too(self):
        # The bug this guards: the results honour the scope and the counts don't,
        # so the page offers to show three chapters when the scope holds one.
        self.assertEqual(self.search().data["totals"]["chapter"], 3)
        self.assertEqual(self.search("book:humility").data["totals"]["chapter"], 1)

    def test_the_show_more_pages_are_scoped_too(self):
        res = self.client.get(
            "/api/library/search/?q=humility&type=chapter&in=book:humility"
        )
        self.assertEqual(self.slugs(res), {"humility"})

    def test_navigational_types_drop_out_of_a_scope(self):
        # Searching within Andrew Murray and being handed Andrew Murray back is
        # noise — you are already there. Same for the book you are reading in.
        res = self.search("author:andrew-murray")
        self.assertNotIn("author", res.data["totals"])
        self.assertNotIn("book", self.search("book:humility").data["totals"])

    def test_a_shelf_with_nothing_in_this_language_is_not_named(self):
        # The chip and the results must come from the same filter. When they
        # didn't, an author with no Swahili work still got a confident "Searching
        # in Andrew Murray" over an empty list — the reader is told the shelf is
        # there and shown nothing on it.
        res = self.client.get(
            "/api/library/search/?q=humility&language=sw&in=author:andrew-murray"
        )
        self.assertIsNone(res.data["scope"])
        self.assertEqual(res.data["results"], [])

    def test_a_scope_that_does_not_exist_is_reported_as_such(self):
        # Not silently unscoped: the page must be able to say "no such shelf"
        # rather than show the whole library under a confident label.
        res = self.search("author:nobody")
        self.assertIsNone(res.data["scope"])
        self.assertEqual(res.data["results"], [])

    def test_a_malformed_scope_searches_the_whole_library(self):
        for junk in ("", "banana", "banana:x", ":x", "author:"):
            res = self.search(junk)
            self.assertNotIn("scope", res.data, junk)
            self.assertEqual(self.slugs(res), {"humility", "abide", "all-of-grace"})

    def test_a_scoped_search_is_not_logged(self):
        # A scoped miss means "this author didn't write about that", not "the
        # library lacks it" — logging it would put phantom gaps into the
        # translation worklist the zero-result report exists to produce.
        SearchQueryLog.objects.all().delete()
        self.search()
        self.search("author:andrew-murray")
        self.search("author:andrew-murray", q="quantum")
        self.assertEqual(SearchQueryLog.objects.count(), 1)

    def test_no_did_you_mean_inside_a_scope(self):
        # The suggester reads the whole library, so inside a scope it would
        # propose a spelling this author never used — a second empty page.
        wide = self.search(q="humilty")
        self.assertIn("suggestion", wide.data)
        scoped = self.search("author:spurgeon", q="humilty")
        self.assertNotIn("suggestion", scoped.data)


class SearchClickTests(TestCase):
    """Whether search results actually get opened.

    The half the query log can't see: a query returning forty near-misses and a
    query returning the right answer are both "found something" there.
    """

    def setUp(self):
        self.client = APIClient()

    def click(self, **kw):
        body = {"query": "humility", "type": "chapter", "position": 1, **kw}
        return self.client.post("/api/library/search-click/", body, format="json")

    def test_a_click_is_recorded_anonymously(self):
        res = self.click()
        self.assertEqual(res.status_code, 204)
        row = SearchClickLog.objects.get()
        self.assertEqual(row.query, "humility")
        self.assertEqual(row.result_type, "chapter")
        self.assertEqual(row.position, 1)
        # No user column exists to leak — the guarantee is structural.
        self.assertFalse(hasattr(row, "profile"))
        self.assertFalse(hasattr(row, "user"))

    def test_the_language_the_reader_was_in_is_recorded(self):
        # It came back "en" for everyone: language_from_request reads only the
        # query string, and the beacon posted to a bare path. Harmless in the
        # total, and wrong the moment click-through is split by language — the
        # form the rest of this report is deliberately built in.
        res = self.client.post(
            "/api/library/search-click/?language=sw",
            {"query": "sala", "type": "chapter", "position": 1},
            format="json",
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(SearchClickLog.objects.get().language, "sw")

    def test_a_cross_origin_form_post_cannot_write(self):
        # An APIView is CSRF-exempt and this API authenticates by bearer token,
        # so with a form parser enabled any page on the internet could make its
        # visitors write rows here — no preflight, CORS irrelevant for a write
        # nobody reads back. JSON-only means the browser must preflight.
        res = self.client.post(
            "/api/library/search-click/",
            {"query": "humility", "type": "chapter", "position": 1},
            format="multipart",
        )
        self.assertEqual(res.status_code, 415)
        self.assertEqual(SearchClickLog.objects.count(), 0)

    def test_junk_is_dropped_without_telling_the_caller(self):
        # An unauthenticated write, so it is bounded rather than trusted. 204
        # either way: there is nothing to say, and nothing worth saying to a
        # prober mapping the validation.
        for bad in (
            {"query": "h"},                      # shorter than a real query
            {"query": "x" * 201},                # past the column
            {"type": "password"},                # not a type search produces
            {"position": 0},                     # ranks are 1-based
            {"position": -3},
            {"position": 99999},                 # past any page served
            {"position": "; drop table"},
            {"query": ["a", "b"]},               # would stringify to "['a', 'b']"
            {"type": {"a": 1}},
        ):
            self.assertEqual(self.click(**bad).status_code, 204, bad)
        self.assertEqual(SearchClickLog.objects.count(), 0)

    def test_a_broken_log_never_breaks_the_click(self):
        from unittest.mock import patch

        with patch.object(
            SearchClickLog.objects, "create", side_effect=RuntimeError("db down")
        ):
            self.assertEqual(self.click().status_code, 204)

    @override_settings(DEBUG=True)
    def test_queries_that_found_things_but_led_nowhere_surface(self):
        # The silent failure. "answered" returned results AND got opened;
        # "ignored" returned results and never did — only the second is a gap,
        # and nothing else on the report can tell them apart.
        for _ in range(4):
            SearchQueryLog.objects.create(query="ignored", language="en", result_count=9)
            SearchQueryLog.objects.create(query="answered", language="en", result_count=9)
        SearchClickLog.objects.create(
            query="answered", language="en", result_type="book", position=1
        )

        res = self.client.get("/api/admin/search-stats/")
        self.assertEqual(res.status_code, 200)
        unopened = [r["query"] for r in res.data["unopened_queries"]]
        self.assertIn("ignored", unopened)
        self.assertNotIn("answered", unopened)
        self.assertEqual(res.data["overview"]["clicks_30d"], 1)

    def test_the_trim_step_prunes_both_logs_together(self):
        # Clicks outliving their queries would compute click-through against a
        # truncated denominator.
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        old = SearchClickLog.objects.create(
            query="ancient", language="en", result_type="book", position=1
        )
        SearchClickLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=200)
        )
        self.click()  # fresh
        call_command("trim_search_log", verbosity=0)
        self.assertEqual(
            list(SearchClickLog.objects.values_list("query", flat=True)), ["humility"]
        )


class InkSafePlateTests(SimpleTestCase):
    """The legibility floor under every generated plate.

    White type on a coloured plate is the house style across both cover tiers,
    so when a plate colour is too pale the colour has to yield, not the ink. The
    numbers below are the library's real ones: 8 of 45 plate colours failed AA
    on the 23px author line, worst at 2.81:1.
    """

    PALE = ["#ca8d21", "#4996a2", "#2f9e44", "#987952", "#987652", "#ffffff"]
    ALREADY_LEGIBLE = ["#3b5bdb", "#1864ab", "#7a5c48", "#14532d", "#000000"]

    def test_pale_plates_are_darkened_until_the_byline_passes(self):
        from library.covers import AUTHOR_MIN_CONTRAST, author_ink_contrast, ink_safe

        for color in self.PALE:
            with self.subTest(color=color):
                self.assertLess(author_ink_contrast(color), AUTHOR_MIN_CONTRAST)
                self.assertGreaterEqual(
                    author_ink_contrast(ink_safe(color)), AUTHOR_MIN_CONTRAST
                )

    def test_legible_plates_are_returned_untouched(self):
        from library.covers import ink_safe

        # The floor must be a no-op on 37 of the library's 45 plate colours, or
        # it would rewrite artwork it has no business rewriting.
        for color in self.ALREADY_LEGIBLE:
            with self.subTest(color=color):
                self.assertEqual(ink_safe(color), color)

    def test_hue_survives_the_floor(self):
        from library.covers import ink_safe

        # Scaling channels, not moving through HLS: a green plate comes back a
        # deeper green. Ratios between channels are what carry the hue.
        darkened = ink_safe("#2f9e44")
        original = (0x2F, 0x9E, 0x44)
        got = tuple(int(darkened[i : i + 2], 16) for i in (1, 3, 5))
        self.assertLess(got[0], original[0])
        self.assertAlmostEqual(got[1] / got[0], original[1] / original[0], delta=0.08)
        self.assertAlmostEqual(got[2] / got[0], original[2] / original[0], delta=0.08)

    def test_blank_and_malformed_colours_fall_back_to_the_house_blue(self):
        from library.covers import ink_safe

        for value in ["", None, "#zzz", "not-a-colour"]:
            with self.subTest(value=value):
                self.assertEqual(ink_safe(value), "#3b5bdb")

    def test_the_drawn_plate_uses_the_floored_colour(self):
        from library.covers import build_ground

        # The floor is only worth anything if build_ground actually applies it.
        svg = build_ground("#ca8d21")
        self.assertIn('stop-color="#956818"', svg)
        self.assertNotIn('stop-color="#ca8d21"', svg)


class CoverEmblemTests(SimpleTestCase):
    """The device that stops a shelf of generated plates reading as wallpaper.

    105 of the library's 153 editions wear a generated plate. The colour varies
    per book but the COMPOSITION doesn't, so a grid of them is twelve coloured
    slabs with nothing to tell one from another at a glance. The emblem is a
    second variable, and it is the book's own — the drawing its topic already
    wears on the topics shelf.
    """

    def test_a_book_wears_its_topics_emblem(self):
        from library.covers import emblem_for_book

        self.assertEqual(emblem_for_book("prevailing-prayer"), "praying-hands")
        self.assertEqual(emblem_for_book("confessions"), "laurel-tome")
        self.assertIsNone(emblem_for_book("a-book-in-no-topic"))

    def test_the_topic_seed_stays_the_source_of_which_books_a_topic_holds(self):
        """One list of shelf members, read by the seed AND by the generator.

        `covers.py` is deliberately Django-free — the curation scripts import it
        as a plain module — so it cannot import `seed_topics`, which pulls in
        `django.core.management`. The membership therefore lives in
        `library/topic_seed.py`, which both import. This fails if a copy is
        introduced: an emblem drawn from a second list would be right until the
        day someone edits only one of them.
        """
        from library.management.commands import seed_topics
        from library.topic_seed import TOPICS

        self.assertIs(seed_topics.TOPICS, TOPICS)

    def test_the_emblem_lands_in_the_band_the_type_reserves(self):
        """The emblem lands in the band, centred, at the size the band allows.

        It used to be fitted instead: the band between the last line of type and
        the lockup was measured and the drawing sized to what was left, because
        a four-line title pushed the type 52 units further down than a one-line
        one. Nothing in this module knows where the type ends any more — the
        browser wraps it — so the band is reserved on both sides instead.

        That the CSS reserves the SAME band is checked by `coverBand.test.ts`,
        which reads the constants below and converts them; asserting it here
        would only restate the arithmetic that defines them.
        """
        import re

        from library.covers import _EMBLEM_BOTTOM, _EMBLEM_TOP, build_ground

        found = re.search(
            r'<g transform="translate\((\d+) (\d+)\) scale\(([\d.]+)\)"',
            build_ground("#0b7285", "praying-hands"),
        )
        left, top, scale = int(found.group(1)), int(found.group(2)), float(found.group(3))
        size = scale * 48  # every emblem is drawn on a 48x48 canvas

        self.assertEqual(top, _EMBLEM_TOP)
        self.assertEqual(top + size, _EMBLEM_BOTTOM)
        self.assertEqual(left, (600 - size) / 2, "emblem is not centred on the plate")

    def test_a_plate_without_an_emblem_is_unchanged(self):
        """A book in no topic, or one whose emblem the API image is missing,
        gets the plate it had — not a broken one, and not a shifted one."""
        from library.covers import build_ground

        self.assertEqual(
            build_ground("#0b7285"),
            build_ground("#0b7285", emblem="not-an-emblem"),
        )


class GeneratedCoverTests(TestCase):
    """The two invariants of the cover generator.

    Both of these were real defects, not hypotheticals: covers were written to
    one path per SLUG while the loop ran over every language row, so the last
    language processed overwrote the rest and every locale served the same
    (English) cover under a translated title.
    """

    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")

    def _book(self, language, title, cover_url=""):
        return Book.objects.create(
            slug="waiting-on-god",
            language=language,
            title=title,
            author=self.author,
            cover_url=cover_url,
            cover_color="#2f6f6b",
        )

    def test_each_language_gets_its_own_cover_path(self):
        from library.management.commands.generate_covers import cover_path

        # English keeps the historic path so the covers already live don't 404.
        self.assertEqual(cover_path("waiting-on-god", "en")[0], "/covers/waiting-on-god.svg")
        self.assertEqual(cover_path("waiting-on-god", "es")[0], "/covers/es/waiting-on-god.svg")
        self.assertEqual(cover_path("waiting-on-god", "ar")[0], "/covers/ar/waiting-on-god.svg")

    def test_artwork_is_never_overwritten_even_with_force(self):
        """--force means "redraw the generated ones", never "replace the art"."""
        from library.management.commands.generate_covers import is_generated

        self.assertFalse(is_generated("/covers/godliness.jpg"))
        self.assertFalse(is_generated("/covers/baptism.png"))
        self.assertTrue(is_generated("/covers/all-of-grace.svg"))
        self.assertTrue(is_generated(""))

    def test_a_ground_carries_no_words(self):
        """The whole point of the tier, and the thing that can regress quietly.

        The generator used to composite the byline, the title, the rule and the
        subtitle into the file, which is why it could only ever set them in a
        font the device already had — an `<img>`-rendered SVG cannot reach the
        page's webfonts, so every cover in the library came out in Georgia. A
        stray `<text>` node here would put a second, worse-set title under the
        one `BookCover` draws, in the wrong language on seven locales out of
        eight.
        """
        from library.covers import build_ground

        svg = build_ground("#8a4b1f", "praying-hands")
        self.assertNotIn("<text", svg)
        self.assertNotIn("font-family", svg)


class CuratedArtFetchTests(SimpleTestCase):
    """A half-downloaded painting must not be mistaken for a whole one.

    `build_curated_covers` caches museum originals under `.cache/` and decides
    it already has one with `raw.exists()` — nothing downstream re-reads the
    bytes. So a transfer that dies mid-stream used to leave a truncated JPEG
    that every later run accepted as the painting, cropped, and committed.

    Not hypothetical: it happened while curating this batch. The Met connection
    dropped and left a 163 KB `met-437975.orig.jpg` with no end-of-image marker,
    which the next run would have shipped as Spurgeon's cover.
    """

    def test_an_interrupted_download_leaves_no_file_behind(self):
        from library.management.commands import build_curated_covers as cmd

        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "painting.orig.jpg"

            # A response that yields some bytes and then dies, which is what a
            # dropped connection looks like from up here.
            def die_partway(src, dst, *a, **kw):
                dst.write(b"\xff\xd8" + b"x" * 4096)
                raise BrokenPipeError(32, "Broken pipe")

            with (
                mock.patch.object(cmd.urllib.request, "urlopen", mock.MagicMock()),
                mock.patch.object(cmd.shutil, "copyfileobj", die_partway),
            ):
                with self.assertRaises(BrokenPipeError):
                    cmd._fetch("https://example.invalid/x.jpg", dest)

            # Nothing at all: not the truncated download the cache would trust
            # as the finished painting, and not the `.part` scratch either.
            self.assertEqual(
                [q.name for q in Path(td).iterdir()],
                [],
                "an interrupted download left a file behind",
            )


class CuratedArtTests(TestCase):
    """Guards on the curated-artwork manifest (library/curated_art.py)."""

    def test_susanna_wesley_has_no_artwork_on_purpose(self):
        """Every candidate portrait was of a DIFFERENT real woman, and a
        portrait on a cover reads as a portrait OF that person. Adding one
        would imply an image is Susanna Wesley when it isn't. If someone adds
        her here later, this should make them argue for it first."""
        from library.curated_art import CURATED

        self.assertNotIn("susanna-wesley-clarke", CURATED)

    def test_every_entry_records_its_provenance_and_reason(self):
        from library.curated_art import CURATED, SOURCES

        for slug, art in CURATED.items():
            with self.subTest(slug=slug):
                # The id is only meaningful with the collection it belongs to —
                # two museums number their objects independently.
                self.assertIn(art.source, SOURCES, "unknown collection")
                self.assertGreater(art.object_id, 0, "needs an object id as the licence receipt")
                self.assertTrue(art.artist.strip())
                self.assertTrue(art.title.strip())
                # `why` is not decoration: it's what stops the next person
                # swapping in a prettier painting that means nothing.
                self.assertTrue(art.why.strip())

    def test_every_source_can_actually_be_fetched(self):
        """A source in the manifest with no fetcher is a build that dies on a
        re-run, months after the entry was added and by someone else."""
        from library.curated_art import CURATED
        from library.management.commands.build_curated_covers import FETCHERS

        for slug, art in CURATED.items():
            with self.subTest(slug=slug):
                self.assertIn(art.source, FETCHERS, f"no fetcher for {art.source!r}")


    def test_credit_names_the_artist_and_the_source(self):
        from library.curated_art import credit

        c = credit("confessions")
        self.assertIn("Géricault", c)
        self.assertIn("Metropolitan Museum", c)
        self.assertIsNone(credit("a-book-with-no-curated-art"))

    def test_the_credit_reaches_the_reader(self):
        """The book detail API must actually SERVE the credit.

        It used to live in the composited SVG's `<desc>`, where nothing
        surfaced it; the painting is now a plain image with the type drawn over
        it in HTML, so the API is the only route left. A `get_artwork_credit`
        method with no field declared beside it computes a value DRF never
        emits — which is exactly what shipped for a moment here, and no test
        would have noticed.
        """
        from library.serializers import BookDetailSerializer

        self.assertIn("artwork_credit", BookDetailSerializer.Meta.fields)
        author = Author.objects.create(slug="augustine", name="Augustine of Hippo")
        painted = Book.objects.create(
            slug="confessions", language="en", title="Confessions", author=author,
            cover_url="/covers/art/confessions.jpg",
        )
        self.assertIn("Géricault", BookDetailSerializer(painted).data["artwork_credit"])

        plain = Book.objects.create(
            slug="a-book-with-no-curated-art", language="en", title="Plain", author=author,
            cover_url="/covers/plain.jpg",
        )
        self.assertIsNone(BookDetailSerializer(plain).data["artwork_credit"])

        # The manifest lists the WORK, but an edition may carry designed artwork
        # of its own — the per-language gate deliberately allows it. Crediting a
        # painter for a cover this reader isn't looking at is worse than saying
        # nothing.
        own_cover = Book.objects.create(
            slug="confessions", language="es", title="Confesiones", author=author,
            cover_url="/covers/es/confessions.jpg",
        )
        self.assertIsNone(BookDetailSerializer(own_cover).data["artwork_credit"])


class CuratedCoversSurviveForceTests(TestCase):
    """`generate_covers --force` must not redraw the curated artwork.

    This is a real regression, observed in production on 2026-08-02: a --force
    run listed pilgrims-progress, the-reformed-pastor, waiting-on-god and the
    rest and rewrote them as plain typographic plates. It did no harm THERE
    (throwaway container, and cover_url was unchanged) — but the same command
    on a developer's machine overwrites the committed artwork, and the loss is
    committable without anyone noticing, because the file still exists and the
    page still renders.

    is_generated() cannot catch this on its own: curated covers are .svg too.
    """

    def setUp(self):
        self.author = Author.objects.create(slug="jb", name="John Bunyan")

    def test_a_curated_slug_is_skipped_even_with_force(self):
        from io import StringIO

        from django.core.management import call_command

        from library.curated_art import CURATED

        slug = "pilgrims-progress"
        self.assertIn(slug, CURATED, "fixture assumes this slug is curated")
        Book.objects.create(
            slug=slug, language="en", title="The Pilgrim's Progress",
            author=self.author, cover_url=f"/covers/{slug}.svg", cover_color="#6b4b2a",
        )
        out = StringIO()
        call_command("generate_covers", "--force", "--dry-run", stdout=out)
        report = out.getvalue()
        self.assertNotIn(f"{slug}.svg", report, "curated cover was redrawn by --force")
        self.assertIn("kept 1 curated", report)

    def test_an_uncurated_slug_is_still_redrawn(self):
        """The guard must not turn --force into a no-op for everything else."""
        from io import StringIO

        from django.core.management import call_command

        from library.curated_art import CURATED

        # A slug this test INVENTS, rather than a real uncurated book. It used
        # to name `till-he-come`, which was a fine example right up until that
        # book was given a painting — at which point the test was asserting the
        # opposite of what it means, and failed for a reason that had nothing to
        # do with the guard it exists to check. Curating another book must not
        # be able to break this again.
        slug = "a-book-nobody-has-curated"
        self.assertNotIn(slug, CURATED)
        Book.objects.create(
            slug=slug, language="en", title="Uncurated",
            author=self.author, cover_url=f"/covers/{slug}.svg", cover_color="#333",
        )
        out = StringIO()
        call_command("generate_covers", "--force", "--dry-run", stdout=out)
        self.assertIn(f"{slug}.svg", out.getvalue())


class ScriptureFetchTests(TestCase):
    """fetch_chapter must never cache a TRANSIENT failure as a permanent miss —
    that is how one dropped request silently strips scripture from every later
    chapter citing the same passage (review #28). Only a definitive answer (the
    verses, or a 404) is cached; a persistent transient failure raises."""

    def setUp(self):
        from library import translation

        translation._verse_cache.clear()
        self.addCleanup(translation._verse_cache.clear)

    def _resp(self, status=200, payload=None):
        r = mock.Mock()
        r.status_code = status
        r.ok = 200 <= status < 300
        r.json.return_value = {} if payload is None else payload
        return r

    def test_404_is_a_definitive_miss_and_is_cached(self):
        with mock.patch(
            "library.translation.requests.get", return_value=self._resp(404)
        ) as get:
            self.assertIsNone(fetch_chapter("rv1858", Ref("JHN", 3)))
            self.assertIsNone(fetch_chapter("rv1858", Ref("JHN", 3)))  # served from cache
        self.assertEqual(get.call_count, 1)

    def test_success_returns_and_caches(self):
        payload = {"reference": "John 3", "verses": [{"number": 16, "text": "For God…"}]}
        with mock.patch(
            "library.translation.requests.get", return_value=self._resp(200, payload)
        ) as get:
            self.assertEqual(fetch_chapter("rv1858", Ref("JHN", 3)), payload)
            fetch_chapter("rv1858", Ref("JHN", 3))
        self.assertEqual(get.call_count, 1)

    def test_transient_failure_retries_then_raises_and_is_not_cached(self):
        import requests

        from library.translation import _FETCH_ATTEMPTS, ScriptureUnavailable

        with mock.patch("library.translation.time.sleep"), mock.patch(
            "library.translation.requests.get",
            side_effect=requests.RequestException("timeout"),
        ) as get:
            with self.assertRaises(ScriptureUnavailable):
                fetch_chapter("rv1858", Ref("ROM", 8))
        self.assertEqual(get.call_count, _FETCH_ATTEMPTS)

        # NOT cached: once the API recovers, the same passage fetches cleanly.
        good = self._resp(200, {"verses": [{"number": 1, "text": "x"}]})
        with mock.patch("library.translation.requests.get", return_value=good):
            self.assertTrue(fetch_chapter("rv1858", Ref("ROM", 8)).get("verses"))

    def test_transient_then_success_is_retried(self):
        import requests

        good = self._resp(200, {"verses": [{"number": 1, "text": "x"}]})
        with mock.patch("library.translation.time.sleep"), mock.patch(
            "library.translation.requests.get",
            side_effect=[requests.RequestException("blip"), good],
        ) as get:
            self.assertTrue(fetch_chapter("rv1858", Ref("PSA", 23)).get("verses"))
        self.assertEqual(get.call_count, 2)

    def test_5xx_is_treated_as_transient(self):
        from library.translation import _FETCH_ATTEMPTS, ScriptureUnavailable

        with mock.patch("library.translation.time.sleep"), mock.patch(
            "library.translation.requests.get", return_value=self._resp(503)
        ) as get:
            with self.assertRaises(ScriptureUnavailable):
                fetch_chapter("rv1858", Ref("ISA", 55))
        self.assertEqual(get.call_count, _FETCH_ATTEMPTS)


class ApprovalDurabilityTests(TestCase):
    """An approval must be written into the committed fixture, or a fresh-DB
    rebuild (seed_if_empty loaddata) re-gates it to unreviewed (review #27)."""

    def _fixture(self, tmp, source_type="ai_unreviewed"):
        rows = [
            {
                "model": "library.book",
                "fields": {
                    "slug": "humility",
                    "language": "sw",
                    "source_type": source_type,
                    "title": "Unyenyekevu",
                },
            }
        ]
        p = Path(tmp) / "humility.sw.json"
        p.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        return p

    def test_persist_source_type_flips_and_is_idempotent(self):
        from library import content_fixtures as cf

        with tempfile.TemporaryDirectory() as tmp:
            p = self._fixture(tmp)
            self.assertTrue(cf.persist_source_type(p, "ai_reviewed"))
            self.assertIn('"source_type": "ai_reviewed"', p.read_text())
            self.assertNotIn("ai_unreviewed", p.read_text())
            self.assertFalse(cf.persist_source_type(p, "ai_reviewed"))  # no-op second time

    def test_persist_source_type_requires_exactly_one_match(self):
        from library import content_fixtures as cf

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.json"
            p.write_text('[{"model": "library.book", "fields": {"slug": "x"}}]', "utf-8")
            with self.assertRaises(ValueError):
                cf.persist_source_type(p, "ai_reviewed")

    def test_approve_translation_updates_db_and_fixture(self):
        from django.core.management import call_command

        author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fixture(tmp)
            with mock.patch(
                "library.content_fixtures.book_fixture_path", return_value=p
            ):
                call_command("approve_translation", "humility", language="sw")
            self.assertIn('"source_type": "ai_reviewed"', p.read_text())
        self.assertEqual(
            Book.objects.get(slug="humility", language="sw").source_type,
            Book.SourceType.AI_REVIEWED,
        )

    def test_approve_translation_survives_a_fixture_write_failure(self):
        # The DB flip is the primary action; a fixture write error (here a
        # read-only-FS style OSError) must warn, not raise — an automated caller
        # would otherwise read the traceback as "approval failed" and retry.
        from django.core.management import call_command

        author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fixture(tmp)
            with mock.patch(
                "library.content_fixtures.book_fixture_path", return_value=p
            ), mock.patch(
                "library.content_fixtures.persist_source_type",
                side_effect=OSError("read-only file system"),
            ):
                call_command("approve_translation", "humility", language="sw")  # must not raise
        self.assertEqual(
            Book.objects.get(slug="humility", language="sw").source_type,
            Book.SourceType.AI_REVIEWED,
        )


class BookCardPayloadTests(TestCase):
    """Book cards must have the same SHAPE wherever they are served from.

    ``BookListSerializer`` renders the shelf, the author page, topic pages and
    "more like this". Two of its fields depended on the caller: ``word_count``
    on an annotation the author page didn't apply (DRF drops a source-less
    field silently, so the key simply vanished), and ``topics`` on a context map
    only ``BookListView`` built (so chips were permanently ``[]`` everywhere
    else). Both are invisible from the serializer's side — only a cross-endpoint
    comparison catches them.
    """

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="murray", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(book=self.book, order=1, title="One", body_html="<p>a</p>",
                               body_text="a", word_count=120)
        Chapter.objects.create(book=self.book, order=2, title="Two", body_html="<p>b</p>",
                               body_text="b", word_count=80)
        topic = Topic.objects.create(slug="prayer", title="On Prayer")
        TopicBook.objects.create(topic=topic, book_slug="humility", sort_order=0)

    def _card(self, url):
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        payload = res.data
        books = payload if isinstance(payload, list) else payload["books"]
        return next(b for b in books if b["slug"] == "humility")

    def test_word_count_is_present_on_every_path(self):
        for url in ("/api/library/books/?language=en",
                    "/api/library/authors/murray/?language=en",
                    "/api/library/topics/prayer/?language=en"):
            with self.subTest(url=url):
                card = self._card(url)
                self.assertEqual(card["word_count"], 200, url)

    def test_topic_chips_are_present_on_every_path(self):
        for url in ("/api/library/books/?language=en",
                    "/api/library/authors/murray/?language=en",
                    "/api/library/topics/prayer/?language=en"):
            with self.subTest(url=url):
                card = self._card(url)
                self.assertEqual([t["slug"] for t in card["topics"]], ["prayer"], url)

    def test_card_keys_are_identical_across_paths(self):
        shelf = set(self._card("/api/library/books/?language=en"))
        page = set(self._card("/api/library/authors/murray/?language=en"))
        self.assertEqual(shelf, page)

    def test_untranslated_topic_yields_no_chip_on_the_author_page(self):
        # The shelf "On Prayer" has no Luganda title, so there is nothing to
        # render — the fallback must honour that rather than printing an English
        # chip onto a Luganda page (same rule the shelf already followed).
        lg = Book.objects.create(
            author=self.author, slug="humility", language="lg", title="Obuwombeefu"
        )
        Chapter.objects.create(book=lg, order=1, title="Emu", body_html="<p>a</p>",
                               body_text="a", word_count=200)
        card = self._card("/api/library/authors/murray/?language=lg")
        self.assertEqual(card["topics"], [])
        # …and the same book still carries the chip in English.
        self.assertEqual(
            [t["slug"] for t in self._card("/api/library/authors/murray/?language=en")["topics"]],
            ["prayer"],
        )

    def test_author_detail_does_not_repeat_its_book_and_sermon_queries(self):
        Sermon.objects.create(
            author=self.author, slug="abide", language="en", title="Abide",
            body_html="<p>x</p>", body_text="x",
        )
        # Books, sermons and the topic walk are each wanted by more than one
        # field, and each field used to re-run its own query — on a page the
        # prerender walks once per author per locale. This was 15; the number
        # is pinned rather than bounded so a reintroduced repeat shows up as a
        # failure with the query list attached.
        with self.assertNumQueries(10):
            self.client.get("/api/library/authors/murray/?language=en")


class SearchThrottleTests(TestCase):
    """Search is a read that WRITES: every unscoped query appends a
    SearchQueryLog row, and a miss additionally runs the full-vocabulary
    difflib scan behind "did you mean". Unbounded, that let anyone grow the
    table and skew the popular-searches report that steers translation work."""

    def setUp(self):
        self.client = APIClient()

    def test_anonymous_callers_are_bounded(self):
        from common.testing import enforcing_throttle

        from .views import _SearchThrottle

        # Throttles are inert under `manage.py test` (see common.throttling —
        # every request comes from 127.0.0.1, so a live throttle would put the
        # whole suite's searches in one bucket). This hands the class a real,
        # private cache and a squeezed rate for the duration.
        with enforcing_throttle(_SearchThrottle, "3/min"):
            codes = [
                self.client.get("/api/library/search/", {"q": f"grace{n}"}).status_code
                for n in range(4)
            ]
        self.assertEqual(codes, [200, 200, 200, 429])
        # And the writes stopped with the requests — the point of the bound.
        self.assertEqual(SearchQueryLog.objects.count(), 3)

    def test_the_shipped_rate_does_not_fire_on_ordinary_use(self):
        # The guard above proves the throttle is wired; this proves the rate we
        # actually ship is above a reader, at the real rate against a real cache.
        from common.testing import enforcing_throttle

        from .views import _SearchThrottle

        rate = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["search"]
        with enforcing_throttle(_SearchThrottle, rate):
            codes = [
                self.client.get("/api/library/search/", {"q": f"mercy{n}"}).status_code
                for n in range(40)
            ]
        self.assertEqual(set(codes), {200})

    def test_the_rate_is_far_above_a_reader(self):
        # The search page debounces at 250ms, so even continuous typing settles
        # well under this. A limit that caught search-as-you-type would be a
        # worse bug than the abuse it prevents.
        rate = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["search"]
        count, _, period = rate.partition("/")
        self.assertEqual(period, "min")
        self.assertGreaterEqual(int(count), 120)
