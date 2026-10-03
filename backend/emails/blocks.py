"""Campaign content as blocks — what the admin designer edits and the email renders.

A broadcast's per-language content is ``{"preheader": ..., "blocks": [...]}``,
an ordered list of typed blocks. Every block is structured data, never HTML: the
template escapes all of it, so there is still nothing to sanitize.

* Layout blocks carry their own words: ``heading``, ``text`` (blank lines split
  paragraphs), ``button`` (label + a reader-site path), ``divider``, ``quote``.
* Library blocks point at a work by slug — ``book``, ``sermon``, ``plan`` — and
  are resolved at render time to the edition in the email's language: its title,
  author, cover and link. Content is per-language rows with **no English
  fallback**, so a work with no edition in that language is simply left out of
  that language's email (the pre-send checks say so beforehand).

Text in ``heading``/``text`` blocks may use ``{name}`` for the reader's first
name — a literal replace, never ``str.format`` (see ``rendering._render``).

Older broadcasts stored fixed fields (heading, greeting, paragraphs, a CTA,
signoff); :func:`blocks_for` reads those as the equivalent blocks, so both shapes
render through the one template.
"""

from __future__ import annotations

from types import SimpleNamespace

from django.db import models

from . import links


class BlockType(models.TextChoices):
    HEADING = "heading", "Heading"
    TEXT = "text", "Text"
    BUTTON = "button", "Button"
    DIVIDER = "divider", "Divider"
    QUOTE = "quote", "Quote"
    BOOK = "book", "Book"
    SERMON = "sermon", "Sermon"
    PLAN = "plan", "Reading plan"


#: The fields each block type keeps (all strings); anything else is dropped.
FIELDS: dict[str, tuple[str, ...]] = {
    BlockType.HEADING: ("text",),
    BlockType.TEXT: ("text",),
    BlockType.BUTTON: ("label", "path"),
    BlockType.DIVIDER: (),
    BlockType.QUOTE: ("text", "attribution"),
    BlockType.BOOK: ("slug", "label"),
    BlockType.SERMON: ("slug", "label"),
    BlockType.PLAN: ("slug", "label"),
}

LIBRARY_TYPES = (BlockType.BOOK, BlockType.SERMON, BlockType.PLAN)

#: Guards against a runaway payload; far above any real email.
MAX_BLOCKS = 60
MAX_TEXT = 5000


def clean(blocks) -> list[dict]:
    """Normalise a submitted block list: known types only, known fields only,
    every value a trimmed, length-capped string. Never raises — an unknown block
    is dropped rather than failing the whole save."""
    if not isinstance(blocks, list):
        return []
    out = []
    for raw in blocks[:MAX_BLOCKS]:
        if not isinstance(raw, dict) or raw.get("type") not in FIELDS:
            continue
        block = {"type": raw["type"]}
        for field in FIELDS[raw["type"]]:
            block[field] = str(raw.get(field) or "").strip()[:MAX_TEXT]
        out.append(block)
    return out


def clean_content(content) -> dict:
    """Clean every language's block list in a broadcast's ``content``, leaving
    the other per-language keys (preheader, the legacy fields) as they are."""
    if not isinstance(content, dict):
        return {}
    out = {}
    for locale, block in content.items():
        if not isinstance(block, dict):
            continue
        block = dict(block)
        if "blocks" in block:
            block["blocks"] = clean(block["blocks"])
        out[str(locale)[:10]] = block
    return out


def legacy_blocks(block: dict) -> list[dict]:
    """The block list equivalent to the old fixed fields."""
    out = []
    if block.get("heading"):
        out.append({"type": BlockType.HEADING, "text": block["heading"]})
    if block.get("greeting"):
        out.append({"type": BlockType.TEXT, "text": block["greeting"]})
    for para in block.get("paragraphs") or []:
        out.append({"type": BlockType.TEXT, "text": para})
    if block.get("cta_label") or block.get("cta_path"):
        out.append(
            {"type": BlockType.BUTTON, "label": block.get("cta_label", ""), "path": block.get("cta_path", "")}
        )
    sign = "\n".join(s for s in (block.get("signoff"), block.get("signature")) if s)
    if sign:
        out.append({"type": BlockType.TEXT, "text": sign})
    return out


def blocks_for(block: dict) -> list[dict]:
    """A language's blocks: its ``blocks`` list, else its legacy fields read as
    blocks — cleaned either way, so a malformed old row (a null paragraph, a
    number for a heading) renders as text instead of raising mid-send."""
    if "blocks" in block:
        return clean(block["blocks"])
    return clean(legacy_blocks(block))


def as_blocks(content: dict) -> dict:
    """A broadcast's or template's ``content`` with every language in the block
    shape — what the admin designer edits, so it never converts old fields itself."""
    return {
        code: {"preheader": block.get("preheader", ""), "blocks": blocks_for(block)}
        for code, block in (content or {}).items()
        if isinstance(block, dict)
    }


#: The fields that carry an admin's own words (what a translation changes).
WORD_FIELDS = ("text", "label", "attribution")


def has_body(blocks: list[dict], reaches=None) -> bool:
    """Whether a block list says anything (not only dividers and empty text).
    ``reaches(block)`` says whether a library block will actually render (has an
    edition in the email's language); by default any chosen work counts."""
    for b in blocks:
        if b["type"] in LIBRARY_TYPES:
            if b.get("slug") and (reaches is None or reaches(b)):
                return True
        elif any(b.get(f) for f in ("text", "label")):
            return True
    return False


