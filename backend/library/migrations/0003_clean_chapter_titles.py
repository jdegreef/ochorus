"""Normalise existing chapter titles.

Applies the same cleaning the importer now does (strip redundant "Chapter N."
prefixes, remove quotation marks, capitalise) plus the per-book title
corrections, so the live library is fixed without a full re-import. The importer
produces clean titles going forward; this is the one-off backfill.
"""

from __future__ import annotations

from django.db import migrations


def clean_titles(apps, schema_editor):
    from library.ingest import clean_title
    from library.corrections import chapter_title_overrides

    Chapter = apps.get_model("library", "Chapter")
    for ch in Chapter.objects.select_related("book").all():
        override = chapter_title_overrides(ch.book.slug).get(ch.order)
        source = override if override is not None else ch.title
        new = clean_title(source)[:300]
        if new != ch.title:
            ch.title = new
            ch.save(update_fields=["title"])


def noop(apps, schema_editor):
    # Not reversible — original titles aren't retained.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0002_book_cover_url_book_pdf_url"),
    ]

    operations = [
        migrations.RunPython(clean_titles, noop),
    ]
