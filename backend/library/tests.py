from unittest import skipUnless

from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .ingest import clean_title
from .models import Author, Book, Chapter, Plan, PlanDay, Sermon
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

    @skipUnless(connection.vendor == "postgresql", "Postgres-only FTS path")
    def test_postgres_stemming_and_ranking(self):
        # "depend" should stem-match "dependence" under the english config.
        results = self.search("depend")
        self.assertTrue(results)
        self.assertIn("⟦", results[0]["snippet"])


class PlanTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="humility-2", language="en", title="Humility")
        for i in (1, 2):
            Chapter.objects.create(book=book, order=i, title=f"Ch {i}", body_html="<p>x</p>")
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

    def test_detail_resolves_chapter_titles(self):
        res = self.client.get("/api/library/plans/humility-12-days/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["days"][0]["chapter_title"], "Ch 1")
        self.assertEqual(res.data["days"][0]["book_title"], "Humility")

    def test_seed_plans_idempotent(self):
        from django.core.management import call_command
        call_command("seed_plans")
        call_command("seed_plans")
        self.assertEqual(Plan.objects.filter(slug="humility-12-days").count(), 1)


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
