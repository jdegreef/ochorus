"""Glossary example passages (library.word_passages + its endpoint)."""

from __future__ import annotations

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Chapter, Sermon
from .word_passages import MAX_CHARS, pattern_for, sentence_around


class PatternTests(SimpleTestCase):
    def test_whole_words_only(self):
        p = pattern_for("hath")
        self.assertTrue(p.search("He hath spoken."))
        self.assertTrue(p.search("Hath he not?"))
        self.assertFalse(p.search("the aftermath of it"))

    def test_a_modern_homograph_matches_only_its_archaic_phrase(self):
        p = pattern_for("art")
        self.assertTrue(p.search("Thou art the Christ."))
        self.assertTrue(p.search("Where art thou?"))
        self.assertFalse(p.search("The art of prayer."))

    def test_hyphenated_terms_match_either_spelling(self):
        p = pattern_for("mercy-seat")
        self.assertTrue(p.search("before the mercy-seat"))
        self.assertTrue(p.search("before the mercy seat"))


class SentenceTests(SimpleTestCase):
    def test_the_sentence_holding_the_word(self):
        text = "First he spoke. Wherefore dost thou cry? Then he wept."
        before, hit, after = sentence_around(text, pattern_for("wherefore").search(text))
        self.assertEqual((before, hit, after), ("", "Wherefore", " dost thou cry?"))

    def test_a_long_sentence_is_cut_around_the_word(self):
        text = ("word " * 120) + "wherefore " + ("more " * 120) + "end."
        before, hit, after = sentence_around(text, pattern_for("wherefore").search(text))
        self.assertEqual(hit, "wherefore")
        self.assertLessEqual(len(before) + len(hit) + len(after), MAX_CHARS + 6)
        self.assertTrue(before.startswith("… "))
        self.assertTrue(after.endswith(" …"))


class WordPassagesApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.bunyan = Author.objects.create(slug="bunyan", name="John Bunyan")
        self.spurgeon = Author.objects.create(slug="spurgeon", name="C. H. Spurgeon")
        book = Book.objects.create(author=self.bunyan, slug="pp", language="en", title="Pilgrim")
        Chapter.objects.create(
            book=book, order=2, title="The Gate",
            body_html="<h2>The Gate</h2><p>He ran on.</p><p>Then said Evangelist, Wherefore dost thou cry? He answered.</p>",
        )
        # Stemmed "wherefores" — the index would find it; the word is not there.
        Chapter.objects.create(
            book=book, order=3, title="Three", body_html="<p>The whys and wherefores of it.</p>"
        )
        Sermon.objects.create(
            author=self.spurgeon, slug="s1", language="en", title="A Sermon",
            body_html="<p>O thou of little faith, wherefore didst thou doubt?</p>",
        )
        hidden = Book.objects.create(
            author=self.bunyan, slug="hid", language="en", title="Hidden", is_published=False
        )
        Chapter.objects.create(book=hidden, order=1, title="H", body_html="<p>Wherefore not.</p>")
        es = Book.objects.create(author=self.bunyan, slug="pp", language="es", title="Peregrino")
        Chapter.objects.create(book=es, order=1, title="Uno", body_html="<p>Wherefore, dijo.</p>")

    def get(self, word):
        return self.client.get(f"/api/library/words/{word}/passages/")

    def test_real_matches_linked_to_their_paragraph(self):
        res = self.get("wherefore")
        self.assertEqual(res.status_code, 200)
        by_href = {p["href"]: p for p in res.data["passages"]}
        self.assertEqual(set(by_href), {"/books/pp/2/?p=2", "/sermons/s1/?p=0"})
        chapter = by_href["/books/pp/2/?p=2"]
        self.assertEqual(
            (chapter["before"], chapter["match"], chapter["after"]),
            ("Then said Evangelist, ", "Wherefore", " dost thou cry?"),
        )
        self.assertEqual(chapter["work"], "Pilgrim")
        self.assertEqual(chapter["title"], "The Gate")
        self.assertEqual(chapter["author"], {"slug": "bunyan", "name": "John Bunyan"})

    def test_one_passage_per_work(self):
        Chapter.objects.create(
            book=Book.objects.get(slug="pp", language="en"), order=4, title="Four",
            body_html="<p>Wherefore again.</p>",
        )
        hrefs = [p["href"] for p in self.get("wherefore").data["passages"]]
        self.assertEqual(sum(h.startswith("/books/pp/") for h in hrefs), 1)

    def test_no_match_is_an_empty_list(self):
        self.assertEqual(self.get("peradventure").data, {"word": "peradventure", "passages": []})

    def test_not_a_word(self):
        for bad in ("thou%20art", "x1", "a" * 31):
            with self.subTest(bad=bad):
                self.assertEqual(self.get(bad).status_code, 404)
