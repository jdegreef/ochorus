"""Give David Brainerd his portrait on live databases.

The fixture carries `photo_url` for fresh installs, but Brainerd already exists
in production, and neither vehicle that normally moves author fields reaches an
existing row: `seed_if_empty` only fills an EMPTY database, and `seed_books`
sets author fields in `get_or_create` defaults — i.e. on CREATE only.

Fill-only, so it cannot overwrite a portrait chosen later by hand.

Licence: the image is the public-domain portrait from Wikimedia Commons
(`File:DavidBrainerd.jpg`, verified `LicenseShortName == "Public domain"` before
use, not assumed). William Law was left without one on purpose — the only
Commons candidate is CC BY 4.0, which would put an attribution obligation on
the page.
"""

from __future__ import annotations

from django.db import migrations

SLUG = "david-brainerd"
PHOTO = "/portraits/david-brainerd.jpg"


def add_portrait(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug=SLUG, photo_url="").update(photo_url=PHOTO)


def remove_portrait(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug=SLUG, photo_url=PHOTO).update(photo_url="")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0061_language_glossary"),
    ]

    operations = [
        migrations.RunPython(add_portrait, remove_portrait),
    ]
