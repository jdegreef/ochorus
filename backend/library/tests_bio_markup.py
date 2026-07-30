"""Structural gate on the translated author biographies.

A translated bio (``migrations/data/author_bios_<lang>/<slug>.html``) must carry
the SAME MARKUP, IN THE SAME ORDER, as the English ``bio_html`` it is a
translation of. The author page styles the prayer callouts by class
(``.prayer`` / ``.prayer.answered``) and lays the piece out by ``<h2>`` and
``<blockquote>``, so a lost tag is a lost design; and because a paragraph is a
tag pair, a lost ``<p>`` is lost *prose*.

Why the ordered sequence and not a count or a length:

    On 2026-07-30 the Swahili and Luganda John Wesley bios (queue jobs #414 and
    #415) were both judged complete and nearly closed as such. Both were
    missing English paragraphs #35 and #36 — the doctrine of Christian
    perfection, and the works of mercy among prisoners, schools and the sick
    poor. The reader went straight from Wesley organising the societies to his
    rules about money.

    Word count could not see it. ~340 words missing from a 3145-word source
    moved the ratio by about a tenth, which is inside the ordinary spread
    between languages (a faithful Luganda bio runs 82-91% of its English
    source; Swahili 88-98%; Spanish and Portuguese 95-115%). A tag COUNT would
    have caught these two, but not a swap or a reorder. The ordered sequence
    catches all three, and it is what this module asserts.

    Sweeping every translated bio with that check turned up 17 files diverging
    from their source — including one at 34 tags against the English 86, and
    four authors incomplete in all three of es, lg and sw whose jobs had
    already been closed as done. Nine months of drift, invisible to every
    length-based check that ran over it.

``KNOWN_GAPS`` is that backlog, pinned. The suite fails on anything NEW, and
also fails when an entry is FIXED but left in the list — so the list can only
shrink, and "known" cannot quietly become "forever". Delete the line when you
ship the repair; every entry carries its queue job (#399-#411, #567-#578).

No DB, no network: reads the fixture and the data files. ~0.05s.
"""

from __future__ import annotations

import re

from django.test import SimpleTestCase

from library.content_fixtures import authors_by_slug
from library.management.commands.seed_author_translations import (
    language_dirs,
    read_bios,
)

# (language, slug) pairs whose translation does NOT match its English source.
# Each is a real, reader-visible gap awaiting re-translation, not an accepted
# deviation. Remove the line when the repair ships — a stale entry fails below.
KNOWN_GAPS = {
    ("es", "amy-carmichael"),  # 68/76 tags — job #567 (re-translated 07-25, still short)
    ("es", "susanna-wesley"),  # 72/84 tags — job #570
    ("es", "watchman-nee"),  # 72/88 tags, 72% of the English — job #573
    ("es", "william-booth"),  # 76/84 tags — job #576
    ("lg", "amy-carmichael"),  # 68/76 tags — job #568
    ("lg", "susanna-wesley"),  # 72/84 tags — job #571
    ("lg", "watchman-nee"),  # 72/88 tags, 57% of the English — job #574
    ("lg", "william-booth"),  # 76/84 tags — job #577
    ("sw", "amy-carmichael"),  # 68/76 tags — job #569
    ("sw", "charles-h-spurgeon"),  # 82/86 tags — job #399
    ("sw", "frederick-brotherton-meyer"),  # 72/80 tags — job #402
    ("sw", "gareth-evans"),  # 34/86 tags — worst in the library; job #405
    ("sw", "hannah-whitall-smith"),  # 76/78 tags — job #408
    ("sw", "jeanne-guyon"),  # 56/70 tags — job #411
    ("sw", "susanna-wesley"),  # 72/84 tags — job #572
    ("sw", "watchman-nee"),  # 72/88 tags — job #575
    ("sw", "william-booth"),  # 76/84 tags — job #578
}

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def tag_sequence(html: str) -> list[str]:
    """Every tag, in document order, with internal whitespace normalised.

    Attributes are KEPT — ``<aside class="prayer">`` and
    ``<aside class="prayer answered">`` are different callouts and the page
    styles them differently, so collapsing them would defeat the check.
    """
    return [_WS.sub(" ", t).strip() for t in _TAG.findall(html)]


def divergences() -> dict[tuple[str, str], tuple[int, int]]:
    """{(lang, slug): (english_tags, translated_tags)} for every mismatch.

    Authors with no English ``bio_html`` are skipped: there is no source to
    match, so a translation of one cannot be judged here.
    """
    english = authors_by_slug()
    out: dict[tuple[str, str], tuple[int, int]] = {}
    for lang, directory in language_dirs():
        for slug, bio in read_bios(directory).items():
            source = (english.get(slug) or {}).get("bio_html") or ""
            translated = bio.get("bio_html") or ""
            if not source or not translated:
                continue
            want, got = tag_sequence(source), tag_sequence(translated)
            if want != got:
                out[(lang, slug)] = (len(want), len(got))
    return out


class TranslatedBioMarkupTests(SimpleTestCase):
    def test_translation_keeps_the_english_markup_in_order(self):
        found = divergences()
        new = {k: v for k, v in found.items() if k not in KNOWN_GAPS}
        detail = "\n".join(
            f"  author_bios_{lang}/{slug}.html — {got} tags, English has {want}"
            for (lang, slug), (want, got) in sorted(new.items())
        )
        self.assertFalse(
            new,
            "Translated bio(s) do not carry the English markup in order:\n"
            f"{detail}\n\n"
            "A missing <p> pair means missing PROSE, not a formatting nit, and "
            "word count will not show it (see this module's docstring). Diff the "
            "ordered tag sequence against the author's bio_html in "
            "fixtures/content/authors.json and restore what was dropped. If the "
            "gap is deliberate and a re-translation is queued, add it to "
            "KNOWN_GAPS with the job number.",
        )

    def test_known_gaps_contains_no_fixed_entries(self):
        fixed = sorted(KNOWN_GAPS - set(divergences()))
        self.assertFalse(
            fixed,
            "These entries now match their English source — delete them from "
            f"KNOWN_GAPS so the backlog can only shrink: {fixed}",
        )

    def test_every_language_dir_is_covered(self):
        """A new author_bios_<lang> dir is in scope automatically.

        The check walks ``language_dirs()`` rather than a hardcoded list, so
        adding pt (or ar) brings its bios under the gate with no edit here.
        Pinned so nobody "simplifies" that into a literal.
        """
        langs = {lang for lang, _ in language_dirs()}
        self.assertGreaterEqual(langs, {"es", "sw", "lg", "pt"})
