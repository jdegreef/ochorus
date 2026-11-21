"""Finding a person by name: initials, run-together initials, a missing middle
initial, a misspelt surname — and the person ranking above the bios that
merely mention them.

The regression this exists for: "d l moody" listed R. A. Torrey and Henry
Drummond under Authors (their bios mention "D. L. Moody") and not Moody himself,
because full-text search asked his name for the word "d"."""

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Sermon
from .people import People, words

NAMES = [
    (1, "Dwight L. Moody"),
    (2, "R. A. Torrey"),
    (3, "Henry Drummond"),
    (4, "Charles H. Spurgeon"),
    (5, "Charles G. Finney"),
    (6, "C. S. Lewis"),
    (7, "Brother Lawrence"),
    (8, "Augustine of Hippo"),
    (9, "Pastor Hsi (Xi Shengmo)"),
    (10, "John Wesley"),
    (11, "Susanna Wesley"),
    (12, "Billy Sunday"),
]


class PeopleTests(SimpleTestCase):
    people = People(NAMES)

    def top(self, q):
        found = self.people.match(q)
        return found[0].name if found else None

    def test_initials_and_name_variants_all_name_moody(self):
        for q in ("d l moody", "D.L. Moody", "D. L. Moody", "dl moody", "Dwight Moody",
                  "dwight l moody", "DWIGHT L MOODY", "Moody"):
            with self.subTest(q=q):
                self.assertEqual(self.top(q), "Dwight L. Moody")

    def test_named_needs_two_name_words_and_nothing_else(self):
        named = {q: self.people.match(q)[0].named for q in (
            "d l moody", "dwight moody", "c s lewis", "CH Spurgeon", "moody", "moody prayer",
        )}
        self.assertEqual(named, {
            "d l moody": True, "dwight moody": True, "c s lewis": True,
            "CH Spurgeon": True, "moody": False, "moody prayer": False,
        })

    def test_an_initial_the_person_lacks_rules_them_out(self):
        self.assertIsNone(self.top("x l moody"))
        # "c s" is Lewis's, not either Charles's.
        self.assertEqual([m.name for m in self.people.match("c s lewis")], ["C. S. Lewis"])

    def test_a_misspelt_surname_still_finds_them(self):
        self.assertEqual(self.top("charles spurgen"), "Charles H. Spurgeon")

    def test_honorifics_and_parentheses(self):
        self.assertEqual(self.top("st augustine"), "Augustine of Hippo")
        self.assertEqual(self.top("brother lawrence"), "Brother Lawrence")
        self.assertEqual(self.top("xi shengmo"), "Pastor Hsi (Xi Shengmo)")

    def test_ordinary_words_name_nobody(self):
        for q in ("prayer", "grace", "the way to god", "holy spirit"):
            with self.subTest(q=q):
                self.assertEqual(self.people.match(q), [])

    def test_a_short_word_is_not_mistaken_for_initials(self):
        # "on" is no one's initials, so it stays a word of the query.
        found = self.people.match("moody on prayer")
        self.assertEqual(found[0].name, "Dwight L. Moody")
        self.assertEqual(found[0].rest, ["on", "prayer"])

    def test_rewrite_spells_the_person_the_library_way(self):
        rw = self.people.rewrite
        self.assertEqual(rw("d l moody"), "dwight l moody")
        self.assertEqual(rw("D.L. Moody prayer"), "dwight l moody prayer")
        self.assertEqual(rw("CH Spurgeon"), "charles h spurgeon")
        # Already the library's spelling, one word, a tie, or websearch syntax.
        self.assertIsNone(rw("dwight l moody"))
        self.assertIsNone(rw("moody"))
        self.assertIsNone(rw("wesley"))
        self.assertIsNone(rw("d l moody -prayer"))
        self.assertIsNone(rw('"d l moody"'))

    def test_review_cases(self):
        m = self.people.match
        # A possessive is the name, not an initial "s".
        self.assertEqual(m("d l moody's sermons")[0].name, "Dwight L. Moody")
        # An excluded person is never asked for.
        self.assertEqual([p.name for p in m("moody -torrey")], ["Dwight L. Moody"])
        # A particle never makes a second name word.
        self.assertFalse(m("augustine of")[0].named)
        # An honorific after the name is something else asked for.
        self.assertEqual(m("d l moody mother")[0].rest, ["mother"])
        self.assertFalse(m("d l moody mother")[0].named)
        self.assertTrue(m("st augustine")[0].whole)
        # A first name inside a longer query names no one wholly.
        self.assertFalse(any(p.whole for p in m("gospel of john")))

    def test_words_fold_accents_and_split_punctuation(self):
        self.assertEqual(words("Frédéric L. Godet"), ["frederic", "l", "godet"])
        self.assertEqual(words("D.L."), ["d", "l"])


