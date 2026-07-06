"""Set public-domain portrait URLs for the classic authors + fix Torrey's years.

Portraits are Wikimedia Commons images individually verified as Public domain,
downloaded, converted to black-and-white, and self-hosted under
frontend/static/portraits/<slug>.jpg. Contemporary authors (no PD portrait
exists) stay blank and keep the initials avatar in the UI. Idempotent.
"""

from django.db import migrations

PORTRAITS = [
    "amy-carmichael",
    "andrew-murray",
    "catherine-booth",
    "charles-h-spurgeon",
    "dwight-l-moody",
    "frederick-brotherton-meyer",
    "hannah-whitall-smith",
    "jeanne-guyon",
    "r-a-torrey",
    "susanna-wesley",
    "watchman-nee",
    "william-booth",
]


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug in PORTRAITS:
        Author.objects.filter(slug=slug).update(photo_url=f"/portraits/{slug}.jpg")
    # R. A. Torrey's years were missing from the source metadata.
    Author.objects.filter(slug="r-a-torrey", birth_year__isnull=True).update(
        birth_year=1856, death_year=1928
    )


def revert(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=PORTRAITS).update(photo_url="")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0014_author_photo_url"),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
