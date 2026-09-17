"""Publish the teen and children editions of Talks to the Farmer.

Both editions ship with ``is_published: true`` in their fixtures, but
``is_published`` is create-only in ``seed_books`` (``CREATE_ONLY_FIELDS``), so a
fixture flip only takes effect when the row is FIRST created. The teen edition
(``talks-to-the-farmer-teens``) was already created in production unpublished
(PR #2480), so the seed will never update it — this migration flips the existing
row. The children edition is new; on a fresh DB it is created published from the
fixture, and on prod this migration publishes it too. Idempotent either way:
``filter(...).update(...)`` no-ops when a row is absent (fresh DB, before
loaddata) or already published.

Both are Spurgeon, public domain — the copyright unpublish in migration 0022 is
a different book (``the-body-of-christ-teens``, Watchman Nee).
"""

from __future__ import annotations

from django.db import migrations

PUBLISH_SLUGS = [
    "talks-to-the-farmer-teens",
    "talks-to-the-farmer-children",
]


def publish(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug__in=PUBLISH_SLUGS).update(is_published=True)


def unpublish(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug__in=PUBLISH_SLUGS).update(is_published=False)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0152_fix_torrey_initials"),
    ]

    operations = [
        migrations.RunPython(publish, unpublish),
    ]
