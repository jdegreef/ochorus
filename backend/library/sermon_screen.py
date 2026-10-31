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
  the whole English library (``LibraryIndex.overlap``). Shared Scripture alone
  scores 0–2%.
* **Furniture at the end.** A publisher's notice, an editor's bracketed note or
  the order of service the Pulpit printed after a sermon (``ending``).

None of this judges content — whether a sermon is warm or polemical is for the
reader who writes its questions (see the sermon-import skill).
"""

from __future__ import annotations

import collections
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from library.content_fixtures import CONTENT_DIR

_ARCHAISM = re.compile(r"\b(thee|thou|thy|thine|ye|hath|unto|doth|art|shalt|wilt)\b", re.I)
_ETH = re.compile(r"\b\w+eth\b")
_WORD = re.compile(r"[a-z]+")
_TAG = re.compile(r"<[^>]+>")
# A paragraph ending on a letter or comma, the next opening in lower case.
_SPLIT = re.compile(r"[a-z,]\s*</p>\s*<p>\s*[a-z]")
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


def plain(body_html: str) -> str:
    return _TAG.sub(" ", body_html)


def archaism_density(text: str) -> tuple[int, int]:
    """(KJV archaisms, -eth verbs) per 10,000 words."""
    words = len(text.split()) or 1
    return (
        round(len(_ARCHAISM.findall(text)) * 10_000 / words),
        round(len(_ETH.findall(text)) * 10_000 / words),
    )


def page_splits(body_html: str) -> int:
    return len(_SPLIT.findall(body_html))


def ending(body_html: str, chars: int = 90) -> str:
    return " ".join(plain(body_html).split())[-chars:]


class LibraryIndex:
    """Every `NGRAM`-word run of the English library, mapped to the works using it."""

    def __init__(self, content_dir: Path = CONTENT_DIR):
        self._grams: dict[str, set[str]] = collections.defaultdict(set)
        for folder in ("books", "sermons"):
            for path in sorted((content_dir / folder).glob("*.en.json")):
                work = path.name[: -len(".en.json")]
                for row in json.loads(path.read_text(encoding="utf-8")):
                    words = _WORD.findall((row["fields"].get("body_text") or "").lower())
                    for i in range(len(words) - NGRAM):
                        self._grams[" ".join(words[i : i + NGRAM])].add(work)

    def overlap(self, text: str, own_slug: str = "") -> tuple[str, int]:
        """(the work sharing most of `text`'s wording, its share in percent)."""
        words = _WORD.findall(text.lower())
        grams = [" ".join(words[i : i + NGRAM]) for i in range(0, len(words) - NGRAM, NGRAM)]
        if not grams:
            return "", 0
        hits = collections.Counter(
            work for g in grams for work in self._grams.get(g, ()) if work != own_slug
        )
        if not hits:
            return "", 0
        work, n = hits.most_common(1)[0]
        return work, round(100 * n / len(grams))


def taken_slugs(content_dir: Path = CONTENT_DIR) -> dict[str, set[str]]:
    """Slugs already in use, per folder, in any language."""
    return {
        folder: {path.name.split(".")[0] for path in (content_dir / folder).glob("*.json")}
        for folder in ("books", "sermons", "articles")
    }


def collides(slug: str, taken: dict[str, set[str]], imported: bool) -> bool:
    """Does another work already use `slug`? A sermon's own rows (and their
    translations, which share its slug) are not a collision once it is imported."""
    return slug in taken["books"] or slug in taken["articles"] or (
        not imported and slug in taken["sermons"]
    )


@dataclass
class Screen:
    slug: str
    words: int
    archaisms: tuple[int, int]
    splits: int
    overlap: tuple[str, int]
    ending: str
    flags: list[str] = field(default_factory=list)


def screen(slug: str, body_html: str, index: LibraryIndex, slug_taken: bool = False) -> Screen:
    text = plain(body_html)
    result = Screen(
        slug=slug,
        words=len(text.split()),
        archaisms=archaism_density(text),
        splits=page_splits(body_html),
        overlap=index.overlap(text, own_slug=slug),
        ending=ending(body_html),
    )
    arch, eth = result.archaisms
    if arch < MODERN_ARCHAISMS and eth < MODERN_ETH:
        result.flags.append("modernised?")
    if result.splits:
        result.flags.append("page-splits")
    if result.overlap[1] > OVERLAP_LIMIT:
        result.flags.append(f"overlaps {result.overlap[0]}")
    if result.words < SHORT_WORDS:
        result.flags.append("short")
    if slug_taken:
        result.flags.append("slug taken")
    if _FURNITURE.search(result.ending):
        result.flags.append("ends on furniture")
    return result
