"""The sermon-question generator's parse/clean helpers — the model-free half.

The API call is not exercised here (it costs a token and needs a key); these
guard the tolerant parsing and the plain-text/shape cleaning, which are where a
malformed or over-eager generation would otherwise reach a fixture.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from .management.commands.generate_sermon_questions import _insert_after
from .sermon_questions import MAX_ANSWER, clean_questions, parse_questions


class InsertAfterTests(SimpleTestCase):
    def test_inserts_directly_after_the_key(self):
        fields = {"title": "T", "summary": "S", "body_html": "B"}
        out = _insert_after(fields, "summary", "study_questions", [{"q": 1}])
        self.assertEqual(
            list(out), ["title", "summary", "study_questions", "body_html"]
        )

    def test_updates_in_place_when_present(self):
        fields = {"title": "T", "study_questions": [], "body_html": "B"}
        out = _insert_after(fields, "summary", "study_questions", [{"q": 1}])
        self.assertEqual(list(out), ["title", "study_questions", "body_html"])
        self.assertEqual(out["study_questions"], [{"q": 1}])

    def test_appends_when_anchor_absent(self):
        fields = {"title": "T", "body_html": "B"}
        out = _insert_after(fields, "summary", "study_questions", [])
        self.assertEqual(list(out)[-1], "study_questions")


class ParseQuestionsTests(SimpleTestCase):
    def test_plain_array(self):
        raw = '[{"question": "Q1?", "answer": "A1."}]'
        self.assertEqual(parse_questions(raw), [{"question": "Q1?", "answer": "A1."}])

    def test_json_fence_is_tolerated(self):
        raw = '```json\n[{"question": "Q?", "answer": "A."}]\n```'
        self.assertEqual(parse_questions(raw), [{"question": "Q?", "answer": "A."}])

    def test_prose_around_the_array_is_tolerated(self):
        raw = 'Here you go:\n[{"question": "Q?", "answer": "A."}]\nHope that helps.'
        self.assertEqual(parse_questions(raw), [{"question": "Q?", "answer": "A."}])

    def test_no_array_raises(self):
        with self.assertRaises(ValueError):
            parse_questions("I could not do that.")

    def test_non_list_json_raises(self):
        with self.assertRaises(ValueError):
            parse_questions('{"question": "Q?", "answer": "A."}')


class CleanQuestionsTests(SimpleTestCase):
    def test_strips_html_to_plain_text(self):
        items = [{"question": "What of <b>grace</b>?", "answer": "It is <i>free</i>."}]
        self.assertEqual(
            clean_questions(items),
            [{"question": "What of grace?", "answer": "It is free."}],
        )

    def test_drops_items_missing_a_half(self):
        items = [
            {"question": "Only a question?"},
            {"answer": "Only an answer."},
            {"question": "  ", "answer": "blank question"},
            {"question": "Good?", "answer": "Good."},
        ]
        self.assertEqual(clean_questions(items), [{"question": "Good?", "answer": "Good."}])

    def test_ignores_non_dict_items(self):
        items = ["not a dict", 42, {"question": "Q?", "answer": "A."}]
        self.assertEqual(clean_questions(items), [{"question": "Q?", "answer": "A."}])

    def test_drops_null_or_non_string_values(self):
        # A JSON null must not become the literal string "None" and slip through.
        items = [
            {"question": None, "answer": "A."},
            {"question": "Q?", "answer": 123},
            {"question": ["a", "list"], "answer": "A."},
            {"question": "Good?", "answer": "Good."},
        ]
        self.assertEqual(clean_questions(items), [{"question": "Good?", "answer": "Good."}])

    def test_caps_the_count(self):
        items = [{"question": f"Q{i}?", "answer": f"A{i}."} for i in range(10)]
        self.assertEqual(len(clean_questions(items, count=4)), 4)

    def test_caps_answer_length(self):
        items = [{"question": "Q?", "answer": "word " * 500}]
        self.assertLessEqual(len(clean_questions(items)[0]["answer"]), MAX_ANSWER)
