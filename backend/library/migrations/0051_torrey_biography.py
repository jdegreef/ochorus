"""Deliver R. A. Torrey's long biography (and revised short bio) to live rows.

Torrey already exists in production with two books, so neither vehicle that
normally carries author prose reaches him: ``seed_if_empty`` only fills an
EMPTY database, and ``seed_books`` sets bio/bio_html in ``get_or_create``
defaults — i.e. on CREATE only. Migration 0049 fills short bios but
deliberately skips authors whose bio is already non-empty, which Torrey's was.

Both values are read from the fixture (the source of truth) rather than
duplicated here. Two different safety rules:

- ``bio_html`` is filled ONLY where empty — it can't clobber later prose.
- ``bio`` is replaced only where the row still holds the exact pre-existing
  text, so a hand edit or a later deploy's wording always wins.

Fresh installs never run this meaningfully: migrate precedes seeding, so the
author doesn't exist yet and the fixture supplies both fields directly.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

SLUG = "r-a-torrey"

# The short bio as it stood before this change; the anchor for a safe replace.
PREVIOUS_SHORT_BIO = (
    "Reuben Archer Torrey (1856–1928) was an American evangelist, pastor, and "
    "educator, and a close associate of D. L. Moody. He served as the first "
    "superintendent of the Moody Bible Institute and later as dean of the Bible "
    "Institute of Los Angeles, while pastoring the Moody Church in Chicago and "
    "the Church of the Open Door in Los Angeles. Torrey led revival campaigns "
    "across several continents, and his many books on prayer and the Holy Spirit "
    "made him one of the most widely read Bible teachers of his day."
)


def _fixture_fields() -> dict:
    try:
        rows = json.loads(AUTHORS_FILE.read_text())
    except (OSError, ValueError):
        return {}
    for row in rows:
        if row.get("model") == "library.author" and row.get("fields", {}).get("slug") == SLUG:
            return row["fields"]
    return {}


def apply_bio(apps, schema_editor):
    fields = _fixture_fields()
    if not fields:
        return
    Author = apps.get_model("library", "Author")
    bio_html = (fields.get("bio_html") or "").strip()
    if bio_html:
        Author.objects.filter(slug=SLUG, bio_html="").update(bio_html=bio_html)
    bio = (fields.get("bio") or "").strip()
    if bio:
        Author.objects.filter(slug=SLUG, bio=PREVIOUS_SHORT_BIO).update(bio=bio)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0050_self_host_covers"),
    ]

    operations = [
        migrations.RunPython(apply_bio, noop),
    ]
