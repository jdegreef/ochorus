"""`series_block` — the book page's "Book 2 of 6 in Rooted" line and the last
chapter's "next in series", from `Book.series` / `series_position`.

Pinned here: the no-English-fallback rule (an unnamed series shows nothing),
that "of N" counts the SERIES' volume numbers rather than this language's rows,
that previous/next skip a volume this language lacks, and that a collection
(no positions) has no previous or next at all.
"""

from __future__ import annotations

from django.test import TestCase

from .models import Author, Book, Series, SeriesTranslation
from .serializers import BookDetailSerializer, series_block


class SeriesBlockTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        self.series = Series.objects.create(slug="brave-for-god", title="Brave for God")

    def _book(self, slug, position, *, language="en", published=True, series=None):
        return Book.objects.create(
            author=self.author, slug=slug, language=language, title=f"{slug} [{language}]",
            series=series or self.series, series_position=position,
            is_published=published,
        )

    def test_a_middle_volume_knows_its_neighbours_and_the_total(self):
        self._book("bfg-1", 1)
        two = self._book("bfg-2", 2)
        self._book("bfg-3", 3)
        self.assertEqual(
            series_block(two),
            {
                "slug": "brave-for-god",
                "title": "Brave for God",
                "position": 2,
                "total": 3,
                "previous": {"slug": "bfg-1", "title": "bfg-1 [en]"},
                "next": {"slug": "bfg-3", "title": "bfg-3 [en]"},
            },
        )

    def test_the_last_volume_has_no_next(self):
        self._book("bfg-1", 1)
        last = self._book("bfg-2", 2)
        self.assertIsNone(series_block(last)["next"])

    def test_no_series_is_no_block(self):
        book = Book.objects.create(author=self.author, slug="solo", title="Solo")
        self.assertIsNone(series_block(book))

    def test_an_unnamed_series_shows_nothing_in_that_language(self):
        # No English fallback: a Swahili reader is not shown an English name.
        sw = self._book("bfg-1", 1, language="sw")
        self.assertIsNone(series_block(sw))
        SeriesTranslation.objects.create(
            series=self.series, language="sw", title="Jasiri kwa ajili ya Mungu"
        )
        self.assertEqual(series_block(sw)["title"], "Jasiri kwa ajili ya Mungu")

    def test_next_skips_a_volume_this_language_lacks_but_the_total_does_not(self):
        SeriesTranslation.objects.create(series=self.series, language="lg", title="Abavumu")
        for n in (1, 2, 3):
            self._book(f"bfg-{n}", n)
        one = self._book("bfg-1", 1, language="lg")
        self._book("bfg-3", 3, language="lg")  # no Luganda volume 2 yet
        block = series_block(one)
        self.assertEqual(block["next"], {"slug": "bfg-3", "title": "bfg-3 [lg]"})
        self.assertEqual(block["total"], 3)

    def test_unpublished_volumes_are_neither_linked_nor_counted(self):
        one = self._book("bfg-1", 1)
        self._book("bfg-2", 2, published=False)
        block = series_block(one)
        self.assertIsNone(block["next"])
        self.assertEqual(block["total"], 1)

    def test_a_collection_counts_its_books_and_has_no_order(self):
        collection = Series.objects.create(slug="key-teachings", title="The Key Teachings")
        nee = self._book("kt-nee", None, series=collection)
        self._book("kt-baxter", None, series=collection)
        block = series_block(nee)
        self.assertEqual(
            (block["position"], block["total"], block["previous"], block["next"]),
            (None, 2, None, None),
        )

    def test_the_detail_payload_carries_it(self):
        book = self._book("bfg-1", 1)
        self.assertEqual(BookDetailSerializer(book).data["series"]["position"], 1)


