"""Create three new bio-only authors on live databases: Augustine of Hippo,
Lemuel Haynes, and William Law.

These authors are brand-new (no books or sermons yet), so neither vehicle that
normally carries an author to production reaches them: ``seed_if_empty`` only
fills an EMPTY database, and ``seed_books`` creates authors from book fixtures —
a bookless author is never created. Without this migration the three would sit
in the fixture but never appear on the live site.

All field values are read from the fixture (the source of truth) rather than
duplicated here. Semantics:

- The row is CREATED where absent (the production case).
- Where the row already exists, only EMPTY prose/photo fields are filled, so a
  later hand edit or deploy always wins (matching 0051's fill-only rule).

Fresh installs run this harmlessly: migrate precedes seeding, so the row does
not exist yet and gets created here; ``seed_if_empty``'s natural-key loaddata
then reconciles the same row from the fixture. Idempotent on re-run.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

SLUGS = ["augustine-of-hippo", "lemuel-haynes", "william-law"]

# Fields to seed on create; a subset (prose/photo) is also fill-only-updated.
CREATE_FIELDS = (
    "name", "bio", "bio_html", "photo_url",
    "birth_year", "death_year", "original_language", "is_imprint",
)
FILL_ONLY_FIELDS = ("bio", "bio_html", "photo_url")


def _fixture_by_slug() -> dict:
    try:
        rows = json.loads(AUTHORS_FILE.read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for row in rows:
        f = row.get("fields", {})
        if row.get("model") == "library.author" and f.get("slug") in SLUGS:
            out[f["slug"]] = f
    return out


def apply_authors(apps, schema_editor):
    fixtures = _fixture_by_slug()
    if not fixtures:
        return
    Author = apps.get_model("library", "Author")
    for slug in SLUGS:
        fields = fixtures.get(slug)
        if not fields:
            continue
        obj, created = Author.objects.get_or_create(
            slug=slug,
            defaults={k: fields.get(k) for k in CREATE_FIELDS},
        )
        if created:
            continue
        # Row already exists: fill only fields that are still empty, never
        # clobbering prose someone may have edited since.
        updates = {
            k: fields[k]
            for k in FILL_ONLY_FIELDS
            if fields.get(k) and not (getattr(obj, k) or "").strip()
        }
        if updates:
            Author.objects.filter(pk=obj.pk).update(**updates)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0051_torrey_biography"),
    ]

    operations = [
        migrations.RunPython(apply_authors, noop),
    ]
