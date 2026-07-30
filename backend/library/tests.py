import os
from io import StringIO
from unittest import mock, skipUnless

from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .ingest import clean_title
from .translation import (
    GLOSSARY_TERMS,
    LANGUAGES,
    Ref,
    fetch_chapter,
    verify_bible_code,
)
from .models import (
    Author,
    Language,
    AuthorTranslation,
    Book,
    Chapter,
    Plan,
    PlanDay,
    SearchQueryLog,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)
from . import readiness as readiness_module
from .text import html_to_text


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
            "approve_translation", translated.slug, language=translated.language
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
        drifted = dict(
            (b.slug, reason)
            for b, reason in chapter_drift(
                Book.objects.prefetch_related("chapters"), chapters_by_book
            )
        )
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
        call_command("approve_sermon_translation", "the-immutability-of-god", language="lg")
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
        # to short.json/<slug>.html must reach prod on the next deploy.
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
        call_command("seed_plans")
        stale.refresh_from_db()
        self.assertEqual(stale.title, "Obwetoowaze mu Nnaku 12")


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
        """A language in TOPIC_TRANSLATIONS must cover ALL topics, not some.

        There is no English fallback: a topic missing from a language's block is
        omitted from that language's shelf list entirely. So a partial language
        silently ships a partial set of shelves — the same discipline as the
        per-language glossaries, which are pinned the same way.
        """
        from library.management.commands.seed_topics import (
            TOPIC_TRANSLATIONS,
            TOPICS,
        )

        slugs = {t[0] for t in TOPICS}
        for lang, per_topic in TOPIC_TRANSLATIONS.items():
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
        codes = [l["code"] for l in res.data["languages"]]
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
        res = self.client.get("/api/admin/review-queue/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([b["slug"] for b in res.data["books"]], ["humility"])
        self.assertEqual(res.data["books"][0]["language"], "sw")
        self.assertEqual([b["language"] for b in res.data["bios"]], ["sw"])
        self.assertTrue(res.data["bios"][0]["has_long"])

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
        self.assertEqual(follow.data["books"], [])

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

        langs = {l["code"]: l for l in res.data["languages"]}
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
        from django.core.management.base import CommandError
        from django.core.management import call_command

        with self.assertRaises(CommandError):
            call_command("translate_sermon", "nope", language="es")

    def test_approve_flips_to_reviewed(self, _fetch):
        from django.core.management import call_command

        self._translate("es")
        call_command("approve_sermon_translation", "the-new-birth", language="es")
        s = Sermon.objects.get(slug="the-new-birth", language="es")
        self.assertEqual(s.source_type, "ai_reviewed")

    def test_approve_rejects_public_domain_original(self, _fetch):
        from django.core.management.base import CommandError
        from django.core.management import call_command

        with self.assertRaises(CommandError):
            call_command("approve_sermon_translation", "the-new-birth", language="en")


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
        call_command("approve_translation", "humility", language="en-modern")
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

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_admin_search_stats_requires_admin(self):
        res = self.client.get("/api/admin/search-stats/")
        self.assertIn(res.status_code, (401, 403))


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

        from .search import _scripture_chapter_hits

        self.assertEqual(_scripture_chapter_hits("Matthew", "en"), [])
        self.assertEqual(len(_scripture_chapter_hits("Matthew 5:3", "en")), 1)


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

    def test_popular_searches_is_aggregate_and_private(self):
        # A query that recurs (>= MIN_COUNT) and found results surfaces.
        for _ in range(3):
            SearchQueryLog.objects.create(query="Prayer", language="en", result_count=5)
        # A one-off never does — no single reader's query can leak.
        SearchQueryLog.objects.create(query="my secret note", language="en", result_count=4)
        # A frequent ZERO-result query never does either (only useful queries).
        for _ in range(5):
            SearchQueryLog.objects.create(query="missing", language="en", result_count=0)
        # Wrong language is scoped out.
        for _ in range(3):
            SearchQueryLog.objects.create(query="oracion", language="es", result_count=5)

        res = self.client.get("/api/library/popular-searches/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["queries"], ["prayer"])  # case-folded, only the recurring hit

    def test_popular_searches_empty_when_sparse(self):
        res = self.client.get("/api/library/popular-searches/?language=en")
        self.assertEqual(res.data["queries"], [])


class TranslationLanguageConfigTests(SimpleTestCase):
    """Guards on LANGUAGES; see the note above the dict in translation.py."""

    def test_every_language_is_fully_configured(self):
        for code, cfg in LANGUAGES.items():
            with self.subTest(language=code):
                for field in ("name", "native", "bible", "bible_label", "glossary"):
                    self.assertTrue(cfg.get(field), f"{code}: empty {field}")

    def test_glossaries_cover_the_shared_term_set(self):
        for code, cfg in LANGUAGES.items():
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
        #     library.tests.TranslationLanguageConfigTests
        for code, cfg in LANGUAGES.items():
            with self.subTest(language=code, bible=cfg["bible"]):
                data = fetch_chapter(cfg["bible"], Ref("JHN", 1))
                self.assertTrue(
                    data and data.get("verses"),
                    f"{code}: {cfg['bible']} returned no verses",
                )

    def test_verify_bible_code_raises_when_the_code_does_not_resolve(self):
        # The preflight every translate_* command runs. Mocked so it stays
        # hermetic — what matters is that a non-resolving code RAISES rather
        # than letting the job proceed and quietly drop all scripture.
        with mock.patch("library.translation.fetch_chapter", return_value=None):
            with self.assertRaises(ValueError) as ctx:
                verify_bible_code("pt")
        self.assertIn("scripture would be silently omitted", str(ctx.exception))

    def test_verify_bible_code_passes_when_verses_come_back(self):
        with mock.patch(
            "library.translation.fetch_chapter", return_value={"verses": [{"number": 1}]}
        ):
            verify_bible_code("pt")  # must not raise


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
        from library.admin_views.jobs import JOB_TYPES, _TITLE_RE

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
        out = StringIO()
        call_command("translate_topic", *args, stdout=out, stderr=out, **kwargs)
        return out.getvalue()

    def test_dry_run_touches_nothing(self):
        out = self._run("--language", "sw", "--dry-run")
        self.assertIn("prayer", out)
        self.assertFalse(TopicTranslation.objects.exists())

    def test_translates_title_and_description_and_emits_the_seed_block(self):
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
        # And the paste-ready block names the seed, which is the delivery path.
        self.assertIn('"sw": {', out)
        self.assertIn("Kuhusu Maombi", out)
        self.assertIn("seed_topics", out)

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
        self.assertEqual(codes, {"en", "es", "sw", "lg", "pt", "ar"})

        en = Language.objects.get(code="en")
        self.assertTrue(en.is_source)
        self.assertEqual(en.bible_code, "")  # nothing to translate scripture into

        ar = Language.objects.get(code="ar")
        self.assertTrue(ar.rtl, "Arabic is right-to-left")
        self.assertFalse(ar.is_source)
        self.assertTrue(ar.bible_code, "a target language needs a Bible")

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

            res = self.client.patch(
                "/api/admin/languages/ar/thresholds/",
                {"min_books": 0, "min_bios": 0, "require_all_topics": False},
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
