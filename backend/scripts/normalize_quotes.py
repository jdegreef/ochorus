"""Normalise quotation marks in fixture files that MIX styles.

Why only the mixed ones: a work that is consistently straight-quoted reads fine;
a work that is 264 straight and 1,132 curly shows the reader both in the same
chapter. 23 of 94 English files are in that state, which is also why the
"mirror the file's own English source" rule cannot be applied as written — for a
quarter of the corpus the source has no single style to mirror.

Curly is the target: it is 76% of the corpus already (50,482 to 15,946) and is
correct typography in every language we ship.

    uv run python scripts/normalize_quotes.py --check   # report, change nothing
    uv run python scripts/normalize_quotes.py           # rewrite in place

SAFETY. Punctuation only. Every file is asserted to come out with an identical
ordered tag sequence and identical letters/digits; only the quote characters
move. That assertion is what makes it safe to run over scripture, whose WORDING
is protected byte-for-byte — quotation marks are typography, not the text.

Opening vs closing is decided by CONTEXT, never by an alternating toggle: these
books leave quotations unbalanced (one opens in a paragraph and closes in the
next, and some never close at all), and a toggle turns the next stray mark into
an opener and stays wrong for the rest of the file.

The decision itself lives in `library/quotes.py`, because migration 0082 makes
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

from library.quotes import convert_work  # noqa: E402  (path set above; no Django)


def main() -> int:
    check = "--check" in sys.argv
    files = sorted(CONTENT.glob("books/*.json")) + sorted(CONTENT.glob("sermons/*.json"))
    touched = total = 0
    for path in files:
        rows = json.loads(path.read_text())
        bodies = [r["fields"].get("body_html") or "" for r in rows]
        repaired, changed_here = convert_work(bodies, path.name)
        for row, new in zip(rows, repaired, strict=True):
            if row["fields"].get("body_html"):
                row["fields"]["body_html"] = new
        if not changed_here:
            continue
        touched += 1
        total += changed_here
        print(f"  {path.name:<52} {changed_here:>6} marks")
        if not check:
            body = "[\n" + ",\n".join(
                json.dumps(r, indent=1, ensure_ascii=False) for r in rows
            ) + "\n]\n"
            path.write_text(body)
    print(f"\n{'would convert' if check else 'converted'} {total} marks across {touched} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
