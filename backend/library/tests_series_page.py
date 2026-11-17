"""The series page's second round (2026-11): what it reads from inside its
books (``library/series_page.py``) and what the API sends for it.

Pinned here: a plate is a self-hosted PORTRAIT picture (the opening map is
not), at most ``PLATES_PER_BOOK`` from a book; a daily chapter splits into
verse, teaching, prompts and prayer by structure, so a translated day splits
too; Book 1's Q&A, the volumes' chapter lists and downloads, and the daily
block ride the page; the /series index carries each card's tagline and art.
"""

from __future__ import annotations

from django.test import TestCase

from .models import Author, Book, Chapter, Series
from .series_page import PLATES_PER_BOOK, _first_plate, sample_day, series_plates

DAY = (
    "<blockquote><p>“Do not fear, for I am with you.”</p><p>— Isaiah 41:10 (BSB)</p></blockquote>"
    "<p>Lots of girls think being brave means never feeling scared.</p>"
    "<p>But God says something else.</p>"
    "<p><strong>Think about it:</strong> What makes you afraid?</p>"
    "<p><strong>Try this:</strong> Write the verse on a card.</p>"
    "<p><em>Dear God, thank You that I don’t have to be fearless. Amen.</em></p>"
)

DIA = (
    "<blockquote><p>«No temas, porque yo estoy contigo».</p><p>— Isaías 41:10</p></blockquote>"
    "<p>Muchas chicas piensan que ser valiente es no tener miedo.</p>"
    "<p><strong>Piénsalo:</strong> ¿Qué te da miedo?</p>"
    "<p><em>Querido Dios, gracias. Amén.</em></p>"
)


def _img(src, width, height, alt="A plate"):
    return f'<img src="{src}" alt="{alt}" width="{width}" height="{height}">'


class SampleDayTests(TestCase):
    def test_a_day_splits_into_its_parts(self):
        self.assertEqual(
            sample_day(DAY),
            {
                "verse": {"text": "“Do not fear, for I am with you.”", "ref": "Isaiah 41:10 (BSB)"},
                "teaching": "Lots of girls think being brave means never feeling scared.",
                "prompts": [
                    {"label": "Think about it", "text": "What makes you afraid?"},
                    {"label": "Try this", "text": "Write the verse on a card."},
                ],
                "prayer": "Dear God, thank You that I don’t have to be fearless. Amen.",
            },
        )

    def test_a_translated_day_splits_by_structure_and_keeps_its_words(self):
        day = sample_day(DIA)
        self.assertEqual(day["verse"]["ref"], "Isaías 41:10")
        self.assertEqual(day["prompts"], [{"label": "Piénsalo", "text": "¿Qué te da miedo?"}])
        self.assertEqual(day["prayer"], "Querido Dios, gracias. Amén.")

    def test_a_chapter_not_shaped_like_a_day_is_none(self):
        self.assertIsNone(sample_day("<p>An introduction, all prose.</p>"))
        # A verse and teaching but no prayer is not a whole day.
        self.assertIsNone(sample_day(DAY.rsplit("<p><em>", 1)[0]))
        self.assertIsNone(sample_day(""))


class PlateTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        self.series = Series.objects.create(slug="lamps", title="Lamps")

    def test_the_first_portrait_self_hosted_picture_is_the_plate(self):
        window = (
            _img("/illustrations/b/map.jpg", 1600, 900, "The map")
            + _img("https://example.com/p.jpg", 600, 900)
            + _img("/illustrations/b/plate-01-the-lamp.jpg", 600, 800, "Wren &amp; the lamp")
        )
        self.assertEqual(
            _first_plate(window), {"src": "/illustrations/b/plate-01-the-lamp.jpg", "alt": "Wren & the lamp"}
        )
        self.assertIsNone(_first_plate(_img("/illustrations/b/map.jpg", 1600, 900)))

    def test_plates_walk_the_series_a_few_per_book(self):
        books = []
        for pos in (1, 2):
            book = Book.objects.create(
                author=self.author, slug=f"lamps-{pos}", title=f"Lamps {pos}",
                series=self.series, series_position=pos,
            )
            books.append(book)
            for order in range(1, PLATES_PER_BOOK + 3):
                body = "<p>Text.</p>" if order == 1 else _img(f"/illustrations/{pos}/plate-{order}.jpg", 600, 800)
                Chapter.objects.create(book=book, order=order, title=f"Ch {order}", body_html=body)
        plates = series_plates(books)
        self.assertEqual(len(plates), 2 * PLATES_PER_BOOK)
        self.assertEqual(
            plates[0],
            {"src": "/illustrations/1/plate-2.jpg", "alt": "A plate", "book": "lamps-1", "order": 2, "chapter": "Ch 2"},
        )
        self.assertEqual(plates[PLATES_PER_BOOK]["book"], "lamps-2")
        self.assertEqual(series_plates([]), [])


class SeriesPageApiTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(slug="ochorus-originals", name="Ochorus")
        self.series = Series.objects.create(
            slug="daughters", title="Daughters", days_per_book=30,
            tagline="Thirty days at a time.", hero_image="/covers/art/d.webp", hero_tone=Series.HeroTone.LIGHT,
        )
        self.one = Book.objects.create(
            author=self.author, slug="daughters-1", title="Daughters 1", series=self.series,
            series_position=1, qa=[{"question": "Who is it for?", "answer": "Girls 8–12."},
                                   {"question": "How long is a day?", "answer": "Ten minutes."}],
        )
        Book.objects.create(
            author=self.author, slug="daughters-2", title="Daughters 2", series=self.series, series_position=2,
        )
        Chapter.objects.create(book=self.one, order=1, title="Introduction", body_html="<p>Welcome.</p>")
        Chapter.objects.create(book=self.one, order=2, title="Brave, Not Fearless", body_html=DAY)

    def _get(self, slug="daughters"):
        return self.client.get(f"/api/library/series/{slug}/?language=en", HTTP_HOST="localhost").json()

    def test_book_ones_questions_ride_the_page(self):
        self.assertEqual([q["question"] for q in self._get()["qa"]], ["Who is it for?", "How long is a day?"])

    def test_volumes_carry_their_chapter_list_and_downloads(self):
        one, two = self._get()["books"]
        self.assertEqual(one["toc"], ["Introduction", "Brave, Not Fearless"])
        self.assertEqual(two["toc"], [])
        for book in (one, two):
            self.assertIn("pdf_url", book)
            self.assertIn("epub_url", book)

    def test_a_daily_series_sends_its_days_and_a_sample_day(self):
        daily = self._get()["daily"]
        self.assertEqual(daily["days"], 30)
        sample = daily["sample"]
        self.assertEqual((sample["title"], sample["order"]), ("Brave, Not Fearless", 2))
        self.assertEqual(sample["verse"]["ref"], "Isaiah 41:10 (BSB)")
        self.assertEqual(len(sample["prompts"]), 2)

    def test_a_series_without_days_or_pictures_sends_neither(self):
        plain = Series.objects.create(slug="plain", title="Plain")
        Book.objects.create(author=self.author, slug="p-1", title="P", series=plain, series_position=1)
        body = self._get("plain")
        self.assertEqual((body["daily"], body["plates"], body["qa"]), (None, [], []))

    def test_the_index_card_carries_tagline_and_art(self):
        rows = self.client.get("/api/library/series/?language=en", HTTP_HOST="localhost").json()
        row = next(r for r in rows if r["slug"] == "daughters")
        self.assertEqual(row["tagline"], "Thirty days at a time.")
        self.assertEqual(row["hero"], {"image": "/covers/art/d.webp", "tone": "light"})
