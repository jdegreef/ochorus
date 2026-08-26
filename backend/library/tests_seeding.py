"""The idempotent deploy seeds: what they create, what they re-assert on every
deploy, and — the part worth guarding — what they must leave alone.

A field a workflow owns after creation has to be create-only in the seed, or a
deploy silently walks the approver's decision back. That rule has no home in the
code; these tests are where it lives."""

import json
from io import StringIO
from unittest import skipUnless
from unittest.mock import patch  # noqa: E402

from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from .models import (
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Sermon,
)


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
