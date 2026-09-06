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

from .models import Author, Book, Chapter, Quote, QuoteTopic, Sermon
from .quote_seed import (
    APPROVED,
    QUOTE_TOPIC_SLUGS,
    QUOTE_TOPICS,
    QUOTES,
    TOPIC_MEMBERS,
)


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

    def test_the_curated_authors_are_the_reviewed_set(self):
        # Scope guard: every author carrying quotations must also be one the
        # repo has signed off in APPROVED, so a curated-but-unapproved author
        # cannot ship a page by accident. Widen both together, deliberately.
        from library.quote_seed import APPROVED

        self.assertEqual(set(QUOTES), set(APPROVED))
        self.assertEqual(
            set(QUOTES),
            {
                "charles-h-spurgeon",
                "thomas-a-kempis",
                "andrew-murray",
                "e-m-bounds",
                "augustine-of-hippo",
                "jonathan-edwards",
                "john-wesley",
                "george-muller",
                "hudson-taylor",
                "gareth-evans",
                "richard-allen",
                "amanda-berry-smith",
            },
        )


class QuoteTopicSeedTests(SimpleTestCase):
    """Shape of the theme vocabulary and the tags, before any database."""

    def test_the_vocabulary_is_wellformed(self):
        slugs = [slug for slug, *_ in QUOTE_TOPICS]
        self.assertEqual(len(slugs), len(set(slugs)), "duplicate topic slug")
        for slug, title, blurb, ref, txt in QUOTE_TOPICS:
            with self.subTest(slug=slug):
                self.assertRegex(slug, r"^[a-z0-9-]+$")
                self.assertTrue(title.strip())
                self.assertTrue(blurb.strip())
                # The epigraph is the topic page's furniture; both halves or
                # neither, never a reference with no words under it.
                self.assertEqual(bool(ref.strip()), bool(txt.strip()))

    def test_every_tag_names_a_known_topic(self):
        for topic_slug in TOPIC_MEMBERS:
            with self.subTest(topic=topic_slug):
                self.assertIn(topic_slug, QUOTE_TOPIC_SLUGS)

    def test_every_tagged_quote_slug_exists(self):
        known = {q["slug"] for quotes in QUOTES.values() for q in quotes}
        for topic_slug, quote_slugs in TOPIC_MEMBERS.items():
            # A tag pointing at a slug no quote carries would silently file
            # nothing — the seed would skip it and the theme would be short a
            # line nobody could find.
            self.assertEqual(len(quote_slugs), len(set(quote_slugs)),
                             f"{topic_slug}: a quote is listed twice")
            for qslug in quote_slugs:
                with self.subTest(topic=topic_slug, quote=qslug):
                    self.assertIn(qslug, known)


