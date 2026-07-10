"""Unpublish books that are NOT public domain (US).

A copyright audit (2026-07-10) found six titles in the library that are still
under US copyright, not public domain:

- Watchman Nee — The Normal Christian Life (1957 English tr., Kinnear/CLC),
  Grace for Grace (1983 CFP), The Body of Christ: A Reality (1978 CFP) and its
  teens edition, Let Us Pray (1977 CFP). Nee spoke the material in the 1930s–40s
  but the English translations/compilations are separate, later, enforced works.
- Amy Carmichael — If (1938; a British work whose author died 1951, so US
  copyright was restored under the URAA regardless of renewal).

Production is never re-seeded (seed_if_empty only fills an empty DB, seed_books
only creates MISSING books), so hiding these from the live library requires a
data migration over the existing rows. Reversible; also excluded from re-import
in library/corrections.py so a future import can't republish them.
"""

from __future__ import annotations

from django.db import migrations

COPYRIGHTED_SLUGS = [
    "the-normal-christian-life",
    "grace-for-grace-2",
    "the-body-of-christ-a-reality",
    "the-body-of-christ-teens",
    "let-us-pray-2",
    "if",
]


def unpublish(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug__in=COPYRIGHTED_SLUGS).update(is_published=False)


def republish(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug__in=COPYRIGHTED_SLUGS).update(is_published=True)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0019_jesus_himself_pilot_translations"),
    ]

    operations = [
        migrations.RunPython(unpublish, republish),
    ]
