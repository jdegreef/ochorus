"""Reshape nine Key Teachings volumes, and carry their readers along.

The Key Teachings companions (#4518, #4523) all shipped at exactly 22 chapters,
which read as a template rather than as books. Their manuscripts now vary —
some teaching chapters merged, some new ones added — so nine volumes move to
18-25 chapters (Julia Foote stays at 14; the first four volumes, older and
carrying the "Four Teachers" reading plan, keep their shape).

`seed_books` syncs an existing book's chapters by `order` but never deletes or
renumbers, so on a live install this migration, per volume:

1. Rebuilds the chapters from the fixture, only while the live book still has
   its OLD shape — 22 chapters whose titles are not already the fixture's (a
   re-run is a no-op; a fresh install, which seeds the new shape from the
   fixture, is untouched).
2. Moves every saved reader position — reading progress, bookmarks and their
   removal tombstones, highlight/note marks, notebook entries — to where the
   same paragraph now lives. Each old chapter goes to exactly one new chapter
   (`old_to_new` in the data file, from the editors' maps); within it a
   paragraph is found again by its exact text, and a paragraph that was
   rewritten in the merge lands on the nearest surviving paragraph before it.
   The `remap_marks` release step then re-finds each highlight's words.

The guards against a stale device pushing an old spot back are 0165's: moved
progress and notebook rows get a fresh ``client_updated_at``, a vacated
bookmark spot gets a removal tombstone, and a mark moved to another chapter is
tombstoned by id in its old chapter's row.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

from library.content_fixtures import book_fixture_path

DATA = Path(__file__).resolve().parent / "data" / "key_teachings_reshape.json"
OLD_COUNT = 22


# The stock set-apart labels every chapter carries. A merge keeps one set, at
# its end, so matching the first chapter's labels there would carry its whole
# closing run past the second chapter's text; they are left to the fallback.
_LABELS = {"FOR REFLECTION AND ACTION", "A PRAYER"}


def _positions(old_blocks: dict[int, list[str]], new_blocks: dict[int, list[str]], old_to_new):
    """(old_order, p) -> (new_order, p) for every paragraph of the old book."""
    table: dict[tuple[int, int], tuple[int, int]] = {}
    groups: dict[int, list[int]] = {}
    for old in sorted(old_blocks):
        groups.setdefault(old_to_new[old], []).append(old)
    for new, olds in groups.items():
        index: dict[str, list[int]] = {}
        for i, text in enumerate(new_blocks.get(new, [])):
            index.setdefault(" ".join(text.split()), []).append(i)
        # One cursor across a merge group, so the second chapter's paragraphs are
        # found after the first's — a line both share cannot pull it back.
        last = 0
        for old in olds:
            found: list[int | None] = []
            for text in old_blocks[old]:
                key = " ".join(text.split())
                hits = [] if key in _LABELS else index.get(key, [])
                hit = next((i for i in hits if i >= last), None)
                if hit is not None:
                    last = hit
                found.append(hit)
            # A rewritten paragraph lands on the nearest surviving one before it
            # in its own old chapter — or, when it opened that chapter, on the
            # next one (a merged-in chapter's opening belongs with its own text,
            # not the end of the chapter it joined).
            for p, spot in enumerate(found):
                if spot is None:
                    before = [f for f in found[:p] if f is not None]
                    after = [f for f in found[p + 1:] if f is not None]
                    spot = before[-1] if before else (after[0] if after else last)
                table[(old, p)] = (new, spot)
    return table


def reshape(apps, schema_editor):
    from library.corrections import settled_chapter_body
    from library.ingest import word_count
    from library.text import html_to_text
    from reading.anchor import block_texts

    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")
    for slug, spec in json.loads(DATA.read_text(encoding="utf-8")).items():
        try:
            book = Book.objects.get(slug=slug, language="en")
        except Book.DoesNotExist:
            continue  # fresh install: seed_books creates the new shape
        rows = json.loads(book_fixture_path(slug, "en").read_text(encoding="utf-8"))
        chapters = [r["fields"] for r in rows if r["model"] == "library.chapter"]
        live_titles = list(book.chapters.order_by("order").values_list("title", flat=True))
        if len(live_titles) != OLD_COUNT or live_titles == [f["title"] for f in chapters]:
            continue  # already reshaped (or hand-edited) — never clobber
        old_to_new = {int(k): v for k, v in spec["old_to_new"].items()}
        old_blocks = {c.order: block_texts(c.body_html) for c in book.chapters.all()}
        old_titles = set(live_titles)

        new_blocks = {}
        book.chapters.all().delete()
        for f in chapters:
            body = settled_chapter_body(slug, f["order"], f["body_html"])
            new_blocks[f["order"]] = block_texts(body)
            Chapter.objects.create(
                book=book,
                order=f["order"],
                title=f["title"],
                body_html=body,
                body_text=html_to_text(body),
                word_count=word_count(body),
                citations_indexed_at=None,
                search_vector=None,
            )
        table = _positions(old_blocks, new_blocks, old_to_new)
        # A spot saved past an old chapter's last paragraph goes where that
        # paragraph went — not to the end of a merged chapter.
        ends = {old: table.get((old, len(b) - 1), (old_to_new[old], 0)) for old, b in old_blocks.items()}

        def remap(order: int, p: int, table=table, ends=ends):
            if (order, p) in table:
                return table[(order, p)]
            return ends.get(order, (order, p))

        move_readers(apps, slug, remap, old_titles)


def move_readers(apps, slug, remap, old_titles):
    """0165's reader move (kept in step with it), for one book and a
    one-to-one chapter map."""
    from django.utils import timezone

    ReadingProgress = apps.get_model("reading", "ReadingProgress")
    Bookmark = apps.get_model("reading", "Bookmark")
    Removal = apps.get_model("reading", "Removal")
    ChapterMarks = apps.get_model("reading", "ChapterMarks")
    JournalEntry = apps.get_model("reading", "JournalEntry")
    Chapter = apps.get_model("library", "Chapter")

    now = timezone.now()
    now_ms = int(now.timestamp() * 1000)
    titles = dict(
        Chapter.objects.filter(book__slug=slug, book__language="en").values_list("order", "title")
    )

    # `furthest_order` is a chapter, so it follows its chapter's move; `pct` is a
    # share of the whole work's words, which a reshape barely shifts, so it stays.
    # English only: the chapters rebuilt above are the English edition's.
    for row in ReadingProgress.objects.filter(kind="book", book_slug=slug, language="en"):
        moved = remap(row.chapter_order, row.paragraph_index)
        furthest = remap(row.furthest_order, 0)[0] if row.furthest_order else 0
        if moved == (row.chapter_order, row.paragraph_index) and furthest == row.furthest_order:
            continue
        row.chapter_order, row.paragraph_index = moved
        row.furthest_order = furthest
        row.client_updated_at = now
        row.save(update_fields=[
            "chapter_order", "paragraph_index", "furthest_order", "client_updated_at", "updated_at",
        ])

    rems = list(Removal.objects.filter(domain="bookmark", kind="book", slug=slug))
    for r in rems:
        Removal.objects.filter(pk=r.pk).update(chapter_order=r.chapter_order + 10_000)
    seen = set()
    for r in rems:
        order, p = remap(r.chapter_order, r.paragraph_index)
        key = (r.profile_id, order, p)
        if key in seen:
            Removal.objects.filter(pk=r.pk).delete()
            continue
        seen.add(key)
        Removal.objects.filter(pk=r.pk).update(chapter_order=order, paragraph_index=p)

    rows = list(Bookmark.objects.filter(kind="book", book_slug=slug))
    old_spots = {r.pk: (r.chapter_order, r.paragraph_index) for r in rows}
    for r in rows:
        Bookmark.objects.filter(pk=r.pk).update(chapter_order=r.chapter_order + 10_000)
    taken = set()
    for r in rows:
        order, p = remap(*old_spots[r.pk])
        key = (r.profile_id, order, p)
        if key in taken:
            Bookmark.objects.filter(pk=r.pk).delete()
            continue
        taken.add(key)
        fields = {"chapter_order": order, "paragraph_index": p}
        if r.title in old_titles:  # a cached chapter title: follow the move
            fields["title"] = titles.get(order, r.title)
        Bookmark.objects.filter(pk=r.pk).update(**fields)
    for r in rows:
        spot = old_spots[r.pk]
        if remap(*spot) == spot or (r.profile_id, *spot) in taken:
            continue
        Removal.objects.get_or_create(
            profile_id=r.profile_id,
            domain="bookmark",
            kind="book",
            slug=slug,
            chapter_order=spot[0],
            paragraph_index=spot[1],
            defaults={"removed_at": now},
        )

    rows = list(ChapterMarks.objects.filter(kind="book", book_slug=slug, language="en"))
    ChapterMarks.objects.filter(pk__in=[r.pk for r in rows]).delete()
    merged: dict[tuple, dict] = {}

    def slot(profile_id, language, order):
        return merged.setdefault((profile_id, language, order), {"marks": [], "deleted": {}})

    for r in rows:
        new_order = remap(r.chapter_order, 0)[0]
        slot(r.profile_id, r.language, new_order)["deleted"].update(r.deleted or {})
        for m in r.marks or []:
            order, p = remap(r.chapter_order, int(m.get("p", 0)))
            slot(r.profile_id, r.language, order)["marks"].append({**m, "p": p})
            if order != r.chapter_order and m.get("id"):
                slot(r.profile_id, r.language, r.chapter_order)["deleted"][m["id"]] = now_ms
    for (profile_id, language, order), s in merged.items():
        if not s["marks"] and not s["deleted"]:
            continue
        ChapterMarks.objects.create(
            profile_id=profile_id,
            kind="book",
            book_slug=slug,
            language=language,
            chapter_order=order,
            marks=s["marks"],
            deleted=s["deleted"],
        )

    for e in JournalEntry.objects.filter(source__kind="book", source__slug=slug):
        s = e.source
        try:
            order, p = int(s.get("order", 1)), int(s.get("p", 0))
        except (TypeError, ValueError):
            continue
        moved = remap(order, p)
        if moved == (order, p):
            continue
        s["order"], s["p"] = moved
        e.source = s
        e.client_updated_at = now
        e.save(update_fields=["source", "client_updated_at", "updated_at"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0169_remove_henry_blackaby_bio"),
        ("reading", "0031_progress_furthest_and_pct"),
    ]

    operations = [
        migrations.RunPython(reshape, noop),
    ]
