"""Checks run on a candidate sermon before it is imported (``screen_sermons``).

Each sermon batch was screened the same way by hand, and each check below is a
trap a batch fell into:

* **Modernised text.** Most of CCEL's Spurgeon from about 1862 on, and
  SermonIndex's Davies and Winslow, silently rewrite the Authorised Version the
  preacher quoted ("all you that labor"); Davies's even quotes the NIV. The
  printed text runs ~90–400 archaisms per 10,000 words, the rewrites under ~50
  with almost no -eth verbs (``archaism_density``).
* **Page-split damage.** The same modernised transcriptions break paragraphs
  mid-sentence at every page turn (``page_splits``).
* **The same text under another title.** Ryle's *Let Any Man Come* is
  *Holiness* ch. 18 word for word; a quarter of *The Good Way* is *Old Paths*
  ch. 15. Titles don't show it, so the candidate's wording is measured against
  the whole English library (``LibraryIndex``). Shared Scripture alone scores
  0–2%.
* **Furniture at the end.** A publisher's notice, an editor's bracketed note or
  the order of service the Pulpit printed after a sermon (``ending``).

None of this judges content — whether a sermon is warm or polemical is for the
reader who writes its questions (see the sermon-import skill).
"""

from __future__ import annotations

import collections
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from library.content_fixtures import ARTICLES_DIR, BOOKS_DIR, SERMONS_DIR
from library.text import text_of, word_count

_ARCHAISM = re.compile(r"\b(thee|thou|thy|thine|ye|hath|unto|doth|art|shalt|wilt)\b", re.I)
# Lower-case only (Nazareth, Seth), and not an ordinal (twentieth) or a noun.
_ETH = re.compile(r"\b(?!(?:teeth|beneath)\b)[a-z]+(?<!ti)eth\b")
_WORD = re.compile(r"[a-z]+")
# A paragraph ending on a letter, comma or hyphen ("al- / ways"), the next
# opening in lower case.
_SPLIT = re.compile(r"[a-z,-]\s*</p>\s*<p>\s*[a-z]")
_FURNITURE = re.compile(
    r"\]\s*$|PORTIONS? OF SCRIPTURE|OUR OWN HYMN|authori[sz]ed edition|LETTER FROM", re.I
)

# Below both, a text reads as a modernised rewrite of the printed sermon.
MODERN_ARCHAISMS = 50
MODERN_ETH = 3
# Above this share of its wording already on the shelf, a candidate is a duplicate.
OVERLAP_LIMIT = 5
SHORT_WORDS = 1500
NGRAM = 10
ENDING_CHARS = 90


def archaism_density(text: str) -> tuple[int, int]:
    """(KJV archaisms, -eth verbs) per 10,000 words."""
    words = len(text.split()) or 1
    return (
        round(len(_ARCHAISM.findall(text)) * 10_000 / words),
        round(len(_ETH.findall(text)) * 10_000 / words),
    )


def page_splits(body_html: str) -> int:
    return len(_SPLIT.findall(body_html))


def _sampled_grams(text: str) -> list[str]:
    """Every `NGRAM`-th run of `NGRAM` words: the sample a candidate is measured by."""
    words = _WORD.findall(text.lower())
    return [" ".join(words[i : i + NGRAM]) for i in range(0, len(words) - NGRAM + 1, NGRAM)]


class LibraryIndex:
    """Which English books and sermons use each sampled run of some candidates.

    Indexing every run of the library is ~21M strings and several GB, so only
    the runs the candidates sample are recorded: the library is streamed once
    and a window is joined only when its first two words start one of them.
    """

    def __init__(self, texts: Iterable[str], dirs: Iterable[Path] = (BOOKS_DIR, SERMONS_DIR)):
        wanted = {g for text in texts for g in _sampled_grams(text)}
        starts = {tuple(g.split(" ", 2)[:2]) for g in wanted}
        self._works: dict[str, set[str]] = collections.defaultdict(set)
        for folder in dirs:
            for path in sorted(folder.glob("*.en.json")):
                work = path.name.split(".")[0]
                for row in json.loads(path.read_text(encoding="utf-8")):
                    words = _WORD.findall((row["fields"].get("body_text") or "").lower())
                    for i in range(len(words) - NGRAM + 1):
                        if (words[i], words[i + 1]) in starts and (
                            g := " ".join(words[i : i + NGRAM])
                        ) in wanted:
                            self._works[g].add(work)

    def overlap(self, text: str, own_slug: str = "") -> tuple[str, int]:
        """(the work sharing most of `text`'s wording, its share in percent)."""
        grams = _sampled_grams(text)
        hits = collections.Counter(
            work for g in grams for work in self._works.get(g, ()) if work != own_slug
        )
        if not hits:
            return "", 0
        work, n = hits.most_common(1)[0]
        pct = round(100 * n / len(grams))
        return (work, pct) if pct else ("", 0)


def taken_slugs() -> set[str]:
    """Slugs a book or article already uses, in any language. (A sermon's own
    translations share its slug, so sermons are not counted.)"""
    return {path.name.split(".")[0] for d in (BOOKS_DIR, ARTICLES_DIR) for path in d.glob("*.json")}


@dataclass
class Screen:
    words: int
    archaisms: int
    eth: int
    splits: int
    overlap_work: str
    overlap_pct: int
    ending: str
    flags: list[str] = field(default_factory=list)


def screen(slug: str, body_html: str, index: LibraryIndex, slug_taken: bool = False) -> Screen:
    text = text_of(body_html)
    arch, eth = archaism_density(text)
    work, pct = index.overlap(text, own_slug=slug)
    result = Screen(
        words=word_count(body_html),
        archaisms=arch,
        eth=eth,
        splits=page_splits(body_html),
        overlap_work=work,
        overlap_pct=pct,
        ending=text[-ENDING_CHARS:],
    )
    if arch < MODERN_ARCHAISMS and eth < MODERN_ETH:
        result.flags.append("modernised?")
    if result.splits:
        result.flags.append("page-splits")
    if pct > OVERLAP_LIMIT:
        result.flags.append(f"overlaps {work}")
    if result.words < SHORT_WORDS:
        result.flags.append("short")
    if slug_taken:
        result.flags.append("slug taken")
    if _FURNITURE.search(result.ending):
        result.flags.append("ends on furniture")
    return result
