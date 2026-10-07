"""`/api/library/audiences/<audience>/` — the /young-readers/ and /teens/ hubs.

Pinned here: each book appears once (series, then retold editions, then the
curated topic's remainder); a suffix alone does not make a retelling (the full
text must exist); a plan is offered only when every book it reads is the hub's;
nothing falls back to English; and an unknown audience is a 404.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.test import TestCase

from common.testing import body_of

from .book_people_seed import BOOK_PEOPLE
from .models import (
    Author,
    Book,
    BookPerson,
    Chapter,
    Plan,
    PlanDay,
    Series,
    SeriesTranslation,
    Topic,
    TopicBook,
    TopicTranslation,
)
from .serializers import AUDIENCE_EDITION_SUFFIX, EDITION_SUFFIXES
from .views import AUDIENCE_STARTS, AUDIENCE_TOPICS


class AudienceShelfTests(TestCase):
    URL = "/api/library/audiences/{}/?language={}"

    def setUp(self):
        self.author = Author.objects.create(slug="bunyan", name="John Bunyan")
        self.series = Series.objects.create(
            slug="brave-for-god", title="Brave for God", audience="young_readers",
            min_age=8, max_age=12,
        )
        self.topic = Topic.objects.create(slug="for-young-readers", title="For Young Readers")

    def _book(self, slug, *, language="en", series=None, published=True):
        return Book.objects.create(
            author=self.author, slug=slug, language=language, title=slug,
            series=series, is_published=published,
        )

    def _get(self, audience="young_readers", language="en"):
        response = self.client.get(self.URL.format(audience, language))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def _slugs(self, rows):
        return [r["slug"] for r in rows]

    def test_each_book_is_claimed_once_series_then_editions_then_topic(self):
        self._book("bfg-1", series=self.series)
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        self._book("north-wind")
        for slug in ("bfg-1", "pilgrims-progress-children", "north-wind"):
            TopicBook.objects.create(topic=self.topic, book_slug=slug)
        data = self._get()
        self.assertEqual(self._slugs(data["series"]), ["brave-for-god"])
        self.assertEqual(self._slugs(data["editions"]), ["pilgrims-progress-children"])
        self.assertEqual(self._slugs(data["more"]), ["north-wind"])
        self.assertEqual(data["topic"], {"slug": "for-young-readers", "title": "For Young Readers"})

    def test_a_suffix_alone_is_not_a_retelling(self):
        # Watts's Divine Songs for Children is an original: no "divine-songs-for".
        self._book("divine-songs-for-children")
        TopicBook.objects.create(topic=self.topic, book_slug="divine-songs-for-children")
        data = self._get()
        self.assertEqual(data["editions"], [])
        self.assertEqual(self._slugs(data["more"]), ["divine-songs-for-children"])

    def test_teens_gather_teen_editions_not_childrens(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        self._book("pilgrims-progress-teens")
        data = self._get("teens")
        self.assertEqual(self._slugs(data["editions"]), ["pilgrims-progress-teens"])
        self.assertEqual(data["series"], [])
        self.assertIsNone(data["topic"])  # no for-teens topic in this DB

    def test_a_plan_shows_only_when_it_reads_nothing_but_the_hubs_books(self):
        self._book("bfg-1", series=self.series)
        self._book("all-of-grace")
        kids = Plan.objects.create(slug="brave-24", language="en", title="Brave 24")
        PlanDay.objects.create(plan=kids, day=1, book_slug="bfg-1", chapter_order=1)
        mixed = Plan.objects.create(slug="mixed", language="en", title="Mixed")
        PlanDay.objects.create(plan=mixed, day=1, book_slug="bfg-1", chapter_order=1)
        PlanDay.objects.create(plan=mixed, day=2, book_slug="all-of-grace", chapter_order=1)
        self.assertEqual(self._slugs(self._get()["plans"]), ["brave-24"])

    def test_no_english_fallback(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        TopicBook.objects.create(topic=self.topic, book_slug="pilgrims-progress-children")
        data = self._get(language="sw")
        self.assertEqual(
            [data[k] for k in ("series", "editions", "more", "plans")], [[], [], [], []]
        )
        # The topic has no Swahili title, so the page links to no shelf.
        self.assertIsNone(data["topic"])

    def test_unpublished_books_are_left_out(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children", published=False)
        self.assertEqual(self._get()["editions"], [])

    def test_printable_names_the_export_editions_only(self):
        self._book("brave-for-god", series=self.series)  # in the export pilot
        self._book("north-wind")
        self._book("north-wind-children")  # not in it
        self.assertEqual(self._get()["printable"], ["brave-for-god"])

    def test_an_unknown_audience_is_not_found(self):
        self.assertEqual(self.client.get(self.URL.format("adults", "en")).status_code, 404)

    def test_languages_name_every_language_with_something_to_show(self):
        self._book("bfg-1", series=self.series)  # en: a named series
        self._book("bfg-1", language="sw", series=self.series)  # sw: series unnamed there
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children", language="am")  # am: a retelling
        self._book("north-wind", language="lg")  # lg: a topic book, topic titled there
        self._book("north-wind", language="hi")  # hi: topic untitled there
        TopicBook.objects.create(topic=self.topic, book_slug="north-wind")
        TopicTranslation.objects.create(topic=self.topic, language="lg", title="Abaana")
        self.assertEqual(self._get()["languages"], ["am", "en", "lg"])

    def test_modern_english_is_never_a_language(self):
        self._book("north-wind")
        self._book("north-wind", language="en-modern")
        TopicBook.objects.create(topic=self.topic, book_slug="north-wind")
        self.assertEqual(self._get()["languages"], ["en"])

    def test_the_languages_index_answers_for_both_hubs_at_once(self):
        self._book("bfg-1", series=self.series)
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-teens", language="am")
        response = self.client.get("/api/library/audiences/")
        self.assertEqual(response.json(), {"young_readers": ["en"], "teens": ["am"]})

    def test_each_hub_audience_has_an_edition_suffix_of_the_convention(self):
        self.assertEqual(set(AUDIENCE_EDITION_SUFFIX.values()), set(EDITION_SUFFIXES))
        self.assertEqual(set(AUDIENCE_EDITION_SUFFIX), set(AUDIENCE_TOPICS))

    def test_start_is_the_first_preferred_book_the_hub_holds_else_its_first(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        self._book("north-wind")
        TopicBook.objects.create(topic=self.topic, book_slug="north-wind")
        self.assertEqual(self._get()["start"], "pilgrims-progress-children")
        Book.objects.filter(slug="pilgrims-progress-children").update(is_published=False)
        self.assertEqual(self._get()["start"], "north-wind")
        self.assertIsNone(self._get("teens")["start"])

    def test_every_start_pick_names_a_real_book(self):
        # A renamed or retired slug would fall through to the hub's first book
        # in silence. Checked against the fixture, so a content PR trips it.
        books = Path(__file__).parent / "fixtures" / "content" / "books"
        missing = [
            slug
            for picks in AUDIENCE_STARTS.values()
            for slug in picks
            if not (books / f"{slug}.en.json").exists()
        ]
        self.assertEqual(missing, [])

    def _story(self, book, order, title, person, *, words=90):
        Chapter.objects.create(book=book, order=order, title=title, body_html=body_of(words))
        if person is not None:
            BookPerson.objects.get_or_create(
                book_slug=book.slug, person=person,
                defaults={"role": "subject", "chapter": order},
            )

    def test_people_are_the_series_stories_in_reading_order(self):
        crowther = Author.objects.create(slug="samuel-ajayi-crowther", name="Samuel Ajayi Crowther")
        carey = Author.objects.create(slug="william-carey", name="William Carey", photo_url="/c.jpg")
        jim = Author.objects.create(slug="jim-elliot", name="Jim Elliot")
        betty = Author.objects.create(slug="elisabeth-elliot", name="Elisabeth Elliot")
        two = self._book("bfg-2", series=self.series)
        Book.objects.filter(pk=two.pk).update(series_position=2)
        one = self._book("bfg-1", series=self.series)
        Book.objects.filter(pk=one.pk).update(series_position=1)
        self._story(two, 1, "William Carey: The Cobbler Who Would Not Give Up", carey, words=120)
        self._story(two, 2, "Jim and Elisabeth Elliot: The Ones Who Went Back", jim)
        BookPerson.objects.create(
            book_slug="bfg-2", person=betty, role="subject", chapter=2, sort_order=1
        )
        self._story(one, 1, "Samuel Crowther: The Boy from the Slave Ship", crowther)
        people = self._get()["people"]
        self.assertEqual(
            [(p["book"], p["chapter"], p["name"], p["hook"]) for p in people],
            [
                ("bfg-1", 1, "Samuel Crowther", "The Boy from the Slave Ship"),
                ("bfg-2", 1, "William Carey", "The Cobbler Who Would Not Give Up"),
                # Two subjects, one chapter: one face, the first person's.
                ("bfg-2", 2, "Jim and Elisabeth Elliot", "The Ones Who Went Back"),
            ],
        )
        self.assertEqual(people[1]["slug"], "william-carey")
        self.assertEqual(people[1]["photo_url"], "/c.jpg")
        self.assertEqual(people[1]["words"], 120)
        self.assertEqual(people[2]["slug"], "jim-elliot")

    def test_people_follow_the_language_and_its_script(self):
        crowther = Author.objects.create(slug="samuel-ajayi-crowther", name="Samuel Ajayi Crowther")
        en = self._book("bfg-1", series=self.series)
        am = self._book("bfg-1", language="am", series=self.series)
        SeriesTranslation.objects.create(series=self.series, language="am", title="ለእግዚአብሔር ደፋር")
        self._story(en, 1, "Samuel Crowther: The Boy from the Slave Ship", crowther)
        Chapter.objects.create(book=am, order=1, title="ሳሙኤል ክራውዘር፦ ከባሪያ መርከብ የወጣው ልጅ",
                               body_html="<p>x</p>")
        [person] = self._get(language="am")["people"]
        self.assertEqual((person["name"], person["hook"]), ("ሳሙኤል ክራውዘር", "ከባሪያ መርከብ የወጣው ልጅ"))
        # No English fallback: a language without the book has no faces.
        self.assertEqual(self._get(language="sw")["people"], [])

    def test_a_title_without_a_name_falls_back_to_the_person(self):
        crowther = Author.objects.create(slug="samuel-ajayi-crowther", name="Samuel Ajayi Crowther")
        book = self._book("bfg-1", series=self.series)
        self._story(book, 1, "The Boy from the Slave Ship", crowther)
        [person] = self._get()["people"]
        self.assertEqual((person["name"], person["hook"]),
                         ("Samuel Ajayi Crowther", "The Boy from the Slave Ship"))

    def test_only_chapter_stories_in_the_hubs_series_are_faces(self):
        crowther = Author.objects.create(slug="samuel-ajayi-crowther", name="Samuel Ajayi Crowther")
        book = self._book("bfg-1", series=self.series)
        Chapter.objects.create(book=book, order=1, title="Samuel Crowther: A", body_html="<p>x</p>")
        # Mentioned, with no chapter of their own: not a face.
        BookPerson.objects.create(book_slug="bfg-1", person=crowther, role="mentioned")
        # A story in a book outside every hub series: not a face either.
        loose = self._book("men-who-moved-heaven")
        self._story(loose, 1, "Samuel Crowther: B", Author.objects.create(slug="x", name="X"))
        self.assertEqual(self._get()["people"], [])

    def test_every_story_chapter_in_the_seed_is_a_real_chapter(self):
        # The seed names chapters by number; a re-cut anthology would point a
        # face at the wrong life. Checked against the English fixture.
        books = Path(__file__).parent / "fixtures" / "content" / "books"
        surname = {
            a["fields"]["slug"]: a["fields"]["name"].split()[-1].replace("'", "’")
            for a in json.loads((books.parent / "authors.json").read_text())
        }
        wrong = []
        for slug, members in BOOK_PEOPLE:
            stories = [m for m in members if len(m) == 3]
            if not stories:
                continue
            rows = json.loads((books / f"{slug}.en.json").read_text())
            titles = {r["fields"]["order"]: r["fields"]["title"] for r in rows[1:]}
            for person, _role, chapter in stories:
                if surname[person] not in titles.get(chapter, ""):
                    wrong.append((slug, person, chapter))
        self.assertEqual(wrong, [])


class BookAgesTests(TestCase):
    """The book page's "Ages 8–12" (`serializers.book_ages`)."""

    def setUp(self):
        self.author = Author.objects.create(slug="bunyan", name="John Bunyan")

    def _ages(self, slug, *, series=None):
        Book.objects.create(
            author=self.author, slug=slug, language="en", title=slug, series=series,
            is_published=True,
        )
        response = self.client.get(f"/api/library/books/{slug}/?language=en")
        self.assertEqual(response.status_code, 200)
        return response.json()["ages"]

    def test_a_series_range_wins(self):
        series = Series.objects.create(
            slug="rooted", title="Rooted", audience="young_readers", min_age=9, max_age=12
        )
        self.assertEqual(self._ages("rooted-1", series=series), {"min_age": 9, "max_age": 12})

    def test_a_series_without_a_range_has_none_never_guessed(self):
        series = Series.objects.create(slug="straight-talk", title="Straight Talk", audience="teens")
        self.assertIsNone(self._ages("straight-talk-teens", series=series))

    def test_a_retold_edition_reads_its_audiences(self):
        Book.objects.create(author=self.author, slug="pilgrims-progress", title="PP", language="sw")
        self.assertEqual(self._ages("pilgrims-progress-children"), {"min_age": 8, "max_age": 12})

    def test_a_suffix_alone_and_everything_else_have_no_ages(self):
        self.assertIsNone(self._ages("divine-songs-for-children"))
        self.assertIsNone(self._ages("all-of-grace"))
        adults = Series.objects.create(slug="key-teachings", title="KT", audience="adults")
        self.assertIsNone(self._ages("kt-1", series=adults))
