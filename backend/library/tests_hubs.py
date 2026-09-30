"""Biography hubs (library/hubs.py): the curated data, and the API over it."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from library import hubs
from library.models import Author, AuthorTranslation, Book

AUTHORS = Path(__file__).parent / "fixtures" / "content" / "authors.json"


class HubDataTests(SimpleTestCase):
    """The files are hand-edited and keyed by slug, so nothing in the schema
    stops a typo'd writer, a dangling region or a hub no language can show."""

    def setUp(self):
        self.hubs = hubs.raw_members()
        self.prose = hubs.raw_prose()
        self.by_slug = {h["slug"]: h for h in self.hubs}
        rows = [r["fields"] for r in json.loads(AUTHORS.read_text(encoding="utf-8"))]
        self.listable = {
            f["slug"] for f in rows if not f.get("is_imprint") and f.get("list_in_biographies", True)
        }

    def test_hubs_are_well_formed(self):
        self.assertEqual(len(self.by_slug), len(self.hubs), "duplicate hub slug")
        for h in self.hubs:
            with self.subTest(hub=h["slug"]):
                self.assertIn(h["kind"], hubs.KINDS)
                self.assertRegex(h["slug"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
                self.assertEqual(len(set(h["members"])), len(h["members"]), "member listed twice")
                if h["kind"] == "place" and h.get("region"):
                    self.assertEqual(self.by_slug[h["region"]]["kind"], "region")
                else:
                    self.assertNotIn("region", h, "only a place sits in a region")

    def test_every_member_is_a_listable_writer(self):
        stray = [
            f"{h['slug']}/{m}" for h in self.hubs for m in h["members"] if m not in self.listable
        ]
        self.assertEqual(stray, [], "not an author, an imprint, or withheld from Biographies")

    def test_a_writer_is_tagged_at_one_place(self):
        # A region folds in its places, so a writer on both would be counted
        # twice in the data and would get two place chips on their page.
        places: dict[str, list[str]] = {}
        for h in self.hubs:
            if h["kind"] != "tradition":
                for m in h["members"]:
                    places.setdefault(m, []).append(h["slug"])
        self.assertEqual({m: p for m, p in places.items() if len(p) > 1}, {})

    def test_every_hub_could_show(self):
        folded = hubs.memberships(self.hubs)
        thin = [s for s, m in folded.items() if len(m) < hubs.MIN_MEMBERS]
        self.assertEqual(thin, [], "a hub under the floor never shows anywhere")

    def test_english_covers_every_hub_and_prose_names_only_real_hubs(self):
        self.assertEqual(set(self.prose["en"]), set(self.by_slug))
        for lang, entries in self.prose.items():
            self.assertEqual(set(entries) - set(self.by_slug), set(), lang)

    def test_prose_entries_are_complete(self):
        for lang, entries in self.prose.items():
            for slug, e in entries.items():
                with self.subTest(lang=lang, hub=slug):
                    self.assertTrue(e["name"].strip())
                    self.assertTrue(e["label"].strip())
                    self.assertLessEqual(len(e["label"]), len(e["name"]), "a label is the SHORT form")
                    self.assertGreater(len(e["intro"]), 60)
                    self.assertEqual(
                        len(e["qa"]), len(self.prose["en"][slug]["qa"]), "Q&A count differs from English"
                    )
                    for item in e["qa"]:
                        self.assertEqual(set(item), {"q", "a"})
                        self.assertTrue(item["q"].strip() and item["a"].strip())
                        # House rules for Q&A: no site name in an answer, and
                        # the section is never called an FAQ.
                        self.assertNotIn("Ochorus", item["a"])
                        self.assertIsNone(re.search(r"\bFAQ\b", item["q"] + item["a"]))


def _writer(slug, *, bio="A life.", language="en", **fields):
    return Author.objects.create(slug=slug, name=slug.title(), bio=bio, original_language=language, **fields)


class HubApiTests(TestCase):
    MEMBERS = [
        {"kind": "tradition", "slug": "puritans", "members": ["a", "b", "c", "d"]},
        {"kind": "region", "slug": "britain", "members": ["e"]},
        {"kind": "place", "slug": "wales", "region": "britain", "members": ["a", "b", "c", "d"]},
        {"kind": "place", "slug": "scotland", "region": "britain", "members": ["f"]},
    ]

    def setUp(self):
        for s in "abcdef":
            _writer(s)
        entry = lambda name: {"name": f"{name} writers", "label": name, "intro": f"About {name}.", "qa": [{"q": "Q?", "a": "A."}]}  # noqa: E731
        self.prose = {
            "en": {s: entry(s.title()) for s in ("puritans", "britain", "wales", "scotland")},
            # Swahili has prose for two hubs and bios for only three writers.
            "sw": {"puritans": entry("Wapuriti"), "wales": entry("Welisi")},
        }
        for s in "abc":
            AuthorTranslation.objects.create(author=Author.objects.get(slug=s), language="sw", bio="Maisha.")
        patches = [
            patch("library.hubs.raw_members", return_value=self.MEMBERS),
            patch("library.hubs.raw_prose", return_value=self.prose),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _hubs(self, lang="en"):
        res = self.client.get(f"/api/library/hubs/?language={lang}")
        self.assertEqual(res.status_code, 200)
        return {h["slug"]: h for h in res.json()}

    def test_a_region_folds_in_its_places_and_a_thin_place_is_hidden(self):
        got = self._hubs()
        self.assertEqual(set(got), {"puritans", "britain", "wales"})  # scotland has 1 writer
        self.assertEqual(got["britain"]["members"], ["e", "a", "b", "c", "d", "f"])
        self.assertEqual(got["wales"]["region"], "britain")
        self.assertEqual(got["puritans"]["name"], "Puritans writers")
        self.assertEqual(got["puritans"]["label"], "Puritans")
        self.assertEqual(got["puritans"]["qa"], [{"q": "Q?", "a": "A."}])

    def test_a_language_needs_prose_and_enough_listed_writers(self):
        self.assertEqual(self._hubs("sw"), {})  # three listed writers, under the floor
        AuthorTranslation.objects.create(author=Author.objects.get(slug="d"), language="sw", bio="Maisha.")
        got = self._hubs("sw")
        # Prose for two hubs, and Britain has none in Swahili: no fallback.
        self.assertEqual(set(got), {"puritans", "wales"})
        self.assertEqual(got["puritans"]["label"], "Wapuriti")
        self.assertEqual(got["puritans"]["available_languages"], ["en", "sw"])
        self.assertEqual(self._hubs()["britain"]["available_languages"], ["en"])

    def test_a_book_in_the_language_lists_a_writer_without_a_bio(self):
        e = _writer("g", bio="")
        Book.objects.create(author=e, slug="bk", language="sw", title="T", is_published=True)
        self.prose["sw"]["britain"] = self.prose["en"]["britain"]
        members = [dict(h) for h in self.MEMBERS]
        members[1] = {**members[1], "members": ["e", "g"]}
        with patch("library.hubs.raw_members", return_value=members):
            got = self._hubs("sw")
        self.assertEqual(got["britain"]["members"], ["g", "a", "b", "c"])

    def test_the_author_page_links_traditions_then_the_most_specific_place(self):
        res = self.client.get("/api/library/authors/a/?language=en").json()
        self.assertEqual(
            res["hubs"],
            [
                {"kind": "tradition", "slug": "puritans", "label": "Puritans"},
                {"kind": "place", "slug": "wales", "label": "Wales"},
            ],
        )
        # Scotland is too thin for a page, so its writer links to the region.
        res = self.client.get("/api/library/authors/f/?language=en").json()
        self.assertEqual(res["hubs"], [{"kind": "region", "slug": "britain", "label": "Britain"}])
        # And nothing in a language where the hubs don't exist.
        res = self.client.get("/api/library/authors/a/?language=sw").json()
        self.assertEqual(res["hubs"], [])
