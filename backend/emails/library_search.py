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

from types import SimpleNamespace

from django.db.models import Q

from . import blocks as blocks_mod
from .blocks import BlockType

#: Results per kind; the panel shows counts and lets the admin narrow by kind.
PER_KIND = 8
#: The order kinds are listed in.
KINDS = ("author", "book", "sermon", "plan", "article", "topic", "quote")
MIN_QUERY = 2


def _cover(slug: str, language: str, cover_url: str) -> str:
    from library.book_export import cover_image_url

    return cover_image_url(SimpleNamespace(slug=slug, language=language, cover_url=cover_url))


def _per_language(kind: str, q: str) -> tuple[list[dict], int]:
    """Books, sermons, plans or articles matching ``q``: one row per slug."""
    _, _, _, title_field = blocks_mod.LIBRARY[kind]
    model = blocks_mod.library_model(kind)
    match = Q(**{f"{title_field}__icontains": q}) | Q(slug__icontains=q)
    if blocks_mod.has_author(kind):
        match |= Q(author__name__icontains=q)
    rows = model.objects.filter(is_published=True).filter(match)
    slugs = list(rows.order_by("slug").values_list("slug", flat=True).distinct())
    total = len(slugs)
    slugs = slugs[:PER_KIND]
    fields = ["slug", "language", title_field]
    if blocks_mod.has_author(kind):
        fields.append("author__name")
    if kind == BlockType.BOOK:
        fields.append("cover_url")
    found: dict[str, dict] = {}
    for row in model.objects.filter(is_published=True, slug__in=slugs).order_by("slug", "language").values(*fields):
        item = found.setdefault(
            row["slug"],
            {
                "kind": kind,
                "key": f"{kind}:{row['slug']}",
                "title": row[title_field],
                "subtitle": row.get("author__name", ""),
                "image": "",
                "languages": [],
                "block": {"type": kind, "slug": row["slug"], "label": ""},
            },
        )
        item["languages"].append(row["language"])
        if row["language"] == "en" or not item["image"]:
            if row["language"] == "en":
                item["title"] = row[title_field]
            if kind == BlockType.BOOK:
                item["image"] = _cover(row["slug"], row["language"], row["cover_url"])
    return [found[s] for s in slugs if s in found], total


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
            "subtitle": "–".join(str(y) for y in (r["birth_year"], r["death_year"]) if y),
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

    rows = Quote.objects.filter(reviewed=True).filter(Q(text__icontains=q) | Q(author__name__icontains=q))
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
                "kind": "quote",
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
        "author": _authors(q),
        "topic": _topics(q),
        "quote": _quotes(q),
    }
    for kind in (BlockType.BOOK, BlockType.SERMON, BlockType.PLAN, BlockType.ARTICLE):
        found[kind] = _per_language(kind, q)
    return {
        "results": [item for kind in KINDS for item in found[kind][0]],
        "counts": {kind: found[kind][1] for kind in KINDS},
    }
