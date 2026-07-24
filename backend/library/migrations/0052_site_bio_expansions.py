"""Deliver the ochorus.com-sourced biography expansions to live author rows.

Thirteen authors' long biographies were expanded by merging in material from
the publisher's site (ochorus.com/biographies/) — most notably Gareth Evans
(631 -> ~2,400 words; the site is the authoritative source on a living
author). Seven more get an entity-normalization-only pass (see the ANCHORS
comment). All twenty already exist in production with non-empty ``bio_html``,
so no seed command carries the change (``seed_if_empty`` fills only an empty
DB; ``seed_books`` writes bios on CREATE only).

New prose is read from the fixture (the source of truth), never duplicated
here. Because this migration REPLACES non-empty prose, each update is anchored
on the md5 of the text it replaces: a row is only rewritten while it still
holds the exact bio this change was written against, so a hand edit made
after this branch was cut — or a later deploy's wording — always wins.
Empty rows (a fresh install racing ahead of seeding can't happen — migrate
precedes seeding — but a manually blanked row could) are filled as well.

Idempotent: after the first run the row's md5 matches the NEW text, no anchor
matches, and re-runs are no-ops.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from django.db import migrations

AUTHORS_FILE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "content" / "authors.json"
)

# slug -> md5 of the bio_html this change replaces (captured from the fixture
# as committed on main at branch time).
ANCHORS = {
    "amy-carmichael": "89e4de4c57ef0213033916f37b49b81d",
    "andrew-murray": "3fd8a30600e84deebc438fc3d210681f",
    "catherine-booth": "4f19b20598841c1cc6f8f691406a3c66",
    "charles-h-spurgeon": "be25d9bc6264dd1fc260eda9764d882f",
    "frederick-brotherton-meyer": "85a869531f82f868434765bc290b7c57",
    "gareth-evans": "0f5f414f00f5bd9dbf7aef0a0ad4be88",
    "hannah-whitall-smith": "140a449483b61f1b8eef78cce2e02100",
    "jeanne-guyon": "2661c1b6019e34bb54bba29939141c52",
    "john-wesley": "8d0b5a9f7fefae2c66f50625c184c2dc",
    "r-a-torrey": "8ebd1fa0d99f8e212fa0ea3eccad785d",
    "susanna-wesley": "774b0bff8fdfce305206d2cf8c43e85e",
    "watchman-nee": "6e1ad51c6832792d23fff8cde5114311",
    "william-booth": "c2d1426ccd84ce09d5b2a9a563ebd7ea",
    # Entity-normalization only (no prose change): named HTML entities
    # (&ldquo; &mdash; &hellip; …) replaced with literal Unicode. The hero
    # epigraph extracts the first pull-quote as PLAIN TEXT, so entities were
    # rendering raw ("&lsquo;stepping stones&rsquo;") on these author pages.
    "dwight-l-moody": "2ac9a6d9a4586f76dbe980d7e37df35b",
    "a-b-simpson": "ec8767ce2e8263765e87a1ed72bc2841",
    "john-bunyan": "038b46d2dae5da2e93b7ff4d993373e9",
    "thomas-watson": "69d8e357696552a218ade3d7d75269c3",
    "richard-baxter": "5c38c244a7ac545632b1d418b97515cb",
    "jonathan-edwards": "73edadb9c4e0af84fd732140a80ac6dc",
    "george-whitefield": "602c35b8c50f63449b7c09f4af45cc9b",
}


def _fixture_bios() -> dict[str, str]:
    try:
        rows = json.loads(AUTHORS_FILE.read_text())
    except (OSError, ValueError):
        return {}
    return {
        r["fields"]["slug"]: r["fields"].get("bio_html", "")
        for r in rows
        if r["fields"]["slug"] in ANCHORS
    }


def apply_bios(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    bios = _fixture_bios()
    for slug, old_md5 in ANCHORS.items():
        new = bios.get(slug, "")
        if not new:
            continue  # fixture missing/renamed — leave the row alone
        row = Author.objects.filter(slug=slug).first()
        if row is None:
            continue  # fresh install: fixture seeding supplies the bio directly
        current = hashlib.md5((row.bio_html or "").encode()).hexdigest()
        if row.bio_html and current != old_md5:
            continue  # hand-edited or already newer — that prose wins
        Author.objects.filter(pk=row.pk).update(bio_html=new)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0051_torrey_biography"),
    ]

    operations = [
        migrations.RunPython(apply_bios, migrations.RunPython.noop),
    ]
