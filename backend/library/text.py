"""Plain-text derivations from chapter HTML.

One canonical place for the HTML→text rules so the two stored columns derived
from ``body_html`` — ``body_text`` (what search matches) and ``word_count``
(reading times, the length sort, book and plan totals) — are always derived the
same way, from the model's save(), the backfill commands, and the data
migrations.

The two rules are NOT interchangeable, and both live here so the difference is
visible rather than rediscovered: see ``text_of``.
"""

from __future__ import annotations

import html
import re

from django.utils.html import strip_tags

# Block-level tags become word boundaries so "…end.</p><p>Start…" doesn't fuse
# into "end.Start" in the text (which would break both matching and snippets).
_BLOCK_BREAK = re.compile(r"</(p|div|h[1-6]|li|blockquote|br)>|<br\s*/?>", re.I)
_WS = re.compile(r"\s+")


def html_to_text(body_html: str) -> str:
    spaced = _BLOCK_BREAK.sub(" \\g<0>", body_html)
    return _WS.sub(" ", html.unescape(strip_tags(spaced))).strip()


def text_of(html_str: str) -> str:
    """The reduction ``word_count`` counts, and it is not ``html_to_text``.

    Every tag becomes a space here, inline ones included, so "<i>one</i><b>two</b>"
    is two words; ``html_to_text`` spaces only block closers, so the same markup
    joins into one. Entities are left escaped for the same reason — "G&amp;C"
    is one word either way, but unescaping first is a second rule to keep in
    step for no gain in a count.

    Every importer has counted words this way since the first one, so this is
    the rule a stored count has to match; deriving one with ``html_to_text``
    instead undercounts every body that leans on inline markup.
    """
    return _WS.sub(" ", re.sub(r"<[^>]+>", " ", html_str)).strip()


def word_count(html_str: str) -> int:
    return len(text_of(html_str).split())
