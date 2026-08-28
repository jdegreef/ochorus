"""Title the thirteen chapters of Purpose in Prayer on already-seeded databases.

The 1920 edition numbers its chapters and never names them — unlike Bounds'
other three books, which CCEL carries with their own titles — so the import
faithfully stored 13 blank titles and the reader showed a bare "1", "2", "3"
with nothing to tell one chapter from another. ``corrections.py`` now carries a
title for each, written from that chapter's own argument.

``seed_books`` creates a NEW book with its chapters straight from the fixture,
but leaves an EXISTING book's chapters alone, so the corrected fixture cannot
reach a database where the book already landed. Hence this backfill.

Anchored on the blank title, so it is a no-op wherever the fixture already
supplied the titles (a fresh install, or a deploy that created the book after
this change), and it can never overwrite a title someone has since edited by
hand or a real one from a titled edition.

`search_vector` is NULLed on every row written, as 0090 does. A chapter's title
is weight A in its own stored tsvector (library/fts.py), and neither
`queryset.update()` nor a historical model's `save()` runs the hook that would
refresh it — so a retitled row would keep matching the OLD text and these
titles would be unsearchable. The release step's `backfill_search_vectors`
repairs NULLs on the next deploy; a stale vector it would never notice.
"""

from __future__ import annotations

from django.db import migrations

SLUG = "purpose-in-prayer"


def add_titles(apps, schema_editor):
    from library.corrections import chapter_title_overrides

    Chapter = apps.get_model("library", "Chapter")
    titles = chapter_title_overrides(SLUG)
    if not titles:
        return  # corrections entry removed — nothing to assert

    # `title=""` is the anchor: only an untitled chapter is filled. Iterated and
    # saved rather than `update()`d so `search_vector` can be NULLed with it.
    rows = Chapter.objects.filter(
        book__slug=SLUG, book__language="en", title="", order__in=titles
    ).only("id", "title", "order")
    for ch in rows:
        ch.title = titles[ch.order]
        ch.search_vector = None
        ch.save(update_fields=["title", "search_vector"])


def remove_titles(apps, schema_editor):
    from library.corrections import chapter_title_overrides

    Chapter = apps.get_model("library", "Chapter")
    titles = chapter_title_overrides(SLUG)
    # Only clear a title this migration could have written.
    rows = Chapter.objects.filter(
        book__slug=SLUG, book__language="en", order__in=titles
    ).only("id", "title", "order")
    for ch in rows:
        if ch.title != titles[ch.order]:
            continue
        ch.title = ""
        ch.search_vector = None
        ch.save(update_fields=["title", "search_vector"])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0090_strip_chapter_title_numbering"),
    ]

    operations = [
        migrations.RunPython(add_titles, remove_titles),
    ]
