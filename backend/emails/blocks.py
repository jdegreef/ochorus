"""Campaign content as blocks — what the admin designer edits and the email renders.

A broadcast's per-language content is ``{"preheader": ..., "blocks": [...]}``,
an ordered list of typed blocks. Every block is structured data, never HTML: the
template escapes all of it, so there is still nothing to sanitize.

* Layout blocks carry their own words: ``heading``, ``text`` (blank lines split
  paragraphs), ``button`` (label + a reader-site path), ``divider``, ``quote``.
* ``continue_reading`` is the reader's OWN book in progress — their most recent
  unfinished book, at the chapter they reached — so it differs per recipient and
  is left out for a reader with nothing in progress.
* Design blocks: ``image`` (an uploaded or site image, optionally linked),
  ``hero`` (a coloured banner with a title, optional picture and button),
  ``spacer``, and ``scripture`` (a verse and its reference, in the email's own
  words).
* ``book_row`` shows up to three books side by side, each the edition in the
  email's language; books with no such edition drop out of the row.
* ``author`` and ``topic`` point at one row with translated text: an author card
  (photo, name, the bio in that language when there is one) and a topic card
  (its title in that language — a topic not translated into it is left out).
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
    CONTINUE = "continue_reading", "Continue reading"
    IMAGE = "image", "Image"
    HERO = "hero", "Hero banner"
    BOOK_ROW = "book_row", "Book row"
    SPACER = "spacer", "Spacer"
    SCRIPTURE = "scripture", "Scripture"
    AUTHOR = "author", "Author"
    TOPIC = "topic", "Topic"
    ARTICLE = "article", "Article"


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
    BlockType.CONTINUE: ("heading", "label"),
    BlockType.IMAGE: ("url", "alt", "path", "caption"),
    BlockType.HERO: ("eyebrow", "title", "text", "image", "color", "label", "path"),
    BlockType.BOOK_ROW: ("slugs", "label"),
    BlockType.SPACER: ("size",),
    BlockType.SCRIPTURE: ("text", "reference"),
    BlockType.AUTHOR: ("slug", "label"),
    BlockType.TOPIC: ("slug", "label"),
    BlockType.ARTICLE: ("slug", "label"),
}

#: Per-language rows sharing a slug: a block renders the email language's own
#: row, or nothing (there is no English fallback).
LIBRARY_TYPES = (BlockType.BOOK, BlockType.SERMON, BlockType.PLAN, BlockType.ARTICLE)
#: One row with translated text (authors, topics).
ENTITY_TYPES = (BlockType.AUTHOR, BlockType.TOPIC)
#: Every block that names something in the library by slug.
SLUG_TYPES = (*LIBRARY_TYPES, *ENTITY_TYPES)

#: A hero's background colours — the site's own hues, dark enough for white text.
HERO_COLORS = {
    "navy": "#1f3a6e",
    "cypress": "#2c594d",
    "indigo": "#3b438f",
    "plum": "#613f64",
    "oxblood": "#833731",
    "ochre": "#795725",
}
#: A spacer's heights, in pixels.
SPACER_SIZES = {"small": 12, "medium": 28, "large": 48}
#: Most books a book row shows.
BOOK_ROW_MAX = 3

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
WORD_FIELDS = ("text", "label", "attribution", "heading", "title", "eyebrow", "caption", "alt", "reference")


def has_body(blocks: list[dict], reaches=None) -> bool:
    """Whether a block list says anything (not only dividers and empty text).
    ``reaches(block)`` says whether a library block will actually render (has an
    edition in the email's language); by default any chosen work counts."""
    for b in blocks:
        if b["type"] == BlockType.CONTINUE:
            continue  # per reader, and absent for anyone with nothing in progress
        if b["type"] in SLUG_TYPES:
            if b.get("slug") and (reaches is None or reaches(b)):
                return True
        elif b["type"] == BlockType.BOOK_ROW:
            if any(reaches is None or reaches({"type": BlockType.BOOK, "slug": s}) for s in row_slugs(b)):
                return True
        elif b["type"] == BlockType.IMAGE:
            if b.get("url"):
                return True
        elif any(b.get(f) for f in ("text", "label", "title")):
            return True
    return False


def row_slugs(block: dict) -> list[str]:
    """The books a ``book_row`` names, in order (comma-separated, deduplicated)."""
    seen: list[str] = []
    for slug in (block.get("slugs") or "").split(","):
        slug = slug.strip()
        if slug and slug not in seen:
            seen.append(slug)
    return seen[:BOOK_ROW_MAX]


def library_refs(blocks: list[dict]) -> dict[str, set[str]]:
    """``{kind: slugs}`` for the library blocks that name a work."""
    refs: dict[str, set[str]] = {}
    for b in blocks:
        if b["type"] in SLUG_TYPES and b.get("slug"):
            refs.setdefault(b["type"], set()).add(b["slug"])
        elif b["type"] == BlockType.BOOK_ROW:
            refs.setdefault(BlockType.BOOK, set()).update(row_slugs(b))
    return refs


# --- Library lookups ------------------------------------------------------------


#: What each library type is: its model, its reader-site section, the field its
#: card's blurb comes from, and its title field. Plans and articles have no author.
LIBRARY = {
    BlockType.BOOK: ("Book", "books", "description", "title"),
    BlockType.SERMON: ("Sermon", "sermons", "summary", "title"),
    BlockType.PLAN: ("Plan", "plans", "description", "title"),
    BlockType.ARTICLE: ("Article", "articles", "description", "h1"),
    BlockType.AUTHOR: ("Author", "authors", "bio", "name"),
    BlockType.TOPIC: ("Topic", "topics", "description", "title"),
}


def library_model(kind: str):
    """The library model a library block type points at."""
    from django.apps import apps

    return apps.get_model("library", LIBRARY[kind][0])


def has_author(kind: str) -> bool:
    return kind in (BlockType.BOOK, BlockType.SERMON)


def editions(kind: str, slugs) -> dict[str, set[str]]:
    """``{slug: {languages it is published in}}`` for one library type.

    An author is in every language (their name and photo travel; the bio shows
    where it is translated); a topic is in English and each language it has a
    translated title in."""
    from library.languages import known_codes

    out: dict[str, set[str]] = {}
    if kind == BlockType.AUTHOR:
        codes = set(known_codes())
        return {slug: set(codes) for slug in library_model(kind).objects.filter(slug__in=set(slugs)).values_list("slug", flat=True)}
    if kind == BlockType.TOPIC:
        from library.models import TopicTranslation

        for slug in library_model(kind).objects.filter(slug__in=set(slugs), is_published=True).values_list("slug", flat=True):
            out[slug] = {"en"}
        rows = (
            TopicTranslation.objects.filter(topic__slug__in=list(out))
            .exclude(title="")
            .values_list("topic__slug", "language")
        )
        for slug, language in rows:
            out[slug].add(language)
        return out
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

    if kind in ENTITY_TYPES:
        return _entity_cards(kind, slugs, lang)
    _, section, blurb_field, title_field = LIBRARY[kind]
    fields = ["slug", title_field, blurb_field]
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
            "title": row[title_field],
            "author": row.get("author__name", ""),
            "description": _blurb(row[blurb_field]),
            "cover_url": links.site_url(cover) if cover.startswith("/") else cover,
            "url": links.site_url(links.reader_path(section, row["slug"], lang)),
        }
    return cards


