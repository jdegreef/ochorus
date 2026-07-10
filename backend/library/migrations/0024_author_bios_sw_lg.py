"""Swahili + Luganda translations of all 13 author bios (Phase 2, workload 2).

Fills AuthorTranslation.bio (short) and .bio_html (long-form) for languages
"sw" and "lg" from the data shipped alongside this migration:

    data/author_bios_<lang>/short.json   -> {slug: short bio}
    data/author_bios_<lang>/<slug>.html  -> long bio_html (structure 1:1 with EN)

AI-drafted, reviewed=False pending native review (same gate as the Spanish
bios in 0021/0023). Guarded skip-if-absent so it no-ops on a fresh DB where
authors are seeded after migrate.
"""

import json
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).parent / "data"
LANGS = ("sw", "lg")


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")
    for lang in LANGS:
        d = DATA / f"author_bios_{lang}"
        short = json.loads((d / "short.json").read_text(encoding="utf-8"))
        for slug, bio in short.items():
            author = Author.objects.filter(slug=slug).first()
            if author is None:
                continue  # fresh DB: authors seeded after migrate — no-op here
            tr, _ = AuthorTranslation.objects.get_or_create(author=author, language=lang)
            changed = []
            if not tr.bio and bio:
                tr.bio = bio
                changed.append("bio")
            long_path = d / f"{slug}.html"
            if not tr.bio_html and long_path.exists():
                tr.bio_html = long_path.read_text(encoding="utf-8").strip()
                changed.append("bio_html")
            if changed:
                tr.reviewed = False
                tr.save(update_fields=[*changed, "reviewed", "updated_at"])


def unapply(apps, schema_editor):
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")
    AuthorTranslation.objects.filter(language__in=LANGS).update(bio="", bio_html="")


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0023_author_bios_es_long"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
