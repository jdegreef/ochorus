"""Is a `mined` claim true? — the wording, checked against the file it cites.

A translation's notes file marks each scripture reference `mined` (the wording
came verbatim out of something we already ship) or `self_rendered` (the
translator rendered it itself — the actual review task). The admin review queue
turns that into "N verses checked", and a reviewer skips what it says is
checked. So the number has to be true.

Until now nothing checked it. ``seed_translation_notes`` requires a `mined` row
to NAME a source, and ``tests_translation_notes`` requires that name to be
non-empty — but nothing ever opened the file and looked. Job #426 is the
measured cost: its PR claimed five recovered verses and exactly one (John 20:13)
was verbatim; the other four were pronoun adaptations of Rom 8:28, John 11:25,
1 John 4:19 and Ps 41:3. A reviewer reading "5 verses checked" would have
skipped four nobody had checked.

WHAT IS AND IS NOT CHECKABLE HERE

`mined` in practice covers two provenances, and only one of them is a file:

* **A shipped fixture** — ``godliness.sw.json``. The claim is a substring claim
  and this module tests it.
* **A Bible edition** — ``Van Dyck (arb-vd) Bible text``, ``Louis Segond
  (1910)``. The verse was fetched from the Take Root API at translation time.
  That is *stronger* provenance than a corpus lift, but the text is not in the
  repo and CI has no egress, so there is nothing here to compare against.

Measured on 2026-09-17: 6,559 `mined` rows against 13,371 `self_rendered`, and
of the mined ones only **554 cite a fixture** — the other 6,005 cite a Bible.
So this module speaks to about 8% of the mined rows and is silent, by
construction, on the rest. It says so in its census rather than implying
coverage it does not have.

HOW A CLAIM IS TESTED, AND WHY EACH RULE IS THERE

Both sides are located by the quotation-plus-citation form
``verse_consistency`` already reads, keyed on chapter:verse — the notes carry an
ENGLISH reference ("Mark 9:23") while a translated body cites a localized book
name ("Marko 9:23"), so the book name cannot be the join.

1. **Both sides must be locatable.** If the translation never quotes the verse
   in that form, or the cited file doesn't, there is nothing to compare and the
   row is counted, not failed. 317 + 46 rows land here — most quotations are
   not written as «…» (Ref c:v).

2. **Same-verse confirmation, proportionally.** A numeric key alone conflates
   different books: Joel 2:25 with Revelation 2:25, and — measured in
   ``watchman-nee-a-life.pt`` — a note reading "1 Coríntios 2:14" against a body
   quoting 2 Corinthians 2:14 and a source holding 1 John 2:14, three different
   books all numbered 2:14. Requiring one shared content word did NOT separate
   that case (both mention "Deus"), so the bar is a proportion: the shorter
   quotation must share at least ``SAME_VERSE_OVERLAP`` of its content words.
   The two cases sat at 11% and 75%, so the threshold is not finely balanced.

3. **Verbatim means containment, either way.** Quoting half a verse where the
   source has all of it is still verbatim mining, so a substring in either
   direction passes — the same exemption ``verse_consistency._diverges`` makes,
   for the same reason.

What survives all three is a claim that the two texts ARE the same verse and are
NOT the same words: a verse adapted while being lifted. The one the corpus
carries today is ``watchman-nee-a-life.sw`` Ephesians 5:21 — the source reads
"kunyenyekeana katika kumcha Kristo", the translation "mkinyenyekeana katika
kumcha Kristo", the verb re-personed. Faithful Swahili; not a mined verse.

Reads the committed fixtures, not the database — the fixture is what ships, so a
drifted local DB cannot make this lie. Same reasoning as ``english_audit`` and
``verse_consistency``, and the same shape on purpose.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path

from . import verse_consistency as vc

CONTENT = Path(__file__).resolve().parent / "fixtures" / "content"
NOTES = Path(__file__).resolve().parent / "fixtures" / "translation_notes"

# The shorter quotation must share this proportion of its content words with the
# longer one before the two are accepted as renderings of the SAME verse. See
# rule 2 in the module docstring for the measurement behind the number.
SAME_VERSE_OVERLAP = 0.5

# A source_file that looks like `<slug>.<lang>.json`. Anything else is prose
# naming a Bible edition, which is a real provenance and simply not a file.
_FIXTURE_NAME = re.compile(r"[a-z0-9-]+\.[a-z]{2,3}\.json")
_REF_NUMBERS = re.compile(r"(\d{1,3})\s*:\s*(\d{1,3})")


@dataclass(frozen=True)
class Finding:
    """One `mined` claim the corpus contradicts."""

    notes_file: str
    reference: str
    source_file: str
    translation: str  # as written in the translation
    source: str  # as written in the file it cites

    def __str__(self) -> str:
        return (
            f"{self.notes_file}: {self.reference} claims to be mined from "
            f"{self.source_file}, but the wording differs.\n"
            f"      translation: {self.translation}\n"
            f"      source     : {self.source}"
        )


@lru_cache(maxsize=1)
def _fixture_paths() -> dict[str, Path]:
    return {
        p.name: p
        for sub in ("books", "sermons")
        for p in (CONTENT / sub).glob("*.json")
    }


def names_a_shipped_fixture(source_file: str) -> bool:
    """Does this source_file name a content file we actually ship?

    False for a Bible edition (prose) AND for a fixture-shaped name that isn't
    there — the second is a defect, but it is the caller's to report, because
    "you cited a file that does not exist" and "you cited a Bible" need
    different words.
    """
    return source_file in _fixture_paths()


def looks_like_a_filename(source_file: str) -> bool:
    """Fixture-SHAPED, whether or not it exists."""
    return bool(_FIXTURE_NAME.fullmatch(source_file))


@cache
def cited_quotations(filename: str) -> dict[tuple[int, int], tuple[str, ...]]:
    """``{(chapter, verse): (quote, …)}`` for one shipped fixture.

    Keyed on the numbers alone, deliberately: the book name is localized and
    differs between the two files being compared. Rule 2 above is what makes
    that safe.
    """
    path = _fixture_paths().get(filename)
    if path is None:
        return {}
    found: dict[tuple[int, int], list[str]] = defaultdict(list)
    for row in json.loads(path.read_text(encoding="utf-8")):
        body = row.get("fields", {}).get("body_html")
        if not body:
            continue
        for m in vc.PAIR.finditer(body):
            quote = vc.clean(m.group("quote"))
            if len(quote.split()) < vc.MIN_WORDS:
                continue
            found[(int(m.group("chapter")), int(m.group("verse")))].append(quote)
    return {k: tuple(v) for k, v in found.items()}


def reference_numbers(reference: str) -> tuple[int, int] | None:
    """``"Matthew 15:28a"`` → ``(15, 28)``; ``None`` when there are none.

    The a/b suffix marks which half of a split verse was quoted (see the
    translation-worker skill) and carries no number of its own.
    """
    m = _REF_NUMBERS.search(reference or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def same_verse(a: str, b: str) -> bool:
    """Are these two quotations renderings of the same verse? (Rule 2.)"""
    # _content_words is this package's own helper: diacritic-folded, short words
    # dropped. Reused rather than re-implemented — a second copy of a matching
    # heuristic drifts, and this one carries a measurement (the Arabic
    # vocalisation case) that a fresh implementation would lose.
    wa, wb = vc._content_words(a), vc._content_words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / min(len(wa), len(wb)) >= SAME_VERSE_OVERLAP


def is_verbatim(translation: str, source: str) -> bool:
    """Verbatim in the containment sense — rule 3."""
    t, s = vc.normalise(translation), vc.normalise(source)
    return bool(t) and bool(s) and (t in s or s in t)


def audit(notes_dir: Path | None = None) -> tuple[list[Finding], Counter]:
    """Every contradicted `mined` claim, plus a census of what was examined.

    The census is half the point. A bare "0 findings" from a check that could
    only see 2% of the rows reads as a clean bill of health; the counts say how
    much was actually looked at.
    """
    root = notes_dir or NOTES
    findings: list[Finding] = []
    census: Counter = Counter()
    seen: set[tuple[str, str, str]] = set()

    for path in sorted(root.glob("*/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            census["notes_unreadable"] += 1
            continue
        slug, language = data.get("slug"), data.get("language")
        if not slug or not language:
            census["notes_missing_header"] += 1
            continue
        target = f"{slug}.{language}.json"

        for ref in data.get("references") or []:
            status = ref.get("status")
            census[f"rows_{status}"] += 1
            if status != "mined":
                continue
            reference = (ref.get("reference") or "").strip()
            source_file = (ref.get("source_file") or "").strip()

            if not names_a_shipped_fixture(source_file):
                if looks_like_a_filename(source_file):
                    census["cites_a_missing_file"] += 1
                    findings.append(
                        Finding(path.name, reference, source_file, "", "")
                    )
                else:
                    census["cites_a_bible"] += 1
                continue

            key = (target, reference, source_file)
            if key in seen:
                census["duplicate_row"] += 1
                continue
            seen.add(key)

            numbers = reference_numbers(reference)
            if numbers is None:
                census["reference_has_no_numbers"] += 1
                continue
            mine = cited_quotations(target).get(numbers, ())
            theirs = cited_quotations(source_file).get(numbers, ())
            if not mine:
                census["not_quoted_in_translation"] += 1
                continue
            if not theirs:
                census["not_quoted_in_source"] += 1
                continue

            pairs = [(a, b) for a in mine for b in theirs if same_verse(a, b)]
            if not pairs:
                census["different_book_same_numbers"] += 1
                continue
            if any(is_verbatim(a, b) for a, b in pairs):
                census["verified"] += 1
            else:
                census["contradicted"] += 1
                findings.append(
                    Finding(path.name, reference, source_file, *pairs[0])
                )

    return findings, census


def format_census(census: Counter) -> str:
    """The census as a human report — what was checked, and what wasn't."""
    mined = census.get("rows_mined", 0)
    self_rendered = census.get("rows_self_rendered", 0)
    checkable = census.get("verified", 0) + census.get("contradicted", 0)
    lines = [
        f"Notes rows: {mined} mined, {self_rendered} self-rendered.",
        "",
        f"  cite a Bible edition (not a file, not checkable here): "
        f"{census.get('cites_a_bible', 0)}",
        f"  cite a file that does not exist:                       "
        f"{census.get('cites_a_missing_file', 0)}",
        f"  duplicate rows:                                        "
        f"{census.get('duplicate_row', 0)}",
        f"  reference carries no chapter:verse:                    "
        f"{census.get('reference_has_no_numbers', 0)}",
        f"  verse not quoted in the translation:                   "
        f"{census.get('not_quoted_in_translation', 0)}",
        f"  verse not quoted in the cited file:                    "
        f"{census.get('not_quoted_in_source', 0)}",
        f"  same numbers, different book:                          "
        f"{census.get('different_book_same_numbers', 0)}",
        "",
        f"  CHECKED: {checkable}  →  {census.get('verified', 0)} verbatim, "
        f"{census.get('contradicted', 0)} contradicted",
    ]
    return "\n".join(lines)
