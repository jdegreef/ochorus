"""Structural gate on translated BOOKS and SERMONS.

The sibling of ``tests_bio_markup``, which has gated the author biographies
since jobs #414/#415. Books and sermons — the bulk of the library — had no
equivalent, so the most reliable rule in the translation playbook applied to the
smallest content type and to nothing else.

A translation must carry the SAME MARKUP, IN THE SAME ORDER, as the English it
was made from. The pipeline already guarantees this by construction when it is
followed (split on ``re.split(r'(<[^>]+>)', body_html)``, translate the text
runs, reassemble), which is exactly why a divergence is worth failing on: it
means something other than that happened.

Why the ordered sequence rather than a count or a word ratio:

    Word count cannot see a missing paragraph. ~340 words dropped from a
    3145-word source moves the ratio by about a tenth — inside the ordinary
    spread between languages (sw sermons run 73.6-93.5% of their English, sw
    book chapters 77-91%, es bios 95-115%). A tag COUNT catches a deletion but
    not a swap or a reorder. The ordered sequence catches all three and is
    language-independent.

What this gate found on the sweep that introduced it (2026-08-14):

    ``free-grace.es.json`` ended with a literal ``</content></invoke>`` — the
    closing syntax of a translator session's own tool call, committed into
    ``body_html`` and rendering on the live Spanish page. No length check, no
    fixture-coherence check and no reviewer had seen it. Repaired in the same
    commit as this module; the check is what makes a recurrence impossible.

``KNOWN_GAPS`` pins the remaining backlog. The suite fails on anything NEW, and
also fails when a pinned entry is FIXED but left behind — so the list can only
shrink and "known" cannot quietly become "forever".

No DB, no network: reads the fixtures. Fast.
"""

from __future__ import annotations

import re

from django.test import SimpleTestCase

from library.content_fixtures import rows_by_file

# Translations whose markup does NOT match their English source.
#   sermons: (language, slug)
#   chapters: (language, book_slug, chapter_order)
# Each is a real divergence awaiting re-translation, not an accepted deviation.
# Delete the line when the repair ships — a stale entry fails below.
KNOWN_SERMON_GAPS: set[tuple[str, str]] = set()

# es/the-unselfishness-of-god: the Spanish edition carries substantially MORE
# markup than its English source (ch11 is 126 tags against 40) — the translator
# broke the prose into more paragraphs and added <em> emphasis the original does
# not have. Markup drift rather than lost prose, but it is a different-looking
# book, so it is pinned rather than accepted. Needs a re-translation pass.
KNOWN_CHAPTER_GAPS: set[tuple[str, str, int]] = {
    ("es", "the-unselfishness-of-god", 10),   # en 52 tags -> es 62
    ("es", "the-unselfishness-of-god", 11),   # en 40 -> es 126
    ("es", "the-unselfishness-of-god", 12),   # en 46 -> es 48
    ("es", "the-unselfishness-of-god", 22),   # en 74 -> es 84
    ("es", "the-unselfishness-of-god", 32),   # en 36 -> es 40
}

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def tag_sequence(html: str) -> list[str]:
    """Every tag, in document order, with internal whitespace normalised.

    Attributes are KEPT: a class is sometimes load-bearing (the bios' prayer
    callouts are styled by one), and a translation has no reason to change one.
    """
    return [_WS.sub(" ", t).strip() for t in _TAG.findall(html or "")]


def _corpus() -> tuple[dict, dict]:
    """({slug: {lang: {order: html}}}, {slug: {lang: html}}) from the fixtures."""
    books: dict[str, dict[str, dict[int, str]]] = {}
    sermons: dict[str, dict[str, str]] = {}
    for rows in rows_by_file().values():
        for obj in rows:
            f, model = obj["fields"], obj["model"]
            if model == "library.book":
                books.setdefault(f["slug"], {}).setdefault(f["language"], {})
            elif model == "library.chapter":
                slug, lang = f["book"]
                books.setdefault(slug, {}).setdefault(lang, {})[f["order"]] = (
                    f.get("body_html") or ""
                )
            elif model == "library.sermon":
                sermons.setdefault(f["slug"], {})[f["language"]] = f.get("body_html") or ""
    return books, sermons


def sermon_divergences() -> dict[tuple[str, str], tuple[int, int]]:
    _, sermons = _corpus()
    out = {}
    for slug, by_lang in sermons.items():
        source = by_lang.get("en")
        if not source:
            continue
        for lang, html in by_lang.items():
            if lang == "en" or not html:
                continue
            want, got = tag_sequence(source), tag_sequence(html)
            if want != got:
                out[(lang, slug)] = (len(want), len(got))
    return out


def chapter_divergences() -> dict[tuple[str, str, int], tuple[int, int]]:
    books, _ = _corpus()
    out = {}
    for slug, by_lang in books.items():
        source = by_lang.get("en")
        if not source:
            continue
        for lang, chapters in by_lang.items():
            if lang == "en" or not chapters:
                continue
            for order in sorted(set(chapters) & set(source)):
                want = tag_sequence(source[order])
                got = tag_sequence(chapters[order])
                if want != got:
                    out[(lang, slug, order)] = (len(want), len(got))
    return out


