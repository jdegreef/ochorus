"""The idempotent deploy seeds: what they create, what they re-assert on every
deploy, and — the part worth guarding — what they must leave alone.

A field a workflow owns after creation has to be create-only in the seed, or a
deploy silently walks the approver's decision back. That rule has no home in the
code; these tests are where it lives."""

import json
import re
from io import StringIO
from unittest import skipUnless
from unittest.mock import patch  # noqa: E402

from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from .models import (
    Article,
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Sermon,
)


def synthetic_repair(body_html):
    """BODY_CORRECTIONS replacement pairs that repair ``body_html``.

    The tests below need a work the correction step still changes. Reading one
    out of the committed fixture is the obvious way and the wrong one: the
    non-English backlog is 30 chapters and 1 sermon TODAY, and normalising it
    away is a live option — so a corpus-derived probe pins the backlog's
    existence, and doing the right thing later would fail the build with
    "this test no longer exercises the behaviour it guards". These tests are
    about the mechanism, so they bring their own defect.

    Upper-cases the first long word, which is idempotent (the upper-cased form
    no longer contains the lower-cased original) — the property every entry in
    BODY_CORRECTIONS needs, and the one convergence rests on.
    """
    match = re.search(r">[^<>]*?\b([a-z]{6,})\b", body_html)
    assert match, "no lower-case word in the body to build a repair from"
    word = match.group(1)
    return [(word, word.upper())]


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


    def test_a_new_book_is_created_with_corrected_prose(self):
        # seed_books runs AFTER apply_body_corrections in the release, so a book
        # that lands today would otherwise sit live with a known defect until
        # the NEXT deploy walked the corpus again — and read as drift meanwhile.
        from library import corrections
        from library.content_fixtures import BOOKS_DIR, work_filename

        row = json.loads(
            (BOOKS_DIR / work_filename("the-way-to-god", "en")).read_text()
        )
        raw = next(r for r in row if r["model"] == "library.chapter")["fields"]

        with patch.dict(
            corrections.BODY_CORRECTIONS,
            {"the-way-to-god": {"replacements": synthetic_repair(raw["body_html"])}},
        ):
            corrected = corrections.settled_chapter_body(
                "the-way-to-god", raw["order"], raw["body_html"]
            )
            self.assertNotEqual(corrected, raw["body_html"])
            # The test DB starts empty, so this first seed IS the create path.
            call_command("seed_books", verbosity=0)

        chapter = Chapter.objects.get(
            book__slug="the-way-to-god", book__language="en", order=raw["order"]
        )
        self.assertEqual(chapter.body_html, corrected)


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

    def test_faq_is_fixture_wins_and_reaches_an_existing_row(self):
        # `faq` is a SYNCED_FIELD (like same_as), not fill-only: a corrected or
        # expanded set in the fixture must overwrite whatever the row holds, so a
        # roll-out fix reaches prod on the next deploy without a migration.
        from library.content_fixtures import authors_by_slug

        fixture_faq = authors_by_slug()["john-bunyan"]["faq"]
        self.assertTrue(fixture_faq, "the pilot fixture should carry a faq set")

        # A stale/edited value on the live row is replaced, not kept.
        Author.objects.filter(slug="john-bunyan").update(faq=[{"q": "old", "a": "old"}])
        call_command("seed_books", verbosity=0)
        self.assertEqual(Author.objects.get(slug="john-bunyan").faq, fixture_faq)

        # An author whose fixture OMITS faq is left untouched (no empty list
        # forced). Picked dynamically off a live, seeded author whose fixture row
        # has no faq key, so this stays honest as roll-out batches add more sets.
        by_slug = authors_by_slug()
        untouched = next(
            a.slug
            for a in Author.objects.order_by("slug")
            if "faq" not in by_slug.get(a.slug, {})
        )
        Author.objects.filter(slug=untouched).update(faq=[{"q": "mine", "a": "mine"}])
        call_command("seed_books", verbosity=0)
        self.assertEqual(
            Author.objects.get(slug=untouched).faq, [{"q": "mine", "a": "mine"}]
        )

    def test_a_no_op_deploy_changes_no_author(self):
        # Author has no updated_at, so snapshot the synced fields themselves.
        fields = ("slug", "bio", "bio_html", "photo_url", "birth_year", "death_year")
        before = list(Author.objects.order_by("slug").values_list(*fields))
        call_command("seed_books", verbosity=0)
        self.assertEqual(
            list(Author.objects.order_by("slug").values_list(*fields)), before
        )

    def test_series_membership_reaches_the_db(self):
        # The numeral on a cover reads `series_position`; the table it replaced
        # (coverStyles.SERIES_VOLUME) numbered these volumes, so they must land.
        def membership(slug, language):
            return (
                Book.objects.filter(slug=slug, language=language)
                .values_list("series__slug", "series_position")
                .get()
            )

        self.assertEqual(membership("rooted-3", "en"), ("rooted", 3))
        self.assertEqual(membership("brave-for-god-2", "sw"), ("brave-for-god", 2))
        # A collection: in the series, with no reading order to number.
        self.assertEqual(
            membership("key-teachings-of-watchman-nee", "en"), ("key-teachings", None)
        )
        self.assertEqual(membership("the-way-to-god", "en"), (None, None))

    def test_a_series_edit_reaches_an_existing_db_and_a_rerun_touches_nothing(self):
        from django.core.management import call_command

        from library.models import Series

        Series.objects.filter(slug="rooted").update(title="stale", sort_order=999)
        call_command("seed_books", verbosity=0)  # the next deploy
        rooted = Series.objects.get(slug="rooted")
        self.assertNotEqual(rooted.title, "stale")
        self.assertNotEqual(rooted.sort_order, 999)

        stamps = dict(Series.objects.values_list("pk", "updated_at"))
        call_command("seed_books", verbosity=0)
        self.assertEqual(dict(Series.objects.values_list("pk", "updated_at")), stamps)

    def test_a_book_the_fixture_takes_out_of_a_series_leaves_it(self):
        # Membership is the fixture's fact: a row with no `series` key is in no
        # series, not "leave whatever the DB has".
        from django.core.management import call_command

        from library.models import Series

        book = Book.objects.get(slug="the-way-to-god", language="en")
        Book.objects.filter(pk=book.pk).update(
            series=Series.objects.get(slug="brave-for-god"), series_position=99
        )
        call_command("seed_books", verbosity=0)  # the next deploy
        book.refresh_from_db()
        self.assertIsNone(book.series)
        self.assertIsNone(book.series_position)

    def _fixture_fields(self, slug, language):
        """The fixture's Book row for one work — its own file's first record.

        FileCoherenceTests pins that layout, so this reads one file instead of
        parsing all ~170 to find one row.
        """

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
        # Exactly the drift report seed_books emits, streamed one work file at a
        # time (the command runs the same per-book check inline while it seeds).
        from library.management.commands.seed_books import iter_chapter_drift

        return {b.slug: reason for b, reason in iter_chapter_drift()}

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

    def test_a_corrected_chapter_is_not_drift(self):
        # apply_body_corrections runs over every stored chapter immediately
        # BEFORE seed_books on each deploy, so the corrected text is a faithful
        # state, not a divergence. Comparing the raw fixture only, prod (whose
        # chapters seed_if_empty loaded raw) reported 13 books "differ from
        # fixture" every deploy — all of them the corrections step doing its
        # job. The check exists to catch a live-DB transform that never got a
        # fixture regen, and a warning that is permanently on cannot.
        from library import corrections

        chapter = self.book.chapters.first()
        raw = chapter.body_html

        with patch.dict(
            corrections.BODY_CORRECTIONS,
            {self.book.slug: {"replacements": synthetic_repair(raw)}},
        ):
            corrected = corrections.settled_chapter_body(
                self.book.slug, chapter.order, raw
            )
            self.assertNotEqual(corrected, raw)
            self.assertEqual(self._drift(), {})  # the raw fixture is faithful…
            call_command("apply_body_corrections", stdout=StringIO())
            chapter.refresh_from_db()
            self.assertEqual(chapter.body_html, corrected)  # …it was corrected…
            self.assertEqual(self._drift(), {})  # …and that is not drift either

    def test_drift_check_failure_never_aborts_the_seed(self):
        # The drift pass runs inside seed_books' @transaction.atomic handle(),
        # so a bug in this diagnostics-only code must not roll back a good seed
        # or fail the deploy — it's caught and reported, and the command still
        # succeeds (creating a book that was missing).

        from django.core.management import call_command

        self.book.delete()  # so this run has real work to commit
        out = StringIO()
        with patch(
            "library.management.commands.seed_books.chapter_drift_reason",
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

    def test_second_run_updates_nothing(self):
        """A no-op deploy must not touch a single row — updated_at is the tell.

        `seed_books` has had this gate for a while; sermons went without, and
        that is what let a DERIVED column into SERMON_FIELDS go unnoticed. The
        seed compared the fixture's stored word_count against the one save()
        derives, "repaired" every row where the two disagreed, and save() then
        derived the value straight back — 33 full-row rewrites plus 33 tsvector
        rebuilds, on every deploy, converging never.
        """
        from django.core.management import call_command

        call_command("seed_sermons", verbosity=0)
        stamps = dict(Sermon.objects.values_list("pk", "updated_at"))
        self.assertTrue(stamps, "the seed created no sermons to check")
        call_command("seed_sermons", verbosity=0)
        self.assertEqual(dict(Sermon.objects.values_list("pk", "updated_at")), stamps)

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

    def test_a_correction_survives_the_next_deploy(self):
        # The release corrects the stored prose and THEN runs this seed, which
        # compares the fixture against the DB — so while it compared the RAW
        # fixture body the two steps fought over the same sermon forever.
        # christ-all-in-all[sw] cites John 14:6; the fixture body says "(Yohana
        # 10)", corrections repaired it, and the seed wrote the wrong reference
        # back. Every deploy. The waste was a full-row UPDATE and a tsvector
        # rebuild, but the real cost was the log: "Sermons: 0 created, N
        # updated" is the seed's ONLY signal that a sermon edit shipped, and it
        # could never return to zero to mean anything.
        #
        # test_second_run_updates_nothing does NOT catch this — without the
        # corrections step in between there is nothing for the seed to revert.
        from library import corrections

        call_command("seed_sermons", verbosity=0)
        sermon = Sermon.objects.filter(language="en").first()

        with patch.dict(
            corrections.BODY_CORRECTIONS,
            {sermon.slug: {"replacements": synthetic_repair(sermon.body_html)}},
        ):
            corrected = corrections.settled_sermon_body(sermon.slug, sermon.body_html)
            self.assertNotEqual(corrected, sermon.body_html)
            call_command("apply_body_corrections", stdout=StringIO())
            stamps = dict(Sermon.objects.values_list("pk", "updated_at"))

            for _ in range(2):  # two more deploys
                call_command("apply_body_corrections", stdout=StringIO())
                out = StringIO()
                call_command("seed_sermons", stdout=out)
                self.assertIn("already up to date", out.getvalue())

            # Not one row rewritten, and the repair is still there.
            self.assertEqual(
                dict(Sermon.objects.values_list("pk", "updated_at")), stamps
            )
            sermon.refresh_from_db()
            self.assertEqual(sermon.body_html, corrected)

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
                # The translated Q&A rides the same seed (empty for an author with
                # no <slug>.faq.json yet).
                self.assertEqual(tr.faq, bios[tr.author.slug].get("faq", []))
                self.assertFalse(tr.reviewed)
        # One literal oracle, independent of read_bios (which fed the seed too).
        murray_es = AuthorTranslation.objects.get(
            author__slug="andrew-murray", language="es"
        )
        self.assertTrue(murray_es.bio.startswith("Andrew Murray hijo"))
        self.assertIn("<", murray_es.bio_html)
        # Its Q&A came through too — a plain-text {q, a} list, not empty.
        self.assertTrue(murray_es.faq)
        self.assertEqual(set(murray_es.faq[0]), {"q", "a"})

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


class BackfillWordCountTests(TestCase):
    """`word_count` is derived, and the routes that bypass save() need a keeper.

    `Chapter.save()`/`Sermon.save()` derive it now, so a row written through the
    model is in step. This command is for the routes that do not go through it —
    loaddata above all — where a row keeps its zero permanently. That is how 32
    chapters shipped with no reading time in the TOC drawer and sorting as the
    shortest books in the library.
    """

    def _book(self, slug="w", language="en"):
        author = Author.objects.create(slug=f"a-{slug}-{language}", name="A")
        return Book.objects.create(slug=slug, language=language, title="T", author=author)

    def test_fills_a_zero_count_from_the_body(self):
        book = self._book()
        # queryset.update(), so the count stays as created — the exact shape the
        # fixture rows arrived in.
        ch = Chapter.objects.create(
            book=book, order=1, title="One", body_html="<p>one two three four</p>"
        )
        Chapter.objects.filter(pk=ch.pk).update(word_count=0)

        call_command("backfill_word_count", verbosity=0)
        ch.refresh_from_db()
        self.assertEqual(ch.word_count, 4)

    def test_leaves_a_genuinely_empty_chapter_at_zero(self):
        book = self._book(slug="x")
        ch = Chapter.objects.create(book=book, order=1, title="Empty", body_html="")
        Chapter.objects.filter(pk=ch.pk).update(word_count=0)

        call_command("backfill_word_count", verbosity=0)
        ch.refresh_from_db()
        self.assertEqual(ch.word_count, 0)

    def test_does_not_touch_a_count_that_is_already_set(self):
        # Only zeroes, mirroring backfill_body_text's "fill what is empty"
        # contract: recomputing every row on every deploy to correct the few
        # that drifted would rewrite the whole corpus.
        book = self._book(slug="y")
        ch = Chapter.objects.create(
            book=book, order=1, title="One", body_html="<p>one two three four</p>"
        )
        Chapter.objects.filter(pk=ch.pk).update(word_count=999)

        call_command("backfill_word_count", verbosity=0)
        ch.refresh_from_db()
        self.assertEqual(ch.word_count, 999)

    def test_fills_sermons_too_and_is_idempotent(self):
        author = Author.objects.create(slug="a-s", name="A")
        s = Sermon.objects.create(
            slug="s", language="en", title="S", author=author,
            body_html="<p>one two three</p>",
        )
        Sermon.objects.filter(pk=s.pk).update(word_count=0)

        call_command("backfill_word_count", verbosity=0)
        s.refresh_from_db()
        self.assertEqual(s.word_count, 3)

        out = StringIO()
        call_command("backfill_word_count", stdout=out)
        s.refresh_from_db()
        self.assertEqual(s.word_count, 3)
        self.assertIn("already have a word_count", out.getvalue())


class SeedArticlesTests(TestCase):
    """`seed_articles`, focused on the create-only review badge.

    There are no committed article translation fixtures yet (every article is an
    English original), so these drive the seed with a synthetic fixture file via
    ``iter_work_files`` — the same ``(path, rows)`` shape it yields — rather than
    a checked-in ``.es.json``. The invariant under test is the one the
    constitution stresses: ``source_type`` is create-only, so an approval is not
    reverted on the next deploy.
    """

    @staticmethod
    def _rows(source_type):
        return [
            {
                "model": "library.article",
                "fields": {
                    "slug": "what-is-grace",
                    "language": "es",
                    "h1": "¿Qué es la gracia?",
                    "body_html": "<p>La gracia es el favor inmerecido.</p>",
                    "source_type": source_type,
                },
            }
        ]

    def test_seed_creates_the_translation_badge(self):
        with patch(
            "library.management.commands.seed_articles.iter_work_files",
            return_value=[("what-is-grace.es.json", self._rows("ai_unreviewed"))],
        ):
            call_command("seed_articles", verbosity=0)
        art = Article.objects.get(slug="what-is-grace", language="es")
        self.assertEqual(art.source_type, Book.SourceType.AI_UNREVIEWED)

    def test_seed_never_reverts_an_approved_article(self):
        # source_type is create-only: once a native speaker approves a
        # translation the review workflow owns it. Re-asserting the fixture's
        # ai_unreviewed on the next deploy would silently restore the "awaiting
        # native review" badge and make approve_article_translation useless.
        with patch(
            "library.management.commands.seed_articles.iter_work_files",
            return_value=[("what-is-grace.es.json", self._rows("ai_unreviewed"))],
        ):
            call_command("seed_articles", verbosity=0)
            call_command(
                "approve_article_translation",
                "what-is-grace",
                language="es",
                no_fixture=True,
            )
            call_command("seed_articles", verbosity=0)  # the next deploy
        art = Article.objects.get(slug="what-is-grace", language="es")
        self.assertEqual(art.source_type, Book.SourceType.AI_REVIEWED)


class SeedAuthorMilestonesTests(TestCase):
    """Timeline milestones are CODE-owned content (like the topic shelves), not
    an approver-owned field — so the seed re-asserts them every deploy, and only
    touches authors already in the library."""

    def test_sets_curated_author(self):
        from library.author_milestones import AUTHOR_MILESTONES

        Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        call_command("seed_author_milestones", verbosity=0)
        murray = Author.objects.get(slug="andrew-murray")
        self.assertEqual(murray.milestones, AUTHOR_MILESTONES["andrew-murray"])
        self.assertGreaterEqual(len(murray.milestones), 2)

    def test_reasserts_code_owned_values(self):
        from library.author_milestones import AUTHOR_MILESTONES

        # Drifted content is overwritten back to the code's definition — the
        # opposite of the create-only rule the approver-owned seeds follow.
        Author.objects.create(
            slug="andrew-murray", name="Andrew Murray", milestones=[{"year": 1, "label": "x"}]
        )
        call_command("seed_author_milestones", verbosity=0)
        self.assertEqual(
            Author.objects.get(slug="andrew-murray").milestones,
            AUTHOR_MILESTONES["andrew-murray"],
        )

    def test_skips_authors_absent_from_library(self):
        # A slug not yet in the library is skipped, not created — the command can
        # run ahead of an author landing.
        call_command("seed_author_milestones", verbosity=0)
        self.assertEqual(Author.objects.count(), 0)

    def test_curated_milestones_are_wellformed(self):
        # Guards the hand-authored data: sorted-able years within the lifespan
        # feel, non-empty labels, at least two events (a lone dot is not a line).
        from library.author_milestones import AUTHOR_MILESTONES

        for slug, events in AUTHOR_MILESTONES.items():
            self.assertGreaterEqual(len(events), 2, slug)
            years = [e["year"] for e in events]
            self.assertEqual(years, sorted(years), f"{slug} milestones must be chronological")
            for e in events:
                self.assertIsInstance(e["year"], int)
                self.assertTrue(e["label"].strip(), f"{slug} has an empty label")
