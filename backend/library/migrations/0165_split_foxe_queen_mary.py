"""Split Fox's Book of Martyrs' Queen Mary chapter, and carry readers along.

#3216 shipped the book with chapter XVI ("Persecutions in England During the
Reign of Queen Mary") as ONE chapter of ~46,000 words, far past a day's reading.
The build command now cuts it at its own section headings into eight parts
(chapters 16-23), so the old chapters 17-22 become 24-29. The same rebuild
rejoins 15 section titles CCEL had broken across two or three headings, and
turns two "headings" that are really prose back into paragraphs; that shifts
paragraph indices inside chapters 3, 5, 6, 15 and 16. The wording is unchanged.

`seed_books` never touches an existing book's chapters (order is a public
contract), so this migration does two things on a live install:

1. Rebuilds the book's chapters from the fixture, only while the live book
   still has the OLD 22-chapter shape (so a re-run is a no-op and a fresh
   install, which seeds 29 from the fixture, is untouched).
2. Moves every saved reader position on this book to where the same paragraph
   now lives: reading progress, bookmarks, bookmark-removal tombstones,
   highlight/note marks, and notebook entries written from a passage. The map
   is exact: it was computed by aligning the old and new top-level blocks
   (2,220 -> 2,205) and stored below as (old_order, first_p, last_p,
   new_order, p_delta) ranges. A highlight on the tail line of a rejoined
   heading keeps its character offsets, which now count from that heading's
   start; no text is lost.

Bodies go through `settled_chapter_body` as `seed_books` does; derived columns
are set by hand as in 0162.
"""

from __future__ import annotations

import json

from django.db import migrations

from library.content_fixtures import book_fixture_path

SLUG = "foxes-book-of-martyrs"
OLD_CHAPTERS = 22

# (old_order, first_p, last_p, new_order, p_delta)
RANGES = [
    (1, 0, 29, 1, 0),
    (2, 0, 191, 2, 0),
    (3, 0, 35, 3, 0),
    (3, 36, 54, 3, -1),
    (4, 0, 83, 4, 0),
    (5, 0, 24, 5, 0),
    (5, 25, 119, 5, -1),
    (5, 120, 172, 5, -2),
    (6, 0, 121, 6, 0),
    (6, 122, 154, 6, -1),
    (6, 155, 363, 6, -2),
    (7, 0, 22, 7, 0),
    (8, 0, 105, 8, 0),
    (9, 0, 40, 9, 0),
    (10, 0, 52, 10, 0),
    (11, 0, 18, 11, 0),
    (12, 0, 38, 12, 0),
    (13, 0, 18, 13, 0),
    (14, 0, 57, 14, 0),
    (15, 0, 21, 15, 0),
    (15, 22, 22, 15, -1),
    (15, 23, 63, 15, -2),
    (16, 0, 12, 16, 0),
    (16, 13, 31, 16, -1),
    (16, 32, 53, 16, -2),
    (16, 54, 136, 17, -54),
    (16, 137, 152, 18, -137),
    (16, 153, 164, 18, -138),
    (16, 165, 214, 18, -139),
    (16, 215, 219, 18, -140),
    (16, 220, 276, 19, -220),
    (16, 277, 368, 20, -277),
    (16, 369, 422, 21, -369),
    (16, 423, 454, 22, -423),
    (16, 455, 472, 22, -424),
    (16, 473, 526, 23, -473),
    (16, 527, 547, 23, -474),
    (17, 0, 86, 24, 0),
    (18, 0, 25, 25, 0),
    (18, 26, 76, 25, -1),
    (19, 0, 11, 26, 0),
    (20, 0, 14, 27, 0),
    (21, 0, 66, 28, 0),
    (22, 0, 93, 29, 0),
]


def remap(order: int, p: int) -> tuple[int, int]:
    for old, first, last, new, delta in RANGES:
        if old == order and first <= p <= last:
            return new, p + delta
    # Past the last known block (a position saved beyond the end): keep the
    # chapter's own shift and the index as is.
    if order >= 17:
        return order + 7, p
    if order == 16:
        return 23, max(p - 474, 0)
    return order, p