def library_refs(blocks: list[dict]) -> dict[str, set[str]]:
    """``{kind: slugs}`` for the library blocks that name a work."""
    refs: dict[str, set[str]] = {}
    for b in blocks:
        if b["type"] in LIBRARY_TYPES and b.get("slug"):
            refs.setdefault(b["type"], set()).add(b["slug"])
    return refs


# --- Library lookups ------------------------------------------------------------


#: What each library type is: its model, its reader-site section, and the field
#: its card's blurb comes from. Plans have no author.
LIBRARY = {
    BlockType.BOOK: ("Book", "books", "description"),
    BlockType.SERMON: ("Sermon", "sermons", "summary"),
    BlockType.PLAN: ("Plan", "plans", "description"),
}


def library_model(kind: str):
    """The library model a library block type points at."""
    from django.apps import apps

    return apps.get_model("library", LIBRARY[kind][0])


def has_author(kind: str) -> bool:
    return kind != BlockType.PLAN


def editions(kind: str, slugs) -> dict[str, set[str]]:
    """``{slug: {languages it is published in}}`` for one library type."""
    out: dict[str, set[str]] = {}
    rows = library_model(kind).objects.filter(slug__in=set(slugs), is_published=True).values_list(
        "slug", "language"
    )
    for slug, language in rows:
        out.setdefault(slug, set()).add(language)
    return out


def _blurb(text: str) -> str:
    text = (text or "").strip()
    return text if len(text) <= 220 else text[:217].rsplit(" ", 1)[0] + "…"


def _cards(kind: str, slugs, lang: str) -> dict[str, dict]:
    """``{slug: card}`` for the editions of ``slugs`` published in ``lang``.
    Only the card's columns are read — a sermon row also carries its whole body."""
    from library.book_export import cover_image_url

    _, section, blurb_field = LIBRARY[kind]
    fields = ["slug", "title", blurb_field]
    if has_author(kind):
        fields.append("author__name")
    if kind == BlockType.BOOK:
        fields.append("cover_url")
    rows = library_model(kind).objects.filter(
        slug__in=set(slugs), language=lang, is_published=True
    ).values(*fields)
    cards = {}
    for row in rows:
        cover = ""
        if kind == BlockType.BOOK:
            # The raster that shows the cover WITH its title (a painting or a
            # plate is a wordless ground; a plate is also an SVG, which mail
            # clients won't show) — the site's one rule for that.
            cover = cover_image_url(
                SimpleNamespace(slug=row["slug"], language=lang, cover_url=row["cover_url"])
            )
        cards[row["slug"]] = {
            "title": row["title"],
            "author": row.get("author__name", ""),
            "description": _blurb(row[blurb_field]),
            "cover_url": links.site_url(cover) if cover.startswith("/") else cover,
            "url": links.site_url(links.reader_path(section, row["slug"], lang)),
        }
    return cards


def _button_path(path: str, lang: str) -> str:
    """An admin-written button path in ``lang``'s pages, so a layout copied from
    English into Spanish doesn't send Spanish readers to English pages. A path
    that already names a language is left alone."""
    from library.languages import language_map

    path = path.lstrip("/")
    if not path or path.split("/", 1)[0] in language_map():
        return path
    return links.localized(path, lang)


def resolve(
    blocks: list[dict],
    lang: str,
    *,
    name: str,
    cards=None,
    localize_buttons: bool = True,
) -> list[dict]:
    """Render-ready blocks for one email in ``lang``: ``{name}`` filled in,
    button paths made absolute, library blocks looked up in ``lang`` — and those
    with no edition in ``lang`` left out.

    ``localize_buttons`` puts admin-written button paths in ``lang``'s pages.
    The fixed-copy emails pass False: their paths are built by code that already
    chose the right edition (a series nudge may point an English series at a
    reader whose email is Spanish), and English pages are unprefixed.

    ``cards`` is an optional cache owned by the caller, ``{(kind, lang, slug):
    card or None}``: a send renders the same blocks for thousands of readers, so
    each card is looked up once per run, not per reader.
    """
    if cards is None:
        cards = {}
    for kind, slugs in library_refs(blocks).items():
        missing = {s for s in slugs if (kind, lang, s) not in cards}
        if missing:
            found = _cards(kind, missing, lang)
            for slug in missing:
                cards[(kind, lang, slug)] = found.get(slug)

    out = []
    for b in blocks:
        kind = b["type"]
        if kind in LIBRARY_TYPES:
            card = cards.get((kind, lang, b.get("slug", "")))
            if card is None:
                continue
            out.append({"type": kind, "label": b.get("label", ""), **card})
        elif kind == BlockType.BUTTON:
            if b.get("label"):
                path = b.get("path", "")
                url = links.site_url(_button_path(path, lang) if localize_buttons else path)
                out.append({**b, "url": url})
        elif kind in (BlockType.HEADING, BlockType.TEXT):
            text = b.get("text", "").replace("{name}", name)
            if not text:
                continue
            if kind == BlockType.TEXT:
                # Blank lines separate paragraphs; single breaks stay in one.
                paras = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
                out.append({"type": kind, "paragraphs": [p for p in paras if p]})
            else:
                out.append({"type": kind, "text": text})
        else:
            out.append(b)
    return out
