"""Typographic quotation marks: decide each straight mark from its context.

Lives here rather than in `scripts/normalize_quotes.py` because TWO callers
need the identical decision and the decision is subtle:

* `scripts/normalize_quotes.py` sweeps the committed fixture, and
* migration `0084` repairs the rows already in a deployed database.

`seed_books` deliberately never rewrites an existing book's chapters, so a
fixture sweep reaches a fresh build and never a running one. Two
implementations of a context-sensitive converter would drift, and the drift
would show as one edition quoted two ways depending on when its row was
written — so there is one.

No Django import: the fixture script runs without a settings module.
"""

from __future__ import annotations

import re
from html import unescape

TAG = re.compile(r"<[^>]+>")
STRAIGHT = '"'
ENTITY = "&quot;"


def mark_counts(text: str) -> tuple[int, int]:
    """(straight, typographic) quotation marks this text sets.

    Guillemets count as typographic, not as a third style. Spanish books set
    « » as the OUTER mark and “ ” as the nested one, so a work using « » with
    straight marks is mixing exactly what this rule exists to stop — but it
    carries no “, and counting only curly marks left three es books invisible
    (prevailing-prayer, jesus-himself-2, clothed-with-strength-and-dignity).

    Returned rather than reduced to the verdict because the corpus guard names
    the numbers in its failure message, and a guard nothing else guards should
    not be running its own private copy of the rule to get them.
    """
    plain = TAG.sub(" ", text)
    straight = plain.count(ENTITY) + plain.count(STRAIGHT)
    curly = plain.count("“") + plain.count("”") + plain.count("«") + plain.count("»")
    return straight, curly


def is_mixed(text: str) -> bool:
    """Does this work show the reader BOTH styles? The one question callers ask.

    Deliberately not a four-valued `quote_style()`: `library/qa.py` already has
    a function of that name with different vocabulary and a different rule (it
    ignores guillemets and counts entities as a third style), and two same-named
    style oracles in one app is a caller away from a silently different verdict.
    """
    straight, curly = mark_counts(text)
    return bool(straight and curly)


# Where a quotation's context resets. Shared by `convert` (the start of a block
# is where a quotation opens) and `mispaired_marks` (a paragraph that closes
# with its quotation still open is a period convention — the next paragraph
# reopens — not a wrongly-set mark). `<br>` counts: verse lines are set with it.
_BLOCK = re.compile(r"</?(?:p|h\d|li|blockquote|div|br|td|tr)\b[^>]*>", re.I)
# A tag as `convert` walks one, unterminated included, so both read the same text.
_TAG_WALK = re.compile(r"<[^>]*>?")
_OPENING_CONTEXT = " \t\n\xa0([{—–-"
_CLOSING_CONTEXT = ".,;:!?)]—–-…"
_MARK_OR_BREAK = re.compile("[\n“”‘’']")


