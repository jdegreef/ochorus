"""Carry the John Hyde factual corrections into any REVIEWED translation.

The English bio was corrected against contemporary sources (#4493: Ferozepore,
not Sialkot, as his station; the 1901–02 furlough; the soul-a-day / 400
figures as devotional tradition; Prayer Union "moving spirit" rather than
founder; Griswold's account of the last words), and #4494 carried the same
corrections into ``migrations/data/author_bios_<lang>/john-hyde.*``.

``seed_author_translations`` re-asserts those files only over UNREVIEWED rows —
an approved row keeps the approver's wording, which here still states the
errors. This migration writes the corrected files over the reviewed Hyde rows
and re-gates them (``reviewed=False``): the new wording is AI-written, and only
the founder promotes a translation (CLAUDE.md). ``source_stale`` is cleared
because the row now translates the current English. After this, the rows are
unreviewed, so the seed owns them like any other.

Reads the data files at run time, with the seed's own rules (strip; empty file
= field absent). On a fresh DB there are no translation rows yet — the seed
creates them later from the same files — so this no-ops. Idempotent: a row
already matching the files, or unreviewed, is left alone.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.db import migrations

SLUG = "john-hyde"
LANGUAGES = ("am", "ar", "es", "hi", "pt", "sw")
DATA_DIR = Path(__file__).resolve().parent / "data"


def corrected_fields(language: str) -> dict:
    d = DATA_DIR / f"author_bios_{language}"
    fields: dict = {}
    short = d / f"{SLUG}.short.txt"
    if short.exists() and (bio := short.read_text(encoding="utf-8").strip()):
        fields["bio"] = bio
    html = d / f"{SLUG}.html"
    if html.exists() and (bio_html := html.read_text(encoding="utf-8").strip()):
        fields["bio_html"] = bio_html
    faq = d / f"{SLUG}.faq.json"
    if faq.exists() and (pairs := json.loads(faq.read_text(encoding="utf-8"))):
        fields["faq"] = pairs
    return fields


def correct_reviewed(apps, schema_editor):
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")
    rows = AuthorTranslation.objects.filter(
        author__slug=SLUG, language__in=LANGUAGES, reviewed=True
    )
    for tr in rows:
        fields = corrected_fields(tr.language)
        changed = [n for n, v in fields.items() if getattr(tr, n) != v]
        if not changed:
            continue
        for name in changed:
            setattr(tr, name, fields[name])
        tr.reviewed = False
        tr.source_stale = False
        tr.save(update_fields=[*changed, "reviewed", "source_stale", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0167_series_audience"),
    ]

    operations = [
        migrations.RunPython(correct_reviewed, migrations.RunPython.noop),
    ]