class SeriesViewTests(TestCase):
    """`/api/library/series/` and `/api/library/series/<slug>/` — the series page."""

    def setUp(self):
        self.author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        self.series = Series.objects.create(
            slug="brave-for-god", title="Brave for God", description="True stories."
        )

    def _book(self, slug, position, *, language="en", published=True, series=None):
        return Book.objects.create(
            author=self.author, slug=slug, language=language, title=f"{slug} [{language}]",
            series=series or self.series, series_position=position,
            is_published=published,
        )

    def _get(self, path, language="en"):
        return self.client.get(f"/api/library/{path}?language={language}", HTTP_HOST="localhost")

    def test_the_page_lists_its_books_in_volume_order(self):
        for n in (3, 1, 2):
            self._book(f"bfg-{n}", n)
        body = self._get("series/brave-for-god/").json()
        self.assertEqual([b["slug"] for b in body["books"]], ["bfg-1", "bfg-2", "bfg-3"])
        self.assertEqual(
            (body["title"], body["description"], body["ordered"], body["available_languages"]),
            ("Brave for God", "True stories.", True, ["en"]),
        )
        self.assertEqual(body["books"][0]["series_position"], 1)

    def test_a_language_without_a_name_or_a_book_has_no_page(self):
        self._book("bfg-1", 1)
        self._book("bfg-1", 1, language="sw")
        self.assertEqual(self._get("series/brave-for-god/", "sw").status_code, 404)  # no name
        SeriesTranslation.objects.create(series=self.series, language="lg", title="Abavumu")
        self.assertEqual(self._get("series/brave-for-god/", "lg").status_code, 404)  # no book
        SeriesTranslation.objects.create(series=self.series, language="sw", title="Jasiri")
        sw = self._get("series/brave-for-god/", "sw").json()
        self.assertEqual((sw["title"], sw["description"]), ("Jasiri", ""))
        # hreflang: only where the page exists — sw now, lg still not.
        self.assertEqual(sw["available_languages"], ["en", "sw"])

    def test_unpublished_books_are_left_out(self):
        self._book("bfg-1", 1)
        self._book("bfg-2", 2, published=False)
        body = self._get("series/brave-for-god/").json()
        self.assertEqual([b["slug"] for b in body["books"]], ["bfg-1"])

    def test_a_collection_is_unordered_and_keeps_the_shelf_order(self):
        kt = Series.objects.create(slug="key-teachings", title="The Key Teachings")
        self._book("kt-nee", None, series=kt)
        self._book("kt-baxter", None, series=kt)
        body = self._get("series/key-teachings/").json()
        self.assertFalse(body["ordered"])
        self.assertEqual(sorted(b["slug"] for b in body["books"]), ["kt-baxter", "kt-nee"])

    def test_the_list_holds_only_series_with_a_page_in_the_language(self):
        self._book("bfg-1", 1)
        Series.objects.create(slug="empty", title="Empty")
        self.assertEqual(
            [(r["slug"], r["title"], r["book_count"]) for r in self._get("series/").json()],
            [("brave-for-god", "Brave for God", 1)],
        )
        self.assertEqual(self._get("series/", "sw").json(), [])

    def test_the_list_carries_what_a_series_card_draws(self):
        for n in (5, 3, 1, 2, 4):
            self._book(f"bfg-{n}", n)
        self._book("bfg-6", 6, published=False)
        Series.objects.filter(pk=self.series.pk).update(sort_order=20)
        kt = Series.objects.create(slug="key-teachings", title="The Key Teachings", sort_order=10)
        self._book("kt-nee", None, series=kt)
        rows = self._get("series/").json()
        # Series order, not book order: the collection sorts first.
        self.assertEqual([r["slug"] for r in rows], ["key-teachings", "brave-for-god"])
        kt_row, bfg = rows
        self.assertEqual((bfg["description"], bfg["book_count"]), ("True stories.", 5))
        self.assertEqual(bfg["books"], ["bfg-1", "bfg-2", "bfg-3", "bfg-4", "bfg-5"])
        # Untagged: no group, no age line.
        self.assertEqual((bfg["audience"], bfg["min_age"], bfg["max_age"]), ("", None, None))
        # The fan: the first four published volumes, in reading order.
        self.assertEqual([c["slug"] for c in bfg["covers"]], ["bfg-1", "bfg-2", "bfg-3", "bfg-4"])
        self.assertEqual(set(bfg["covers"][0]), {"kind", "slug", "cover_url", "cover_color", "title"})
        self.assertEqual(kt_row["book_count"], 1)
        # Languages with a page: a name AND a published book there.
        self._book("bfg-1", 1, language="sw")
        self._book("bfg-2", 2, language="lg")
        SeriesTranslation.objects.create(series=self.series, language="sw", title="Jasiri")
        bfg = self._get("series/").json()[1]
        self.assertEqual(bfg["languages"], ["en", "sw"])

    def test_the_list_costs_the_same_however_many_series(self):
        self._book("bfg-1", 1)
        for i in range(3):
            s = Series.objects.create(slug=f"s{i}", title=f"S{i}")
            self._book(f"s{i}-1", 1, series=s)
        # The books, the languages they are held in, the series, their
        # translations — and the cache mixin's content-revision read.
        with self.assertNumQueries(5):
            self._get("series/")