class QuoteResolutionTests(SimpleTestCase):
    """Every quote's `paragraph` must land on the block it was taken from.

    This is the gate the pilot lacked. `paragraph` is `body.children[p]` — the
    0-indexed top-level child the reader jumps to — counted against the SERVED
    HTML, so the check applies `annotate_references` (the one transform the
    chapter and sermon serializers run on `body_html`) before parsing, then
    asserts the quote's own text is in that block. Without it, eighteen of the
    sixty Spurgeon rows shipped off by one, their card links landing nowhere.

    Reads the fixtures directly, like `tests_english_audit`, so it needs no DB.
    """

    from pathlib import Path

    BOOKS = Path(__file__).resolve().parent / "fixtures" / "content" / "books"
    SERMONS = Path(__file__).resolve().parent / "fixtures" / "content" / "sermons"

    def _body_html(self, q):
        import json

        if "chapter" in q:
            slug, order = q["chapter"]
            rows = json.loads((self.BOOKS / f"{slug}.en.json").read_text())
            for r in rows:
                f = r["fields"]
                if r["model"] == "library.chapter" and f.get("order") == order:
                    return f["body_html"]
            return None
        rows = json.loads((self.SERMONS / f"{q['sermon']}.en.json").read_text())
        for r in rows:
            if r["model"] == "library.sermon":
                return r["fields"]["body_html"]
        return None

    def test_every_quote_resolves_to_a_block_containing_its_text(self):
        from bs4 import BeautifulSoup

        from .scripture import annotate_references

        def norm(t):
            return " ".join(t.split())

        for _author, quotes in QUOTES.items():
            for q in quotes:
                body = self._body_html(q)
                with self.subTest(slug=q["slug"]):
                    self.assertIsNotNone(body, "source work missing from fixtures")
                    served = annotate_references(body)
                    blocks = [
                        norm(k.get_text())
                        for k in BeautifulSoup(f"<div>{served}</div>", "lxml").div.find_all(
                            recursive=False
                        )
                    ]
                    p = q["paragraph"]
                    self.assertTrue(0 < p < len(blocks), f"paragraph {p} out of range {len(blocks)}")
                    self.assertIn(norm(q["text"]), blocks[p])

    def test_no_quote_cites_an_unpublished_work(self):
        """A quote links to its source page. If that page is not published it
        404s — a dead card link, and a prerender failure. Amy Carmichael was
        held out of the launch for exactly this: her aphorisms are in *If*,
        which is `is_published=False`.
        """
        import json

        def is_published(q):
            if "chapter" in q:
                slug = q["chapter"][0]
                rows = json.loads((self.BOOKS / f"{slug}.en.json").read_text())
                model = "library.book"
            else:
                slug = q["sermon"]
                rows = json.loads((self.SERMONS / f"{slug}.en.json").read_text())
                model = "library.sermon"
            row = next(r for r in rows if r["model"] == model)
            # Absent means the model default, which is published.
            return row["fields"].get("is_published", True)

        for _author, quotes in QUOTES.items():
            for q in quotes:
                with self.subTest(slug=q["slug"]):
                    self.assertTrue(is_published(q), "quote cites an unpublished work")


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

    def test_repairing_text_under_the_same_slug_updates_in_place(self):
        """The slug freeze (Wave 0 of the per-quote-URL plan).

        A quotation's slug is its permanent identity — the address a per-quote
        page will be served at. Repairing the TEXT (an OCR slip, a punctuation
        fix — the english-qa channels) while keeping the SAME slug must edit the
        existing row: same pk, same slug, approval intact. It must NOT create a
        new row and strand the approved original — which, once the slug is a
        URL, would 404 every link to it. A fresh hash is reserved for a
        genuinely new quotation, not a repair (the extraction skill says so).
        """
        import copy
        from unittest import mock

        call_command("seed_quotes", verbosity=0)
        row = Quote.objects.first()
        pk, slug = row.pk, row.slug
        self.assertTrue(row.reviewed)  # Spurgeon is in APPROVED.
        n = Quote.objects.count()

        # The same slug, carrying a repaired sentence — the edit-in-place the
        # freeze requires. Patched on the COMMAND namespace (it does
        # `from ... import QUOTES`, so patching the seed module would miss it).
        patched = copy.deepcopy(QUOTES)
        repaired = None
        for quotes in patched.values():
            for q in quotes:
                if q["slug"] == slug:
                    q["text"] = repaired = q["text"] + " — repaired."
        self.assertIsNotNone(repaired, "the first row's slug must be in the seed")

        with mock.patch(
            "library.management.commands.seed_quotes.QUOTES", patched
        ):
            call_command("seed_quotes", verbosity=0)

        self.assertEqual(Quote.objects.count(), n)  # No new row, nothing orphaned.
        row.refresh_from_db()
        self.assertEqual(row.pk, pk)  # Same row …
        self.assertEqual(row.slug, slug)  # … same address …
        self.assertEqual(row.text, repaired)  # … text repaired …
        self.assertTrue(row.reviewed)  # … approval intact.

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

    def test_seed_plants_the_whole_topic_vocabulary(self):
        call_command("seed_quotes", verbosity=0)
        self.assertEqual(QuoteTopic.objects.count(), len(QUOTE_TOPICS))

    def test_tags_are_applied(self):
        # At least one Spurgeon quote citing all-of-grace is filed under a theme;
        # the seed should have set the M2M from TOPIC_MEMBERS.
        call_command("seed_quotes", verbosity=0)
        self.assertTrue(
            Quote.objects.filter(topics__isnull=False).exists(),
            "no quote came out tagged — the tag inversion is not wired",
        )

    def test_tags_are_reasserted_not_create_only(self):
        # Unlike `reviewed`, filing is curation: a re-tag must ship. Clearing the
        # members and re-seeding must therefore strip the tags back off.
        from unittest import mock

        call_command("seed_quotes", verbosity=0)
        self.assertTrue(Quote.objects.filter(topics__isnull=False).exists())
        with mock.patch(
            "library.management.commands.seed_quotes.TOPIC_MEMBERS", {}
        ):
            call_command("seed_quotes", verbosity=0)
        self.assertFalse(Quote.objects.filter(topics__isnull=False).exists())

    def test_topic_prose_updates_on_reseed(self):
        # The blurb/epigraph live here (a declared content root), so a wording
        # fix must reach the row on the next deploy — update_or_create, not
        # create-only.
        import copy
        from unittest import mock

        call_command("seed_quotes", verbosity=0)
        patched = copy.deepcopy(QUOTE_TOPICS)
        slug = patched[0][0]
        patched[0] = (slug, patched[0][1], "A rewritten blurb.", "", "")
        with mock.patch(
            "library.management.commands.seed_quotes.QUOTE_TOPICS", patched
        ):
            call_command("seed_quotes", verbosity=0)
        self.assertEqual(QuoteTopic.objects.get(slug=slug).blurb, "A rewritten blurb.")


