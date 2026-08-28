"""Drop the leading heading a fixture chapter uses to repeat its own title.

The reader renders the chapter title above the body, so such a heading prints
the title twice — `all-of-grace` chapter 1 is titled "To You" and its prose
began "<h2>TO YOU</h2>".

    uv run python scripts/strip_restated_headings.py            # report only
    uv run python scripts/strip_restated_headings.py --write    # rewrite in place
    uv run python scripts/strip_restated_headings.py all-of-grace   # just these

A trailing NAME limits the run to files whose name contains it.

The decision itself lives in `library.ingest.strip_restated_heading`, because
migration 0092 makes the same repair to rows already in a deployed database —
`seed_books` never re-syncs an existing book's chapters, so this sweep reaches a
fresh build and never a running one. Same shape as `normalize_quotes.py` beside
migration 0084.

ENGLISH DECIDES. A translated chapter is judged by its English twin (same slug
and order) rather than by its own title: a translation is written from the
English body and keeps its markup block for block
(`tests_translation_markup` enforces the ordered tag sequence), so the block
facing a restated English heading is the same restatement. Read against its own
title the rule agrees on 58 of the 60 translated rows and misses two, where the
translator paraphrased the heading rather than repeating the title.

`body_text` and `word_count` are DERIVED from `body_html`, and both are written
here — unlike `normalize_quotes.py`, which leaves `body_text` to
`rederive_body_text`, because that sweep moves punctuation only while this one
moves whole words and would leave the committed word counts wrong.

Files are patched TEXTUALLY — anchored on the row's own `body_html` value and
bounded to that record — so untouched bytes survive exactly, including the
known indentation drift between fixture files. Re-running finds nothing.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")

import django  # noqa: E402

django.setup()

from library.ingest import (  # noqa: E402
    strip_leading_heading_element,
    strip_restated_heading,
    word_count,
)
from library.text import html_to_text  # noqa: E402

BOOKS = BACKEND / "library/fixtures/content/books"


def _encode(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _patch(raw: str, fields: dict, body_html: str) -> str:
    """Replace one chapter's three body columns, in place, by anchored text."""
    anchor = f'"body_html": {_encode(fields["body_html"])}'
    if raw.count(anchor) != 1:
        raise SystemExit(f"body_html is not unique in its file: order {fields['order']}")
    start = raw.index(anchor)
    end = raw.find('"model"', start)
    end = len(raw) if end < 0 else end
    record = raw[start:end].replace(anchor, f'"body_html": {_encode(body_html)}', 1)
    for name, value in (
        ("body_text", html_to_text(body_html)),
        ("word_count", word_count(body_html)),
    ):
        if fields.get(name) is None:
            continue
        needle = f'"{name}": {_encode(fields[name])}'
        if record.count(needle) != 1:
            raise SystemExit(f"{name} is not unique in its record: order {fields['order']}")
        record = record.replace(needle, f'"{name}": {_encode(value)}', 1)
    return raw[:start] + record + raw[end:]


def main(argv: list[str]) -> int:
    write = "--write" in argv
    only = [a for a in argv if not a.startswith("--")]

    chapters: dict[tuple[str, str], dict[int, dict]] = {}
    for path in sorted(BOOKS.glob("*.json")):
        slug, language, _ = path.name.split(".")
        chapters[(slug, language)] = {
            row["fields"]["order"]: row["fields"]
            for row in json.loads(path.read_text())
            if row["model"] == "library.chapter"
        }

    # English first, by the title rule; then translations, by their English twin.
    bodies: dict[tuple[str, str, int], str] = {}
    decided: set[tuple[str, int]] = set()
    for (slug, language), by_order in chapters.items():
        if language != "en":
            continue
        for order, fields in by_order.items():
            body = strip_restated_heading(fields.get("body_html") or "", fields.get("title") or "")
            if body and body != fields.get("body_html"):
                bodies[(slug, language, order)] = body
                decided.add((slug, order))
    for (slug, language), by_order in chapters.items():
        if language == "en":
            continue
        for order, fields in by_order.items():
            if (slug, order) not in decided:
                continue
            body = strip_leading_heading_element(fields.get("body_html") or "")
            if body and body != fields.get("body_html"):
                bodies[(slug, language, order)] = body

    total = 0
    for path in sorted(BOOKS.glob("*.json")):
        if only and not any(name in path.name for name in only):
            continue
        slug, language, _ = path.name.split(".")
        raw = out = path.read_text()
        for order, fields in chapters[(slug, language)].items():
            body = bodies.get((slug, language, order))
            if body is None:
                continue
            out = _patch(out, fields, body)
            total += 1
        if out == raw:
            continue
        # The patch is textual; parsing it back is what proves it stayed JSON.
        if len(json.loads(out)) != len(json.loads(raw)):
            raise SystemExit(f"patch changed the row count of {path.name}")
        print(f"{sum(1 for o in chapters[(slug, language)] if (slug, language, o) in bodies):5d}"
              f"  {path.name}")
        if write:
            path.write_text(out)

    print(f"{total} chapter(s) {'rewritten' if write else 'would change'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