class PersonSearchTests(TestCase):
    """The whole path, on whichever database the suite runs (Postgres in CI)."""

    def setUp(self):
        self.client = APIClient()
        self.moody = Author.objects.create(
            slug="dwight-l-moody", name="Dwight L. Moody", bio="An American evangelist."
        )
        torrey = Author.objects.create(
            slug="r-a-torrey",
            name="R. A. Torrey",
            bio="D. L. Moody made him the first superintendent of the Moody Bible Institute.",
        )
        drummond = Author.objects.create(
            slug="henry-drummond",
            name="Henry Drummond",
            bio="He worked beside D. L. Moody in the 1873 campaign.",
        )
        secret = Book.objects.create(
            author=self.moody, slug="secret-power", language="en", title="Secret Power"
        )
        Chapter.objects.create(
            book=secret, order=1, title="Power in Prayer",
            body_html="<p>Prayer is the breath of the soul.</p>",
        )
        for author, slug in ((torrey, "how-to-pray"), (drummond, "the-greatest-thing")):
            Book.objects.create(author=author, slug=slug, language="en", title=slug)
        Sermon.objects.create(
            author=self.moody, slug="excuses", language="en", title="Excuses",
            body_html="<p>They all with one consent began to make excuse.</p>",
        )

    def get(self, q, **params):
        res = self.client.get("/api/library/search/", {"q": q, "language": "en", **params})
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_d_l_moody_finds_moody_first_and_named(self):
        for q in ("d l moody", "D.L. Moody", "dwight moody"):
            with self.subTest(q=q):
                data = self.get(q)
                authors = [h for h in data["results"] if h["type"] == "author"]
                self.assertEqual(authors[0]["author_slug"], "dwight-l-moody")
                self.assertTrue(authors[0].get("named"))
                # He leads the whole list, above the bios that mention him.
                self.assertEqual(data["results"][0]["author_slug"], "dwight-l-moody")
                self.assertGreaterEqual(data["totals"]["author"], 1)

    def test_his_works_are_found_by_the_same_spelling(self):
        results = self.get("D.L. Moody")["results"]
        self.assertIn("secret-power", {h.get("book_slug") for h in results if h["type"] == "book"})
        self.assertIn("excuses", {h.get("sermon_slug") for h in results if h["type"] == "sermon"})
        # Narrowed by what else was typed: his chapter on prayer, by initials.
        chapters = [h for h in self.get("d l moody prayer")["results"] if h["type"] == "chapter"]
        self.assertEqual([h["book_slug"] for h in chapters], ["secret-power"])

    def test_the_author_page_ranks_the_named_person_first(self):
        page = self.get("d l moody", type="author")["results"]
        self.assertEqual(page[0]["author_slug"], "dwight-l-moody")

    def test_a_lone_surname_is_found_but_not_named(self):
        authors = [h for h in self.get("moody")["results"] if h["type"] == "author"]
        self.assertEqual(authors[0]["author_slug"], "dwight-l-moody")
        self.assertNotIn("named", authors[0])

    def test_a_shared_first_name_in_a_longer_query_is_not_an_author_hit(self):
        Author.objects.create(slug="john-wesley", name="John Wesley", bio="A preacher.")
        Book.objects.create(
            author=Author.objects.get(slug="john-wesley"), slug="journal", language="en",
            title="Journal",
        )
        authors = [h for h in self.get("gospel of john")["results"] if h["type"] == "author"]
        self.assertEqual(authors, [])

    def test_the_snippet_does_not_highlight_an_initial(self):
        hit = next(h for h in self.get("d l moody")["results"] if h["type"] == "author")
        self.assertNotIn("⟦d⟧", hit["snippet"].lower())


