"""Give the-bruised-reed's last chapter its whole title on seeded databases.

0134 re-imported the book from Pickering's 1838 printing, which has 28
chapters. ``corrections.chapter_titles`` stopped at 27, because it was written
for Grosart's scan, which had lost the "XXVIII." marker and merged the last two
chapters. So chapter 28 kept the importer's first heading line, cut off mid-
phrase: "Be encouraged to go on cheerfully, with confidence". The heading reads
"… with confidence of prevailing." ``corrections.py`` now carries it.

A correction to 0134's own docstring, which can't be edited once deployed: it
says the old edition carried chapters 17-27 under the WRONG TITLES. It did not.
Every one of its titles matched its body; it was one chapter SHORT, the last
two merged.

``seed_books`` leaves an existing book's chapters alone, so the fixture fix
cannot reach a database where the book already landed — hence this backfill
(the body repairs need none: ``apply_body_corrections`` rewrites stored bodies
on every deploy). Anchored on the truncated title, so it is a no-op on a fresh
install, where the fixture already carries the whole title, and can never
overwrite a title someone has edited since.

``search_vector`` is NULLed on the row written, as 0091 does: a chapter's title
is weight A in its tsvector, and a historical model's ``save()`` doesn't run
the hook that refreshes it. ``backfill_search_vectors`` refills it on deploy.
"""

from __future__ import annotations

from django.db import migrations

SLUG = "the-bruised-reed"
ORDER = 28
TRUNCATED = "Be encouraged to go on cheerfully, with confidence"
WHOLE = "Be encouraged to go on cheerfully, with confidence of prevailing"


def _retitle(apps, old: str, new: str) -> None:
    Chapter = apps.get_model("library", "Chapter")
    rows = Chapter.objects.filter(
        book__slug=SLUG, book__language="en", order=ORDER, title=old
    ).only("id", "title")
    for ch in rows:
        ch.title = new
        ch.search_vector = None
        ch.save(update_fields=["title", "search_vector"])


def complete_title(apps, schema_editor):
    _retitle(apps, TRUNCATED, WHOLE)


def restore_truncated(apps, schema_editor):
    _retitle(apps, WHOLE, TRUNCATED)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0137_clear_imprint_bios"),
    ]

    operations = [
        migrations.RunPython(complete_title, restore_truncated),
    ]
