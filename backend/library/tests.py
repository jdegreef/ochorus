import copy
import json
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from . import language_suggestions
from .ingest import clean_title
from .languages import config as language_config
from .models import (
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Language,
    Plan,
    PlanDay,
    SearchQueryLog,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)
from .text import html_to_text
from .translation import (
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


class SermonBodyTextTests(TestCase):
    def test_save_derives_body_text(self):
        author = Author.objects.create(slug="a", name="A")
        s = Sermon.objects.create(
            author=author, slug="s", title="S", body_html="<p>Hear my <b>cry</b>.</p>"
        )
        self.assertEqual(s.body_text, "Hear my cry.")


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
    "library.management.commands._translate_base.anthropic.Anthropic",
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
        with mock.patch("library.management.commands._translate_base.verify_bible_code"), \
             mock.patch("library.management.commands._translate_base.anthropic"), \
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
        with mock.patch("library.management.commands._translate_base.verify_bible_code"), \
             mock.patch("library.management.commands._translate_base.anthropic"), \
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
        with mock.patch("library.management.commands._translate_base.verify_bible_code"), \
             mock.patch("library.management.commands._translate_base.anthropic"), \
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

        with mock.patch("library.management.commands._translate_base.verify_bible_code"), \
             mock.patch("library.management.commands._translate_base.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value={"title": "Mpya", "description": "mpya"},
             ) as meta:
            self._run("--language", "sw", "--force")
            meta.assert_called_once()
        self.assertEqual(
            TopicTranslation.objects.get(topic=self.topic, language="sw").title, "Mpya"
        )


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


