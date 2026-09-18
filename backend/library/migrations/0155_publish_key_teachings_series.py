"""Publish the four Key Teachings companion books.

The series shipped (PR #2888) with ``is_published: false`` so the founder could
review the render first. ``is_published`` is create-only in ``seed_books``
(``CREATE_ONLY_FIELDS``), so the fixtures — now flipped to ``true`` — only take
effect when a row is FIRST created. These four were already created in
production unpublished, so the seed will never update them; this migration flips
the existing rows. On a fresh DB they are created published straight from the
fixture, and the ``filter(...).update(...)`` here no-ops (rows absent before
loaddata, or already published) — idempotent either way.

Simpson, Edwards and Baxter are public domain; the Nee companion is Ochorus's
own house-written exposition (KJV-only, no copyrighted prose), so all four are
ours to publish.
"""

from __future__ import annotations

from django.db import migrations

PUBLISH_SLUGS = [
    "key-teachings-of-a-b-simpson",
    "key-teachings-of-jonathan-edwards",
    "key-teachings-of-richard-baxter",
    "key-teachings-of-watchman-nee",
]


def publish(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug__in=PUBLISH_SLUGS).update(is_published=True)


def unpublish(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug__in=PUBLISH_SLUGS).update(is_published=False)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0154_alter_adminaction_action"),
    ]

    operations = [
        migrations.RunPython(publish, unpublish),
    ]