class QuoteTopicApiTests(TestCase):
    """The theme pages: "Quotes on X" and "<Author> Quotes on X"."""

    def setUp(self):
        self.client = APIClient()
        self.murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        self.spurgeon = Author.objects.create(slug="charles-h-spurgeon", name="C. H. Spurgeon")
        book = Book.objects.create(
            author=self.murray, slug="with-christ", language="en", title="With Christ"
        )
        self.ch = Chapter.objects.create(
            book=book, order=1, title="One", body_html="<p>a</p><p>b</p>"
        )
        self.prayer = QuoteTopic.objects.create(slug="prayer", title="Prayer", blurb="On prayer.")
        self.faith = QuoteTopic.objects.create(slug="faith", title="Faith", blurb="On faith.")
        # Eight reviewed Murray quotes on prayer — clears both thresholds.
        for i in range(8):
            q = Quote.objects.create(
                slug=f"andrew-murray-p{i}", author=self.murray,
                text=f"A sentence on prayer number {i} that is long enough.",
                chapter=self.ch, paragraph=i + 1, reviewed=True,
            )
            q.topics.add(self.prayer)
        # One unreviewed prayer quote — must never leak.
        hidden = Quote.objects.create(
            slug="andrew-murray-hidden", author=self.murray,
            text="An unreviewed sentence on prayer that must stay hidden.",
            chapter=self.ch, paragraph=20, reviewed=False,
        )
        hidden.topics.add(self.prayer)

    def test_topic_page_groups_reviewed_quotes_by_author(self):
        res = self.client.get("/api/library/quote-topics/prayer/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["topic"]["title"], "Prayer")
        self.assertEqual(len(res.data["authors"]), 1)
        group = res.data["authors"][0]
        self.assertEqual(group["author"]["slug"], "andrew-murray")
        self.assertEqual(group["count"], 8)
        slugs = [q["slug"] for q in group["quotes"]]
        self.assertNotIn("andrew-murray-hidden", slugs)

    def test_author_topic_page(self):
        res = self.client.get("/api/library/quotes/andrew-murray/prayer/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["author"]["name"], "Andrew Murray")
        self.assertEqual(res.data["topic"]["slug"], "prayer")
        self.assertEqual(len(res.data["quotes"]), 8)

    def test_topic_index_lists_only_topics_over_the_threshold(self):
        data = self.client.get("/api/library/quote-topics/").data
        by_slug = {r["slug"]: r for r in data}
        self.assertIn("prayer", by_slug)
        self.assertEqual(by_slug["prayer"]["count"], 8)
        # faith has no reviewed quotes; below the bar, so it is not advertised.
        self.assertNotIn("faith", by_slug)

    def test_pages_list_gives_author_topic_pairs_over_the_threshold(self):
        pairs = self.client.get("/api/library/quote-topics/pages/").data
        self.assertIn({"author": "andrew-murray", "topic": "prayer"}, pairs)

    def test_a_pair_below_the_threshold_is_not_a_page(self):
        # Three reviewed Spurgeon quotes on faith — under QUOTE_AUTHOR_TOPIC_MIN.
        for i in range(3):
            q = Quote.objects.create(
                slug=f"charles-h-spurgeon-f{i}", author=self.spurgeon,
                text=f"A sentence on faith number {i} that is long enough.",
                chapter=self.ch, paragraph=i + 1, reviewed=True,
            )
            q.topics.add(self.faith)
        pairs = self.client.get("/api/library/quote-topics/pages/").data
        self.assertNotIn({"author": "charles-h-spurgeon", "topic": "faith"}, pairs)
        # But the page itself still serves if reached directly (>= 1).
        res = self.client.get("/api/library/quotes/charles-h-spurgeon/faith/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["quotes"]), 3)

    def test_a_pair_whose_theme_has_no_page_is_not_a_page(self):
        # Five reviewed Spurgeon quotes on faith: the pair clears 4, but faith's
        # total (5) misses the theme threshold (8), so no "Quotes on Faith" page
        # is built. The pair must NOT be advertised either — otherwise the
        # author-theme page's "More quotes on Faith" link would be an orphan.
        for i in range(5):
            q = Quote.objects.create(
                slug=f"charles-h-spurgeon-f{i}", author=self.spurgeon,
                text=f"A sentence on faith number {i} that is long enough.",
                chapter=self.ch, paragraph=i + 1, reviewed=True,
            )
            q.topics.add(self.faith)
        self.assertNotIn(
            "faith", {r["slug"] for r in self.client.get("/api/library/quote-topics/").data}
        )
        pairs = self.client.get("/api/library/quote-topics/pages/").data
        self.assertNotIn({"author": "charles-h-spurgeon", "topic": "faith"}, pairs)

    def test_unknown_topic_and_pair_are_404(self):
        self.assertEqual(self.client.get("/api/library/quote-topics/nope/").status_code, 404)
        self.assertEqual(
            self.client.get("/api/library/quotes/andrew-murray/nope/").status_code, 404
        )
        self.assertEqual(
            self.client.get("/api/library/quotes/nobody/prayer/").status_code, 404
        )

    def test_the_author_page_offers_its_topic_chips(self):
        # The author quote page carries the themes deep enough to link, so it can
        # show "on Prayer" without a second request.
        data = self.client.get("/api/library/quotes/andrew-murray/").data
        chips = {t["slug"]: t for t in data["topics"]}
        self.assertIn("prayer", chips)
        self.assertEqual(chips["prayer"]["count"], 8)
        self.assertNotIn("faith", chips)


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
        listing = self.client.get("/api/library/quotes/").data
        self.assertEqual(
            listing, [{"slug": "w", "name": "A Writer", "birth_year": None, "count": 1}]
        )

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
