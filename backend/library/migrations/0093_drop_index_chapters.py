"""Delete four back-matter "chapters" that are really CCEL's word indexes.

Watson's *Ten Commandments* ends on a chapter called "Latin Words and Phrases";
so does Edwards' *Freedom of the Will*; Wesley's *Sermons on Several Occasions*
ends on two. They are CCEL's glossaries of Greek and Latin terms, filed under an
"Indexes" part whose LEAF titles name nothing ``is_front_matter`` could
recognise — so the leaf-level check passed them and they imported as chapters.

The importer now inherits a part's front-matter verdict down to its leaves, so
a re-import no longer produces them. This removes the ones already in prod.

Safe to run because all four are the LAST chapter of their book: nothing is
renumbered, no ``PlanDay`` mapping moves, and the only reading position that
could be disturbed is one parked on a glossary.

Anchored on the exact title as well as the order, so it cannot delete a real
chapter that happens to sit at that position, and a re-run is a no-op.
"""

from __future__ import annotations

from django.db import migrations

#: (book slug, chapter title) — the order is deliberately NOT part of the key;
#: matching on title alone means a fixture that has already dropped them, or a
#: book re-imported at a different length, still resolves correctly.
INDEX_CHAPTERS = [
    ("ten-commandments", "Latin Words and Phrases"),
    ("freedom-of-the-will", "Latin Words and Phrases"),
    ("sermons-on-several-occasions", "Greek Words and Phrases"),
    ("sermons-on-several-occasions", "Latin Words and Phrases"),
]


def drop_index_chapters(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    for slug, title in INDEX_CHAPTERS:
        Chapter.objects.filter(book__slug=slug, title=title).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0092_strip_restated_chapter_headings"),
    ]

    operations = [
        migrations.RunPython(drop_index_chapters, migrations.RunPython.noop),
    ]
