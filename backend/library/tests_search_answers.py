"""Answers: a typed question met by one the library already answers."""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Sermon
from .search_answers import is_question


class AnswerSearchTests(TestCase):
    def setUp(self):
        murray = Author.objects.create(
            slug="andrew-murray", name="Andrew Murray",
            faq=[{"q": "Who was Andrew Murray?", "a": "A South African pastor and writer."}],
        )
        Book.objects.create(
            author=murray, slug="humility", language="en", title="Humility",
            qa=[
                {"question": "Why does Murray call humility the root of every virtue?",
                 "answer": "Because pride put man in his own place, and humility gives God His."},
                {"question": "Who was Andrew Murray?", "answer": "The author of this book."},
            ],
        )
        Sermon.objects.create(
            author=murray, slug="forgiving", language="en", title="Forgiving",
            body_html="<p>a</p>",
            study_questions=[{"question": "How can I forgive someone who has hurt me deeply?",
                              "answer": "By remembering how much you have been forgiven."}],
        )
        Book.objects.create(
            author=murray, slug="humildad", language="es", title="Humildad",
            qa=[{"question": "¿Por qué la humildad es la raíz de toda virtud?", "answer": "Porque..."}],
        )

    def answers(self, q, language="en", **params):
        res = APIClient().get("/api/library/search/", {"q": q, "language": language, **params})
        return [h for h in res.data["results"] if h["type"] == "answer"]

    def test_a_question_is_answered_by_the_closest_question_with_its_answer(self):
        [hit] = self.answers("how do i forgive someone who hurt me")
        self.assertEqual((hit["work_kind"], hit["work_slug"]), ("sermon", "forgiving"))
        self.assertIn("forgiven", hit["answer"])
        self.assertIn("⟦forgive⟧", hit["snippet"])

    def test_a_writers_own_page_answers_who_they_were(self):
        hits = self.answers("who was andrew murray")
        self.assertEqual((hits[0]["work_kind"], hits[0]["work_slug"]), ("author", "andrew-murray"))
        self.assertEqual(len(hits), 2)  # one per page

    def test_words_alone_are_not_a_question(self):
        self.assertEqual(self.answers("humility root virtue"), [])
        self.assertFalse(is_question("humility", "en"))
        self.assertTrue(is_question("humildad raíz?", "es"))

    def test_too_loose_a_match_answers_nothing(self):
        self.assertEqual(self.answers("why is the sky blue"), [])

    def test_each_language_answers_from_its_own_pages(self):
        [hit] = self.answers("¿por qué la humildad es la raíz de la virtud?", language="es")
        self.assertEqual(hit["work_slug"], "humildad")

    def test_not_inside_a_scope(self):
        self.assertEqual(self.answers("who was andrew murray", **{"in": "author:andrew-murray"}), [])
