"""One search across everything an email can show from the site — books,
sermons, reading plans, articles, authors, topics and sourced quotes — for the
designer's "Insert from the library" panel.

Each result carries the block that inserts it, ready to drop into the email, so
the panel needs no knowledge of block shapes: a book becomes a ``book`` block, a
quote a ``quote`` block with its text and attribution already written. Results
say which languages they reach, the same way the block pickers do, and a work
matching the query by its author's name counts ("murray" finds Murray's books).
"""

from __future__ import annotations

from django.db.models import Q

from . import blocks as blocks_mod
from .blocks import BlockType

#: Results per kind; the panel shows counts and lets the admin narrow by kind.
PER_KIND = 8
#: The order kinds are listed in.
KINDS = (
    BlockType.AUTHOR,
    BlockType.BOOK,
    BlockType.SERMON,
    BlockType.PLAN,
    BlockType.ARTICLE,
    BlockType.TOPIC,
    BlockType.QUOTE,
)
MIN_QUERY = 2


def _per_language(kind: str, q: str) -> tuple[list[dict], int]:
    """Books, sermons, plans or articles matching ``q``: one row per slug."""
    _, _, _, title_field = blocks_mod.LIBRARY[kind]
    rows = blocks_mod.library_model(kind).objects.filter(is_published=True)
    match = Q(**{f"{title_field}__icontains": q}) | Q(slug__icontains=q)
    if blocks_mod.has_author(kind):
        match |= Q(author__name__icontains=q)
    matching = rows.filter(match).values("slug").distinct()
    total = matching.count()
    slugs = list(matching.order_by("slug").values_list("slug", flat=True)[:PER_KIND])
    works = blocks_mod.works_by_slug(kind, rows, slugs)
    return [
        {
            "kind": kind,
            "key": f"{kind}:{slug}",
            "title": works[slug]["title"],
            "subtitle": works[slug]["author"],
            "image": works[slug]["cover"],
            "languages": works[slug]["languages"],
            "block": {"type": kind, "slug": slug, "label": ""},
        }
        for slug in slugs
        if slug in works
    ], total


def _authors(q: str) -> tuple[list[dict], int]:
    from library.models import Author

    rows = Author.objects.filter(is_imprint=False, list_in_biographies=True).filter(
        Q(name__icontains=q) | Q(slug__icontains=q)
    )
    total = rows.count()
    rows = list(rows.order_by("name")[:PER_KIND].values("slug", "name", "photo_url", "birth_year", "death_year"))
    reach = blocks_mod.editions(BlockType.AUTHOR, [r["slug"] for r in rows])
    return [
        {
            "kind": BlockType.AUTHOR,
            "key": f"author:{r['slug']}",
            "title": r["name"],
            "subtitle": blocks_mod.life_years(r["birth_year"], r["death_year"]),
            "image": r["photo_url"] or "",
            "languages": sorted(reach.get(r["slug"], set())),
            "block": {"type": BlockType.AUTHOR, "slug": r["slug"], "label": ""},
        }
        for r in rows
    ], total


def _topics(q: str) -> tuple[list[dict], int]:
    from library.models import Topic

    rows = Topic.objects.filter(is_published=True).filter(
        Q(title__icontains=q) | Q(slug__icontains=q) | Q(translations__title__icontains=q)
    ).distinct()
    total = rows.count()
    rows = list(rows.order_by("title")[:PER_KIND].values("slug", "title"))
    reach = blocks_mod.editions(BlockType.TOPIC, [r["slug"] for r in rows])
    return [
        {
            "kind": BlockType.TOPIC,
            "key": f"topic:{r['slug']}",
            "title": r["title"],
            "subtitle": "",
            "image": "",
            "languages": sorted(reach.get(r["slug"], set())),
            "block": {"type": BlockType.TOPIC, "slug": r["slug"], "label": ""},
        }
        for r in rows
    ], total


def _quotes(q: str) -> tuple[list[dict], int]:
    """Reviewed quotes whose words or author match — inserted as a quote block
    with the sourcing written out. A quote is in its source work's language."""
    from library.models import Quote

    rows = (
        Quote.objects.filter(reviewed=True)
        .filter(Q(chapter__book__is_published=True) | Q(sermon__is_published=True))
        .filter(Q(text__icontains=q) | Q(author__name__icontains=q))
    )
    total = rows.count()
    out = []
    for r in rows.order_by("slug")[:PER_KIND].values(
        "slug", "text", "author__name", "chapter__book__title", "chapter__book__language", "sermon__title", "sermon__language"
    ):
        source = r["chapter__book__title"] or r["sermon__title"] or ""
        language = r["chapter__book__language"] or r["sermon__language"] or ""
        attribution = f"{r['author__name']}, {source}" if source else r["author__name"]
        out.append(
            {
                "kind": BlockType.QUOTE,
                "key": f"quote:{r['slug']}",
                "title": r["text"],
                "subtitle": attribution,
                "image": "",
                "languages": [language] if language else [],
                "block": {"type": BlockType.QUOTE, "text": r["text"], "attribution": attribution},
            }
        )
    return out, total


def search(q: str) -> dict:
    """``{"results": [...], "counts": {kind: total}}`` for ``q`` across the site."""
    q = (q or "").strip()
    if len(q) < MIN_QUERY:
        return {"results": [], "counts": dict.fromkeys(KINDS, 0)}
    found: dict[str, tuple[list[dict], int]] = {
        BlockType.AUTHOR: _authors(q),
        BlockType.TOPIC: _topics(q),
        BlockType.QUOTE: _quotes(q),
    }
    for kind in (BlockType.BOOK, BlockType.SERMON, BlockType.PLAN, BlockType.ARTICLE):
        found[kind] = _per_language(kind, q)
    return {
        "results": [item for kind in KINDS for item in found[kind][0]],
        "counts": {kind: found[kind][1] for kind in KINDS},
    }
