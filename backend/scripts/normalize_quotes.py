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
"""

from __future__ import annotations

import json
import re
import sys
from html import unescape
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
CONTENT = BACKEND / "library" / "fixtures" / "content"
TAG = re.compile(r"<[^>]+>")
STRAIGHT = '"'
ENTITY = "&quot;"


def _style(text: str) -> str:
    plain = TAG.sub(" ", text)
    straight = plain.count(ENTITY) + plain.count(STRAIGHT)
    curly = plain.count("“") + plain.count("”")
    if straight and curly:
        return "MIXED"
    return "straight" if straight else ("curly" if curly else "none")


def _convert(html: str) -> tuple[str, int]:
    """Rewrite straight marks as curly, deciding each one from its context."""
    out: list[str] = []
    i, n, changed = 0, len(html), 0
    while i < n:
        # Never touch anything inside a tag: attribute values are quoted too.
        if html[i] == "<":
            j = html.find(">", i)
            j = n if j == -1 else j + 1
            out.append(html[i:j])
            i = j
            continue
        if html.startswith(ENTITY, i):
            mark, width = ENTITY, len(ENTITY)
        elif html[i] == STRAIGHT:
            mark, width = STRAIGHT, 1
        else:
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
        before = "".join(out)[-1:]
        opens = not before or before.isspace() or before in "([{—–->"
        out.append("“" if opens else "”")
        changed += 1
        i += width
    return "".join(out), changed


def _letters(text: str) -> str:
    """Rendered letters and digits only.

    Entities must be unescaped FIRST. `&quot;` literally contains q-u-o-t, so
    comparing raw strings reports "letters changed" the moment an entity becomes
    a curly mark — which is exactly what the assertion caught on the first run.
    What must be identical is what the reader sees, not the storage form.
    """
    return re.sub(
        r"[^0-9A-Za-zÀ-ɏ؀-ۿЀ-ӿ]", "", unescape(TAG.sub("", text))
    )


def main() -> int:
    check = "--check" in sys.argv
    files = sorted(CONTENT.glob("books/*.json")) + sorted(CONTENT.glob("sermons/*.json"))
    touched = total = 0
    for path in files:
        rows = json.loads(path.read_text())
        joined = "".join(r["fields"].get("body_html", "") for r in rows)
        if _style(joined) != "MIXED":
            continue
        changed_here = 0
        for row in rows:
            body = row["fields"].get("body_html")
            if not body:
                continue
            new, k = _convert(body)
            if not k:
                continue
            assert TAG.findall(body) == TAG.findall(new), f"{path.name}: tag sequence moved"
            assert _letters(body) == _letters(new), f"{path.name}: letters/digits changed"
            row["fields"]["body_html"] = new
            changed_here += k
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
