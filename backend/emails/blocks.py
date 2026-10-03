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
    blocks."""
    if "blocks" in block:
        return block["blocks"]
    return legacy_blocks(block)


def has_body(blocks: list[dict]) -> bool:
    """Whether a block list says anything (not only dividers and empty text)."""
    for b in blocks:
        if b["type"] in LIBRARY_TYPES and b.get("slug"):
            return True
        if any(b.get(f) for f in ("text", "label")):
            return True
    return False


# --- Library lookups ------------------------------------------------------------


def library_model(kind: str):
    """The library model a library block type points at."""
    from library.models import Book, Plan, Sermon

    return {BlockType.BOOK: Book, BlockType.SERMON: Sermon, BlockType.PLAN: Plan}[kind]


#: The reader-site section each library type lives under.
SECTION = {BlockType.BOOK: "books", BlockType.SERMON: "sermons", BlockType.PLAN: "plans"}


def editions(kind: str, slugs) -> dict[str, set[str]]:
    """``{slug: {languages it is published in}}`` for one library type."""
    out: dict[str, set[str]] = {}
    rows = library_model(kind).objects.filter(slug__in=set(slugs), is_published=True).values_list(
        "slug", "language"
    )
    for slug, language in rows:
        out.setdefault(slug, set()).add(language)
    return out


def _cards(kind: str, slugs, lang: str) -> dict[str, dict]:
    """``{slug: card}`` for the editions of ``slugs`` published in ``lang``."""
    model = library_model(kind)
    qs = model.objects.filter(slug__in=set(slugs), language=lang, is_published=True)
    if kind != BlockType.PLAN:
        qs = qs.select_related("author")
    cards = {}
    for work in qs:
        cover = getattr(work, "cover_url", "") or ""
        description = (
            getattr(work, "description", "") or getattr(work, "summary", "") or ""
        ).strip()
        if len(description) > 220:
            description = description[:217].rsplit(" ", 1)[0] + "…"
        cards[work.slug] = {
            "title": work.title,
            "author": work.author.name if kind != BlockType.PLAN else "",
            "description": description,
            # Covers are site-relative ("/covers/art/…"); email needs absolute.
            "cover_url": links.site_url(cover) if cover.startswith("/") else cover,
            "url": links.site_url(links.reader_path(SECTION[kind], work.slug, lang)),
        }
    return cards


def resolve(blocks: list[dict], lang: str, *, name: str = "friend") -> list[dict]:
    """Render-ready blocks for one email in ``lang``: ``{name}`` filled in,
    button paths made absolute, library blocks looked up in ``lang`` — and those
    with no edition in ``lang`` left out."""
    wanted: dict[str, list[str]] = {}
    for b in blocks:
        if b["type"] in LIBRARY_TYPES and b.get("slug"):
            wanted.setdefault(b["type"], []).append(b["slug"])
    cards = {kind: _cards(kind, slugs, lang) for kind, slugs in wanted.items()}

    out = []
    for b in blocks:
        kind = b["type"]
        if kind in LIBRARY_TYPES:
            card = cards.get(kind, {}).get(b.get("slug", ""))
            if card is None:
                continue
            out.append({"type": kind, "label": b.get("label", ""), **card})
        elif kind == BlockType.BUTTON:
            if b.get("label"):
                out.append({**b, "url": links.site_url(b.get("path", ""))})
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
