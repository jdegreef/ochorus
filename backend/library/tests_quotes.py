"""Curated quotations — the sourcing, and the gate that keeps them unpublished.

The risk this page type carries is not a bug, it is publication: a quote page
has no primary text under it, so a page of weak or misattributed lines is the
doorway shape search engines judge a whole domain by. These tests hold the two
things that make it safe — every quotation names its exact source, and nothing
reaches a reader until a person approves it.
"""

from __future__ import annotations

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Quote, Sermon
from .quote_seed import APPROVED, QUOTES


class SeedDataTests(SimpleTestCase):
    """Shape of the curated list itself, before any database is involved."""

    def all_quotes(self):
        return [q for quotes in QUOTES.values() for q in quotes]

    def test_every_quotation_names_exactly_one_source(self):
        # A quotation whose source cannot be named is the thing the aggregators
        # already publish, and the reason they cannot be trusted.
        for q in self.all_quotes():
            with self.subTest(slug=q["slug"]):
                self.assertEqual(
                    ("chapter" in q) + ("sermon" in q), 1, "need exactly one source"
                )
                self.assertIsInstance(q["paragraph"], int)

    def test_no_quotation_points_at_paragraph_zero(self):
        # The reader ignores `?p=0` (it treats 0 as "no jump"), so a card citing
        # the first paragraph would silently fail to land.
        for q in self.all_quotes():
            with self.subTest(slug=q["slug"]):
                self.assertGreater(q["paragraph"], 0)

    def test_slugs_are_unique_and_carry_the_author(self):
        slugs = [q["slug"] for q in self.all_quotes()]
        self.assertEqual(len(slugs), len(set(slugs)))
        for author, quotes in QUOTES.items():
            for q in quotes:
                self.assertTrue(q["slug"].startswith(f"{author}-"))

    def test_the_text_is_a_whole_sentence(self):
        # Fragments are the failure mode of extracting from imported prose: the
        # library's own QA has found fragmented paragraphs, and half a sentence
        # under an author's name reads as a misquotation.
        for q in self.all_quotes():
            with self.subTest(slug=q["slug"]):
                self.assertRegex(q["text"], r"^[A-Z“\"]")
                self.assertRegex(q["text"], r"[.!?]$")
                self.assertGreaterEqual(len(q["text"].split()), 8)

    def test_no_unescaped_html_entities_survived_extraction(self):
        # `&#x27;` reached a candidate once, because the first pass used a
        # hand-rolled entity map instead of html.unescape.
        for q in self.all_quotes():
            with self.subTest(slug=q["slug"]):
                self.assertNotRegex(q["text"], r"&[#a-zA-Z0-9]+;")

    def test_the_pilot_is_still_one_author(self):
        # Scope guard, not a limit of the design: the pilot exists so that the
        # indexation of ONE author's page decides whether the rest are built.
        self.assertEqual(list(QUOTES), ["charles-h-spurgeon"])


