"""The Articles public API contract.

Articles are original site writing with no author, addressed by ``slug`` +
``language`` like every other content row. These tests pin the three things the
frontend relies on: the index card carries no body, the detail resolves its
``related`` soft-references into ready-to-render "Read next" cards (dropping any
that don't resolve), and the per-language visibility rules match books/sermons
(unpublished hidden, no English fallback).
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Article, Author, Book

BODY = "<p>" + ("A settled paragraph about prayer. " * 50) + "</p>"


class ArticleApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="george-muller", name="George Müller")
        cls.book = Book.objects.create(
            author=cls.author,
            slug="the-life-of-trust",
            language="en",
            title="The Life of Trust",
            is_published=True,
        )
        # An unpublished book — a related reference to it must be dropped, not
        # shipped as a dead link.
        Book.objects.create(
            author=cls.author,
            slug="draft-book",
            language="en",
            title="Draft",
            is_published=False,
        )
        cls.article = Article.objects.create(
            slug="how-to-pray-so-god-answers",
            language="en",
            h1="How to Pray So That God Answers",
            meta_title="How to Pray — Müller",
            description="How Müller prayed.",
            body_html=BODY,
            sort_order=1,
            related=[
                {"type": "book", "slug": "the-life-of-trust"},
                {"type": "author", "slug": "george-muller"},
                {"type": "book", "slug": "draft-book"},        # unpublished → dropped
                {"type": "book", "slug": "does-not-exist"},    # missing → dropped
            ],
            is_published=True,
        )
        # A second, earlier-sorted published article, to pin ordering.
        Article.objects.create(
            slug="what-is-faith",
            language="en",
            h1="What Is Faith?",
            body_html=BODY,
            sort_order=0,
            is_published=True,
        )
        # Hidden from the en index: one unpublished, one in another language.
        Article.objects.create(
            slug="draft", language="en", h1="Draft", body_html=BODY, is_published=False
        )
        Article.objects.create(
            slug="how-to-pray-so-god-answers",
            language="es",
            h1="Cómo orar",
            body_html=BODY,
            is_published=True,
        )

    def setUp(self):
        self.client = APIClient()

    def test_list_returns_published_en_only_ordered_without_body(self):
        res = self.client.get(reverse("article-list"), {"language": "en"})
        self.assertEqual(res.status_code, 200)
        slugs = [a["slug"] for a in res.data]
        # Ordered by sort_order; unpublished "draft" and the es row are absent.
        self.assertEqual(slugs, ["what-is-faith", "how-to-pray-so-god-answers"])
        self.assertNotIn("body_html", res.data[0])

    def test_source_type_rides_on_the_list_card_and_the_detail(self):
        # The review badge depends on source_type reaching the reader on both the
        # index card and the article page. An AI translation must not be
        # presented as an original (CLAUDE.md), so this pins the field's
        # exposure: a serializer fields-list edit that dropped it would silently
        # remove the "awaiting review" badge from every translated article.
        Article.objects.create(
            slug="what-is-faith", language="sw", h1="Imani Ni Nini?",
            body_html=BODY, is_published=True,
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        card = self.client.get(reverse("article-list"), {"language": "sw"})
        self.assertEqual([a["source_type"] for a in card.data], ["ai_unreviewed"])
        detail = self.client.get(
            reverse("article-detail", args=["what-is-faith"]), {"language": "sw"}
        )
        self.assertEqual(detail.data["source_type"], "ai_unreviewed")
        # The English original carries the neutral value — no badge.
        en = self.client.get(
            reverse("article-detail", args=["what-is-faith"]), {"language": "en"}
        )
        self.assertEqual(en.data["source_type"], "public_domain")

    def test_detail_annotates_scripture_references(self):
        # The body's Bible references are wrapped as tappable spans on read (the
        # same treatment chapters/sermons get), so the reader's scripture popover
        # works in articles. The stored fixture body stays span-free.
        Article.objects.create(
            slug="with-a-verse",
            language="en",
            h1="With a verse",
            body_html="<p>As Paul wrote, John 3:16 is the heart of it.</p>",
            is_published=True,
        )
        res = self.client.get(
            reverse("article-detail", args=["with-a-verse"]), {"language": "en"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(
            '<a class="scripture-ref" data-ref="John 3:16">John 3:16</a>',
            res.data["body_html"],
        )

    def test_detail_builds_toc_and_injects_matching_heading_ids(self):
        # Each <h2> gets a stable, unique id, and toc lists the same ids — the
        # page's jump links and the anchors in the body come from one pass, so
        # they cannot drift. Repeated headings are de-duped with a suffix.
        Article.objects.create(
            slug="with-headings",
            language="en",
            h1="With headings",
            body_html=(
                "<h2>First section</h2><p>a</p>"
                "<h2>Second <em>section</em></h2><p>b</p>"
                "<h2>First section</h2><p>c</p>"
            ),
            is_published=True,
        )
        res = self.client.get(
            reverse("article-detail", args=["with-headings"]), {"language": "en"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data["toc"],
            [
                {"id": "first-section", "text": "First section"},
                {"id": "second-section", "text": "Second section"},
                {"id": "first-section-2", "text": "First section"},
            ],
        )
        # Every toc id resolves to a heading anchor actually present in the body.
        for entry in res.data["toc"]:
            self.assertIn(f'<h2 id="{entry["id"]}">', res.data["body_html"])

    def test_detail_heading_ids_stay_unique_across_slug_collisions(self):
        # A suffixed id must not collide with the slug of a differently-worded
        # heading: 'Section' + 'Section 2' + 'Section' must not both resolve to
        # 'section-2', or the toc carries a duplicate key and the keyed {#each}
        # on the page fails. Uniqueness is checked against all assigned ids.
        Article.objects.create(
            slug="colliding-headings",
            language="en",
            h1="Colliding headings",
            body_html="<h2>Section</h2><p>a</p><h2>Section 2</h2><p>b</p><h2>Section</h2><p>c</p>",
            is_published=True,
        )
        res = self.client.get(
            reverse("article-detail", args=["colliding-headings"]), {"language": "en"}
        )
        self.assertEqual(res.status_code, 200)
        ids = [entry["id"] for entry in res.data["toc"]]
        self.assertEqual(ids, ["section", "section-2", "section-3"])
        self.assertEqual(len(ids), len(set(ids)))  # no duplicate anchor keys

    def test_detail_resolves_related_and_drops_unresolvable(self):
        res = self.client.get(
            reverse("article-detail", args=["how-to-pray-so-god-answers"]),
            {"language": "en"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("body_html", res.data)
        related = res.data["related"]
        # Only the published book and the author survive; the unpublished and
        # missing books are dropped, and order is preserved.
        # A book card carries its cover (url + colour), an author their portrait,
        # so "Read next" renders thumbnails, not bare links (blank here — the
        # test rows set no cover). Order is preserved.
        self.assertEqual(
            related,
            [
                {
                    "type": "book",
                    "slug": "the-life-of-trust",
                    "title": "The Life of Trust",
                    "url": "/books/the-life-of-trust/",
                    "cover_url": "",
                    "cover_color": "",
                },
                {
                    "type": "author",
                    "slug": "george-muller",
                    "title": "George Müller",
                    "url": "/authors/george-muller/",
                    "photo_url": "",
                },
            ],
        )
        self.assertEqual(res.data["available_languages"], ["en", "es"])

    def test_detail_tolerates_malformed_related(self):
        # `related` is a hand-authored JSON field with no schema: a bare slug
        # string, a non-dict, or a non-list must be skipped, not 500 the page.
        Article.objects.create(
            slug="malformed",
            language="en",
            h1="Malformed",
            body_html=BODY,
            related=["the-life-of-trust", {"type": "book", "slug": "the-life-of-trust"}, 7],
            is_published=True,
        )
        res = self.client.get(reverse("article-detail", args=["malformed"]), {"language": "en"})
        self.assertEqual(res.status_code, 200)
        # Only the well-formed entry resolves; the string and the int are dropped.
        self.assertEqual([c["slug"] for c in res.data["related"]], ["the-life-of-trust"])

    def test_detail_hides_unpublished(self):
        res = self.client.get(reverse("article-detail", args=["draft"]), {"language": "en"})
        self.assertEqual(res.status_code, 404)

    def test_detail_404_when_language_missing(self):
        # No English fallback: a slug published only in es must 404 for fr.
        res = self.client.get(
            reverse("article-detail", args=["how-to-pray-so-god-answers"]),
            {"language": "fr"},
        )
        self.assertEqual(res.status_code, 404)


class ArticleTopicLinkageTests(TestCase):
    """The bidirectional funnel: a topic lists its articles, and an article
    lists the topics it belongs to (TopicArticle, both directions)."""

    @classmethod
    def setUpTestData(cls):
        from .models import Topic, TopicArticle

        cls.topic = Topic.objects.create(
            slug="prayer", title="On Prayer", is_published=True
        )
        cls.article = Article.objects.create(
            slug="how-to-pray",
            language="en",
            h1="How to Pray",
            body_html="<p>Prose.</p>",
            is_published=True,
        )
        # An unpublished article and one in another language must not leak onto
        # the topic's English shelf.
        Article.objects.create(
            slug="draft", language="en", h1="Draft", body_html="<p>x</p>",
            is_published=False,
        )
        TopicArticle.objects.create(topic=cls.topic, article_slug="how-to-pray")
        TopicArticle.objects.create(topic=cls.topic, article_slug="draft")

    def setUp(self):
        self.client = APIClient()

    def test_topic_detail_lists_its_published_articles(self):
        res = self.client.get(reverse("topic-detail", args=["prayer"]), {"language": "en"})
        self.assertEqual(res.status_code, 200)
        slugs = [a["slug"] for a in res.data["articles"]]
        self.assertEqual(slugs, ["how-to-pray"])  # unpublished draft excluded

    def test_article_detail_lists_its_topic_chips(self):
        res = self.client.get(reverse("article-detail", args=["how-to-pray"]), {"language": "en"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data["topics"], [{"slug": "prayer", "title": "On Prayer"}]
        )

    def test_list_cards_carry_topic_chips_for_the_index_tabs(self):
        # The index builds its filter tabs from each card's topics, so the LIST
        # endpoint must carry them too (batched, not just on detail). A tagged
        # article gets its chip; an untagged one gets an empty list, never absent.
        Article.objects.create(
            slug="untagged", language="en", h1="Untagged",
            body_html="<p>x</p>", is_published=True,
        )
        res = self.client.get(reverse("article-list"), {"language": "en"})
        self.assertEqual(res.status_code, 200)
        by_slug = {a["slug"]: a for a in res.data}
        self.assertEqual(
            by_slug["how-to-pray"]["topics"],
            [{"slug": "prayer", "title": "On Prayer"}],
        )
        self.assertEqual(by_slug["untagged"]["topics"], [])

    def test_list_topic_queries_do_not_grow_with_the_shelf(self):
        # The map is built once per shelf (mirrors book_topic_map), so the query
        # count must be CONSTANT however many articles are on the index — no N+1.
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from .models import TopicArticle

        with CaptureQueriesContext(connection) as small:
            self.client.get(reverse("article-list"), {"language": "en"})

        for i in range(10):
            a = Article.objects.create(
                slug=f"extra-{i}", language="en", h1=f"Extra {i}",
                body_html="<p>x</p>", is_published=True,
            )
            TopicArticle.objects.create(topic=self.topic, article_slug=a.slug)

        with CaptureQueriesContext(connection) as large:
            self.client.get(reverse("article-list"), {"language": "en"})

        self.assertEqual(len(small), len(large))