def rebuild(apps, schema_editor):
    from library.corrections import settled_chapter_body
    from library.ingest import word_count
    from library.text import html_to_text

    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")
    try:
        book = Book.objects.get(slug=SLUG, language="en")
    except Book.DoesNotExist:
        return  # fresh install: seed_books creates all 29 from the fixture
    if book.chapters.count() != OLD_CHAPTERS:
        return  # already split (or hand-edited) — never clobber

    rows = json.loads(book_fixture_path(SLUG, "en").read_text(encoding="utf-8"))
    book.chapters.all().delete()
    for f in (r["fields"] for r in rows if r["model"] == "library.chapter"):
        body = settled_chapter_body(SLUG, f["order"], f["body_html"])
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
    move_readers(apps)


def move_readers(apps):
    ReadingProgress = apps.get_model("reading", "ReadingProgress")
    Bookmark = apps.get_model("reading", "Bookmark")
    Removal = apps.get_model("reading", "Removal")
    ChapterMarks = apps.get_model("reading", "ChapterMarks")
    JournalEntry = apps.get_model("reading", "JournalEntry")

    for row in ReadingProgress.objects.filter(kind="book", book_slug=SLUG):
        row.chapter_order, row.paragraph_index = remap(row.chapter_order, row.paragraph_index)
        row.save(update_fields=["chapter_order", "paragraph_index"])

    # Unique per spot: rebuild the set, dropping a second bookmark that lands
    # on the same paragraph (the two halves of a rejoined heading).
    for model, filt in (
        (Bookmark, {"kind": "book", "book_slug": SLUG}),
        (Removal, {"domain": "bookmark", "kind": "book", "slug": SLUG}),
    ):
        rows = list(model.objects.filter(**filt))
        model.objects.filter(pk__in=[r.pk for r in rows]).delete()
        seen = set()
        for r in rows:
            r.chapter_order, r.paragraph_index = remap(r.chapter_order, r.paragraph_index)
            key = (r.profile_id, r.chapter_order, r.paragraph_index)
            if key in seen:
                continue
            seen.add(key)
            r.pk = None
            r.save()

    # One marks row per (reader, chapter): a chapter-16 row fans out across the
    # eight parts; its tombstones go with every part (they are keyed by id).
    rows = list(ChapterMarks.objects.filter(kind="book", book_slug=SLUG))
    ChapterMarks.objects.filter(pk__in=[r.pk for r in rows]).delete()
    merged: dict[tuple, dict] = {}
    for r in rows:
        for m in r.marks or []:
            new_order, new_p = remap(r.chapter_order, int(m.get("p", 0)))
            key = (r.profile_id, r.language, new_order)
            slot = merged.setdefault(key, {"marks": [], "deleted": {}})
            slot["marks"].append({**m, "p": new_p})
            slot["deleted"].update(r.deleted or {})
        if not r.marks and r.deleted:
            new_order, _ = remap(r.chapter_order, 0)
            key = (r.profile_id, r.language, new_order)
            merged.setdefault(key, {"marks": [], "deleted": {}})["deleted"].update(r.deleted)
    for (profile_id, language, order), slot in merged.items():
        ChapterMarks.objects.create(
            profile_id=profile_id,
            kind="book",
            book_slug=SLUG,
            language=language,
            chapter_order=order,
            marks=slot["marks"],
            deleted=slot["deleted"],
        )

    for e in JournalEntry.objects.filter(source__isnull=False):
        s = e.source
        if not isinstance(s, dict) or s.get("kind") != "book" or s.get("slug") != SLUG:
            continue
        try:
            order, p = int(s.get("order", 1)), int(s.get("p", 0))
        except (TypeError, ValueError):
            continue
        s["order"], s["p"] = remap(order, p)
        e.source = s
        e.save(update_fields=["source"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0164_unpublish_copyright_blocked_translations"),
        ("reading", "0029_custom_shelf"),
    ]

    operations = [
        migrations.RunPython(rebuild, noop),
    ]
