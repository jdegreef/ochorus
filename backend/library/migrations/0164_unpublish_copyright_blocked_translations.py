"""Unpublish every edition of the copyright-blocked works, in every language.

Migration 0022 unpublished these six works in July 2026 (still under US
copyright, no permission). It only reached the rows that existed then. On
2026-09-24 translation jobs for *Grace for Grace* were filed from the admin, and
its es/fr/pt translations shipped from fixtures with ``is_published: true`` —
live, and derivatives of the protected 1983 English compilation. ``seed_books``
treats ``is_published`` as create-only, so the corrected fixtures alone would
never reach those rows; this does.

Also deletes the works' topic memberships. #2872 took them out of
``topic_seed`` but ``seed_topics`` only adds members, so the rows lingered and
showed *Grace for Grace* on two shelves in the languages where it was live.

The slug list is frozen here on purpose (``corrections.COPYRIGHT_BLOCKED_SLUGS``
is the living copy, enforced in CI). Irreversible by design: republishing needs
the rights holder's permission, not a rollback.
"""

from __future__ import annotations

from django.db import migrations

BLOCKED = (
    "the-normal-christian-life",
    "grace-for-grace-2",
    "the-body-of-christ-a-reality",
    "the-body-of-christ-teens",
    "let-us-pray-2",
    "if",
)


def unpublish(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    TopicBook = apps.get_model("library", "TopicBook")
    Book.objects.filter(slug__in=BLOCKED, is_published=True).update(is_published=False)
    TopicBook.objects.filter(book_slug__in=BLOCKED).delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("library", "0163_book_cover_title")]
    operations = [migrations.RunPython(unpublish, noop)]
