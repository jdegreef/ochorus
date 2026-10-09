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
    Article,
    Author,
    Book,
    BookPerson,
    Chapter,
    Plan,
    PlanDay,
    Quote,
    Series,
    SeriesTranslation,
    Topic,
    TopicArticle,
    TopicBook,
    TopicTranslation,
)
from .serializers import AUDIENCE_EDITION_SUFFIX, EDITION_SUFFIXES
from .views import (
    AUDIENCE_CHALLENGES,
    AUDIENCE_SPOTLIGHTS,
    AUDIENCE_STARTS,
    AUDIENCE_TOPICS,
    split_story_title,
)


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

    def test_cards_carry_the_books_hook(self):
        book = self._book("north-wind")
        book.hook = "A boy, a wind, and the way home."
        book.save()
        TopicBook.objects.create(topic=self.topic, book_slug="north-wind")
        self.assertEqual(self._get()["more"][0]["hook"], "A boy, a wind, and the way home.")

    def test_a_teens_series_of_one_shows_its_book_as_a_card(self):
        solo = Series.objects.create(slug="real-questions", title="Real Questions", audience="teens")
        pair = Series.objects.create(slug="anchored", title="Anchored", audience="teens")
        self._book("real-questions-1", series=solo)
        self._book("anchored-1", series=pair)
        self._book("anchored-2", series=pair)
        self._book("all-of-grace")
        teens = Topic.objects.create(slug="for-teens", title="For Teens")
        for slug in ("all-of-grace", "real-questions-1"):
            TopicBook.objects.create(topic=teens, book_slug=slug)
        data = self._get("teens")
        self.assertEqual(self._slugs(data["series"]), ["anchored"])
        # It leads More to read, ahead of the topic's own order.
        self.assertEqual(self._slugs(data["more"]), ["real-questions-1", "all-of-grace"])

    def test_a_young_readers_series_of_one_stays_a_series(self):
        self._book("bfg-1", series=self.series)
        data = self._get()
        self.assertEqual(self._slugs(data["series"]), ["brave-for-god"])
        self.assertEqual(data["more"], [])

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

    def test_articles_are_the_topics_here_in_its_order(self):
        teens = Topic.objects.create(slug="for-teens", title="For Teens", is_published=True)
        for slug, order in (("is-the-bible-reliable", 2), ("can-i-have-doubts", 1)):
            TopicArticle.objects.create(topic=teens, article_slug=slug, sort_order=order)
            Article.objects.create(slug=slug, language="en", h1=slug, body_html="<p>x</p>", is_published=True)
        Article.objects.create(slug="can-i-have-doubts", language="sw", h1="sw", body_html="<p>x</p>", is_published=True)
        self.assertEqual(
            self._slugs(self._get("teens")["articles"]), ["can-i-have-doubts", "is-the-bible-reliable"]
        )
        # Swahili has one article, but no Swahili topic title: no shelf, no articles.
        self.assertEqual(self._get("teens", "sw")["articles"], [])
        TopicTranslation.objects.create(topic=teens, language="sw", title="Kwa Vijana")
        self.assertEqual(self._slugs(self._get("teens", "sw")["articles"]), ["can-i-have-doubts"])

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

    def test_the_spotlight_is_the_first_pick_published_here(self):
        # A Straight Talk volume, as in the library: so not the start pick.
        straight = Series.objects.create(slug="straight-talk", title="ST", audience="teens")
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-teens", series=straight)
        self._book("talks-to-the-farmer-teens", series=straight)  # a lone volume reads as a book
        self.assertEqual(self._get("teens")["spotlight"]["slug"], "pilgrims-progress-teens")
        # Not in this language, no banner — no English fallback.
        self.assertIsNone(self._get("teens", "sw")["spotlight"])
        # The young readers' hub has none.
        self.assertIsNone(self._get()["spotlight"])

    def test_the_spotlight_is_never_the_start_pick_too(self):
        # No Around the Wicket Gate here, so the start falls to the spotlight's book.
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-teens")
        data = self._get("teens")
        self.assertEqual(data["start"], "pilgrims-progress-teens")
        self.assertIsNone(data["spotlight"])

    def test_ladders_are_each_editions_family_youngest_first(self):
        self._book("pilgrims-progress")
        self._book("pilgrims-progress-children")
        self._book("pilgrims-progress-teens")
        self._book("talks-to-the-farmer")
        self._book("talks-to-the-farmer-children", language="sw")
        self._book("talks-to-the-farmer-teens", published=False)
        self._book("all-of-grace")
        self._book("all-of-grace-children")
        self._book("all-of-grace-teens", published=False)
        ladders = self._get()["ladders"]
        self.assertEqual(
            [(r["rung"], r["slug"]) for r in ladders["pilgrims-progress-children"]],
            [
                ("children", "pilgrims-progress-children"),
                ("teens", "pilgrims-progress-teens"),
                ("full", "pilgrims-progress"),
            ],
        )
        # The unpublished teens edition is no rung.
        self.assertEqual(
            [r["rung"] for r in ladders["all-of-grace-children"]], ["children", "full"]
        )
        # Only this language's published editions climb the ladder.
        self.assertNotIn("talks-to-the-farmer-children", ladders)
        self.assertEqual(
            [r["slug"] for r in self._get(language="sw")["ladders"].get(
                "talks-to-the-farmer-children", [])],
            [],
        )

    def test_the_challenge_is_served_only_where_its_series_is(self):
        self._book("rooted-1", series=Series.objects.create(
            slug="rooted", title="Rooted", audience="young_readers"))
        self.assertEqual(self._get()["challenge"], {"series": "rooted", "days": 30})
        self.assertIsNone(self._get("teens")["challenge"])

    def test_the_etag_moves_with_the_release(self):
        # A code-only deploy can add a field (as `challenge` was added); the
        # cached body must not keep answering 304 without it.
        with self.settings(RELEASE_COMMIT="a"):
            first = self.client.get(self.URL.format("teens", "en"))["ETag"]
        with self.settings(RELEASE_COMMIT="b"):
            second = self.client.get(self.URL.format("teens", "en"))["ETag"]
        self.assertNotEqual(first, second)

    def test_every_spotlight_pick_names_a_real_book(self):
        books = Path(__file__).parent / "fixtures" / "content" / "books"
        missing = [
            slug
            for picks in AUDIENCE_SPOTLIGHTS.values()
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

    def _quote(self, author, chapter, text, *, slug, reviewed=True):
        return Quote.objects.create(
            slug=slug, author=author, text=text, chapter=chapter, paragraph=0,
            reviewed=reviewed,
        )

    def test_quotes_are_the_strips_people_in_their_own_words(self):
        carey = Author.objects.create(slug="william-carey", name="William Carey")
        slessor = Author.objects.create(slug="mary-slessor", name="Mary Slessor")
        outsider = Author.objects.create(slug="john-owen", name="John Owen")
        book = self._book("bfg-1", series=self.series)
        self._story(book, 1, "Mary Slessor: The Girl Who Feared Nothing", slessor)
        self._story(book, 2, "William Carey: The Cobbler", carey)
        source = Chapter.objects.get(book=book, order=1)
        self._quote(carey, source, "Expect great things from God.", slug="carey-b")
        self._quote(carey, source, "Attempt great things for God.", slug="carey-a")
        self._quote(slessor, source, "God plus one is always a majority.", slug="slessor-a")
        self._quote(slessor, source, "A longer line that loses to the shorter one.", slug="slessor-0a")
        self._quote(slessor, source, "Unreviewed.", slug="slessor-0", reviewed=False)
        self._quote(slessor, source, "x" * 200, slug="slessor-00")  # too long to stand alone
        self._quote(outsider, source, "Not one of the strip's people.", slug="owen-a")
        quotes = self._get()["quotes"]
        # The strip's order, one each, the shortest (a tie goes to the slug);
        # reviewed and short enough to stand alone only.
        self.assertEqual(
            [(q["author"]["slug"], q["text"]) for q in quotes],
            [
                ("mary-slessor", "God plus one is always a majority."),
                ("william-carey", "Attempt great things for God."),
            ],
        )

    def test_quotes_are_english_only(self):
        slessor = Author.objects.create(slug="mary-slessor", name="Mary Slessor")
        en = self._book("bfg-1", series=self.series)
        sw = self._book("bfg-1", language="sw", series=self.series)
        SeriesTranslation.objects.create(series=self.series, language="sw", title="Shujaa")
        self._story(en, 1, "Mary Slessor: The Girl", slessor)
        Chapter.objects.create(book=sw, order=1, title="Mary Slessor: Msichana", body_html=body_of(9))
        self._quote(slessor, Chapter.objects.get(book=en), "God plus one.", slug="slessor-a")
        self.assertEqual(len(self._get()["quotes"]), 1)
        data = self._get(language="sw")
        self.assertEqual(len(data["people"]), 1)
        self.assertEqual(data["quotes"], [])

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

    def test_every_story_chapter_splits_into_name_and_hook_in_every_language(self):
        # The strip's name and hook are the chapter title split at its colon
        # ("Name: The Boy Who Looked"). A translation that drops or swaps the
        # separator would show its whole title as the hook — caught here, per
        # edition, rather than on the page.
        books = Path(__file__).parent / "fixtures" / "content" / "books"
        unsplit = []
        for slug, members in BOOK_PEOPLE:
            chapters = {m[2] for m in members if len(m) == 3}
            if not chapters:
                continue
            for path in sorted(books.glob(f"{slug}.*.json")):
                for row in json.loads(path.read_text())[1:]:
                    f = row["fields"]
                    if f["order"] in chapters and split_story_title(f["title"]) is None:
                        unsplit.append((path.name, f["order"], f["title"]))
        self.assertEqual(unsplit, [])


class ChallengeSeriesFixtureTests(TestCase):
    """The hubs frame Anchored and Rooted as a 30-day challenge
    (``views.AUDIENCE_CHALLENGES``, served as ``challenge``): each volume is an introduction, then one chapter a day, so
    a reader's furthest chapter minus one is the day they've reached. Held to
    the English fixture, so a re-cut volume can't silently skew the count."""

    CHALLENGES = dict(AUDIENCE_CHALLENGES.values())

    def test_every_challenge_volume_is_an_introduction_then_one_chapter_a_day(self):
        books = Path(__file__).parent / "fixtures" / "content" / "books"
        wrong, seen = [], 0
        for path in sorted(books.glob("*.en.json")):
            rows = json.loads(path.read_text())
            series = (rows[0]["fields"].get("series") or [None])[0]
            if series not in self.CHALLENGES:
                continue
            seen += 1
            titles = {r["fields"]["order"]: r["fields"]["title"] for r in rows[1:]}
            for day in range(1, self.CHALLENGES[series] + 1):
                if not titles.get(day + 1, "").startswith(f"Day {day} "):
                    wrong.append((path.name, day + 1, titles.get(day + 1)))
        self.assertGreater(seen, 0, "no challenge volumes found — did a series slug change?")
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


class TeensShelfHookTests(TestCase):
    """Every stand-alone book on the For Teens shelf carries a hook in English —
    the teens hub's cards lead with it, and a card without one reads as an
    oversight beside the rest. Series volumes show as their series' tile, so
    they are not held to it."""

    def test_every_standalone_for_teens_book_has_an_english_hook(self):
        from .content_fixtures import BOOKS_DIR
        from .topic_seed import TOPICS

        slugs = next(books for slug, _, _, books in TOPICS if slug == "for-teens")
        missing = []
        for slug in slugs:
            path = BOOKS_DIR / f"{slug}.en.json"
            if not path.exists():
                continue
            fields = json.loads(path.read_text(encoding="utf-8"))[0]["fields"]
            if not fields.get("series") and not fields.get("hook"):
                missing.append(slug)
        self.assertEqual(missing, [], "write a hook (Book.hook) for these")
