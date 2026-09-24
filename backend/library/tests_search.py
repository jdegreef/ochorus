"""Search: the query path, its facets and scopes, the stored vectors behind it, and the log it writes.

Postgres FTS is the production path and CI runs this suite on Postgres as well
as SQLite, so a change here is exercised against the engine that actually
serves it."""

from unittest import mock, skipUnless
from unittest.mock import patch  # noqa: E402

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import search as search_module
from .models import (
    Article,
    Author,
    Book,
    Chapter,
    ChapterCitation,
    Language,
    Plan,
    SearchClickLog,
    SearchQueryLog,
    Sermon,
    Topic,
    TopicBook,
    TopicSermon,
)
from .search import search_library


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
        Article.objects.create(
            slug="how-to-forgive",
            language="en",
            h1="How to Forgive Someone Who Hurt You",
            # A distinctive keyword that appears ONLY in the SEO meta_title, so a
            # test can prove that field is searchable on its own.
            meta_title="Reconciliation: a keyword-led title",
            description="A short guide to forgiveness, drawn from the classics.",
            body_html="<p>Forgiveness begins where the wound is deepest.</p>",
            is_published=True,
        )
        Article.objects.create(
            slug="draft-article",
            language="en",
            h1="Unpublished Forgiveness Draft",
            description="Not for readers yet.",
            body_html="<p>draft</p>",
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

    def test_article_entity_hit(self):
        # An article is a navigational hit — title + snippet, no author/cover.
        hits = [r for r in self.search("Forgive") if r["type"] == "article"]
        self.assertEqual(len(hits), 1)
        hit = hits[0]
        self.assertEqual(hit["article_slug"], "how-to-forgive")
        self.assertEqual(hit["article_title"], "How to Forgive Someone Who Hurt You")
        # The snippet is the standfirst; no author_name/cover keys on the row.
        self.assertNotIn("author_name", hit)
        self.assertNotIn("cover_url", hit)

    def test_article_matches_meta_title(self):
        # The keyword-led SEO meta_title is searchable on its own — guards the
        # `meta_title` term in _pg_vector("article") / _lite_q("article") against
        # a silent drop (a field in the vector that no test exercised is exactly
        # how the topic vector once went wrong on the reader's path).
        hits = [r for r in self.search("Reconciliation") if r["type"] == "article"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["article_slug"], "how-to-forgive")

    def test_article_matches_description(self):
        # Matches the standfirst, not just the headline (the SEO body an article
        # answers a query with). No HTML leaks from body_html into the snippet.
        hits = [r for r in self.search("forgiveness") if r["type"] == "article"]
        self.assertEqual(len(hits), 1)
        self.assertNotIn("<", hits[0]["snippet"])

    def test_unpublished_article_excluded(self):
        slugs = {r.get("article_slug") for r in self.search("Forgiveness")}
        self.assertNotIn("draft-article", slugs)

    def test_article_absent_for_other_language(self):
        # Articles are per-language rows with no English fallback, so an
        # English-only article must not surface for a non-English query — the
        # per-language filter is the whole of the English gating.
        hits = [
            r for r in self.search("Forgive", language="es") if r["type"] == "article"
        ]
        self.assertEqual(hits, [])

    def test_article_type_page(self):
        # The "show more of this type" path returns article hits too, so the
        # facet chip a reader clicks lands on a real page rather than an empty one.
        res = self.client.get("/api/library/search/?q=Forgive&type=article&language=en")
        self.assertEqual(res.status_code, 200)
        slugs = {r["article_slug"] for r in res.data["results"]}
        self.assertEqual(slugs, {"how-to-forgive"})

    def test_article_counted_in_totals(self):
        # count_by_type sees articles, so the merged list can report the real
        # per-type total behind the sample it shows.
        res = self._raw("Forgive")
        self.assertEqual(res["totals"].get("article"), 1)

    def test_entities_lead_over_passages(self):
        # A book/author/topic/plan match should rank above raw body-text hits.
        results = self.search("Humility")
        self.assertIn(results[0]["type"], {"book", "author", "topic", "plan"})

    def test_unpublished_author_excluded(self):
        # An author with nothing published in the language shouldn't surface.
        Author.objects.create(slug="ghost", name="Ghost Humility Writer")
        slugs = {r.get("author_slug") for r in self.search("Humility")}
        self.assertNotIn("ghost", slugs)

    def test_imprint_is_not_an_author_hit_but_its_books_are_found(self):
        # A house byline is not a person: no "Author" row for it, while its
        # books stay searchable (the imprint's own shelf is /originals).
        imprint = Author.objects.create(
            slug="ochorus-originals", name="Ochorus Originals", is_imprint=True
        )
        book = Book.objects.create(
            author=imprint, slug="a-hidden-fire", language="en", title="A Hidden Fire"
        )
        Chapter.objects.create(book=book, order=1, title="One", body_html="<p>Kampala</p>")
        self.assertNotIn(
            "ochorus-originals",
            {r.get("author_slug") for r in self.search("Ochorus") if r["type"] == "author"},
        )
        books = [r for r in self.search("Hidden Fire") if r["type"] == "book"]
        self.assertEqual([b["book_slug"] for b in books], ["a-hidden-fire"])

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

    def test_suggests_word_from_article_title(self):
        # Article h1 words feed the did-you-mean vocabulary, so a misspelt one
        # resolves — the same guarantee the book/author suggestions carry.
        data = self._raw("somone")
        self.assertEqual(data["results"], [])
        self.assertEqual(data.get("suggestion", "").lower(), "someone")

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


ROM_8 = 45008000  # BBBCCCVVV base for Romans 8
ROM_8_28 = 45008028


class ScripturePageHitTests(TestCase):
    """The scripture HUB page as a navigational search hit — a reference query's
    lead result, above the sermons and chapters that treat the passage."""

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="a", name="A")
        self.book = Book.objects.create(
            author=author, slug="b", language="en", title="B"
        )
        # Five DISTINCT chapters each cite Romans 8:28. That clears the verse
        # floor (5) for the verse page and, a fortiori, the chapter floor (3).
        for order in range(1, 6):
            ch = Chapter.objects.create(
                book=self.book, order=order, title=f"Ch {order}", body_html="<p>x</p>"
            )
            ChapterCitation.objects.create(
                chapter=ch,
                ref_text="Romans 8:28",
                start_verse_id=ROM_8_28,
                end_verse_id=ROM_8_28,
            )

    def _raw(self, q, **params):
        res = self.client.get(
            "/api/library/search/", {"q": q, "language": "en", **params}
        )
        self.assertEqual(res.status_code, 200)
        return res.data

    def _scripture(self, q, **params):
        return [r for r in self._raw(q, **params)["results"] if r["type"] == "scripture"]

    def test_verse_query_leads_with_the_verse_page(self):
        data = self._raw("Romans 8:28")
        scr = [r for r in data["results"] if r["type"] == "scripture"]
        self.assertEqual(len(scr), 1)
        hit = scr[0]
        self.assertEqual(
            (hit["book_slug"], hit["chapter"], hit["verse"]), ("romans", 8, 28)
        )
        self.assertEqual(hit["reference"], "Romans 8:28")
        # The passage hub leads the merged list, above the chapters that cite it.
        self.assertEqual(data["results"][0]["type"], "scripture")

    def test_chapter_only_query_gives_the_chapter_page(self):
        scr = self._scripture("Romans 8")
        self.assertEqual(len(scr), 1)
        self.assertIsNone(scr[0]["verse"])
        self.assertEqual(scr[0]["reference"], "Romans 8")

    def test_non_reference_query_has_no_scripture_hit(self):
        self.assertEqual(self._scripture("grace"), [])

    def test_unqualified_reference_has_no_page(self):
        # Nothing cites Romans 9, so it never earned a page — no dead-link hit.
        self.assertEqual(self._scripture("Romans 9"), [])

    def test_not_surfaced_for_non_english(self):
        # Scripture pages are English-only; the hit must not appear for /es.
        self.assertEqual(self._scripture("Romans 8:28", language="es"), [])

    def test_not_surfaced_inside_a_scope(self):
        # A global hub, not something inside "search within this book".
        self.assertEqual(self._scripture("Romans 8:28", **{"in": "book:b"}), [])

    def test_type_page_returns_the_scripture_hit(self):
        # Selecting the Scripture facet fetches ?type=scripture — it must return
        # the hit rather than a blank list.
        res = self._raw("Romans 8:28", type="scripture")
        self.assertEqual(
            [(r["book_slug"], r["chapter"], r["verse"]) for r in res["results"]],
            [("romans", 8, 28)],
        )


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

        with patch.object(
            SearchQueryLog.objects, "create", side_effect=RuntimeError("db down")
        ):
            res = self.search("humility")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["results"])

    def test_trim_command_prunes_old_rows_only(self):
        from datetime import timedelta

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
    def test_returns_the_matching_works_to_queue(self):
        # Beyond the per-language counts, the specific works behind them — so a
        # gap becomes a one-click translation job. A chapter match resolves to
        # its book (the queueable work), deduped.
        res = self.gap("humility", "sw")
        works = res.data["works"]
        self.assertEqual(len(works), 1)
        w = works[0]
        self.assertEqual(w["type"], "book")
        self.assertEqual(w["slug"], "humility")
        self.assertEqual(w["title"], "Humility")
        self.assertEqual(w["languages"], ["en"])

    @override_settings(DEBUG=True)
    def test_nothing_anywhere_means_translation_will_not_help(self):
        # The distinction the whole endpoint exists to draw: this is a work to
        # acquire, not a work to translate.
        res = self.gap("theosis", "sw")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["elsewhere"], [])
        self.assertEqual(res.data["works"], [])

    @override_settings(DEBUG=True)
    def test_a_missing_or_trivial_query_is_rejected(self):
        self.assertEqual(self.gap("humility", "").status_code, 400)
        self.assertEqual(self.gap("h", "sw").status_code, 400)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        self.assertIn(self.gap("humility", "sw").status_code, (401, 403))


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
