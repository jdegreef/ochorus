"""`scripts/wikidata_p953.py`: the QuickStatements batch that lists Ochorus
editions on Wikidata as P953 ("full work available at URL").

The batch is submitted by hand (docs/wikidata.md), so what it must never do is
offer Wikidata a link it shouldn't: a work that is not public domain, the
house's own retellings, an unpublished edition, or a statement QuickStatements
would mangle.
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase


def _script():
    path = Path(__file__).resolve().parent.parent / "scripts" / "wikidata_p953.py"
    spec = importlib.util.spec_from_file_location("wikidata_p953", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclass looks itself up there
    spec.loader.exec_module(module)
    return module


W = _script()


def _book(
    slug,
    language,
    title,
    author="john-bunyan",
    published=True,
    attribution="",
    source_type="public_domain",
):
    return [
        {
            "model": "library.book",
            "fields": {
                "author": [author],
                "slug": slug,
                "language": language,
                "title": title,
                "attribution": attribution,
                "source_type": source_type,
                "is_published": published,
            },
        }
    ]


class FixtureTests(SimpleTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.content = Path(tmp.name)
        (self.content / "books").mkdir()
        authors = [
            {
                "model": "library.author",
                "fields": {"slug": "john-bunyan", "death_year": 1688},
            },
            {
                "model": "library.author",
                "fields": {"slug": "ochorus-originals", "death_year": None},
            },
            {
                "model": "library.author",
                "fields": {"slug": "living-writer", "death_year": 2020},
            },
        ]
        (self.content / "authors.json").write_text(json.dumps(authors))
        for rows in (
            _book("pilgrims-progress", "en", "The Pilgrim's Progress"),
            _book(
                "pilgrims-progress",
                "sw",
                "Safari ya Msafiri",
                source_type="ai_unreviewed",
            ),
            _book("pilgrims-progress", "fr", "Le Voyage du pèlerin", published=False),
            _book(
                "pilgrims-progress",
                "en-modern",
                "The Pilgrim's Progress (Modern English)",
            ),
            _book(
                "pilgrims-progress-teens", "en", "The Pilgrim's Progress (For Teens)"
            ),
            _book("rooted", "en", "Rooted", author="ochorus-originals"),
            _book("recent", "en", "Recent", author="living-writer"),
            _book(
                "shared",
                "en",
                "Shared",
                attribution="© A. Writer. Shared with permission.",
            ),
        ):
            name = f"{rows[0]['fields']['slug']}.{rows[0]['fields']['language']}.json"
            (self.content / "books" / name).write_text(json.dumps(rows))

    def test_lists_only_published_public_domain_editions_of_the_work_itself(self):
        works = W.load_editions(self.content)
        self.assertEqual(list(works), ["pilgrims-progress"])
        self.assertEqual([e.language for e in works["pilgrims-progress"]], ["en", "sw"])

    def test_writes_one_qualified_statement_per_language_edition(self):
        works = W.load_editions(self.content)
        lines = W.batch(works, {"pilgrims-progress": "Q268211"})
        self.assertEqual(
            lines,
            [
                'Q268211\tP953\t"https://ochorus.com/books/pilgrims-progress/"\tP407\tQ1860'
                '\tP1476\ten:"The Pilgrim\'s Progress"',
                'Q268211\tP953\t"https://ochorus.com/sw/books/pilgrims-progress/"\tP407\tQ7838'
                '\tP1476\tsw:"Safari ya Msafiri"',
            ],
        )

    def test_skips_unmapped_works_and_urls_that_are_not_live(self):
        works = W.load_editions(self.content)
        self.assertEqual(W.batch(works, {}), [])
        lines = W.batch(
            works, {"pilgrims-progress": "Q268211"}, keep=lambda url: "/sw/" not in url
        )
        self.assertEqual(len(lines), 1)

    def test_refuses_a_value_that_is_not_an_item_id(self):
        works = W.load_editions(self.content)
        with self.assertRaises(ValueError):
            W.batch(
                works, {"pilgrims-progress": "https://www.wikidata.org/wiki/Q268211"}
            )


class StatementTests(SimpleTestCase):
    def test_leaves_out_a_title_quickstatements_cannot_quote(self):
        line = W.statement("Q1", W.Edition("x", "en", 'The "Holy" War'))
        self.assertEqual(line, 'Q1\tP953\t"https://ochorus.com/books/x/"\tP407\tQ1860')


class MappingTests(SimpleTestCase):
    def test_the_curated_mapping_names_eligible_works_by_item_id(self):
        mapping = W.load_mapping()
        works = W.load_editions()
        for slug, qid in mapping.items():
            self.assertRegex(qid, r"^Q\d+$", slug)
            self.assertIn(slug, works, f"{slug} is mapped but is not an eligible work")
        self.assertEqual(
            len(set(mapping.values())), len(mapping), "two works share one item"
        )
