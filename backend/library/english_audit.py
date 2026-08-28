"""Scan English source text for the import-defect classes we keep finding.

Every check here was written from a real instance found the expensive way —
during translation, after the defect had already propagated into three to six
language editions. The worst was *Humility* ch04, where the import put words in
Andrew Murray's mouth (an invented objection about Christians owning "land,
cars, and lots of businesses" — cars, in an 1895 devotional) and Luganda,
Arabic and Swahili had all reproduced it faithfully, as a translator should.
The point of this module is to find the rest before that happens again.

PRECISION IS THE WHOLE GAME. A first version of this scanner reported 8,917
findings, of which the overwhelming majority were false: it flagged
17th-century spaced punctuation as an artifact, every capitalised word
beginning with I as a fused drop cap, and "A SHORT" as broken small caps. A
scanner nobody trusts is worse than none, because its output gets skimmed. So
each check below is narrowed by a test that distinguishes the defect from the
convention, and the comment says what that test is. Do not add a check without
one.

## Entry points, because there are two moments worth checking

`audit_records` is the core and takes whatever you can give it. The adapters
differ only in where the text comes from:

* `audit_fixtures` — the whole English corpus: books and sermons off
  `fixtures/content/*.en.json`, plus every author biography out of
  `authors.json`. This is the standing corpus scan and what the CI ratchet
  measures.
* `audit_book` / `audit_sermon` — a single work's **database rows**. The
  importers need this: at the moment an import finishes, the work exists only
  in the DB, and the fixture will not be regenerated until later. Checking the
  fixture at import time would check the previous import.

Nothing here writes. Repairs go through `corrections.BODY_CORRECTIONS` (which
the release chain re-applies on every deploy) or `source_fixes` — see the
`english-qa` skill for which class goes where.
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache
from itertools import chain
from pathlib import Path

from library.content_fixtures import (
    BOOKS_DIR,
    SERMONS_DIR,
    authors_by_slug,
)

# NOT `library.text.html_to_text`, which collapses runs of whitespace. Two of
# the checks here are ABOUT whitespace — `space-before-punct` and `hyphen-space`
# — so normalising it away would delete the signal they exist to find.
#
# Inline tags are removed rather than spaced, because spacing them MANUFACTURES
# the defect: `<em>The True Vine</em>, dedicating` became "Vine , dedicating"
# and every italicised title followed by a comma read as an italics-strip
# artifact. That was 2,457 of 4,178 raw space-before-punct hits — 59% — and it
# is worst in the biographies, where citing works in italics is the house style.
# Only INLINE tags are dropped. Everything else — a nested <p> inside a
# blockquote, a <br> — still becomes a space, or sentences fuse across it and
# `run-together` starts firing on the seam (11 findings became 30 when this was
# applied to every tag indiscriminately).
INLINE_TAG = re.compile(r"</?(?:em|i|b|strong|cite|a|span|sup|sub|small|u|code)\b[^>]*>", re.I)
TAG = re.compile(r"<[^>]+>")
BLOCK = re.compile(r"<(p|h2|h3|h4|blockquote|li)>(.*?)</\1>", re.S)

# An anachronism is only a defect in a book its author could not have written it
# in. Gareth Evans (b. 1938) may mention television; Andrew Murray may not.
# House-written originals are exempt for the same reason.
PD_CUTOFF = 1930


@dataclass(frozen=True)
class Record:
    """One piece of English prose to check.

    `where` is a human label that lands in the report ("humility-2 ch04");
    `work` is the slug, and is what both the ratchet and the space-before-punct
    check key on — the latter needs a whole work's counts before it can tell an
    artifact from a house style (see `_sporadic_only`).
    """

    where: str
    work: str
    title: str
    body_html: str
    is_pd: bool


@dataclass(frozen=True)
class Finding:
    label: str
    where: str
    work: str
    block: int
    excerpt: str


# --- checks ---------------------------------------------------------------

# Matched against a lowercased copy rather than with re.I: a 14-branch
# alternation under re.I was 32% of a whole-corpus scan (1.56s of 4.9s), and
# `str.lower()` is a C loop (0.68s). Offsets survive because no block in the
# corpus changes length when lowercased, and `excerpt` reads the original text.
ANACHRONISM = re.compile(
    r"\b(cars?|automobiles?|internet|online|websites?|e-?mails?|smartphones?|"
    r"computers?|television|tv|social media|podcasts?|credit cards?|ceos?)\b"
)

# The test that makes this precise: the split letters must REJOIN into a real
# word. "L ORD" -> LORD is the defect (stepping-stones-2 ch02). "A SHORT" ->
# ASHORT is not a word, so it is just a small-caps opening. That single test
# took this check from 233 findings to 8.
SMALLCAP_WORDS = {
    "LORD", "GOD", "JESUS", "CHRIST", "SPIRIT", "FATHER", "SON",
    "KING", "HOLY", "AMEN", "SELAH", "ISRAEL",
}
BROKEN_SMALLCAPS = re.compile(r"\b([A-Z])\s+([A-Z]{2,})\b")

# A fused drop cap is "Ithink" -> I + think. The test is that the REMAINDER is a
# common word; without it the pattern matches Indian, Inquire, Ireland, In...
FUSED_TAIL = {
    "think", "thank", "have", "know", "will", "want", "believe",
    "remember", "asked", "said", "went", "saw", "am", "was", "had",
    "shall", "would", "could", "should", "must", "wish", "hope",
    "love", "pray", "cannot", "never", "always", "once", "often",
}
DROPCAP_FUSED = re.compile(r"\b(I)([a-z]{2,})\b")

HYPHEN_SPACE = re.compile(r"\b\w+-\s+\w+\b")
RUN_TOGETHER = re.compile(r"\b[a-z]{3,}\.[A-Z][a-z]{2,}\b")

# `run-together` catches SENTENCE fusion (a lost space after a full stop). This
# is the same defect inside a sentence: "weresafe", "tospeak", "andhappiness".
#
# The rule that makes it precise, measured against the whole English corpus:
#
#   1. The head is a function word that CANNOT begin an English word. English
#      does not compound `to`+verb or `and`+noun, so that shape is a lost space.
#      The productive prefixes are excluded by their absence here — `in`, `be`,
#      `a`, `up`, `for`, `as`, `at`, `by`, `un`, `re` gave `inborn`,
#      `befitting`, `aboard`, `uphill`, `forgiver`, 253 candidates between them
#      and almost all real words.
#   2. The tail is a word the library uses OFTEN (`COMMON_MIN`). Without this
#      the same heads match `tornado`, `torchlight`, `buttery`, `shearings` —
#      35 findings, nearly all false, which is the 8,917-finding failure this
#      module exists to avoid.
#   3. The fused form itself is RARE (`FUSED_MAX`). A real word recurs:
#      `himself` 3,491 times, `today` 445, `willfully` 14. Without this the
#      rule adds `islands`, `shewing`, `whensoever`, `willest`, `willpower`.
#
# All three together find 9 across the corpus and every one is a real defect.
# Both thresholds have margin: at `tail >= 10` it gains two false positives,
# and the true findings all occur exactly once against a cut of two.
FUSION_HEADS = frozenset({
    "an", "and", "been", "but", "from", "had", "has", "have", "he", "him", "if",
    "is", "it", "its", "no", "not", "she", "so", "that", "their", "them",
    "these", "they", "this", "those", "to", "was", "were", "what", "when",
    "will", "you", "your",
})

#: Real words the heads above also produce, and the check's curated test — the
#: same role `FUSED_TAIL` plays for drop caps. `an`, `he`, `no`, `not` and `so`
#: each earn their place (`aninstant`, `hehad`, `nohappiness`, `nointelligence`,
#: `socalled`, `sogenerous`, and `notability` where the text means "no ability
#: to obtain or keep employment"), and each also produces a handful of real
#: words. Listing those is cheaper than losing seven findings.
#:
#: `solet` and `nomen` are not English at all — Latin, from a couplet quoted in
#: `ten-commandments` and from the inscription on Thomas à Kempis's memorial
#: ("cujus nomen perennius quam monumentum"). A foreign quotation is the one
#: thing an English word oracle cannot judge, so they are named here rather
#: than reasoned about.
FUSION_EXEMPT = frozenset({
    "anothers", "nomad", "nomen", "noway", "noways", "solet", "sounder",
})
#: A tail must reach this many uses across the English library to count as a word.
COMMON_MIN = 20
#: Above this the fused form is itself a word, not a fusion.
FUSED_MAX = 2
SPACE_BEFORE_PUNCT = re.compile(r"\S\s+[,.;:!?](?:\s|$)")

# --- lost paragraphing -----------------------------------------------------
#
# A chapter whose blocks average this many words has not lost A paragraph
# break; it has lost its paragraphing. `the-gospel-of-healing` ch03 is 4,602
# words in TWO blocks, one of them 4,571 words carrying an enumerated list
# inside it. Nobody wrote that, and no reader can face it.
#
# MEASURED AT CHAPTER SCALE BECAUSE PER-PARAGRAPH RULES DO NOT WORK HERE. Four
# were tried against the whole corpus and each failed the precision bar this
# module exists to hold:
#
#   * a long block alone — 749 blocks run to 20+ sentences and most are the
#     period's own prose, quoted letters, or Chrysostom, who simply writes long;
#   * a division marker mid-block (`Secondly,`, `II.`, a vocative) — 922 and 954
#     blocks, and a read of nine showed roughly two true: the rest were scripture
#     citations split at `Rom. viii. ‖ 32.`, markers inside a quoted psalm, and
#     run-in enumerations Bunyan wrote deliberately;
#   * a long quotation fused to its commentary — 3 findings, of which one matched
#     a `”` inside a bracketed editorial note;
#   * a mid-block speech attribution — 8 findings, mostly Wesley citing apostles
#     (`Paul: … James: … John:`) rather than dialogue.
#
# The reason none of them works is that there is no oracle. `word-fusion` can
# ask the library whether a word exists; "should this have been two paragraphs"
# has nothing to ask. At CHAPTER scale the question changes and needs no oracle:
# against a corpus median of 92 words per block and a 99th percentile of 379, a
# chapter averaging 400+ is broken however it got that way.
#
# Seven chapters across three works exceed it, and all seven were read: four
# chapters of `the-gospel-of-healing` (up to 2,301 w/block), two Whitefield
# sermons, and `on-the-priesthood` ch06.
#
# The cut is deliberately on the conservative side, and one case shows by how
# much: `on-the-incarnation` ch44 is a 78-word editorial summary followed by the
# whole chapter as a single 713-word block — plainly the same defect, and it
# sits just outside at 396. Lowering the bar to catch it would admit the ordinary
# long-winded chapter as well, and a class that reports those is the 8,917-finding
# failure this module was built after. Under-reporting is the safer error here:
# every finding it does make is one a reader can confirm at a glance.
#
# Deliberately NOT auto-fixable: where a paragraph breaks is a judgement about
# the prose, not a rule, so this reports and a person repairs.
MEAN_BLOCK_MAX = 400
#: Below this a work is front matter or a stub, where one block is normal.
PARAGRAPHING_MIN_WORDS = 600


def _lost_paragraphing(blocks: list[str]) -> Iterator[tuple[str, str]]:
    words = sum(len(t.split()) for t in blocks)
    if not blocks or words < PARAGRAPHING_MIN_WORDS:
        return
    mean = words / len(blocks)
    if mean >= MEAN_BLOCK_MAX:
        yield (
            "lost-paragraphing",
            f"{words:,} words in {len(blocks)} block(s) — {mean:,.0f} words each, "
            f"against a corpus median of 92",
        )



# Overlaps `corrections.BODY_CORRECTIONS` by design: that table REPAIRS these in
# the books they were found in, this one DETECTS them anywhere, including a book
# imported tomorrow. Matched on word boundaries — a bare substring search made
# "Brazilia" fire on every correct "Brazilian" (6 of 23 findings were false), the
# exact trap the BODY_CORRECTIONS entry for it warns about.
MISSPELLINGS = {
    "Millenium": "Millennium", "capitol city": "capital city",
    "Stocklholm": "Stockholm", "Guatamalan": "Guatemalan",
    "Malasia": "Malaysia", "Chapultapek": "Chapultepec",
    "Brazilia": "Brasília", "Deja Vue": "déjà vu",
    "Bob Beamer": "Bob Beamon", "Nicki Cruz": "Nicky Cruz",
    "Cuidad": "Ciudad", "Heratii": "Horatii", "Te quyiero": "Te quiero",
    "selfexaltation": "self-exaltation", "allpervading": "all-pervading",
    "Weibe": "Wiebe (spelled Wiebe elsewhere in the same book)",
}
MISSPELLED = re.compile(
    r"\b(?:{})\b".format("|".join(re.escape(k) for k in sorted(MISSPELLINGS, key=len, reverse=True)))
)

# Findings a machine may apply unattended, because the defect and its repair are
# both unambiguous: the split letters rejoin into exactly one real word. Every
# other class needs a human against the source — an anachronism could be the
# author quoting someone, a misspelling could be a period spelling, and the
# *Humility* "cars" case needed someone to read the 1895 edition to know the
# real text was "The poor, who have nothing in themselves". The `english-qa`
# skill enforces this split; it is named here so the two cannot drift apart.
AUTO_FIXABLE = frozenset({"broken-smallcaps"})

# The classes a normalization pass should own rather than per-book string pairs
# (~690 instances corpus-wide). Reported, never auto-applied, until that pass
# lands — see the english-qa skill.
MECHANICAL = frozenset({"hyphen-space", "space-before-punct"})


def text(fragment: str) -> str:
    return html.unescape(TAG.sub(" ", INLINE_TAG.sub("", fragment)))


def excerpt(t: str, i: int, w: int = 65) -> str:
    return " ".join(t[max(0, i - w) : i + w].split())


def _word_fusion(t: str, counts: Counter[str]) -> Iterator[tuple[str, str]]:
    """Two words run together inside a sentence — see FUSION_HEADS above."""
    for m in re.finditer(r"\b[a-z]{5,}\b", t):
        word = m.group(0)
        if word in FUSION_EXEMPT or counts.get(word, 0) > FUSED_MAX:
            continue
        for k in range(2, len(word) - 2):
            if word[:k] in FUSION_HEADS and counts.get(word[k:], 0) >= COMMON_MIN:
                yield "word-fusion", excerpt(t, m.start())
                break


def _check_block(t: str, is_pd: bool, counts: Counter[str]) -> Iterator[tuple[str, str]]:
    if is_pd:
        for m in ANACHRONISM.finditer(t.lower()):
            yield "anachronism", excerpt(t, m.start())
    for m in BROKEN_SMALLCAPS.finditer(t):
        if m.group(1) + m.group(2) in SMALLCAP_WORDS:
            yield "broken-smallcaps", excerpt(t, m.start())
    for m in DROPCAP_FUSED.finditer(t):
        if m.group(2) in FUSED_TAIL:
            yield "dropcap-fused", excerpt(t, m.start())
    for m in HYPHEN_SPACE.finditer(t):
        yield "hyphen-space", excerpt(t, m.start())
    for m in RUN_TOGETHER.finditer(t):
        yield "run-together", excerpt(t, m.start())
    yield from _word_fusion(t, counts)
    for m in MISSPELLED.finditer(t):
        yield "misspelling", excerpt(t, m.start())


def _orphan_quotes(blocks: list[str]) -> Iterator[tuple[str, int, str]]:
    """A closing quote with nothing open.

    Long quotations open every paragraph and close only the last, so an odd
    count mid-run is the convention, not a defect. What is wrong is a block that
    closes when nothing is open — humility-2 ch09 and stepping-stones-2 ch13
    both do this, and in both the speech attribution breaks mid-sentence.
    """
    depth = 0
    for i, t in enumerate(blocks):
        opens, closes = t.count("“"), t.count("”")
        if closes > opens and depth + opens - closes < 0:
            yield "orphan-close-quote", i, excerpt(t, t.find("”"))
        depth = max(0, depth + opens - closes)


# Above this many hits in ONE work, space-before-punct is the era's typography
# rather than an italics-strip artifact. The distribution is sharply bimodal:
# 777 / 647 / 586 in the three 17th-century texts, against 1 or 2 in a modern
# one. Anything in between has never occurred, which is why a flat cut is safe.
SPB_CONVENTION_MIN = 16


def _sporadic_only(per_work: dict[str, list[Finding]]) -> Iterator[Finding]:
    for rows in per_work.values():
        if len(rows) < SPB_CONVENTION_MIN:
            yield from rows


@lru_cache(maxsize=1)
def library_word_counts() -> Counter[str]:
    """How often each lowercase word occurs across the English library.

    The oracle behind `word-fusion`: it is what separates `to`+`speak` from
    `to`+`rnado`, and a fusion from a rare real word.

    Derived from the committed fixture rather than from whatever is being
    audited, so the check behaves the same at both entry points. That is not a
    convenience — a per-work vocabulary was measured and is unusable: inside a
    single book `ever`, `self` and `land` do not recur often enough, so
    `whenever`, `himself` and `island` all read as fusions and one corpus scan
    produced 60 findings, nearly all false.

    Cached: the corpus is 94 works, and `audit_book` is called per import.
    """
    counts: Counter[str] = Counter()
    # The same corpus `audit_fixtures` scans — biographies included, or a word
    # that is common in the bios but nowhere else reads as unknown and the
    # fusions there go unjudged.
    for rec in chain(_fixture_records(), _bio_records()):
        for _, block in BLOCK.findall(rec.body_html or ""):
            for w in re.findall(r"[A-Za-z]+", text(block)):
                counts[w.lower()] += 1
    return counts


def audit_records(records: Iterable[Record]) -> list[Finding]:
    """Every finding across `records`, per-work aggregation applied."""
    found: list[Finding] = []
    spb: dict[str, list[Finding]] = defaultdict(list)
    counts = library_word_counts()

    for rec in records:
        blocks = [text(b) for _, b in BLOCK.findall(rec.body_html or "")]
        for i, t in enumerate(blocks):
            for label, ex in _check_block(t, rec.is_pd, counts):
                found.append(Finding(label, rec.where, rec.work, i, ex))
            for m in SPACE_BEFORE_PUNCT.finditer(t):
                spb[rec.work].append(
                    Finding("space-before-punct", rec.where, rec.work, i, excerpt(t, m.start()))
                )
        for label, i, ex in _orphan_quotes(blocks):
            found.append(Finding(label, rec.where, rec.work, i, ex))
        # Whole-record, so block -1 as `title-case-vs-body` does: the finding is
        # about the chapter's structure, not about any one block in it.
        for label, ex in _lost_paragraphing(blocks):
            found.append(Finding(label, rec.where, rec.work, -1, ex))
        # A title that hyphenates a word the body capitalises after the hyphen
        # ("Self-denial" vs "Self-Denial") — one of them was retyped.
        body = " ".join(blocks)
        for m in re.finditer(r"\b([A-Za-z]+)-([a-z])\b", rec.title or ""):
            if f"{m.group(1)}-{m.group(2).upper()}" in body:
                found.append(Finding("title-case-vs-body", rec.where, rec.work, -1, rec.title))

    found.extend(_sporadic_only(spb))
    return found


# --- adapters -------------------------------------------------------------


def _is_pd(death_year: int | None) -> bool:
    return bool(death_year) and death_year < PD_CUTOFF


def _fixture_records(slug: str | None = None) -> Iterator[Record]:
    """English books and sermons as they stand in the committed fixture."""
    authors = authors_by_slug()
    paths = sorted(BOOKS_DIR.glob("*.en.json")) + sorted(SERMONS_DIR.glob("*.en.json"))
    for p in paths:
        work = p.name[: -len(".en.json")]
        if slug and slug != work:
            continue
        recs = json.loads(p.read_text(encoding="utf-8"))
        meta = next(
            (r["fields"] for r in recs if r["model"] in ("library.book", "library.sermon")), {}
        )
        author = authors.get((meta.get("author") or [None])[0]) or {}
        is_pd = _is_pd(author.get("death_year"))
        for rec in recs:
            f = rec["fields"]
            if rec["model"] == "library.chapter":
                where = f"{work} ch{f['order']:02d}"
            elif rec["model"] == "library.sermon":
                where = f"{work} (sermon)"
            else:
                continue
            yield Record(where, work, f.get("title", ""), f.get("body_html", ""), is_pd)


def _bio_records(slug: str | None = None) -> Iterator[Record]:
    """Author biographies, from `authors.json`.

    These were the one English content type nothing checked, and they have a
    different provenance from everything else: we *write* them, in modern
    English, rather than importing a public-domain scan. So `is_pd=False` — a
    biographer may mention television and the author may not — and what the
    checks earn here is the typography and transcription damage that afflicts
    any prose. Invented detail, the failure mode a written bio actually has, is
    not something a regex can see; that stays a human-review job (see the
    `write-biography` skill).
    """
    for author_slug, fields in authors_by_slug().items():
        if slug and slug != author_slug:
            continue
        body = fields.get("bio_html") or ""
        if body:
            yield Record(f"{author_slug} (bio)", author_slug, fields.get("name", ""), body, False)


def audit_fixtures(slug: str | None = None) -> list[Finding]:
    return audit_records(chain(_fixture_records(slug), _bio_records(slug)))


def audit_book(book) -> list[Finding]:
    """A `Book` and its chapters straight from the database.

    Used by `import_ochorus` on what it has just written — at that point the
    fixture still describes the *previous* import, so auditing the fixture would
    check the wrong text.
    """
    is_pd = _is_pd(getattr(book.author, "death_year", None))
    return audit_records(
        Record(f"{book.slug} ch{c.order:02d}", book.slug, c.title or "", c.body_html or "", is_pd)
        for c in book.chapters.all().only("order", "title", "body_html")
    )


def audit_sermon(sermon) -> list[Finding]:
    is_pd = _is_pd(getattr(sermon.author, "death_year", None))
    return audit_records(
        [
            Record(
                f"{sermon.slug} (sermon)",
                sermon.slug,
                sermon.title or "",
                sermon.body_html or "",
                is_pd,
            )
        ]
    )


# --- reporting ------------------------------------------------------------


def counts(findings: Iterable[Finding]) -> dict[str, int]:
    return dict(Counter(f.label for f in findings))


def counts_by_work(findings: Iterable[Finding]) -> dict[str, dict[str, int]]:
    """Per-work class counts — the shape the ratchet is keyed on."""
    per: dict[str, Counter] = defaultdict(Counter)
    for f in findings:
        per[f.work][f.label] += 1
    return {work: dict(sorted(c.items())) for work, c in sorted(per.items())}


# The CI ratchet, keyed PER WORK. `tests_english_audit.py` fails when any work's
# class grows, so an import that drags in forty new hyphen-space artifacts is
# caught at the PR rather than eighteen months later by a translator.
#
# Per work rather than one set of corpus-wide counters, for the same reason the
# content fixture is one file per work: a shared tail makes parallel sessions
# collide. With flat counts, adding any ordinary English book (~12 findings)
# pushes a class past its pin and red-lights a PR that has nothing to do with
# English QA, re-pinning touches lines every other in-flight PR also touches,
# and a regression in one book cancels against a fix in another so the ratchet
# reads clean. Keyed per work, new works add their own line, git auto-merges
# disjoint ones, and nothing cancels.
BASELINE_PATH = Path(__file__).resolve().parent / "data" / "english_audit_baseline.json"


def read_baseline() -> dict[str, dict[str, int]]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["works"]


def write_baseline(per_work: dict[str, dict[str, int]]) -> None:
    BASELINE_PATH.write_text(
        json.dumps(
            {
                "_comment": (
                    "Ratchet for library/tests_english_audit.py — a work's class may "
                    "shrink but never grow. Regenerate with `manage.py audit_english "
                    "--update-baseline` and say in the commit message what you fixed."
                ),
                "works": per_work,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )


def format_report(findings: list[Finding], limit: int = 8, klass: str | None = None) -> str:
    """The human summary. Ordered by class size — the long tail is the noise."""
    if klass:
        findings = [f for f in findings if f.label == klass]
    by_label: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_label[f.label].append(f)

    lines = [f"{len(findings)} findings across {len(by_label)} classes"]
    for label in sorted(by_label, key=lambda k: -len(by_label[k])):
        rows = by_label[label]
        note = ""
        if label in AUTO_FIXABLE:
            note = "  [safe to auto-apply]"
        elif label in MECHANICAL:
            note = "  [mechanical — wants a normalization pass, not string pairs]"
        lines.append(f"\n=== {label}  ({len(rows)}){note}")
        for f in rows[:limit] if limit else rows:
            lines.append(f"   {f.where} p{f.block}: {f.excerpt[:145]}")
        if limit and len(rows) > limit:
            lines.append(f"   … {len(rows) - limit} more")
    return "\n".join(lines)


def report(cmd, findings: list[Finding], slug: str) -> None:
    """Print a per-class summary to a management command's stdout.

    Lives here rather than in each importer because there are seven writers of
    English text — `import_ochorus`, the five that go through
    `ingest.upsert_book`, and `import_sermons` — and a gate with six holes in it
    is not a gate. Reports; never rewrites (see `AUTO_FIXABLE`).
    """
    if not findings:
        cmd.stdout.write("  clean — no English defects found")
        return
    by_class = counts(findings)
    cmd.stdout.write(cmd.style.WARNING(f"  ⚠ {len(findings)} English defect(s) to review:"))
    for label in sorted(by_class, key=lambda k: -by_class[k]):
        cmd.stdout.write(f"      {by_class[label]:4d}  {label}")
    cmd.stdout.write(f"      → manage.py audit_english {slug} --examples 0")
