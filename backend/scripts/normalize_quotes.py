"""Normalise quotation marks in fixture files that MIX styles.

Why only the mixed ones: a work that is consistently straight-quoted reads fine;
a work that is 264 straight and 1,132 curly shows the reader both in the same
chapter. 23 of 94 English files are in that state, which is also why the
"mirror the file's own English source" rule cannot be applied as written — for a
quarter of the corpus the source has no single style to mirror.

Curly is the target: it is 76% of the corpus already (50,482 to 15,946) and is
correct typography in every language we ship.

    uv run python scripts/normalize_quotes.py --check          # report only
    uv run python scripts/normalize_quotes.py                  # rewrite in place
    uv run python scripts/normalize_quotes.py humility.es      # just these

A trailing NAME limits the run to files whose name contains it, so a repair
scoped to a few works is shippable without sweeping every one.

Writes `body_html` only. `body_text` is derived from it, so after a run do
`manage.py rederive_body_text --write` — a gate in `tests_fixture` fails until
you have.

SAFETY. Punctuation only. Every file is asserted to come out with an identical
ordered tag sequence and identical letters/digits; only the quote characters
move. That assertion is what makes it safe to run over scripture, whose WORDING
is protected byte-for-byte — quotation marks are typography, not the text.

Opening vs closing is decided by CONTEXT, never by an alternating toggle: these
books leave quotations unbalanced (one opens in a paragraph and closes in the
next, and some never close at all), and a toggle turns the next stray mark into
an opener and stays wrong for the rest of the file.

The decision itself lives in `library/quote_marks.py`, because migration 0084 makes
the same repair to rows already in a deployed database — `seed_books` never
rewrites an existing book's chapters, so this sweep reaches a fresh build and
never a running one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
CONTENT = BACKEND / "library" / "fixtures" / "content"

sys.path.insert(0, str(BACKEND))

from library.content_fixtures import render_rows  # noqa: E402  (path set above)
from library.quote_marks import convert_work  # noqa: E402  (no Django needed)


def main() -> int:
    check = "--check" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    files = sorted(CONTENT.glob("books/*.json")) + sorted(CONTENT.glob("sermons/*.json"))
    if only:
        files = [p for p in files if any(name in p.name for name in only)]
    touched = total = 0
    for path in files:
        rows = json.loads(path.read_text())
        # `body_html` ONLY. `body_text` is DERIVED from it — `save()` sets it to
        # `html_to_text(body_html)` — and converting it here independently is
        # not the same operation: this decision is context-sensitive, so a field
        # whose marks are already converted and one whose are not reach
        # different depths and land on different pairs. `the-inner-chamber.pt`
        # is the case that showed it, taking » in `body_text` where `body_html`
        # has ”. Convert the source; then run `manage.py rederive_body_text
        # --write`, which `tests_fixture.BodyTextDerivationTests` will demand.
        bodies = [r["fields"].get("body_html") or "" for r in rows]
        repaired, changed_here = convert_work(bodies, path.name)
        if not changed_here:
            continue
        for row, new in zip(rows, repaired, strict=True):
            if row["fields"].get("body_html"):
                row["fields"]["body_html"] = new
        touched += 1
        total += changed_here
        print(f"  {path.name:<52} {changed_here:>6} marks")
        if not check:
            path.write_text(render_rows(rows))
    print(f"\n{'would convert' if check else 'converted'} {total} marks across {touched} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
