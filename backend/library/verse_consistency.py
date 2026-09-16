"""Does a language quote the same verse the same way everywhere?

A translator sees one work. Nobody sees the language. So two workers — or two
chapters of one work, or the same work a month apart — can render John 14:27
three different ways and every per-job gate stays green, because each rendering
is fine on its own. #756 found this *inside* one book (Job 13:15 quoted in two
chapters with opposite meanings under one citation) and answered it with a
whole-book reconciliation pass. Across works there is no such pass, and running
translation sessions in parallel removes the one thing that used to catch it:
a single worker's memory of what it wrote last time.

So this reads the shipped corpus per language and asks the only question that
matters here — is one reference rendered more than one way?

**No Bible parsing.** Book names are localized (`Yokaana`, `Mathayo`, `مزمور`),
and pythonbible only knows English, so `scripture.extract_citations` cannot see
this content at all. It also isn't needed: within a language the citation *as
written* is a perfectly good key, and if two works spell the book name
differently that is itself worth knowing.

Precision is the whole game — a report nobody trusts gets skimmed, which is how
`english_audit` began life with 8,917 findings. Two rules do most of the work:

1. **The citation must follow the closing quote mark almost immediately.**
   Scanning backwards for "the last quote before the citation" pairs a verse
   with whatever was quoted nearby: it offered Ephesians 4:26's *let not the sun
   go down upon your wrath* as a rendering of Luke 17:1. Requiring adjacency
   dropped the finding count 95 -> 69 and took that class with it.
2. **Containment is not conflict.** Quoting half a verse in one place and all of
   it in another is normal, so a rendering that is a substring of another is the
   same rendering. Only genuinely divergent wordings are reported.

Punctuation and spacing are normalised away before comparing; **diacritics are
not**. In Arabic, vocalisation is a semantic signal — the corpus convention is
that a vocalised quotation claims to be verbatim Van Dyck — so two spellings
that differ only in harakat are a real difference, not noise.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CONTENT = Path(__file__).resolve().parent / "fixtures" / "content"
BASELINE_PATH = Path(__file__).resolve().parent / "data" / "verse_consistency_baseline.json"

# A quoted span, then a citation, with only closing punctuation between them.
# The `[^«»“”]` inside the quote stops one match swallowing several quotations.
PAIR = re.compile(
    r"[«“„](?P<quote>[^«»“”]{12,600}?)[»”]"  # the quotation
    r"\s*(?:<[^>]+>\s*)?"  # an inline tag may close between the two
    r"[^()\w]{0,8}"  # a comma, dash, space — not a sentence
    r"\(\s*(?P<book>[^)]{0,40}?)(?P<chapter>\d+)\s*:\s*(?P<verse>\d+)\s*\)",
    re.S,
)

_TAG = re.compile(r"<[^>]+>")
_ENTITY = re.compile(r"&[a-z]+;|&#\d+;")
MIN_WORDS = 4  # below this a "quotation" is a fragment and matches everything
# A word this long carries meaning; shorter ones are articles, prepositions and
# conjunctions that two unrelated clauses of the same verse share by accident
# ("de", "la", "que", "los"). Used only to ask whether two renderings quote the
# same words at all — never to compare wording, which stays exact.
MIN_WORD_LEN = 4
#: Arabic alef variants folded to bare alef for the same-words test only. Van
#: Dyck sets ٱ (alef wasla) where an unvocalised quotation writes ا, which is a
#: spelling of the same word — without this, رؤيا 1:8's two renderings of ONE
#: clause shared no word and were exempted as different clauses.
_ALEF = str.maketrans("\u0671\u0623\u0625\u0622", "\u0627\u0627\u0627\u0627")


def clean(fragment: str) -> str:
    """Readable text: tags and entities out, whitespace collapsed."""
    return re.sub(r"\s+", " ", _ENTITY.sub(" ", _TAG.sub("", fragment))).strip()


def normalise(text: str) -> str:
    """Comparison key: case-folded, punctuation and spacing dropped.

    Diacritics are DELIBERATELY kept — see the module docstring.
    """
    return "".join(
        c
        for c in text.casefold()
        if not unicodedata.category(c).startswith("P") and not c.isspace()
    )


@dataclass(frozen=True)
class Rendering:
    key: str  # normalised, for comparison
    text: str  # as written, for the report
    where: str  # file it came from


def _fixture_bodies():
    """(language, filename, body_html) for every non-English shipped work."""
    for sub in ("books", "sermons"):
        for path in sorted((CONTENT / sub).glob("*.json")):
            language = path.name.split(".")[-2]
            if language == "en":
                continue
            for row in json.loads(path.read_text(encoding="utf-8")):
                body = row.get("fields", {}).get("body_html")
                if body:
                    yield language, path.name, body


def scan(bodies=None) -> dict[tuple[str, str], list[Rendering]]:
    """Group every cited quotation by (language, reference-as-written)."""
    found: dict[tuple[str, str], list[Rendering]] = defaultdict(list)
    for language, where, body in bodies if bodies is not None else _fixture_bodies():
        for m in PAIR.finditer(body):
            quote = clean(m.group("quote"))
            if len(quote.split()) < MIN_WORDS:
                continue
            book = clean(m.group("book")).strip(" .,;:")
            ref = f"{book} {m.group('chapter')}:{m.group('verse')}".strip()
            found[(language, ref)].append(Rendering(normalise(quote), quote, where))
    return dict(found)


def _content_words(text: str) -> frozenset[str]:
    """The words long enough to mean something, WITHOUT diacritics.

    Diacritics are stripped here and nowhere else, and the distinction is the
    whole safety of the exemption below. `normalise` keeps them on purpose:
    in Arabic a vocalised quotation claims to be verbatim Van Dyck, so two
    spellings differing only in harakat are a real disagreement (see the module
    docstring). But this function asks a different question — *which words are
    these two quoting?* — and that is about the words, not their pointing.

    Keeping them here was measured and wrong: it exempted 30 Arabic references,
    among them يوحنا 3:16, whose two renderings are the SAME clause, one
    unvocalised and one fully vocalised. Character-exact word sets shared
    nothing, so the pair read as two different clauses and the ratchet would
    have dropped 124 entries to 87 — losing the real findings this module was
    written for.
    """
    return frozenset(
        w
        for w in (
            "".join(
                c for c in normalise(part)
                if not unicodedata.category(c).startswith("M")
            ).translate(_ALEF)
            for part in text.split()
        )
        if len(w) >= MIN_WORD_LEN
    )


def _diverges(renderings: list[Rendering]) -> bool:
    """Do these renderings actually disagree?

    Two exemptions, and both are about a pair that is not competing:

    1. **Containment.** Quoting half a verse in one place and all of it in
       another is normal (see the module docstring).
    2. **No shared words at all.** A verse is often several clauses, and two
       works can quote different ones under the same citation — `Juan 6:68` is
       quoted here as both "¿A quién más iremos?" and "Tú tienes palabras de
       vida eterna", which are the two halves of Peter's answer, not two
       renderings of one sentence. Matching them would force one of them to be
       rewritten into words its own sentence does not contain, degrading an
       accurate quotation into a paraphrase.

    The second exemption is deliberately at ZERO overlap, not "little": two
    translations of the SAME clause practically always keep a content word in
    common, so requiring none at all is what keeps this from excusing real
    drift. Both flagged pairs that survive it prove the point — `Juan 3:6`
    still shares "carne", and `1 Juan 1:9` still shares "fiel", "justo" and
    "maldad", so both remain reported.
    """
    unique: dict[str, Rendering] = {}
    for r in renderings:
        unique.setdefault(r.key, r)
    items = sorted(unique.values(), key=lambda r: len(r.key))
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a.key in b.key or b.key in a.key:
                continue
            if not (_content_words(a.text) & _content_words(b.text)):
                continue
            return True
    return False


def conflicts(grouped=None) -> dict[tuple[str, str], list[Rendering]]:
    """References rendered more than one way, containment excluded."""
    grouped = scan() if grouped is None else grouped
    return {k: v for k, v in grouped.items() if _diverges(v)}


def baseline_counts(found: dict[tuple[str, str], list[Rendering]]) -> dict[str, int]:
    """`{"lg\\tYokaana 14:27": 3}` — the reference AND how many ways it is rendered.

    Pinning only the reference set was not enough, and a deliberately-injected
    conflict proved it: `sw Warumi 10:17` was already listed, so adding a THIRD
    rendering of it changed nothing and the ratchet stayed green. A pinned
    reference would have become a place drift could accumulate unseen. The count
    closes that — the pin is "two ways", so a third fails.
    """
    return {f"{lang}\t{ref}": len({r.key for r in rs}) for (lang, ref), rs in found.items()}


def read_baseline() -> dict[str, int]:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["conflicts"]


def baseline_regressions(
    counts: dict[str, int], previous: dict[str, int] | None = None
) -> list[str]:
    """Pins in ``counts`` that would LOOSEN the committed ratchet, as prose lines.

    The ratchet in ``tests_verse_consistency`` is airtight against drift — a new
    key or a grown count fails CI. What it cannot see is the re-pin itself:
    ``write_baseline`` writes whatever it is handed, so
    ``--update-baseline`` after a batch ABSORBS every conflict that batch
    introduced and CI goes green on the wider number. That is how the pin went
    from 110 conflicts on 2026-08-24 to 322 on 2026-09-16 while the tests passed
    on every commit — 0.62 to 0.78 conflicts per translated edition, so the
    corpus was getting less consistent, not merely bigger.

    Absorbing is sometimes right (a reconciliation you cannot finish today), but
    it is a decision, not a side effect of re-pinning. So the command refuses
    unless ``--absorb`` says so out loud, and this is what it prints.
    """
    old = read_baseline() if previous is None else previous
    return sorted(
        (
            f"{k.replace(chr(9), ' ')}: {old[k]} -> {n} renderings"
            if k in old
            else f"{k.replace(chr(9), ' ')}: NEW, {n} renderings"
        )
        for k, n in counts.items()
        if n > old.get(k, 0)
    )


def write_baseline(counts: dict[str, int]) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(
        json.dumps(
            {
                "_comment": (
                    "Shrink-only ratchet for library/tests_verse_consistency.py. Maps a "
                    "reference to HOW MANY distinct ways its language renders it; a "
                    "count may fall or a reference may leave, neither may grow. "
                    "Regenerate with `manage.py audit_verse_consistency "
                    "--update-baseline` and say in the commit message which renderings "
                    "you reconciled. That command REFUSES a re-pin that would loosen "
                    "the ratchet — absorbing a new or widened conflict needs --absorb "
                    "said out loud, because a silent re-pin is how this file went from "
                    "110 conflicts to 322 with CI green throughout."
                ),
                "conflicts": dict(sorted(counts.items())),
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )


def format_report(found: dict[tuple[str, str], list[Rendering]], language=None) -> str:
    rows = sorted(found.items())
    if language:
        rows = [r for r in rows if r[0][0] == language]
    if not rows:
        return "No divergent renderings found."
    out = [f"{len(rows)} reference(s) rendered more than one way:", ""]
    for (lang, ref), renderings in rows:
        out.append(f"  [{lang}] {ref}")
        seen: set[str] = set()
        for r in renderings:
            if r.key in seen:
                continue
            seen.add(r.key)
            out.append(f"      {r.where}: {r.text[:150]}")
        out.append("")
    return "\n".join(out)
