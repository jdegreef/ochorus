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
OLD_QUEEN_MARY_TITLE = "Persecutions in England During the Reign of Queen Mary"

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
    """Move every saved position on this book, and fence off the old ones.

    The server rows are remapped in place. Readers' devices also cache these
    positions and sync by union / client timestamp, so a stale device could
    push an old spot back under the new numbering. Three guards stop that:
    moved progress and notebook rows get a fresh ``client_updated_at`` so the
    server copy wins the merge; each bookmark's vacated spot gets a removal
    tombstone (unless a moved bookmark now lives there); and each mark moved to
    another chapter is tombstoned, by id, in its old chapter's row. A mark that
    stays in its chapter with a shifted paragraph can't be fenced this way (same
    row, same id); those are the few tails of rejoined headings.
    """
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
        Chapter.objects.filter(book__slug=SLUG, book__language="en").values_list("order", "title")
    )

    known_titles = set(titles.values()) | {OLD_QUEEN_MARY_TITLE}

    for row in ReadingProgress.objects.filter(kind="book", book_slug=SLUG):
        moved = remap(row.chapter_order, row.paragraph_index)
        if moved == (row.chapter_order, row.paragraph_index):
            continue
        row.chapter_order, row.paragraph_index = moved
        row.client_updated_at = now
        row.save(update_fields=["chapter_order", "paragraph_index", "client_updated_at", "updated_at"])

    # Existing bookmark tombstones move with the numbering, like the bookmarks.
    rems = list(Removal.objects.filter(domain="bookmark", kind="book", slug=SLUG))
    for r in rems:
        Removal.objects.filter(pk=r.pk).update(chapter_order=r.chapter_order + 10_000)
    seen = set()
    for r in rems:
        order, p = remap(r.chapter_order, r.paragraph_index)
        key = (r.profile_id, order, p)
        clash = Removal.objects.filter(
            profile_id=r.profile_id, domain="bookmark", kind="book", slug=SLUG,
            chapter_order=order, paragraph_index=p,
        ).exists()
        if key in seen or clash:
            Removal.objects.filter(pk=r.pk).delete()
            continue
        seen.add(key)
        Removal.objects.filter(pk=r.pk).update(chapter_order=order, paragraph_index=p)

    # Bookmarks move IN PLACE (a re-insert would reset created_at). The spot is
    # unique, so park every row on a temporary order first, then set the final
    # one; a second bookmark landing on the same paragraph (the two halves of a
    # rejoined heading) is dropped.
    rows = list(Bookmark.objects.filter(kind="book", book_slug=SLUG))
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
        if r.title in known_titles:  # cached chapter title: follow the move
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
            slug=SLUG,
            chapter_order=spot[0],
            paragraph_index=spot[1],
            defaults={"removed_at": now},
        )

    # One marks row per (reader, chapter): a chapter-16 row fans out across the
    # eight parts, and its tombstones go to every part it spans.
    rows = list(ChapterMarks.objects.filter(kind="book", book_slug=SLUG))
    ChapterMarks.objects.filter(pk__in=[r.pk for r in rows]).delete()
    merged: dict[tuple, dict] = {}

    def slot(profile_id, language, order):
        return merged.setdefault((profile_id, language, order), {"marks": [], "deleted": {}})

    for r in rows:
        spans = {remap(r.chapter_order, 0)[0], remap(r.chapter_order, 10_000)[0]}
        if r.chapter_order == 16:
            spans = set(range(16, 24))
        for order in spans:
            slot(r.profile_id, r.language, order)["deleted"].update(r.deleted or {})
        for m in r.marks or []:
            new_order, new_p = remap(r.chapter_order, int(m.get("p", 0)))
            slot(r.profile_id, r.language, new_order)["marks"].append({**m, "p": new_p})
            if new_order != r.chapter_order and m.get("id"):
                slot(r.profile_id, r.language, r.chapter_order)["deleted"][m["id"]] = now_ms
    for (profile_id, language, order), s in merged.items():
        if not s["marks"] and not s["deleted"]:
            continue
        ChapterMarks.objects.create(
            profile_id=profile_id,
            kind="book",
            book_slug=SLUG,
            language=language,
            chapter_order=order,
            marks=s["marks"],
            deleted=s["deleted"],
        )

    for e in JournalEntry.objects.filter(source__kind="book", source__slug=SLUG):
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
        ("library", "0164_unpublish_copyright_blocked_translations"),
        ("reading", "0029_custom_shelf"),
    ]

    operations = [
        migrations.RunPython(rebuild, noop),
    ]