def _entity_cards(kind: str, slugs, lang: str) -> dict[str, dict]:
    """Cards for authors and topics: one row each, its words in ``lang`` from the
    translation side-table (English from the row itself). A topic with no title
    in ``lang`` has no card; an author always has one, with their bio only where
    it is written in ``lang``."""
    from library.models import AuthorTranslation, TopicTranslation

    _, section, _, _ = LIBRARY[kind]
    model = library_model(kind)
    cards: dict[str, dict] = {}
    if kind == BlockType.AUTHOR:
        rows = model.objects.filter(slug__in=set(slugs)).values(
            "id", "slug", "name", "bio", "tagline", "photo_url", "birth_year", "death_year"
        )
        bios = {}
        if lang != "en":
            bios = dict(
                AuthorTranslation.objects.filter(author__slug__in=set(slugs), language=lang)
                .exclude(bio="")
                .values_list("author__slug", "bio")
            )
        for row in rows:
            bio = row["bio"] if lang == "en" else bios.get(row["slug"], "")
            years = "–".join(str(y) for y in (row["birth_year"], row["death_year"]) if y)
            photo = row["photo_url"] or ""
            cards[row["slug"]] = {
                "title": row["name"],
                "author": years,
                "description": _blurb(bio),
                "cover_url": links.site_url(photo) if photo.startswith("/") else photo,
                "url": links.site_url(links.reader_path(section, row["slug"], lang)),
            }
        return cards
    rows = model.objects.filter(slug__in=set(slugs), is_published=True).values("id", "slug", "title", "description")
    words = {}
    if lang != "en":
        words = {
            t["topic__slug"]: t
            for t in TopicTranslation.objects.filter(topic__slug__in=set(slugs), language=lang)
            .exclude(title="")
            .values("topic__slug", "title", "description")
        }
    for row in rows:
        text = row if lang == "en" else words.get(row["slug"])
        if not text:
            continue
        cards[row["slug"]] = {
            "title": text["title"],
            "author": "",
            "description": _blurb(text["description"]),
            "cover_url": "",
            "url": links.site_url(links.reader_path(section, row["slug"], lang)),
        }
    return cards


