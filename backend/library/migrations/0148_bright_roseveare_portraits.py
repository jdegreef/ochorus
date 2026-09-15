"""Portraits for Bill Bright and Helen Roseveare.

Two more 20th-century bios that had no portrait, added under the 2026-09-15
sourcing steer (freely-offered / low-risk is fine — see `sourcing-not-strictly-pd`
and CLAUDE.md). Same mechanism as 0129 / 0146: ``author_sync`` fill-syncs
``photo_url`` but NOT the credit fields, so a CC portrait's ``photo_attribution``
/ ``photo_source_url`` are set here for the seeded prod DB (a fresh DB gets them
from ``authors.json``). Each was found on Wikimedia Commons, licence read on the
File: page, converted to black-and-white and scaled to <=600px tall, self-hosted.

  bill-bright     File:Bill Bright (1980).jpg           Public domain — no credit due
  helen-roseveare File:Roseveare Dr Helen 2003 WEC.jpg  CC BY-SA 4.0 (Zohre6) — credit shown

Idempotent. RunPython only — 0129 already added the two credit columns.
"""

from django.db import migrations

# slug -> (attribution, source_url). "" attribution == public domain, no credit due.
PORTRAITS = {
    "bill-bright": ("", ""),
    "helen-roseveare": (
        "Zohre6, CC BY-SA 4.0, via Wikimedia Commons — adapted (black-and-white)",
        "https://commons.wikimedia.org/wiki/File:Roseveare_Dr_Helen_2003_WEC.jpg",
    ),
}


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug, (attribution, source_url) in PORTRAITS.items():
        Author.objects.filter(slug=slug).update(
            photo_url=f"/portraits/{slug}.jpg",
            photo_attribution=attribution,
            photo_source_url=source_url,
        )


def unapply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=PORTRAITS).update(
        photo_url="", photo_attribution="", photo_source_url=""
    )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0147_merge_20260915_1825"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
