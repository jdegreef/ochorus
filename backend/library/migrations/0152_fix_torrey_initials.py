"""Correct R. A. Torrey's initials in the *Men of Prayer* contents.

The evangelist is Reuben Archer Torrey — R. A. Torrey — but chapter 6 of
*Men of Prayer* (``men-of-prayer-2``) shipped with the initials reversed,
"A. R. Torrey (1856 – 1928)". The fixture was corrected in #1166, but
``seed_books`` deliberately never syncs an existing book's chapters (chapter
``order`` is a public contract), so no deploy has carried that fix to the row
already in production. This is the backfill; the fixture already holds the
right form, and ``tests_fixture`` keeps the two from drifting apart.

Scoped to the one chapter (this book, English, order 6) and a no-op once the
initials read correctly, so it is safe to re-run.

``search_vector`` is NULLed on the row written: the title is weight A in the
chapter's stored tsvector (library/fts.py), and a historical model's ``save()``
runs none of the real hooks, so the retitled row would keep matching "A. R.".
The release chain's ``backfill_search_vectors`` refills NULLs on the next
deploy. See 0121 for the same shape.
"""

from __future__ import annotations

from django.db import migrations

OLD = "A. R. Torrey"
NEW = "R. A. Torrey"


def fix(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    qs = Chapter.objects.filter(
        book__slug="men-of-prayer-2",
        book__language="en",
        order=6,
        title__contains=OLD,
    ).only("id", "title")
    for ch in qs.iterator():
        ch.title = ch.title.replace(OLD, NEW)
        ch.search_vector = None
        ch.save(update_fields=["title", "search_vector"])


def noop(apps, schema_editor):
    """Deliberately irreversible — restoring "A. R. Torrey" would only put the
    error back."""


class Migration(migrations.Migration):
    dependencies = [("library", "0151_meyer_display_name")]
    operations = [migrations.RunPython(fix, noop)]