class AliasSearchTests(TestCase):
    """Other names (library/search_aliases.py): a person's full or by-name, a
    work's Latin title."""

    def setUp(self):
        self.client = APIClient()
        spurgeon = Author.objects.create(slug="charles-h-spurgeon", name="Charles H. Spurgeon")
        Sermon.objects.create(
            author=spurgeon, slug="the-ravens-cry", language="en", title="The Ravens' Cry",
            body_html="<p>He gives to the young ravens which cry.</p>",
        )
        augustine = Author.objects.create(slug="augustine-of-hippo", name="Augustine of Hippo")
        city = Book.objects.create(
            author=augustine, slug="the-city-of-god", language="en", title="The City of God"
        )
        Chapter.objects.create(
            book=city, order=1, title="Book I", body_html="<p>The glorious city of God.</p>"
        )

    def results(self, q):
        res = self.client.get("/api/library/search/", {"q": q, "language": "en"})
        self.assertEqual(res.status_code, 200)
        return res.data["results"]

    def test_a_full_or_by_name_finds_the_person(self):
        for q in ("Charles Haddon Spurgeon", "prince of preachers"):
            with self.subTest(q=q):
                hits = self.results(q)
                self.assertEqual(hits[0]["author_slug"], "charles-h-spurgeon")
                self.assertTrue(hits[0].get("named"))
        sermons = [h for h in self.results("Charles Haddon Spurgeon") if h["type"] == "sermon"]
        self.assertEqual([h["sermon_slug"] for h in sermons], ["the-ravens-cry"])

    def test_a_latin_title_finds_the_book(self):
        books = [h for h in self.results("De Civitate Dei") if h["type"] == "book"]
        self.assertEqual([b["book_slug"] for b in books], ["the-city-of-god"])

    def test_every_alias_names_a_real_slug(self):
        import json
        from pathlib import Path

        from .search_aliases import AUTHOR_ALIASES, BOOK_ALIASES

        content = Path(__file__).parent / "fixtures" / "content"
        authors = {r["fields"]["slug"] for r in json.loads((content / "authors.json").read_text())}
        self.assertEqual(set(AUTHOR_ALIASES) - authors, set())
        books = {p.name.split(".")[0] for p in (content / "books").glob("*.json")}
        self.assertEqual(set(BOOK_ALIASES) - books, set())


class NamesInEachLanguageTests(SimpleTestCase):
    """A reader types the name the way their language writes it
    (library/data/author_names.json)."""

    def people(self, slug, name):
        from .search_aliases import other_names

        return People([(1, name)] + [(1, other, name) for other in other_names(slug)])

    def test_each_script_finds_moody(self):
        people = self.people("dwight-l-moody", "Dwight L. Moody")
        for q in ("무디", "D. L. 무디", "무디의 설교", "ムーディー", "ムーディ", "Муді",
                  "Д. Л. Муді", "مودي", "मूडी", "ሙዲ"):
            with self.subTest(q=q):
                found = people.match(q)
                self.assertTrue(found, q)
                self.assertEqual(found[0].name, "Dwight L. Moody")

    def test_exonyms_in_latin_scripts(self):
        self.assertEqual(self.people("augustine-of-hippo", "Augustine of Hippo")
                         .match("San Agustín")[0].name, "Augustine of Hippo")
        self.assertTrue(self.people("martin-luther", "Martin Luther").match("Martín Lutero")[0].named)
        self.assertTrue(self.people("john-calvin", "John Calvin").match("Jean Calvin")[0].named)

    def test_the_file_is_well_formed(self):
        import json
        from pathlib import Path

        from .search_aliases import author_names_by_language

        content = Path(__file__).parent / "fixtures" / "content"
        slugs = {r["fields"]["slug"] for r in json.loads((content / "authors.json").read_text())}
        site = {"am", "ar", "es", "fr", "hi", "ja", "ko", "lg", "pt", "ru", "sw", "uk", "vi", "zh"}
        for slug, by_language in author_names_by_language().items():
            self.assertIn(slug, slugs)
            for language, forms in by_language.items():
                self.assertIn(language, site, slug)
                self.assertTrue(forms and all(isinstance(f, str) and f.strip() for f in forms), slug)
