from pathlib import Path
from unittest import mock

from django.db import connection
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from common.testing import body_of

from . import language_suggestions
from .ingest import clean_title
from .models import (
    Article,
    Author,
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
from .text import html_to_text, word_count


class CleanTitleTests(TestCase):
    def test_allcaps_ccel_heading_becomes_title_case(self):
        self.assertEqual(clean_title("II. THE DIGNITY OF CHRIST"), "The Dignity of Christ")
        self.assertEqual(clean_title("XXXII. GOD A CONSUMING FIRE."), "God a Consuming Fire")

    def test_preserves_apostrophe_when_recasing(self):
        self.assertEqual(
            clean_title("VIII. CHRIST'S MERCIFUL AND FAITHFUL HELP"),
            "Christ's Merciful and Faithful Help",
        )

    def test_preserves_a_plural_possessive(self):
        # Finney's "Revival at Evans' Mills" came out "Evans Mills".
        self.assertEqual(clean_title("Revival at Evans' Mills"), "Revival at Evans' Mills")
        self.assertEqual(clean_title("REVIVAL AT EVANS' MILLS"), "Revival at Evans' Mills")
        # A quoted phrase still loses its quotes.
        self.assertEqual(clean_title("'Lo here' and 'lo there'"), "Lo here and lo there")

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

    def test_strips_a_bare_number_prefix(self):
        # A CCEL TOC numbers its own entries and the reader prepends the chapter
        # order itself, so "1. Men of Prayer Needed" rendered as "1. 1. Men of
        # Prayer Needed". Same redundancy as "Chapter N.".
        self.assertEqual(clean_title("1. Men of Prayer Needed"), "Men of Prayer Needed")
        self.assertEqual(clean_title("01. Walking with God"), "Walking with God")
        self.assertEqual(clean_title("13) Grace from the Heart"), "Grace from the Heart")

    def test_keeps_a_bare_numeral_that_is_the_whole_title(self):
        # Nothing descriptive follows, so as with a bare "Chapter 3" there would
        # be nothing left to show. (The stop goes to the older trailing-noise
        # rule, not to this one.)
        self.assertEqual(clean_title("12."), "12")

    def test_keeps_digits_that_are_not_a_numbering_prefix(self):
        # No separator follows the digits, so this is the author's own text.
        # ("and" is capitalised by the pre-existing first-letter rule, which is
        # not what this test is about — it is pinned here only to stay honest.)
        self.assertEqual(clean_title("1859 and After"), "1859 And After")
        # Four digits are a year, not a chapter number.
        self.assertEqual(clean_title("1662. The Great Ejection"), "1662. The Great Ejection")

    def test_keeps_the_numeral_of_a_numbered_bible_book(self):
        # The numeral is part of the book's NAME, so stripping it would collapse
        # the three epistles of John to one title. `_ROMAN_PREFIX` guards the
        # roman spelling ("II. Timothy") for the same reason.
        self.assertEqual(clean_title("1. John"), "1. John")
        self.assertEqual(clean_title("2. John"), "2. John")
        self.assertEqual(clean_title("2. Peter"), "2. Peter")
        # Matched whole: a real numbered title that merely STARTS with a book
        # name still loses its numbering.
        self.assertEqual(clean_title("1. John the Baptist"), "John the Baptist")
        # And the guard is not a word-count test — Murray's one-word chapter
        # titles must still be stripped.
        self.assertEqual(clean_title("11. Patiently"), "Patiently")

    def test_is_idempotent_on_a_doubly_numbered_title(self):
        # The docstring promises it, and it is applied more than once by design
        # (migration 0003 runs it over already-cleaned rows).
        for raw in ("1. 2. Title", "Chapter 1. Chapter 2. Title", "1. 1. Men of Prayer"):
            once = clean_title(raw)
            self.assertEqual(clean_title(once), once, raw)

    def test_a_bare_chapter_counter_survives_clean_title(self):
        # Emptying it is `upsert_book`'s job, not this function's: `clean_title`
        # also cleans HEADINGS that other code reads the counter out of —
        # Confessions' 276 grouped leaf headings are bare counters, and
        # `import_gutenberg._ROMAN_OR_NUM` matches one to know it must borrow
        # the real title from the next node. See `_BARE_CHAPTER`.
        self.assertEqual(clean_title("Chapter I"), "Chapter I")
        self.assertEqual(clean_title("CHAPTER IV."), "Chapter IV")
        # A real title that merely begins with the word is untouched.
        self.assertEqual(clean_title("Chapter Summary"), "Chapter Summary")

    def test_bare_roman_numeral_left_alone(self):
        self.assertEqual(clean_title("IV"), "IV")

    def test_idempotent_on_clean_title(self):
        self.assertEqual(clean_title("The Dignity of Christ"), "The Dignity of Christ")


class ResolveTitleTests(SimpleTestCase):
    """`import_gutenberg.resolve_title` on the numeral-over-title heading shape."""

    def _title(self, html):
        from .management.commands.import_gutenberg import resolve_title, soup

        return resolve_title(soup(html).find(["h1", "h2", "h3"]))[0]

    def test_bare_numeral_line_over_title_drops_the_numeral(self):
        # Torrey's "<h2>I<br/>BEGINNING RIGHT</h2>" fuses to "I BEGINNING RIGHT"
        # under a space join, which no roman-prefix rule can safely strip (it
        # would also break "I AM THE WAY"). The <br/> is the reliable signal.
        self.assertEqual(self._title("<h2>I<br/>BEGINNING RIGHT</h2>"), "Beginning Right")
        self.assertEqual(self._title("<h2>XIII<br/><small>THE DEVIL</small></h2>"), "The Devil")

    def test_chapter_marker_line_over_title_drops_the_marker(self):
        self.assertEqual(
            self._title("<h2>CHAPTER VII.<br/><br/>Dealing with the Careless</h2>"),
            "Dealing with the Careless",
        )

    def test_trailing_punctuation_outside_the_title_span_keeps_no_space(self):
        # "<span>…of God</span>?" is a separate text node, so the newline join
        # would leave "God ?" without the space-before-punct fix.
        self.assertEqual(
            self._title(
                "<h2>I<br/><small><span>Inspiration, or to What Extent Is the "
                "Bible Inspired of God</span>?</small></h2>"
            ),
            "Inspiration, or to What Extent Is the Bible Inspired of God?",
        )

    def test_leaves_a_single_line_heading_to_the_normal_path(self):
        # No <br/>: the numeral-borrow path (which reads the NEXT node) still owns
        # "<h5>I.</h5>", so this branch must not fire on a one-line heading.
        self.assertEqual(self._title("<h2>Beginning Right</h2>"), "Beginning Right")

    def test_does_not_strip_a_numeral_that_is_the_whole_title(self):
        # If the remainder is itself just a numeral, fall through untouched rather
        # than returning an empty title.
        self.assertEqual(self._title("<h2>I<br/>II</h2>"), "I II")

    def test_splits_on_br_only_not_on_an_inline_pagenum_span(self):
        # A page-anchor span inside a heading is NOT a <br/>, so it must not become
        # a phantom line that the branch mistakes for the title. The numeral stays.
        title = self._title(
            '<h2>CHAPTER I<span class="pagenum" id="Page_12">[Pg 12]</span></h2>'
        )
        self.assertNotEqual(title, "[Pg 12]")  # branch did not fire and eat the numeral
        self.assertIn("[Pg 12]", title)  # fell through to the old fused path intact

    def test_splits_on_br_only_not_on_a_styled_first_letter(self):
        # A drop-cap / styled initial that happens to be a roman-numeral letter
        # (C, I, V, L, …) must not be read as a chapter numeral and stripped.
        title = self._title('<h2><span class="dropcap">C</span>hrist Our Hope</h2>')
        self.assertNotEqual(title, "Hrist Our Hope")
        self.assertIn("hrist Our Hope", title)

    def test_ignores_a_trailing_contents_toc_link(self):
        # Murray's #29296 sets each chapter heading as a bare "CHAPTER N" with a
        # "Contents" TOC-return link on the next line; that link is navigation, so
        # the heading stays a bare counter (the real title comes from corrections),
        # NOT the word "Contents".
        self.assertEqual(
            self._title(
                '<h2>CHAPTER VI<br/><small class="toclink">'
                '<a href="#toc">Contents</a></small></h2>'
            ),
            "Chapter VI",
        )


class HtmlToTextTests(TestCase):
    def test_strips_tags_and_keeps_block_boundaries(self):
        text = html_to_text("<p>First sentence.</p><p>Second one.</p>")
        self.assertEqual(text, "First sentence. Second one.")

    def test_unescapes_entities(self):
        self.assertEqual(html_to_text("<p>God&rsquo;s &amp; grace</p>"), "God’s & grace")


class WordCountRuleTests(SimpleTestCase):
    """Pins the divergence `library.text.text_of` documents.

    Two reductions of the same column live side by side, which makes reaching
    for the wrong one easy — and it is silent, because it only costs words on
    bodies that lean on inline markup.
    """

    def test_every_tag_is_a_word_boundary(self):
        self.assertEqual(word_count("<p><i>one</i><b>two</b></p>"), 2)
        self.assertEqual(html_to_text("<p><i>one</i><b>two</b></p>"), "onetwo")

    def test_entities_are_left_escaped_and_still_count_as_one_word(self):
        self.assertEqual(word_count("<p>G&amp;C</p>"), 1)


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

    def test_save_derives_word_count_and_a_passed_count_does_not_beat_it(self):
        """The column is derived, so the body is the only thing that sets it.

        The passed value is worth pinning: `create(word_count=...)` used to
        stick, and it is still spelled out in `content_sync` and in fixture
        rows that `loaddata` writes without ever reaching `save()`.
        """
        ch = Chapter.objects.create(
            book=self.book, order=1, title="One",
            body_html="<p>Pride must die.</p>", word_count=999,
        )
        ch.refresh_from_db()
        self.assertEqual(ch.word_count, 3)

    def test_save_with_update_fields_keeps_word_count_in_step(self):
        """The gap this closes: a body rewritten in place left the count behind.

        `apply_body_corrections` runs on every deploy and does exactly this —
        assign body_html, save — and nothing downstream repairs a count that is
        present but wrong (`backfill_word_count` fills only zeros).
        """
        ch = Chapter.objects.create(
            book=self.book, order=1, title="One", body_html="<p>One two three.</p>"
        )
        ch.body_html = "<p>One two.</p>"
        ch.save(update_fields=["body_html"])
        ch.refresh_from_db()
        self.assertEqual(ch.word_count, 2)


class SermonBodyTextTests(TestCase):
    def test_save_derives_body_text(self):
        author = Author.objects.create(slug="a", name="A")
        s = Sermon.objects.create(
            author=author, slug="s", title="S", body_html="<p>Hear my <b>cry</b>.</p>"
        )
        self.assertEqual(s.body_text, "Hear my cry.")

    def test_save_derives_word_count_and_keeps_it_in_step(self):
        author = Author.objects.create(slug="a", name="A")
        s = Sermon.objects.create(
            author=author, slug="s", title="S", body_html="<p>Hear my cry.</p>"
        )
        self.assertEqual(s.word_count, 3)
        s.body_html = "<p>Hear me.</p>"
        s.save(update_fields=["body_html"])
        s.refresh_from_db()
        self.assertEqual(s.word_count, 2)


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
        # A real person with a book, withheld from the shelf by choice.
        withheld = Author.objects.create(
            slug="withheld", name="Withheld Writer", list_in_biographies=False
        )
        Book.objects.create(author=withheld, slug="withheld-book", language="en", title="A Book")

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

    def test_person_with_a_book_can_be_withheld_from_the_shelf(self):
        # A real contributor with a book stays on /books but is kept off the
        # Biographies shelf when list_in_biographies is False.
        self.assertNotIn("withheld", self.slugs())

    def test_fixture_withholds_hannah_buyinza(self):
        # Same fresh-DB reasoning as the imprint flag: the fixture has to carry
        # list_in_biographies=false, since a rebuild seeds from it after migrate.
        from library.content_fixtures import load_all_rows

        rows = load_all_rows()
        withheld = {
            r["fields"]["slug"]
            for r in rows
            if r.get("model") == "library.author"
            and r["fields"].get("list_in_biographies") is False
        }
        self.assertIn("hannah-buyinza", withheld)


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

    def test_susanna_damaged_guillemets_reach_a_deployed_database(self):
        """#1132 repaired these in the fixture, which no running database reads.

        `seed_books` did not rewrite an existing book's chapters then, so the ten
        OCR-damaged guillemets it found stayed on the site until they were
        declared here — `apply_body_corrections` runs on every deploy. The two
        CORRUPTED LETTERS are the reason this matters most: they read as a stray
        mark rather than a misspelling, so no other gate will ever catch them.
        """
        from library.corrections import apply_body_corrections

        damaged = (
            "<p>Deborah Ellison also married a French refugee, a «ilk-weaver "
            "named Pierre Collett; in January and February 1750, it was evident "
            "that her «nd was approaching.</p>"
            "<p>« Epworth, June 7th, 1705. MY LORD, « Lincoln Castle, "
            "the key of the chamber which led to my study » I could not find it, "
            "and get «my children over into the street; "
            "the name given by the girls to the intruding agency » f:My brother "
            'came. it is but aiming. #»••*.»# " But I am got to the end.</p>'
            "<p>**•»#* ' ' Of temperance in recreation I shall say little.</p>"
        )
        fixed = apply_body_corrections("susanna-wesley-clarke", 16, damaged)

        self.assertNotIn("«", fixed)
        self.assertNotIn("»", fixed)
        self.assertIn("a silk-weaver named Pierre Collett", fixed)
        self.assertIn("her end was approaching", fixed)
        self.assertIn("led to my study. I could not find", fixed)
        self.assertIn("the intruding agency. My brother", fixed)
        self.assertIn("<p>Epworth, June 7th, 1705.", fixed)
        self.assertIn("<p>' ' Of temperance", fixed)

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
    FAQ_Q = "ZZQ-ENGLISH-FAQQ-SENTINEL"
    FAQ_A = "ZZQ-ENGLISH-FAQA-SENTINEL"
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
            faq=[{"q": self.FAQ_Q, "a": self.FAQ_A}],
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
            self.FAQ_Q,
            self.FAQ_A,
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

    def test_faq_is_served_in_english_and_never_falls_back(self):
        # English readers get the editorial set...
        res = self.client.get("/api/library/authors/jane-doe/?language=en")
        self.assertEqual(res.data["faq"], [{"q": self.FAQ_Q, "a": self.FAQ_A}])
        # ...a locale with no translated set gets [] (the no-leak sweep proves the
        # English strings don't slip through; this pins the shape as an empty list,
        # which is what the page treats as "fall back to the derived block").
        res = self.client.get("/api/library/authors/jane-doe/?language=sw")
        self.assertEqual(res.data["faq"], [])
        # ...and once translated, THAT language's set is served.
        AuthorTranslation.objects.create(
            author=self.author,
            language="sw",
            faq=[{"q": "Nani Jane Doe?", "a": "Mwandishi."}],
        )
        res = self.client.get("/api/library/authors/jane-doe/?language=sw")
        self.assertEqual(res.data["faq"], [{"q": "Nani Jane Doe?", "a": "Mwandishi."}])

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


# A deliberately FICTIONAL language for the admin-created path. It used to be
# Hindi, which collided the moment Hindi became a real seeded language: these
# tests assert an admin-created row can be edited, and a repo-defined one is
# correctly refused with 409. "zz" is unassigned in ISO 639 and will never be a
# real target, so the fixture cannot be overtaken again. Pinned below.


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
        Chapter.objects.create(book=self.book, order=1, title="One", body_html=body_of(120))
        Chapter.objects.create(book=self.book, order=2, title="Two", body_html=body_of(80))
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
        Chapter.objects.create(book=lg, order=1, title="Emu", body_html=body_of(200))
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
        # failure with the query list attached. The +1 over the view's 10 is the
        # one constant read the ETag adds (the content revision — not per-row).
        # The 12th is the `featured_in_books` prefetch for `appears_in` — one
        # constant lookup for the "also appears in" section, prefetched in the
        # view so it stays a single query whether or not the author appears in
        # anything (an author with appearances pays one more, for the books).
        # The 13th is the `articles` field (articles_for_author): ONE scan of the
        # article table (no bodies). Six matching articles are created here so
        # the pin also proves that cost is flat rather than per-article — the
        # page is walked once per author per locale on every prerender, so a
        # per-article cost would multiply. An earlier draft of the field carried
        # a second `Book` query; it was measured to select nothing this one
        # missed and deleted (see articles_for_author).
        for i in range(6):
            Article.objects.create(
                slug=f"a{i}-guide", language="en", h1=f"Guide {i}",
                description="d", body_html="<p>x</p>", is_published=True,
                related=[{"type": "author", "slug": "murray"}],
            )
        with self.assertNumQueries(13):
            self.client.get("/api/library/authors/murray/?language=en")

    def test_book_detail_query_count_is_the_same_in_every_language(self):
        """The book page had NO query guard, which is how it came to pay an
        unmeasured cost: dropping `get_guides`' English-only gate put one article
        scan on every localized edition (15 -> 16 queries, measured), where
        before they paid nothing. That is the right trade — a localized edition
        must be able to show its own guide — but 245 of the 382 book editions in
        the fixture are non-English, so it is 245 extra scans per prerender and
        deserves a pin rather than a shrug.

        Both numbers are pinned, and the localized one is LOWER than English on
        purpose: English additionally resolves the topic chips and the author's
        reviewed-quote count for this fixture. What matters is that neither grows
        with the number of guides or articles.
        """
        lg = Book.objects.create(
            author=self.author, slug="humility", language="lg", title="Obuwombeefu"
        )
        Chapter.objects.create(book=lg, order=1, title="Emu", body_html=body_of(120))
        # Two guides per language: if the scan ever went per-guide, these double it.
        for lang in ("en", "lg"):
            for n in (1, 2):
                Article.objects.create(
                    slug=f"humility-{n}-guide", language=lang, h1=f"Guide {lang}{n}",
                    description="d", body_html="<p>x</p>", is_published=True,
                    related=[{"type": "book", "slug": "humility"}],
                )
        with self.assertNumQueries(18):
            self.client.get("/api/library/books/humility/?language=en")
        with self.assertNumQueries(16):
            self.client.get("/api/library/books/humility/?language=lg")


class TranslationBadgeSourceTypeTests(TestCase):
    """The reader and the author page must badge an unreviewed AI translation —
    CLAUDE.md: never present one as an original. Both payloads now carry the
    review state SourceBadge reads: a chapter's `source_type` (from its
    per-language book) and the author bio's `bio_source_type` (from the
    AuthorTranslation for the requested language)."""

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="w", name="Writer", bio="EN bio.")
        for lang, st in (("en", "public_domain"), ("es", "ai_unreviewed")):
            book = Book.objects.create(
                author=self.author, slug="bk", language=lang, title="Book",
                source_type=st,
            )
            Chapter.objects.create(book=book, order=1, title="One", body_html="<p>x</p>")

    def test_chapter_source_type_is_this_editions(self):
        en = self.client.get("/api/library/books/bk/chapters/1/?language=en")
        self.assertEqual(en.data["source_type"], "public_domain")
        es = self.client.get("/api/library/books/bk/chapters/1/?language=es")
        self.assertEqual(es.data["source_type"], "ai_unreviewed")

    def test_bio_source_type_tracks_the_translation_review_state(self):
        url = "/api/library/authors/w/"
        # The source-language original is not a translation — no badge.
        self.assertEqual(
            self.client.get(url + "?language=en").data["bio_source_type"],
            "public_domain",
        )
        # A translated bio, not yet signed off by a native speaker.
        tr = AuthorTranslation.objects.create(
            author=self.author, language="es", bio_html="<p>ES</p>", reviewed=False
        )
        self.assertEqual(
            self.client.get(url + "?language=es").data["bio_source_type"],
            "ai_unreviewed",
        )
        # Approved.
        tr.reviewed = True
        tr.save()
        self.assertEqual(
            self.client.get(url + "?language=es").data["bio_source_type"],
            "ai_reviewed",
        )
        # A language with no translated prose serves nothing to badge.
        self.assertEqual(
            self.client.get(url + "?language=lg").data["bio_source_type"],
            "public_domain",
        )
