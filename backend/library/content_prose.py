"""Render a content fixture as reviewable prose.

The pipeline's central promise is that a human reads an AI translation before it
ships (``source_type=ai_unreviewed`` until someone runs ``approve_translation``).
Git makes that promise hard to keep: a chapter's ``body_html`` is a single JSON
line — 12 KB in a small book, 190 KB in the largest — so changing one word
prints tens of kilobytes of escaped HTML with the change buried inside it.
Measured on ``humility-2.en.json``: a one-word fix is a 36 KB diff, and
``--word-diff`` only brings it to 24 KB. Nobody reviews that, so in practice
nobody reviews content at all.

This turns a fixture into one line per paragraph, tags stripped, each carrying
its chapter and paragraph number. A one-word fix then diffs as one short line,
and the surrounding lines say exactly where in the book it happened.

Two things consume it, and both need it to work the same way:

* ``scripts/fixture-textconv.py``, wired up through ``.gitattributes`` so
  ``git diff``/``git log -p`` show prose instead of JSON.
* ``manage.py content_diff``, which needs no git configuration at all.

Deliberately Django-free: the textconv runs as a bare script inside git, with no
settings and no database.
"""

from __future__ import annotations

import json
import re

#: Block-level tags that end a paragraph. Splitting on these is what gives one
#: reviewable line per paragraph; inline tags (<em>, <a>, the scripture spans)
#: are simply stripped, since their text is what a reviewer is reading.
_BLOCK_END = re.compile(
    r"</(?:p|div|h[1-6]|li|blockquote|figcaption|pre)\s*>|<br\s*/?>", re.I
)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t ]+")

_ENTITIES = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
    "&#39;": "'", "&apos;": "'", "&nbsp;": " ", "&mdash;": "—", "&ndash;": "–",
}


def _unescape(text: str) -> str:
    for entity, char in _ENTITIES.items():
        text = text.replace(entity, char)
    return text


def paragraphs(body_html: str) -> list[str]:
    """The block-level text of a body, one string per paragraph."""
    if not body_html:
        return []
    out = []
    for chunk in _BLOCK_END.split(body_html):
        text = _WS.sub(" ", _unescape(_TAG.sub("", chunk))).strip()
        if text:
            out.append(text)
    return out


def _field_lines(kind: str, fields: dict, keys: tuple[str, ...]) -> list[str]:
    """Short metadata fields, one per line, blanks skipped."""
    lines = []
    for key in keys:
        value = fields.get(key)
        if value in (None, "", []):
            continue
        lines.append(f"{kind}.{key}: {value}")
    return lines


#: Metadata worth showing above the prose. Not every column — a diff of
#: `updated_at` or a cover URL tells a reviewer nothing about the translation.
_BOOK_FIELDS = ("slug", "language", "title", "subtitle", "description", "source_type",
                "publication_year", "attribution", "is_published")
_SERMON_FIELDS = ("slug", "language", "title", "scripture_ref", "summary",
                  "source_type", "preached_on", "is_published")
_AUTHOR_FIELDS = ("slug", "name", "bio", "birth_year", "death_year", "is_imprint")


def render(rows: list[dict]) -> str:
    """Fixture rows → reviewable prose.

    Numbers every paragraph, so a hunk header names the chapter and the line
    says which paragraph of it moved — the two things a reviewer needs and the
    raw JSON cannot show.
    """
    lines: list[str] = []
    for row in rows:
        model = row.get("model", "")
        fields = row.get("fields", {})
        if model == "library.book":
            lines += ["", f"=== BOOK {fields.get('slug')} [{fields.get('language')}]"]
            lines += _field_lines("book", fields, _BOOK_FIELDS)
        elif model == "library.author":
            lines += ["", f"=== AUTHOR {fields.get('slug')}"]
            lines += _field_lines("author", fields, _AUTHOR_FIELDS)
        elif model == "library.sermon":
            lines += ["", f"=== SERMON {fields.get('slug')} [{fields.get('language')}]"]
            lines += _field_lines("sermon", fields, _SERMON_FIELDS)
            for n, para in enumerate(paragraphs(fields.get("body_html", "")), 1):
                lines.append(f"[{n:>3}] {para}")
        elif model == "library.chapter":
            order = fields.get("order")
            lines += ["", f"--- CHAPTER {order}: {fields.get('title', '')}".rstrip()]
            for n, para in enumerate(paragraphs(fields.get("body_html", "")), 1):
                lines.append(f"[{order}.{n}] {para}")
        else:
            # Plans, topic members and anything added later: short rows whose
            # JSON is already readable, so show it rather than drop it.
            lines += ["", f"=== {model}", json.dumps(fields, ensure_ascii=False, indent=1)]
    return "\n".join(lines).strip() + "\n"


def render_file(text: str) -> str:
    """Render fixture JSON text; pass non-fixture text through untouched.

    A textconv must never fail: git shows its output as the file's content, so
    raising here would make the file look empty in every diff.
    """
    try:
        rows = json.loads(text)
    except ValueError:
        return text
    if not isinstance(rows, list):
        return text
    return render(rows)