def chapter_count_mismatches() -> dict[tuple[str, str], tuple[int, int]]:
    """A translation missing whole chapters — the loudest possible failure."""
    books, _ = _corpus()
    out = {}
    for slug, by_lang in books.items():
        source = by_lang.get("en")
        if not source:
            continue
        for lang, chapters in by_lang.items():
            if lang == "en" or not chapters:
                continue
            if set(chapters) != set(source):
                out[(lang, slug)] = (len(source), len(chapters))
    return out


class TranslatedSermonMarkupTests(SimpleTestCase):
    def test_sermon_translation_keeps_the_english_markup_in_order(self):
        new = {k: v for k, v in sermon_divergences().items() if k not in KNOWN_SERMON_GAPS}
        detail = "\n".join(
            f"  sermons/{slug}.{lang}.json — {got} tags, English has {want}"
            for (lang, slug), (want, got) in sorted(new.items())
        )
        self.assertFalse(
            new,
            "Translated sermon(s) do not carry the English markup in order:\n"
            f"{detail}\n\n"
            "The pipeline makes this identical BY CONSTRUCTION when followed — "
            "split on re.split(r'(<[^>]+>)', body_html), translate only the text "
            "runs, reassemble — so a divergence means something else happened. "
            "Diff the ordered tag sequence against the .en.json. If a "
            "re-translation is queued, add it to KNOWN_SERMON_GAPS with the job "
            "number.",
        )

    def test_known_sermon_gaps_contains_no_fixed_entries(self):
        fixed = sorted(KNOWN_SERMON_GAPS - set(sermon_divergences()))
        self.assertFalse(
            fixed,
            "These sermons now match their English source — delete them from "
            f"KNOWN_SERMON_GAPS so the backlog can only shrink: {fixed}",
        )

    def test_no_tool_call_syntax_in_shipped_bodies(self):
        """free-grace.es shipped a translator session's own '</invoke>'.

        The tag-sequence gate above catches this as a side effect, but only
        while an English source exists to compare against. This asserts it
        directly, over every body, because leaked scaffolding on a public page
        is its own category of wrong.
        """
        books, sermons = _corpus()
        bad = []
        needles = ("</invoke>", "<invoke", "</content>", "antml:", "</function_calls>")
        for slug, by_lang in sermons.items():
            for lang, html in by_lang.items():
                if any(n in (html or "") for n in needles):
                    bad.append(f"sermons/{slug}.{lang}.json")
        for slug, by_lang in books.items():
            for lang, chapters in by_lang.items():
                for order, html in chapters.items():
                    if any(n in (html or "") for n in needles):
                        bad.append(f"books/{slug}.{lang}.json ch{order}")
        self.assertFalse(
            sorted(bad),
            f"Tool-call scaffolding leaked into shipped content: {sorted(bad)}",
        )


class TranslatedChapterMarkupTests(SimpleTestCase):
    def test_chapter_translation_keeps_the_english_markup_in_order(self):
        new = {k: v for k, v in chapter_divergences().items() if k not in KNOWN_CHAPTER_GAPS}
        detail = "\n".join(
            f"  books/{slug}.{lang}.json ch{order} — {got} tags, English has {want}"
            for (lang, slug, order), (want, got) in sorted(new.items())
        )
        self.assertFalse(
            new,
            "Translated chapter(s) do not carry the English markup in order:\n"
            f"{detail}\n\n"
            "A missing <p> pair means missing PROSE and the word ratio will not "
            "show it. Diff the ordered tag sequence against the .en.json "
            "chapter. If a re-translation is queued, add it to "
            "KNOWN_CHAPTER_GAPS with the job number.",
        )

    def test_known_chapter_gaps_contains_no_fixed_entries(self):
        fixed = sorted(KNOWN_CHAPTER_GAPS - set(chapter_divergences()))
        self.assertFalse(
            fixed,
            "These chapters now match their English source — delete them from "
            f"KNOWN_CHAPTER_GAPS so the backlog can only shrink: {fixed}",
        )

    def test_no_translation_is_missing_whole_chapters(self):
        """Never pinned: a translation short of whole chapters is not shippable."""
        found = chapter_count_mismatches()
        detail = "\n".join(
            f"  books/{slug}.{lang}.json — {got} chapters, English has {want}"
            for (lang, slug), (want, got) in sorted(found.items())
        )
        self.assertFalse(found, f"Translation(s) missing whole chapters:\n{detail}")

    def test_the_gate_actually_covers_the_corpus(self):
        """Guard against the checks silently comparing nothing.

        A refactor that broke `_corpus()` would make every assertion above pass
        vacuously, which is the failure mode a gate like this dies of.
        """
        books, sermons = _corpus()
        translated_sermons = sum(
            1 for by in sermons.values() for lang in by if lang != "en"
        )
        translated_chapters = sum(
            len(ch) for by in books.values() for lang, ch in by.items() if lang != "en"
        )
        self.assertGreater(translated_sermons, 50, "sermon corpus not being read")
        self.assertGreater(translated_chapters, 500, "chapter corpus not being read")