class SeedCommandTests(TestCase):
    def _nobody_approved(self):
        from unittest import mock

        return mock.patch(
            "library.management.commands.seed_quotes.APPROVED", frozenset()
        )

    def setUp(self):
        self.author = Author.objects.create(slug="charles-h-spurgeon", name="C. H. Spurgeon")
        book = Book.objects.create(
            author=self.author, slug="all-of-grace", language="en", title="All of Grace"
        )
        for order in range(1, 21):
            Chapter.objects.create(
                book=book, order=order, title=f"Ch {order}",
                body_html="<p>a</p><p>b</p><p>c</p>" * 60,
            )
        for slug in ("compel-them-to-come-in", "order-and-argument-in-prayer",
                     "christ-crucified", "christ-precious-to-believers",
                     "pauls-first-prayer", "the-sweet-uses-of-adversity"):
            Sermon.objects.create(
                author=self.author, slug=slug, language="en", title=slug,
                body_html="<p>x</p>" * 80,
            )

    def test_an_approved_author_seeds_published(self):
        # The approval is recorded in the repo, so a rebuilt database comes up
        # with the same quotations published — a prod-only approval would not
        # survive one.
        self.assertIn("charles-h-spurgeon", APPROVED)
        call_command("seed_quotes", verbosity=0)
        self.assertTrue(Quote.objects.exists())
        self.assertEqual(Quote.objects.filter(reviewed=False).count(), 0)

    def test_an_author_not_in_approved_seeds_unreviewed(self):
        # The gate still holds for anyone nobody has signed off. Patched on the
        # COMMAND's namespace: it does `from ... import APPROVED`, so the name is
        # bound at import and patching the seed module would miss it.
        with self._nobody_approved():
            call_command("seed_quotes", verbosity=0)
        self.assertTrue(Quote.objects.exists())
        self.assertEqual(Quote.objects.filter(reviewed=True).count(), 0)

    def test_a_takedown_survives_the_next_deploy(self):
        """The reason `reviewed` is create-only, and why it cuts both ways.

        Somebody clears the flag on a quotation — a misattribution spotted, a
        complaint — and the seed runs again on the next deploy. If it re-asserted
        what the repo approved, the quotation would come straight back, which is
        exactly the trap `is_published` is protected from in seed_books.
        """
        call_command("seed_quotes", verbosity=0)
        pulled = Quote.objects.first()
        pulled.reviewed = False
        pulled.save(update_fields=["reviewed"])
        call_command("seed_quotes", verbosity=0)
        pulled.refresh_from_db()
        self.assertFalse(pulled.reviewed)

    def test_re_running_writes_nothing(self):
        call_command("seed_quotes", verbosity=0)
        n = Quote.objects.count()
        call_command("seed_quotes", verbosity=0)
        self.assertEqual(Quote.objects.count(), n)

    def test_a_row_created_before_its_author_was_approved_stays_unreviewed(self):
        # Create-only means the repo cannot retro-publish an existing row; that
        # is what `approve_quotes` is for, and the command's docstring says so.
        with self._nobody_approved():
            call_command("seed_quotes", verbosity=0)
        call_command("seed_quotes", verbosity=0)
        self.assertEqual(Quote.objects.filter(reviewed=True).count(), 0)
        call_command("approve_quotes", "charles-h-spurgeon", verbosity=0)
        self.assertEqual(Quote.objects.filter(reviewed=False).count(), 0)

    def test_approval_survives_a_re_seed(self):
        # `reviewed` is create-only. A seed that re-asserted it would revoke a
        # person's decision on the next deploy — the trap CLAUDE.md warns about.
        call_command("seed_quotes", verbosity=0)
        call_command("approve_quotes", "charles-h-spurgeon", verbosity=0)
        call_command("seed_quotes", verbosity=0)
        self.assertEqual(Quote.objects.filter(reviewed=False).count(), 0)

    def test_a_quotation_whose_work_is_missing_is_skipped_not_stored(self):
        Sermon.objects.all().delete()
        call_command("seed_quotes", verbosity=0)
        # Nothing stored without a source to cite.
        self.assertFalse(Quote.objects.filter(chapter=None, sermon=None).exists())

    def test_every_stored_quote_can_name_its_source(self):
        call_command("seed_quotes", verbosity=0)
        for q in Quote.objects.select_related("chapter", "sermon"):
            with self.subTest(slug=q.slug):
                self.assertTrue(q.chapter_id or q.sermon_id)


class QuotePageApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="w", name="A Writer")
        book = Book.objects.create(
            author=self.author, slug="b", language="en", title="A Work"
        )
        self.chapter = Chapter.objects.create(
            book=book, order=3, title="Third", body_html="<p>a</p><p>b</p>"
        )
        self.quote = Quote.objects.create(
            slug="w-abc", author=self.author, text="A memorable sentence about grace.",
            chapter=self.chapter, paragraph=5,
        )

    def test_an_unreviewed_author_has_no_page(self):
        self.assertEqual(self.client.get("/api/library/quotes/w/").status_code, 404)
        self.assertEqual(self.client.get("/api/library/quotes/").data, [])

    def test_approving_publishes_the_page(self):
        self.quote.reviewed = True
        self.quote.save()
        res = self.client.get("/api/library/quotes/w/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["quotes"]), 1)
        self.assertEqual(self.client.get("/api/library/quotes/").data, ["w"])

    def test_the_payload_carries_the_citation(self):
        self.quote.reviewed = True
        self.quote.save()
        q = self.client.get("/api/library/quotes/w/").data["quotes"][0]
        self.assertEqual(q["paragraph"], 5)
        self.assertEqual(q["source"]["work"], "A Work")
        self.assertEqual(q["source"]["order"], 3)
        self.assertEqual(q["source"]["kind"], "chapter")

    def test_an_unreviewed_quote_never_leaks_onto_a_published_page(self):
        self.quote.reviewed = True
        self.quote.save()
        Quote.objects.create(
            slug="w-def", author=self.author, text="Not yet approved by anyone at all.",
            chapter=self.chapter, paragraph=6,
        )
        slugs = [q["slug"] for q in self.client.get("/api/library/quotes/w/").data["quotes"]]
        self.assertEqual(slugs, ["w-abc"])

    def test_quotes_arrive_in_reading_order(self):
        """Books before sermons, each work from its first chapter to its last.

        Ordering was by `slug` — a hash of the text — so the sequence was
        arbitrary. Reading order is what lets the page GROUP by work, and the
        grouping is what earns the colour (STYLE_GUIDE §5). A regression here
        would not error; it would silently shatter every work into singletons.
        """
        book2 = Book.objects.create(
            author=self.author, slug="a", language="en", title="A Later Work"
        )
        later = Chapter.objects.create(
            book=book2, order=1, title="One", body_html="<p>x</p>"
        )
        serm = Sermon.objects.create(
            author=self.author, slug="s", language="en", title="A Sermon",
            body_html="<p>x</p>",
        )
        # Created deliberately out of order.
        for slug, ch, para in (
            ("z1", self.chapter, 9), ("z2", later, 1), ("z3", self.chapter, 2),
        ):
            Quote.objects.create(
                slug=slug, author=self.author, text="Text.", chapter=ch,
                paragraph=para, reviewed=True,
            )
        Quote.objects.create(
            slug="z0", author=self.author, text="Text.", sermon=serm,
            paragraph=1, reviewed=True,
        )
        self.quote.reviewed = True
        self.quote.save()

        got = [
            (q["source"]["work"], q["source"]["order"], q["paragraph"])
            for q in self.client.get("/api/library/quotes/w/").data["quotes"]
        ]
        self.assertEqual(
            got,
            [
                ("A Later Work", 1, 1),
                ("A Work", 3, 2),
                ("A Work", 3, 5),
                ("A Work", 3, 9),
                ("A Sermon", None, 1),
            ],
        )

    def test_a_chapter_quote_carries_its_book_hue(self):
        # The group heading is tinted from the work, so the payload has to say
        # which colour that is.
        self.chapter.book.cover_color = "#3b5bdb"
        self.chapter.book.save(update_fields=["cover_color"])
        self.quote.reviewed = True
        self.quote.save()
        q = self.client.get("/api/library/quotes/w/").data["quotes"][0]
        self.assertEqual(q["source"]["cover_color"], "#3b5bdb")

    def test_the_author_carries_a_birth_year_for_the_sermons_hue(self):
        # Sermons have no cover colour, so their group takes the writer's era.
        self.quote.reviewed = True
        self.quote.save()
        data = self.client.get("/api/library/quotes/w/").data
        self.assertIn("birth_year", data["author"])

    def test_an_unknown_author_is_404_not_an_empty_page(self):
        self.assertEqual(self.client.get("/api/library/quotes/nobody/").status_code, 404)

    def test_the_author_page_counts_only_reviewed_quotes(self):
        # The author page offers the link on this count; counting unreviewed
        # rows would link to a page the gate keeps 404ing.
        self.assertEqual(self.client.get("/api/library/authors/w/").data["quote_count"], 0)
        self.quote.reviewed = True
        self.quote.save()
        self.assertEqual(self.client.get("/api/library/authors/w/").data["quote_count"], 1)
