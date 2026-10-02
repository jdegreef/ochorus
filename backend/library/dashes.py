"""Typewriter dashes: set a run of hyphens as the em dash it stands for.

Plain-text transcriptions (Gutenberg's above all, and CCEL's) have no em dash,
so they key one as two hyphens: "experienced--everywhere", "dreams -- a living
hope", "Rev. C-- B--". Every printed edition behind them set a dash there. The
run is a transcription convention, not the author's punctuation, so restoring
the dash is the same kind of repair as `quote_marks` setting straight quotes
curly — typography, never wording.

The rule:

* two or three hyphens are one em dash — "pus---unspeakable" is the same mark
  as "experienced--everywhere", keyed longer;
* four or more are a two-em dash, "——" — the printer's mark for a withheld
  name ("Mrs.----?") or a long rule;
* the spacing the source gave the run is kept, so "a -- b" becomes "a — b"
  and "a--b" becomes "a—b";
* a lone hyphen is a hyphen, and is never touched.

It changes PROSE only. A tag's interior and an HTML comment pass through
unchanged — `<!-- -->` is the commonest run of hyphens in the corpus, and an
attribute could legitimately carry one. That makes it safe on a fragment as
well as a whole body: a correction pair's half (`--LUKE ix. 23.</blockquote>`)
converts exactly as it would inside the chapter it repairs.

No Django import: `corrections` runs it on every deploy, and the fixture sweep
runs it without a settings module.
"""

from __future__ import annotations

import re

#: What passes through untouched: an HTML comment, then any tag. Comments first,
#: so `<!-- a -- b -->` is skipped whole rather than ending at the first `>`; a
#: fragment that stops inside a comment skips to its end.
_SKIP = re.compile(r"<!--.*?(?:-->|\Z)|<[^>]*>", re.S)

#: A run of two or more hyphens. The guards keep a FRAGMENT safe where the
#: comment is not wholly inside it: `<!--` and `-->` are never a dash.
_RUN = re.compile(r"(?<!<!)(?<!-)-{2,}(?!-)(?!>)")


def _dash(match: re.Match[str]) -> str:
    return "—" if len(match.group()) <= 3 else "——"


def convert(html: str) -> str:
    """Set every typewriter dash in ``html``'s prose as an em dash. Idempotent."""
    if not _RUN.search(html):
        return html
    out: list[str] = []
    pos = 0
    for skip in _SKIP.finditer(html):
        out.append(_RUN.sub(_dash, html[pos : skip.start()]))
        out.append(skip.group())
        pos = skip.end()
    out.append(_RUN.sub(_dash, html[pos:]))
    return "".join(out)


#: A book or sermon body field's JSON string value, as it stands in a raw
#: fixture file — shared by `scripts/normalize_dashes.py` and the corpus gate.
FIXTURE_BODY_FIELD = re.compile(r'("(?:body_html|body_text)": ")((?:[^"\\]|\\.)*)(")')


def count(html: str) -> int:
    """How many typewriter dashes ``html``'s prose still carries."""
    return sum(len(_RUN.findall(part)) for part in _SKIP.split(html))