def image_url(url: str) -> str:
    """An image address an email can show: a site path made absolute, or an
    https URL as is; anything else (http, data:, javascript:) is ``""``."""
    url = (url or "").strip()
    if url.startswith("/") and not url.startswith("//"):
        return links.site_url(url)
    return url if url.startswith("https://") else ""


def _latest_progress(profile_ids) -> dict:
    """``{profile_id: progress}`` — each reader's most recent unfinished book."""
    from reading.models import ReadingProgress, WorkKind

    latest: dict = {}
    rows = (
        ReadingProgress.objects.filter(
            profile_id__in=profile_ids, kind=WorkKind.BOOK, finished_at__isnull=True
        )
        .order_by("profile_id", "-updated_at")
        .values("profile_id", "book_slug", "language", "chapter_order")
    )
    for row in rows:
        latest.setdefault(row["profile_id"], row)
    return latest


def prefetch_progress(profile_ids, cards: dict) -> None:
    """Look up a whole batch's books in progress in one query, into the send's
    ``cards`` cache, so ``continue_reading`` costs no query per reader."""
    latest = _latest_progress(profile_ids)
    for pk in profile_ids:
        cards[("progress", pk)] = latest.get(pk)


def _continue_card(profile, cards: dict) -> dict | None:
    """The reader's most recent unfinished book, as a card pointing at the
    chapter they reached — in the edition they are reading, which may not be the
    email's language. ``None`` when nothing is in progress (or the edition is no
    longer published)."""
    if profile is None or profile.pk is None:
        return None
    key = ("progress", profile.pk)
    progress = cards[key] if key in cards else _latest_progress([profile.pk]).get(profile.pk)
    if progress is None:
        return None
    lang, slug = progress["language"], progress["book_slug"]
    key = (BlockType.BOOK, lang, slug)
    if key not in cards:
        cards[key] = _cards(BlockType.BOOK, {slug}, lang).get(slug)
    card = cards[key]
    if card is None:
        return None
    chapter = max(progress["chapter_order"] or 1, 1)
    return {
        **card,
        "chapter": chapter,
        "url": links.site_url(links.localized(f"books/{slug}/{chapter}/", lang)),
    }


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
    profile=None,
) -> list[dict]:
    """Render-ready blocks for one email in ``lang``: ``{name}`` filled in,
    button paths made absolute, library blocks looked up in ``lang`` — and those
    with no edition in ``lang`` left out.

    ``localize_buttons`` puts admin-written button paths in ``lang``'s pages.
    The fixed-copy emails pass False: their paths are built by code that already
    chose the right edition (a series nudge may point an English series at a
    reader whose email is Spanish), and English pages are unprefixed.

    ``profile`` is the recipient, for the blocks that differ per reader
    (``continue_reading``); without one those blocks are left out.

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

    def path_url(path: str) -> str:
        path = (path or "").strip()
        if not path:
            return ""
        return links.site_url(_button_path(path, lang) if localize_buttons else path)

    out = []
    for b in blocks:
        kind = b["type"]
        if kind in SLUG_TYPES:
            card = cards.get((kind, lang, b.get("slug", "")))
            if card is None:
                continue
            out.append({"type": kind, "label": b.get("label", ""), **card})
        elif kind == BlockType.BOOK_ROW:
            row = [c for s in row_slugs(b) if (c := cards.get((BlockType.BOOK, lang, s)))]
            if row:
                out.append({"type": kind, "label": b.get("label", ""), "books": row, "width": 100 // len(row)})
        elif kind == BlockType.IMAGE:
            src = image_url(b.get("url", ""))
            if src:
                out.append({**b, "src": src, "url": path_url(b.get("path", ""))})
        elif kind == BlockType.HERO:
            if b.get("title") or b.get("text"):
                out.append(
                    {
                        **b,
                        "src": image_url(b.get("image", "")),
                        "bg": HERO_COLORS.get(b.get("color", ""), HERO_COLORS["navy"]),
                        "url": path_url(b.get("path", "")) if b.get("label") else "",
                        "text": b.get("text", "").replace("{name}", name),
                    }
                )
        elif kind == BlockType.SPACER:
            out.append({"type": kind, "height": SPACER_SIZES.get(b.get("size", ""), SPACER_SIZES["medium"])})
        elif kind == BlockType.SCRIPTURE:
            if b.get("text"):
                out.append(b)
        elif kind == BlockType.CONTINUE:
            card = _continue_card(profile, cards)
            if card is not None:
                # ``{chapter}`` in the label becomes the chapter they reached.
                label = b.get("label", "").replace("{chapter}", str(card["chapter"]))
                out.append({"type": kind, "heading": b.get("heading", ""), "label": label, **card})
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
