"""Typewriter dashes: the rule, and the two gates that hold the corpus at zero."""

from __future__ import annotations

import re

from django.test import SimpleTestCase

from library import corrections
from library.content_fixtures import BOOKS_DIR, SERMONS_DIR
from library.dashes import convert, count


class ConvertTests(SimpleTestCase):
    def test_a_run_of_two_or_three_is_one_em_dash(self):
        self.assertEqual(convert("experienced--everywhere"), "experienced—everywhere")
        self.assertEqual(convert("pus---unspeakable"), "pus—unspeakable")

    def test_the_source_spacing_is_kept(self):
        self.assertEqual(convert("dreams -- a living hope"), "dreams — a living hope")
        self.assertEqual(convert("t. --The"), "t. —The")

    def test_four_or_more_is_a_two_em_dash(self):
        # The printer's mark for a withheld name.
        self.assertEqual(convert("about Mrs.----? I was"), "about Mrs.——? I was")
        self.assertEqual(convert("then------ </p>"), "then—— </p>")

    def test_withheld_initials(self):
        self.assertEqual(convert("The Rev. C-- B-- opposed"), "The Rev. C— B— opposed")

    def test_a_single_hyphen_is_a_hyphen(self):
        self.assertEqual(convert("self-righteous us-ward"), "self-righteous us-ward")

    def test_comments_and_tags_pass_through(self):
        html = '<!-- a -- b --><p data-x="a--b">one--two</p>'
        self.assertEqual(convert(html), '<!-- a -- b --><p data-x="a--b">one—two</p>')

    def test_a_fragment_cut_inside_a_comment_is_safe(self):
        # A correction pair's half can start or end mid-comment.
        self.assertEqual(convert("note --><p>a--b"), "note --><p>a—b")
        self.assertEqual(convert("x<!-- note"), "x<!-- note")

    def test_idempotent(self):
        once = convert("a--b -- c----d")
        self.assertEqual(convert(once), once)

    def test_count(self):
        self.assertEqual(count("<!-- -- --><p>a--b -- c</p>"), 2)


#: A body field's JSON string value in a raw fixture file.
_FIELD = re.compile(r'"(?:body_html|body_text)": "((?:[^"\\]|\\.)*)"')


class CorpusTests(SimpleTestCase):
    def test_no_stored_body_keys_a_typewriter_dash(self):
        """Every book and sermon body, every language, is dashed.

        The deploy's correction step converts any that slip in, but the fixture
        is what a fresh build loads and what the other gates compare against;
        `scripts/normalize_dashes.py` brings it back to zero.
        """
        offenders = {}
        for path in [*BOOKS_DIR.glob("*.json"), *SERMONS_DIR.glob("*.json")]:
            raw = path.read_text(encoding="utf-8")
            if "--" not in raw:
                continue
            n = sum(count(m.group(1)) for m in _FIELD.finditer(raw))
            if n:
                offenders[path.name] = n
        self.assertEqual(
            offenders, {}, "run `uv run python scripts/normalize_dashes.py`"
        )

    def test_no_declared_string_keys_a_typewriter_dash(self):
        """The dash rule runs FIRST, so a declared string carrying "--" never
        matches: the body it is looking for already says "—". Write it dashed.
        """
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, (list, tuple)):
                for item in value:
                    yield from strings(item)
            elif isinstance(value, dict):
                for item in value.values():
                    yield from strings(item)

        bad = [
            (slug, s)
            for slug, entry in corrections.BODY_CORRECTIONS.items()
            for s in strings(entry)
            if count(s)
        ]
        self.assertEqual(bad, [])