def mispaired_marks(html: str) -> list[str]:
    """Quotations CLOSED with the wrong glyph — excerpts, one per mark.

    Two shapes, both invisible to `mark_counts`, which counts double marks and
    cannot count a straight single at all (it is also the apostrophe):

      * a curly opener closed by a STRAIGHT mark — ‘Search the scriptures', says
        our Lord. A straight mark counts as the closer only where nothing but
        punctuation or a capital follows it, so a possessive plural inside the
        quotation (‘the very hairs of his disciples' heads are …’) stays an
        apostrophe;
      * an OPENER used as the closer — it is written “the living God“; — a “
        standing where a closer stands (after a word, before a space or
        punctuation) while a “ is already open in the same block.

    Never asked of a work that sets „…“, where “ IS the closer (Ukrainian).
    """
    if "„" in html or ("‘" not in html and "“" not in html and "&" not in html):
        return []
    plain = unescape(_TAG_WALK.sub(lambda m: "\n" if _BLOCK.match(m[0]) else "", html))
    found: list[str] = []
    double_open = single_open = False
    for m in _MARK_OR_BREAK.finditer(plain):
        k, ch = m.start(), m[0]
        prev = plain[k - 1] if k else "\n"
        nxt = plain[k + 1] if k + 1 < len(plain) else "\n"
        if ch == "\n":
            double_open = single_open = False
        elif ch == "“":
            if (
                double_open
                and prev not in _OPENING_CONTEXT
                and (nxt.isspace() or nxt in _CLOSING_CONTEXT)
            ):
                found.append(plain[max(0, k - 50) : k + 15])
                double_open = False
            else:
                double_open = True
        elif ch == "”":
            double_open = False
        elif ch == "‘":
            single_open = True
        elif ch == "’":
            single_open = False
        # What is left is a straight ': a closer only inside a ‘ quotation, after
        # a word, and followed by punctuation, a block end, or a non-lowercase word.
        elif (
            single_open
            and not prev.isspace()
            and (
                nxt in "\n" + _CLOSING_CONTEXT
                or (nxt.isspace() and not plain[k + 2 : k + 3].islower())
            )
        ):
            found.append(plain[max(0, k - 50) : k + 15])
            single_open = False
    return found


def uses_guillemets(text: str) -> bool:
    """Does this WORK set « » as its outer quotation mark?

    Asked of the whole work — every chapter joined — and never of one chapter,
    which is the distinction `convert`'s `outer_guillemets` exists to carry.
    """
    return "«" in text or "»" in text


def convert(html: str, *, outer_guillemets: bool) -> tuple[str, int]:
    """Rewrite straight marks typographically, deciding each one from context.

    TWO decisions, not one. Which PAIR the mark belongs to comes first, and
    only then does the preceding character decide whether it opens or closes.

    `outer_guillemets` says which pair is the OUTER one, and it is the caller's
    to answer because it is a fact about the WORK, not about this chapter:

      * False — the work quotes with “ ”, so every mark is “ ”. Every English
        work is this one.
      * True — the work sets « » outside and “ ” nested, as the Spanish books
        do. A mark inside an open « … » span is the nested level; a mark
        outside one is the outer level.

    It is a parameter rather than something read off `html` because a chapter
    of a « »-quoting book can easily contain no guillemet of its own, and
    deciding per chapter would then set that one chapter's quotations in “ ”
    and the rest of the book's in « ». The question belongs to the work.

    Getting this wrong in the other direction is what the parameter fixes: the
    first version decided the outer pair from depth alone, so a guillemet-free
    work took « » — which would have put Spanish outer marks into English
    prose. It never fired, because the English works were normalised before
    guillemets were understood at all and none has been mixed since, but a
    single newly-imported mixed English book would have tripped it.

    Depth is per CALL, and a call is one chapter, so neither caller can carry
    an unclosed « across a chapter boundary.
    """
    out: list[str] = []
    i, n, changed = 0, len(html), 0
    depth = 0
    before = ""  # the last VISIBLE character; "" at the start of a block
    while i < n:
        # Never touch anything inside a tag: attribute values are quoted too.
        if html[i] == "<":
            j = html.find(">", i)
            j = n if j == -1 else j + 1
            if _BLOCK.match(html, i):
                before = ""
            out.append(html[i:j])
            i = j
            continue
        if html.startswith(ENTITY, i):
            width = len(ENTITY)
        elif html[i] == STRAIGHT:
            width = 1
        else:
            if html[i] == "«":
                depth += 1
            elif html[i] == "»":
                depth = max(0, depth - 1)
            before = html[i]
            out.append(html[i])
            i += 1
            continue

        # What PRECEDES the mark decides it, and nothing else. A mark following
        # a word or its punctuation closes; a mark following a space, a bracket,
        # a dash, or the start of a block opens. An INLINE tag is transparent:
        # "<i>seen</i>" closes after the n, not after the `>`.
        #
        # Earlier versions were wrong in ways only the corpus showed:
        #
        #   * the start of a block has to open — a quotation opening a paragraph
        #     has `<p>` and nothing else to its left, and without this EVERY
        #     paragraph-initial quotation became a closing mark. That was first
        #     done by counting ANY tag's `>` as opening context, which set
        #     `“<i>seen</i>“` — the backwards closers of the 2026-09-11 sweep
        #     (all thirteen in evening-by-evening follow a `</i>`);
        #   * "followed by punctuation means closing" breaks on a quotation that
        #     opens with an ellipsis — godliness ch14 has
        #     `John 17:14: "...and the world has hated them` — and on sources
        #     that set a space inside the marks, `" Aggressive Christianity ,"`.
        #
        # The preceding character answers all of those correctly on its own.
        opens = not before or before.isspace() or before in "([{—–-"
        if outer_guillemets and depth == 0:
            before = "«" if opens else "»"
        else:
            before = "“" if opens else "”"
        out.append(before)
        changed += 1
        i += width
    return "".join(out), changed