class BookCardSeriesTests(TestCase):
    """The card's series line (`BookListSerializer.series`) agrees with
    `series_block`: the same totals, the same no-English-fallback rule."""

    def setUp(self):
        self.author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        self.series = Series.objects.create(slug="brave-for-god", title="Brave for God")

    def _book(self, slug, position, *, language="en", series=None):
        return Book.objects.create(
            author=self.author, slug=slug, language=language, title=f"{slug} [{language}]",
            series=series or self.series, series_position=position, is_published=True,
        )

    def _cards(self, language="en"):
        body = self.client.get(
            f"/api/library/books/?language={language}", HTTP_HOST="localhost"
        ).json()
        return {b["slug"]: b["series"] for b in body}

    def test_an_ordered_volume_counts_the_series_numbers_in_every_language(self):
        self._book("bfg-1", 1)
        self._book("bfg-3", 3)
        self._book("bfg-2", 2, language="sw")  # volume 2 exists, just not in English
        cards = self._cards()
        self.assertEqual(
            cards["bfg-3"], {"slug": "brave-for-god", "title": "Brave for God", "position": 3, "total": 3}
        )
        block = series_block(Book.objects.get(slug="bfg-3", language="en"))
        self.assertEqual(cards["bfg-3"]["total"], block["total"])

    def test_a_collection_counts_this_languages_books(self):
        kt = Series.objects.create(slug="key-teachings", title="The Key Teachings")
        self._book("kt-nee", None, series=kt)
        self._book("kt-baxter", None, series=kt)
        self._book("kt-nee", None, series=kt, language="sw")
        self.assertEqual(self._cards()["kt-nee"]["total"], 2)

    def test_no_series_and_an_unnamed_series_both_carry_none(self):
        Book.objects.create(author=self.author, slug="plain", language="en", title="Plain", is_published=True)
        self._book("bfg-1", 1, language="sw")
        self.assertIsNone(self._cards()["plain"])
        self.assertIsNone(self._cards("sw")["bfg-1"])  # no Swahili name
        SeriesTranslation.objects.create(series=self.series, language="sw", title="Jasiri")
        self.assertEqual(self._cards("sw")["bfg-1"]["title"], "Jasiri")

    def test_the_series_page_cards_skip_the_line_it_would_repeat(self):
        self._book("bfg-1", 1)
        body = self.client.get(
            "/api/library/series/brave-for-god/?language=en", HTTP_HOST="localhost"
        ).json()
        self.assertIsNone(body["books"][0]["series"])


class SeriesAudienceTests(TestCase):
    """The index groups by audience and prints an age range — both from the
    series row, the same in every language."""

    def test_audience_and_ages_reach_the_list_and_the_page(self):
        author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        rooted = Series.objects.create(
            slug="rooted", title="Rooted", audience=Series.Audience.YOUNG_READERS,
            min_age=9, max_age=12,
        )
        Book.objects.create(
            author=author, slug="rooted-1", language="en", title="Rooted 1",
            series=rooted, series_position=1, is_published=True,
        )

        def get(path):
            return self.client.get(
                f"/api/library/{path}?language=en", HTTP_HOST="localhost"
            ).json()

        row = get("series/")[0]
        self.assertEqual((row["audience"], row["min_age"], row["max_age"]), ("young_readers", 9, 12))
        page = get("series/rooted/")
        self.assertEqual((page["audience"], page["min_age"], page["max_age"]), ("young_readers", 9, 12))
