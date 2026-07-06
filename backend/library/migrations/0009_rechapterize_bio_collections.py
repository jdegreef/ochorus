"""Replace the chapters of the re-chapterized books with the corrected sets.

The importer's chapter detection was fixed for the "Ochorus Originals"
biography-collection layout (two-line headings, TOC/appendix phantom markers,
lost Introduction/Conclusion sections) and for subhead-glued titles. The
affected books were re-imported locally; prod is never re-seeded from the
fixture, so this migration carries the corrected chapter sets to the live DB by
replacing each affected book's chapters from the committed fixture.

Chapter has no inbound FKs (reading progress/marks live in localStorage keyed
by slug+order), so delete-and-recreate is safe.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from django.db import migrations

# Books whose chapter sets were rebuilt by the fixed importer. Books the
# re-import left identical are omitted; the-inner-chamber is deliberately kept
# on its current 36 chapters (the re-import would add a Preface as ch1, which
# shifts every chapter_order and breaks the seeded 36-day reading plan and
# readers' saved positions — not worth a bonus preface).
AFFECTED_SLUGS = {
    "men-who-moved-heaven",
    "men-who-tended-the-flock-2",
    "women-who-moved-heaven-2",
    "men-and-women-who-gave-everything-2",
    "men-of-prayer-2",
    "talks-to-the-farmer",
    "feasting-at-the-table",
    "stepping-stones-2",
}

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "launch.json"


def replace_chapters(apps, schema_editor):
    # Real helper so body_text derives exactly as Chapter.save() would —
    # bulk_create bypasses save(), and the fixture deliberately omits body_text.
    from library.text import html_to_text

    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")

    rows = json.loads(FIXTURE.read_text())
    # Fixture book pk -> (slug, language); chapters reference books by pk.
    book_key = {
        r["pk"]: (r["fields"]["slug"], r["fields"]["language"])
        for r in rows
        if r["model"] == "library.book"
    }
    by_book: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        if r["model"] != "library.chapter":
            continue
        key = book_key.get(r["fields"]["book"])
        if key and key[0] in AFFECTED_SLUGS:
            by_book[key].append(r["fields"])

    for (slug, language), fields in by_book.items():
        try:
            book = Book.objects.get(slug=slug, language=language)
        except Book.DoesNotExist:  # not on this install — nothing to replace
            continue
        book.chapters.all().delete()
        Chapter.objects.bulk_create(
            Chapter(
                book=book,
                order=f["order"],
                title=f["title"],
                body_html=f["body_html"],
                body_text=html_to_text(f["body_html"]),
                word_count=f["word_count"],
            )
            for f in sorted(fields, key=lambda f: f["order"])
        )


def noop(apps, schema_editor):
    # Not reversible — the old (mis-extracted) chapters aren't retained.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0008_merge_20260705_2246"),
    ]

    operations = [
        migrations.RunPython(replace_chapters, noop),
    ]
