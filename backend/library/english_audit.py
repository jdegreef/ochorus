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
#
# `cars?` was here and was REMOVED: across the whole PD corpus it scored 41 false
# / 0 true. In a library that predates the automobile, "car" is a railroad car
# ("took the cars", "baggage car"), a streetcar/tram ("the Sixth avenue cars"),
# a balloon's car, or a biblical/poetic chariot ("car of state", Song of Songs
# 3:9; "juggernaut car") — never a motor-car except in invented text. It was
# added for the humility-2 "land, cars, and lots of businesses" incident, but the
# tell there was a modern COMMODITY LIST, not the word; a token with 0% precision
# stops triaging and just trains the reader to skim the class. The defence that
# remains: the surviving triggers below (which is what caught the real
# way-into-holiest "computer audience … e-mail me" transcriber note) plus the
# human read-pass the english-qa skill mandates for every anachronism. Do not
# re-add a bare `cars?`; if invented-commodity detection is wanted back, build a
# comma-list-of-modern-goods check with its own precision test instead.
ANACHRONISM = re.compile(
    r"\b(automobiles?|internet|online|websites?|e-?mails?|smartphones?|"
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
#: `washer` is `was`+`her` by the head/tail oracle, but it is an ordinary
#: English agent noun — Amanda Smith's mother was "a beautiful washer and
#: ironer". Named here for the same reason as the others: the oracle cannot tell
#: a real `-er` agent noun on a function-word head from a lost space.
FUSION_EXEMPT = frozenset({
    "anothers", "nomad", "nomen", "noway", "noways", "solet", "sounder",
    "washer",
})
#: A tail must reach this many uses across the English library to count as a word.
COMMON_MIN = 20
#: Above this the fused form is itself a word, not a fusion.
FUSED_MAX = 2
SPACE_BEFORE_PUNCT = re.compile(r"\S\s+[,.;:!?](?:\s|$)")

# An empty parenthesis pair: a cross-reference whose ANCHOR TEXT the sanitizer
# deleted, leaving only the punctuation the author wrote around it. Gutenberg
# spells every internal link `<a href="#nt.A" class="pginternal">Note A.</a>`,
# and `sanitize.DROP_SELECTORS`'s `"[class*=pginternal]"` decomposed it whole
# rather than unwrapping it to its text, so `(Note A.)` reached the reader as
# `()`. Every English work naming Gutenberg as its source was exposed to it.
#
# THE SELECTOR IS NOW FIXED — the deferral this comment used to record has been
# discharged. `sanitize._is_pg_navigation` decides on the link's TEXT, so a
# cross-reference keeps its words and only navigation is dropped, and
# `scripts/audit_keep_predicates.py` is the measurement that made the narrowing safe
# ("what does unwrapping let back in?", answered over every Gutenberg work).
# This class stays, and stays a SYMPTOM test: it catches the damage already on
# the shelf in rows that are never re-imported, and it keeps detecting the
# defect if the predicate is ever narrowed wrong.
#
# A DROPPED ANCHOR IS NOT THE ONLY CAUSE, and the pattern is deliberately a
# symptom test rather than a cause test. Two of the eight sites were plain
# transcription damage in books that do not name Gutenberg as their source:
# `selected-sermons-whitefield` ch41 had "(that I may draw towards a
# conclusion()" for "…conclusion)", and `spurgeon-on-prayer` ch09 "and ()h may
# divine grace" for "and Oh". Do not narrow the regex toward the anchor story —
# an empty pair is wrong however it got there.
#
# The one way this class could go false is a source that PARENTHESISES its
# footnote markers: `corrections.strip_footnote_markers` removes a lone
# `<sup>4</sup>`, so `(<sup>4</sup>)` would settle to `()` and read as this
# defect. Measured at zero — the corpus has no parenthesised `<sup>` in any
# language, and `text()` manufactures no empty pair anywhere — so it is a
# vector, not a finding. Re-measure it if a work ever imports with one.
#
# The test that makes this precise is that the pair must be EMPTY. Measured
# over the whole committed corpus — books, sermons and biographies, every
# language — that was 8 hits across 3 works and every one a real defect, the
# best precision of any class in this module. A parenthesis carrying anything
# at all is spared, and that is the whole rule. The neighbouring idea, an
# UNBALANCED-paren check, was measured too and is exactly what this module
# exists not to be — 57 rows, mostly period prose using a parenthesis across a
# sentence boundary.
#
# ALL EIGHT ARE NOW REPAIRED (six here, two in #1562), so this class ships
# pinned at ZERO in every work — no accepted debt, and the next `()` to reach
# the corpus fails the ratchet in the PR that introduces it. That is the state
# a detector is worth the most in, and the reason to keep it after the
# selector is fixed: the sanitizer is not the only thing that can produce
# one.
#
# Three things it will NOT find, recorded so nobody reads a clean report as
# more than it is:
#
#   * a LONE unmatched `)`, which is the same defect where the source's own
#     transcription dropped the opening paren (`ministry-of-intercession` ch13:
#     "of His spirit to the Father. )"). Balance is what the unbalanced check
#     measures, and it does not clear the precision bar.
#   * quote marks left between the parentheses — `holy-in-christ` ch12 shipped
#     `(see ‘’)` where Gutenberg had `(see ‘<a class="pginternal">Sixth
#     Day</a>’)`. The pair is not empty, so it was the same defect one
#     character out of reach; found by hand and repaired alongside ch10.
#   * a dropped HEADING — what the same sanitizer pass does to the other end
#     of a cross-reference, by two separate routes (`holy-in-christ` ch33 lost
#     all seven of its endnote headings this way; the `english-qa` skill has
#     the mechanisms). Nothing survives to match, and `text()` has no tags to
#     notice an absence with either, so no text-level check can ever find it —
#     read the opening lines of a work's endnote chapter instead.
STRAY_PARENS = re.compile(r"\(\s*\)")

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
#: Below this a chapter is a note or a fragment, where one block is honest
#: prose. Set from the corpus rather than by feel: `life-of-antony` sets 28 of
#: its 45 chapters as a SINGLE block, 11 of them over 300 words, and a floor of
#: 600 exempted the whole book — the most complete instance of this defect in
#: the library, hidden by the constant meant to spare stubs.
PARAGRAPHING_MIN_WORDS = 300

#: Every tag that ends a paragraph-level block, counted in the RAW html.
#: `BLOCK` cannot be used for this: its `<(p|…)>(.*?)</\1>` swallows a
#: `<blockquote>` and the `<p>`s inside it as one match, which undercounts the
#: blocks of any chapter carrying a multi-paragraph quotation and inflates its
#: mean — 34 fixture records are already miscounted that way (`the-fourfold-gospel`
#: ch04 scans as 65 blocks against 90 real ones). For a class whose whole claim
#: is precision, that is a false-positive vector, so this counts closing tags
#: directly and sees the nested paragraphs.
BLOCK_END = re.compile(r"</(?:p|li|blockquote|h[1-6])>", re.I)


def _lost_paragraphing(body_html: str) -> Iterator[tuple[str, str]]:
    """A chapter that lost its paragraphing, not a paragraph that ran long.

    Word count comes from the WHOLE body, not from inside block tags: 204
    records carry prose that no `<p>` encloses (up to 843 words in
    `days-of-heaven-upon-earth` ch12), and a chapter that lost its tags
    altogether would otherwise score zero words and be skipped in silence —
    the one shape this check least wants to miss.
    """
    words = len(text(body_html or "").split())
    if words < PARAGRAPHING_MIN_WORDS:
        return
    blocks = max(1, len(BLOCK_END.findall(body_html or "")))
    mean = words / blocks
    if mean >= MEAN_BLOCK_MAX:
        yield (
            "lost-paragraphing",
            f"{words:,} words in {blocks} block(s) — {mean:,.0f} words each, "
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


#: A footnote whose marker was duplicated and whose TEXT was inlined into the
#: prose. The extractor emitted the in-text marker and the note's own label at
#: the foot of the page as two adjacent superscripts, then ran the note body
#: straight on into the sentence:
#:
#:     Should prove <i>ad infinitum</i>,<sup>1</sup><sup>1</sup>Without end. and eat out
#:
#: which renders as "Should prove ad infinitum,11Without end. and eat out" — the
#: gloss spliced into Bunyan's line, and the doubled digits visible in it.
#:
#: The DOUBLED marker is the whole signal, and it is exact: across the corpus
#: every weld carries one and no legitimate footnote does, so a single <sup>
#: (a real reference, an ordinal, a verse number) never fires. The pair must
#: also carry the SAME number — the second superscript is the note's own label,
#: not a second reference, and two different numbers in a row are two ordinary
#: markers.
#:
#: Where the note ENDS is not mechanical (only ~39% close on a clean full stop),
#: which is why this reports and a person repairs.
WELDED_FOOTNOTE = re.compile(r"<sup>(\d{1,3})</sup>\s*<sup>(\1)</sup>")


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



def _welded_footnotes(body_html: str) -> Iterator[tuple[str, int, str]]:
    """A footnote's text run into the prose behind a doubled marker.

    Reported at the block it lands in, so a repair can be located; the excerpt
    is taken from the HTML rather than the stripped text because the doubled
    marker IS the evidence and `text()` deletes it.
    """
    starts = [m.start() for m in BLOCK.finditer(body_html)]
    for m in WELDED_FOOTNOTE.finditer(body_html):
        i = sum(1 for s in starts if s <= m.start()) - 1
        yield "welded-footnote", max(i, 0), excerpt(body_html, m.start())


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
    for m in STRAY_PARENS.finditer(t):
        yield "stray-parens", excerpt(t, m.start())
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


#: A quote mark opening mid-sentence on a lowercase word ("a king of poor ‘and
#: afflicted persons"). Written mark-first, lookbehind after: a pattern that
#: OPENS on a lookbehind gives `re` no literal to scan for (3x slower).
_MID_OPENER = re.compile(r"[‘“](?<=[a-z] [‘“])(?=[a-z])")
_CLOSER = {"‘": re.compile(r"[\w.,;:!?]’(?![a-z])"), "“": re.compile("”")}

# Above this many unclosed mid-sentence openers per 10,000 words, a work's
# opening marks are a scan's margin rules, not quotation. Real quotation rarely
# opens mid-sentence on a lowercase word and nearly always closes in the same
# block; the OCR of `the-bruised-reed`'s 1838 scan read a rule as `‘`/`“` 178
# times against no `”` at all (38.3 per 10k). Every other work sits at 0-3, the
# highest at 17.1 (`walking-with-god`, whose quotations close with STRAIGHT
# marks — a different defect). Judged as a density because a long book earns a
# few, and `orphan-close-quote` cannot see this: it looks the other way.
ORPHAN_OPENER_DENSITY = 20


def _orphan_openers(t: str) -> Iterator[int]:
    for m in _MID_OPENER.finditer(t):
        if not _CLOSER[m.group()].search(t, m.end()):
            yield m.start()


def _dense_only(per_work: dict[str, list[Finding]], words: Counter[str]) -> Iterator[Finding]:
    for work, rows in per_work.items():
        if words[work] and len(rows) * 10_000 / words[work] > ORPHAN_OPENER_DENSITY:
            yield from rows


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
    openers: dict[str, list[Finding]] = defaultdict(list)
    words: Counter[str] = Counter()
    counts = library_word_counts()

    for rec in records:
        blocks = [text(b) for _, b in BLOCK.findall(rec.body_html or "")]
        for i, t in enumerate(blocks):
            words[rec.work] += len(t.split())
            for label, ex in _check_block(t, rec.is_pd, counts):
                found.append(Finding(label, rec.where, rec.work, i, ex))
            for m in SPACE_BEFORE_PUNCT.finditer(t):
                spb[rec.work].append(
                    Finding("space-before-punct", rec.where, rec.work, i, excerpt(t, m.start()))
                )
            for at in _orphan_openers(t):
                openers[rec.work].append(
                    Finding("orphan-open-quote", rec.where, rec.work, i, excerpt(t, at))
                )
        for label, i, ex in _orphan_quotes(blocks):
            found.append(Finding(label, rec.where, rec.work, i, ex))
        for label, i, ex in _welded_footnotes(rec.body_html or ""):
            found.append(Finding(label, rec.where, rec.work, i, ex))
        # Whole-record, so block -1 as `title-case-vs-body` does: the finding is
        # about the chapter's structure, not about any one block in it.
        for label, ex in _lost_paragraphing(rec.body_html or ""):
            found.append(Finding(label, rec.where, rec.work, -1, ex))
        # A title that hyphenates a word the body capitalises after the hyphen
        # ("Self-denial" vs "Self-Denial") — one of them was retyped.
        body = " ".join(blocks)
        for m in re.finditer(r"\b([A-Za-z]+)-([a-z])\b", rec.title or ""):
            if f"{m.group(1)}-{m.group(2).upper()}" in body:
                found.append(Finding("title-case-vs-body", rec.where, rec.work, -1, rec.title))

    found.extend(_sporadic_only(spb))
    found.extend(_dense_only(openers, words))
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
