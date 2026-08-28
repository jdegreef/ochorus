"""Typographic quotation marks: decide each straight mark from its context.

Lives here rather than in `scripts/normalize_quotes.py` because TWO callers
need the identical decision and the decision is subtle:

* `scripts/normalize_quotes.py` sweeps the committed fixture, and
* migration `0082` repairs the rows already in a deployed database.

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


def quote_style(text: str) -> str:
    """"straight", "curly", "MIXED" or "none" — which marks this text sets."""
    plain = TAG.sub(" ", text)
    straight = plain.count(ENTITY) + plain.count(STRAIGHT)
    # Guillemets count as typographic, not as a third style. Spanish books set
    # « » as the OUTER mark and “ ” as the nested one, so a file using « » with
    # straight marks is mixing exactly what this rule exists to stop — but it
    # carries no “, and counting only curly marks left three es books invisible
    # (prevailing-prayer, jesus-himself-2, clothed-with-strength-and-dignity).
    curly = plain.count("“") + plain.count("”") + plain.count("«") + plain.count("»")
    if straight and curly:
        return "MIXED"
    return "straight" if straight else ("curly" if curly else "none")


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
    while i < n:
        # Never touch anything inside a tag: attribute values are quoted too.
        if html[i] == "<":
            j = html.find(">", i)
            j = n if j == -1 else j + 1
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
            out.append(html[i])
            i += 1
            continue

        # What PRECEDES the mark decides it, and nothing else. A mark following
        # a word or its punctuation closes; a mark following a space, a bracket,
        # a dash, or the end of a tag opens.
        #
        # Two earlier versions also consulted the following character, and both
        # were wrong in ways only the corpus showed:
        #
        #   * ">" had to join the opening set — a quotation opening a paragraph
        #     has `<p>` and nothing else to its left, and without this EVERY
        #     paragraph-initial quotation became a closing mark;
        #   * "followed by punctuation means closing" breaks on a quotation that
        #     opens with an ellipsis — godliness ch14 has
        #     `John 17:14: "...and the world has hated them` — and on sources
        #     that set a space inside the marks, `" Aggressive Christianity ,"`.
        #
        # The preceding character answers all of those correctly on its own.
        before = out[-1][-1:] if out else ""
        opens = not before or before.isspace() or before in "([{—–->"
        if outer_guillemets and depth == 0:
            out.append("«" if opens else "»")
        else:
            out.append("“" if opens else "”")
        changed += 1
        i += width
    return "".join(out), changed


def rendered_letters(text: str) -> str:
    """Rendered letters and digits only.

    Entities must be unescaped FIRST. `&quot;` literally contains q-u-o-t, so
    comparing raw strings reports "letters changed" the moment an entity becomes
    a curly mark — which is exactly what the assertion caught on the first run.
    What must be identical is what the reader sees, not the storage form.
    """
    return re.sub(r"[^0-9A-Za-zÀ-ɏ؀-ۿЀ-ӿ]", "", unescape(TAG.sub("", text)))


def assert_punctuation_only(before: str, after: str, where: str) -> None:
    """Guard both callers: only quote characters may have moved.

    This is what makes it safe to run over scripture, whose WORDING is
    protected byte-for-byte — quotation marks are typography, not the text.
    Shared rather than duplicated because a repair that skipped the assertion
    would be the one place it was needed.
    """
    assert TAG.findall(before) == TAG.findall(after), f"{where}: tag sequence moved"
    assert rendered_letters(before) == rendered_letters(after), (
        f"{where}: letters/digits changed"
    )
