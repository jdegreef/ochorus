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


def _scalar(value) -> str:
    """A field value on one line, so a change to it is one changed line."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


#: Fields whose value is prose to be rendered, not printed raw.
_BODY_FIELDS = ("body_html",)

#: Fields a reviewer should not have to scroll past. NOT a whitelist of what is
#: shown — everything else is shown — just of what is dropped, and only where
#: the value is derived from something already on screen. `body_text` and
#: `word_count` both follow from `body_html`; timestamps are not content.
_DERIVED_FIELDS = frozenset(
    {"body_text", "word_count", "search_vector", "created_at", "updated_at",
     "citations_indexed_at"}
)


def _field_lines(kind: str, fields: dict) -> list[str]:
    """Every field except the derived ones, one per line, in a stable order.

    Deliberately not a whitelist. An earlier version listed the fields worth
    showing, which meant a change to any unlisted one — reassigning a book's
    author, flipping is_published — rendered as NO diff at all, and
    ``content_diff`` then called it "formatting only". A review tool that says
    "nothing changed" about a real change is worse than no review tool.
    """
    lines = []
    for key in sorted(fields):
        if key in _DERIVED_FIELDS or key in _BODY_FIELDS:
            continue
        value = fields.get(key)
        if value in (None, "", []):
            continue
        lines.append(f"{kind}.{key}: {_scalar(value)}")
    return lines


def render(rows: list[dict]) -> str:
    """Fixture rows → reviewable prose.

    Numbers every paragraph, so a hunk header names the chapter and the line
    says which paragraph of it moved — the two things a reviewer needs and the
    raw JSON cannot show. Every non-derived field is printed, so no change can
    render as an empty diff.
    """
    lines: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            lines += ["", json.dumps(row, ensure_ascii=False)]
            continue
        model = str(row.get("model", "?"))
        fields = row.get("fields") or {}
        if not isinstance(fields, dict):
            lines += ["", f"=== {model}", json.dumps(fields, ensure_ascii=False)]
            continue
        kind = model.split(".")[-1]

        if kind == "chapter":
            order = fields.get("order")
            lines += ["", f"--- CHAPTER {order}: {fields.get('title', '')}".rstrip()]
        else:
            ident = fields.get("slug") or fields.get("name") or ""
            language = fields.get("language")
            suffix = f" [{language}]" if language else ""
            lines += ["", f"=== {kind.upper()} {ident}{suffix}".rstrip()]

        lines += _field_lines(kind, fields)
        for field in _BODY_FIELDS:
            body = fields.get(field)
            if not body:
                continue
            prefix = f"{fields.get('order')}." if kind == "chapter" else ""
            for n, para in enumerate(paragraphs(str(body)), 1):
                lines.append(f"[{prefix}{n}] {para}")
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
