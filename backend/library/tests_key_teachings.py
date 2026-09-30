"""The Key Teachings build command must agree with the committed fixture.

`build_key_teachings` rewrites each book row from its `WORKS` entry, so a field
the fixture has moved on from (the cover went SVG → painted JPG in #4500) is
silently walked back in any DB the command is run against.
"""

import json

from django.test import SimpleTestCase

from library.content_fixtures import BOOKS_DIR
from library.management.commands.build_key_teachings import (
    DATA_DIR,
    WORKS,
    manuscript,
)


class BuildKeyTeachingsMatchesFixtureTests(SimpleTestCase):
    def test_book_fields_match_the_fixture(self):
        for slug, work in WORKS.items():
            with self.subTest(slug=slug):
                path = BOOKS_DIR / f"{slug}.en.json"
                book = json.loads(path.read_text(encoding="utf-8"))[0]["fields"]
                self.assertEqual(book["cover_url"], work.cover_url)
                # A Markdown work carries its copy in the manuscript's front
                # matter; resolve it the way the command does.
                meta = {}
                if work.source.endswith(".md"):
                    meta, _ = manuscript(
                        (DATA_DIR / work.source).read_text(encoding="utf-8")
                    )
                for field in (
                    "title", "subtitle", "description", "attribution",
                    "about_html", "cover_color",
                ):
                    expected = getattr(work, field) or meta.get(field, "")
                    self.assertEqual(book[field], expected, field)