def convert_work(bodies: list[str], label: str) -> tuple[list[str], int]:
    """Convert every body of ONE work. The unit both callers actually have.

    The gate and the outer-pair question are asked HERE, once, of the joined
    work — because both are facts about the work and getting either one per-row
    is a bug the corpus has already produced:

      * a chapter wholly straight-quoted inside a mixed book must still be
        converted, so the mixed test cannot be per row;
      * a chapter of a « »-quoting book carrying no guillemet of its own must
        still take « », or that one chapter ends up quoted unlike its book.

    Written once rather than in each caller because the fixture sweep and
    migration 0082 have to reach the same text for the same work — a fresh
    build loads the fixture, a deployed database was repaired by the migration,
    and a reader must not be shown two different editions of one book depending
    on when its row was written. That agreement used to rest on a test
    comparing two hand-written copies of this protocol; now there is one.

    Returns the bodies unchanged, and 0, for a work that does not mix styles.
    """
    joined = "".join(bodies)
    if not is_mixed(joined):
        return list(bodies), 0
    outer = uses_guillemets(joined)
    out: list[str] = []
    total = 0
    for i, body in enumerate(bodies):
        new, changed = convert(body, outer_guillemets=outer)
        if changed:
            assert_punctuation_only(body, new, f"{label}[{i}]")
        out.append(new)
        total += changed
    return out, total


# The marks `convert` is allowed to move, and nothing else.
_MARKS = re.compile(r'["“”«»]')


def rendered_without_marks(text: str) -> str:
    """Everything the reader sees EXCEPT the quotation marks themselves.

    Stated as a subtraction rather than as an allowlist of scripts, which is
    what it was: `[0-9A-Za-zÀ-ɏ؀-ۿЀ-ӿ]` covers Latin, Arabic and Cyrillic and
    silently drops Devanagari — so on the Hindi editions the wording half of
    `assert_punctuation_only` was comparing "" with "" and guarding nothing, on
    exactly the works whose script no reviewer here can proofread. Subtracting
    also widens the guard for every language at once: punctuation, digits and
    whitespace are now compared too, and none of them is `convert`'s to move.

    Entities are unescaped FIRST. `&quot;` literally contains q-u-o-t, so
    comparing raw strings reports "text changed" the moment an entity becomes a
    curly mark — which is what this assertion caught on its first run. What must
    be identical is what the reader sees, not the storage form.
    """
    return _MARKS.sub("", unescape(TAG.sub("", text)))


def assert_punctuation_only(before: str, after: str, where: str) -> None:
    """Guard both callers: only quote characters may have moved.

    This is what makes it safe to run over scripture, whose WORDING is
    protected byte-for-byte — quotation marks are typography, not the text.
    Shared rather than duplicated because a repair that skipped the assertion
    would be the one place it was needed.
    """
    assert TAG.findall(before) == TAG.findall(after), f"{where}: tag sequence moved"
    assert rendered_without_marks(before) == rendered_without_marks(after), (
        f"{where}: text other than the quotation marks changed"
    )
