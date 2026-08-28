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

A trailing NAME limits the run to files whose name contains it. The corpus is
not in a settled state — see the `body_text` note below — so a repair that is
scoped to a few works should be shippable without sweeping every one.

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

# `body_text` is DERIVED from `body_html`, so converting one and not the
# other leaves the committed file disagreeing with itself.
FIELDS = ("body_html", "body_text")


def main() -> int:
    check = "--check" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    files = sorted(CONTENT.glob("books/*.json")) + sorted(CONTENT.glob("sermons/*.json"))
    if only:
        files = [p for p in files if any(name in p.name for name in only)]
    touched = total = 0
    for path in files:
        rows = json.loads(path.read_text())
        # BOTH body fields, which the first sweep did not do: it converted
        # body_html and left every one of the four Spanish files carrying its
        # pre-conversion straight marks in body_text (54, 112, 128 and 5 of
        # them). `loaddata` writes body_text verbatim — it never calls `save()`
        # — and `backfill_body_text` only fills an EMPTY one, so a freshly
        # seeded database indexed and snippeted straight quotes while its pages
        # rendered « ». `normalize_english_fixture` normalizes both fields for
        # exactly this reason; so does this.
        fields = [
            (row, key)
            for row in rows
            for key in FIELDS
            if row["fields"].get(key)
        ]
        repaired, changed_here = convert_work(
            [row["fields"][key] for row, key in fields], path.name
        )
        if not changed_here:
            continue
        for (row, key), new in zip(fields, repaired, strict=True):
            row["fields"][key] = new
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
