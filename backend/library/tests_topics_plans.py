"""Topics and reading plans: the shelves, their per-language prose, the day-by-day
plan structure, and the admin view of which topics a language still lacks.

Both are content the reader browses by rather than reads through, and both carry
translated prose in a side-table rather than per-language rows — which is why
they behave differently from books and sermons and are worth exercising apart
from them."""

import copy
from unittest import mock
from unittest.mock import patch  # noqa: E402

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import body_of

from .models import (
    Author,
    Book,
    Chapter,
    Plan,
    PlanDay,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)


class PlanTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="humility-2", language="en", title="Humility")
        for i in (1, 2):
            Chapter.objects.create(
                book=book, order=i, title=f"Ch {i}", body_html=body_of(100)
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

    def test_detail_lists_the_plan_authors(self):
        # Both days read the one book by "am" → one distinct author, linked.
        res = self.client.get("/api/library/plans/humility-12-days/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([a["slug"] for a in res.data["authors"]], ["am"])
        self.assertEqual(res.data["authors"][0]["name"], "Andrew Murray")

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
        call_command("seed_plans")
        call_command("seed_plans")
        self.assertEqual(Plan.objects.filter(slug="humility-12-days").count(), 1)

    def test_seed_plans_rebuilds_a_day_less_plan(self):
        # Simulate a previous run that created the Plan row but died before its
        # PlanDays landed (or an interrupted seed). The reconcile used to report
        # any existing row as "done", leaving it permanently empty; now it's
        # rebuilt with its days.

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
        "Humility in 12 Days" on the Arabic plans page.

        The stand-in language has to be one with no prose for THIS plan. It used
        to be a real locale and moved as each one was translated (Hindi until
        job #1103, Ukrainian until job #811), until every seeded locale had
        prose. So it is now a code with no ``plan_translations`` file at all.
        """

        de_book = Book.objects.create(
            author=Author.objects.get(slug="am"),
            slug="humility-2",
            language="de",
            title="Demut",
        )
        Chapter.objects.create(book=de_book, order=1, title="Eins", body_html="<p>x</p>")
        call_command("seed_plans", verbosity=0)

        self.assertFalse(
            Plan.objects.filter(slug="humility-12-days", language="de").exists(),
            "seed_plans created a German plan with no German prose — it "
            "would render the English title to a German reader.",
        )
        # The languages that DO have prose are unaffected.
        self.assertTrue(Plan.objects.filter(slug="humility-12-days", language="en").exists())

    def test_seed_plans_span_skips_the_bracketing_chapters(self):
        """A devotional's Introduction and Conclusion stay out of its plan, so
        plan day N is the chapter titled "Day N" rather than one off from it."""
        book = Book.objects.create(
            author=Author.objects.get(slug="am"), slug="devotional", language="en", title="D"
        )
        for i in range(1, 6):  # intro, three days, conclusion
            Chapter.objects.create(book=book, order=i, title=f"Ch {i}", body_html="<p>x</p>")
        launch = [("devotional-plan", "devotional", "D", "d", (2, 4))]
        with patch("library.management.commands.seed_plans.LAUNCH_PLANS", launch):
            call_command("seed_plans", verbosity=0)

        days = Plan.objects.get(slug="devotional-plan", language="en").days.all()
        self.assertEqual(
            [(d.day, d.chapter_order) for d in days], [(1, 2), (2, 3), (3, 4)]
        )

    def test_seed_plans_leaves_an_existing_untranslated_row_alone(self):
        """A row created before this guard keeps its prose; deleting a published
        plan is a bigger decision than a seed step makes on its own."""

        de_book = Book.objects.create(
            author=Author.objects.get(slug="am"), slug="humility-2", language="de", title="Demut"
        )
        Chapter.objects.create(book=de_book, order=1, title="Eins", body_html="<p>x</p>")
        legacy = Plan.objects.create(
            slug="humility-12-days", language="de", title="Humility in 12 Days", description="old"
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

    def test_detail_lists_distinct_authors(self):
        # Both member books are by "am" → one distinct author on the shelf.
        res = self.client.get("/api/library/topics/prayer/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([a["slug"] for a in res.data["authors"]], ["am"])
        self.assertEqual(res.data["authors"][0]["name"], "Andrew Murray")

    def test_detail_related_topics_by_shared_books(self):
        # A second published, translated shelf that shares a book with "prayer".
        other = Topic.objects.create(
            slug="deeper-life", title="The Deeper Life", sort_order=3
        )
        TopicBook.objects.create(topic=other, book_slug="humility-2")
        res = self.client.get("/api/library/topics/prayer/?language=en")
        self.assertEqual(res.status_code, 200)
        related = [t["slug"] for t in res.data["related_topics"]]
        self.assertEqual(related, ["deeper-life"])
        # A shelf that shares no book (its only member doesn't exist) is not related.
        self.assertNotIn("empty", related)

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
        call_command("seed_topics")
        call_command("seed_topics")
        self.assertEqual(Topic.objects.filter(slug="prayer").count(), 1)
        # The seed's curated prayer membership includes the-inner-chamber.
        self.assertTrue(
            TopicBook.objects.filter(
                topic__slug="prayer", book_slug="the-inner-chamber"
            ).exists()
        )

    def test_seed_topics_removes_a_member_topic_seed_dropped(self):
        # Membership used to be add-only: #2872 took the copyright-blocked
        # grace-for-grace-2 off two shelves, and its rows stayed live.
        call_command("seed_topics", verbosity=0)
        topic = Topic.objects.get(slug="prayer")
        TopicBook.objects.create(topic=topic, book_slug="dropped-book", sort_order=99)
        TopicSermon.objects.create(topic=topic, sermon_slug="dropped-sermon")
        call_command("seed_topics", verbosity=0)
        self.assertFalse(TopicBook.objects.filter(book_slug="dropped-book").exists())
        self.assertFalse(TopicSermon.objects.filter(sermon_slug="dropped-sermon").exists())
        # ...while every member topic_seed still lists survives.
        self.assertTrue(
            TopicBook.objects.filter(topic=topic, book_slug="the-inner-chamber").exists()
        )

    def test_seed_topics_refreshes_the_english_title_and_description(self):
        call_command("seed_topics", verbosity=0)
        topic = Topic.objects.get(slug="prayer")
        want = (topic.title, topic.description, topic.sort_order)
        Topic.objects.filter(pk=topic.pk).update(
            title="Stale", description="Stale blurb.", sort_order=999
        )
        call_command("seed_topics", verbosity=0)
        topic.refresh_from_db()
        self.assertEqual((topic.title, topic.description, topic.sort_order), want)

    def test_every_translated_language_covers_every_topic(self):
        """A translated language must cover every topic that isn't translation-pending.

        There is no English fallback: a topic missing from a language's file is
        omitted from that language's shelf list entirely. So a partial language
        silently ships a partial set of shelves — the same discipline as the
        per-language glossaries, which are pinned the same way. Reads
        ``data/topic_translations/<lang>.json`` through the loader.

        The one sanctioned exception is ``TRANSLATION_PENDING`` (topic_seed): a
        newly-added shelf ships live in English while the translation queue works
        through it, so its absence from a language is allowed. Everything else is
        still pinned — no prose for an unknown slug, and every non-pending shelf
        present in every language — and a pending shelf that HAS been translated
        must still be well-formed.
        """
        from library.management.commands.seed_topics import TOPICS
        from library.topic_seed import TRANSLATION_PENDING
        from library.topic_translations import topic_translations

        slugs = {t[0] for t in TOPICS}
        required = slugs - TRANSLATION_PENDING
        for lang, per_topic in topic_translations().items():
            with self.subTest(language=lang):
                present = set(per_topic)
                self.assertEqual(
                    present - slugs,
                    set(),
                    f"{lang}: prose for a slug that names no topic",
                )
                self.assertEqual(
                    required - present,
                    set(),
                    f"{lang}: missing shelves that are not translation-pending",
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


class TopicQaTests(TestCase):
    """`Topic.qa` — editorial Questions & Answers, localized via `qa_for` like the
    prose fields, exposed under the unified serializer key `qa`."""

    def setUp(self):
        self.topic = Topic.objects.create(
            slug="prayer",
            title="On Prayer",
            qa=[
                {"question": "What is it?", "answer": "Prayer."},
                {"question": "Why pray?", "answer": "Because."},
            ],
        )
        TopicTranslation.objects.create(
            topic=self.topic,
            language="sw",
            title="Maombi",
            qa=[{"question": "Ni nini?", "answer": "Maombi."}],
        )
        # A locale translated for its title but carrying no Q&A of its own.
        TopicTranslation.objects.create(topic=self.topic, language="fr", title="Prière")

    def test_qa_for_returns_the_english_set_on_the_base_row(self):
        self.assertEqual(self.topic.qa_for("en")[0]["question"], "What is it?")

    def test_qa_for_returns_the_translated_set(self):
        self.assertEqual(
            self.topic.qa_for("sw"), [{"question": "Ni nini?", "answer": "Maombi."}]
        )

    def test_qa_for_a_locale_without_a_set_is_empty_not_english(self):
        # No English fallback — a reader never sees an English Q&A on a localized
        # page — unless a coverage surface asks for it explicitly.
        self.assertEqual(self.topic.qa_for("fr"), [])
        self.assertEqual(self.topic.qa_for("fr", fallback=True), self.topic.qa)

    def test_detail_serializer_exposes_qa_localized(self):
        from library.serializers import TopicDetailSerializer

        en = TopicDetailSerializer(self.topic, context={"language": "en"}).data
        self.assertEqual(len(en["qa"]), 2)
        fr = TopicDetailSerializer(self.topic, context={"language": "fr"}).data
        self.assertEqual(fr["qa"], [])


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

        with patch("accounts.permissions.RequireCapability.has_permission", return_value=True):
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
