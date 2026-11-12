"""The time picker's read: `/api/library/fit/` (library/time_fit.py)."""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Sermon
from .time_fit import parse_reading

URL = reverse("time-fit")


def words(n: int) -> str:
    return "<p>" + " ".join(["grace"] * n) + "</p>"


class TimeFitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="cs", name="C. H. Spurgeon")
        for slug, n in (("short", 500), ("mid", 2500), ("long", 9000)):
            Sermon.objects.create(
                author=cls.author,
                slug=slug,
                language="en",
                title=slug.title(),
                body_html=words(n),
                is_published=True,
            )
        Sermon.objects.create(
            author=cls.author,
            slug="hidden",
            language="en",
            title="Hidden",
            body_html=words(2500),
            is_published=False,
        )
        Sermon.objects.create(
            author=cls.author,
            slug="mid",
            language="es",
            title="Medio",
            body_html=words(2500),
            is_published=True,
        )
        # A well-known book (featured first) and one the reader is in.
        cls.known = Book.objects.create(
            author=cls.author,
            slug="all-of-grace",
            language="en",
            title="All of Grace",
            sort_order=1,
        )
        for order, n in ((1, 2800), (2, 600), (3, 3000), (9, 2900)):
            Chapter.objects.create(
                book=cls.known, order=order, title=f"Known {order}", body_html=words(n)
            )
        cls.reading = Book.objects.create(
            author=cls.author,
            slug="morning-thoughts",
            language="en",
            title="Thoughts",
            sort_order=50,
        )
        for order, n in ((1, 4000), (2, 9000), (3, 1200)):
            Chapter.objects.create(
                book=cls.reading,
                order=order,
                title=f"Reading {order}",
                body_html=words(n),
            )
        teens = Book.objects.create(
            author=cls.author,
            slug="all-of-grace-teens",
            language="en",
            title="All of Grace (For Teens)",
            sort_order=0,
        )
        Chapter.objects.create(
            book=teens, order=1, title="Teens 1", body_html=words(2800)
        )

    def setUp(self):
        self.client = APIClient()

    def get(self, **params):
        res = self.client.get(URL, {"language": "en", **params})
        self.assertEqual(res.status_code, 200)
        return res.json()

    def test_sermon_in_the_window(self):
        body = self.get(min_words=1500, max_words=3000)
        self.assertEqual(body["sermon"]["slug"], "mid")
        self.assertEqual(body["sermon"]["author"]["slug"], "cs")
        self.assertNotIn("body_html", body["sermon"])

    def test_nearest_shorter_sermon_when_none_fit(self):
        # Nothing in 1000–1400, so the longest under the top: "short".
        self.assertEqual(
            self.get(min_words=1000, max_words=1400)["sermon"]["slug"], "short"
        )

    def test_nothing_short_enough(self):
        body = self.get(min_words=50, max_words=100)
        self.assertIsNone(body["sermon"])
        self.assertIsNone(body["chapter"])

    def test_language_and_publication(self):
        res = self.client.get(
            URL, {"language": "es", "min_words": 1500, "max_words": 3000}
        )
        self.assertEqual(res.json()["sermon"]["title"], "Medio")
        # The unpublished English one never shows, whatever the seed.
        for seed in range(4):
            self.assertEqual(
                self.get(min_words=1500, max_words=3000, seed=seed)["sermon"]["slug"],
                "mid",
            )

    def test_opening_chapter_of_a_known_book(self):
        ch = self.get(min_words=1500, max_words=3000)["chapter"]
        # Chapter 9 fits too, but a newcomer starts near the beginning; the
        # teens edition is never the "well-known book".
        self.assertEqual((ch["book"]["slug"], ch["order"]), ("all-of-grace", 1))
        self.assertFalse(ch["continuing"])
        self.assertEqual(ch["book"]["author"]["name"], "C. H. Spurgeon")
        self.assertIn("cover_url", ch["book"])

    def test_front_matter_is_not_where_to_start(self):
        Chapter.objects.filter(book=self.known, order=1).update(title="Preface")
        ch = self.get(min_words=1500, max_words=3000)["chapter"]
        self.assertEqual((ch["book"]["slug"], ch["order"]), ("all-of-grace", 3))

    def test_continues_the_book_in_progress(self):
        ch = self.get(min_words=1500, max_words=3000, reading="morning-thoughts:3")[
            "chapter"
        ]
        self.assertEqual(
            (ch["book"]["slug"], ch["order"], ch["continuing"]),
            ("morning-thoughts", 3, True),
        )

    def test_continuing_takes_the_next_chapter_when_the_current_runs_long(self):
        # Chapter 2 (9000 words) is too long; chapter 3 is next and fits.
        ch = self.get(min_words=1500, max_words=3000, reading="morning-thoughts:2")[
            "chapter"
        ]
        self.assertEqual((ch["order"], ch["continuing"]), (3, True))

    def test_in_progress_book_that_does_not_fit_falls_back(self):
        ch = self.get(min_words=200, max_words=700, reading="morning-thoughts:1")[
            "chapter"
        ]
        self.assertEqual(
            (ch["book"]["slug"], ch["order"], ch["continuing"]),
            ("all-of-grace", 2, False),
        )

    def test_junk_parameters_do_not_500(self):
        res = self.client.get(
            URL,
            {
                "max_words": "lots",
                "min_words": "-4",
                "seed": "x",
                "reading": "<b>:1,a:b,::",
            },
        )
        self.assertEqual(res.status_code, 200)

    def test_parse_reading(self):
        self.assertEqual(
            parse_reading("a:1, b-2:14 ,bad,c:0,D:2"), [("a", 1), ("b-2", 14)]
        )
        self.assertEqual(len(parse_reading(",".join(f"s{n}:1" for n in range(10)))), 3)
