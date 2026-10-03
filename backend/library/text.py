"""Plain-text derivations from chapter HTML.

One canonical place for the HTML→text rules so the two stored columns derived
from ``body_html`` — ``body_text`` (what search matches) and ``word_count``
(reading times, the length sort, book and plan totals) — are always derived the
same way, from the model's save(), the backfill commands, and the data
migrations.

The two rules are NOT interchangeable — see ``text_of`` for how they differ and
what picking the wrong one costs.
"""

from __future__ import annotations

import html
import re
import unicodedata

from django.utils.html import strip_tags

# Block-level tags become word boundaries so "…end.</p><p>Start…" doesn't fuse
# into "end.Start" in the text (which would break both matching and snippets).
_BLOCK_BREAK = re.compile(r"</(p|div|h[1-6]|li|blockquote|br)>|<br\s*/?>", re.I)
_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")


# What renders as nothing: whitespace, control and format characters (zero-width
# spaces and joiners, the BOM, bidi marks — which `str.strip()` keeps), plus the
# few letters that draw blank (Hangul fillers, the combining grapheme joiner).
# A title made only of these reads as no title at all: the admin coverage matrix
# once showed a Spurgeon book as just its author, still offering to queue
# translations of it.
_BLANK_LETTERS = frozenset("\u034f\u115f\u1160\u3164\uffa0")


# The database's copy of the rule (a CHECK constraint on every work's title):
# a title made only of these is refused at the row, whatever path wrote it,
# .update() and bulk_create included. A literal set, since a CHECK can't ask
# Unicode for a character's category — so it covers the invisibles that turn up
# in practice, and is_blank_title (the save() guard, the import, the coverage
# flag) stays the wider rule in front of it.
# The Unicode spaces are spelled out rather than left to `\s`: Postgres's `\s`
# follows the server locale and misses U+00A0 (a PDF's &nbsp;) and U+3000.
BLANK_TITLE_REGEX = (
    r"^[\s\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000"
    r"\u00ad\u034f\u115f\u1160\u180e\u200b-\u200f\u202a-\u202e"
    r"\u2060-\u2064\u2066-\u206f\u3164\ufeff\uffa0]*$"
)


def is_blank_title(title) -> bool:
    """True when ``title`` would show a reader nothing."""
    return all(
        unicodedata.category(c)[0] in "CZ" or c.isspace() or c in _BLANK_LETTERS
        for c in str(title or "")
    )


def html_to_text(body_html: str) -> str:
    spaced = _BLOCK_BREAK.sub(" \\g<0>", body_html)
    # `" ".join(s.split())` is `_WS.sub(" ", s).strip()` exactly — `str.split()`
    # and `re`'s `\s` agree on every code point — but runs in C, where the
    # regex substitution was over half of this function's cost (it derives
    # body_text on every Chapter/Sermon save and in a whole-corpus fixture test).
    return " ".join(html.unescape(strip_tags(spaced)).split())


def text_of(html_str: str) -> str:
    """Tags to spaces, whitespace collapsed — the reduction ``word_count`` counts.

    Every tag becomes a space here, inline ones included, so "<i>one</i><b>two</b>"
    is two words; ``html_to_text`` spaces only block closers, so the same markup
    joins into one. Entities are left escaped for the same reason — "G&amp;C"
    is one word either way, but unescaping first is a second rule to keep in
    step for no gain in a count.

    Every importer has counted words this way since the first one, so this is
    the rule a stored count has to match; deriving one with ``html_to_text``
    instead undercounts every body that leans on inline markup.
    """
    return _WS.sub(" ", _TAG.sub(" ", html_str)).strip()


def word_count(html_str: str) -> int:
    """``text_of`` counted, without building the collapsed string to count it.

    ``str.split()`` already splits on runs of whitespace and drops the empty
    ends, so the collapse and strip in ``text_of`` cannot change this number —
    verified equal on every stored chapter and sermon, and 4.8x faster, which
    is worth having in a rule ``save()` now runs on every write.
    """
    return len(_TAG.sub(" ", html_str).split())
