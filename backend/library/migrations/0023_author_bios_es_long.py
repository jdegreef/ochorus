"""Spanish translations of the 13 long-form author bios (Phase 2, workload 1b).

Fills AuthorTranslation.bio_html for language "es" from the HTML files shipped
alongside this migration (data/author_bios_es/<slug>.html). AI-drafted, HTML
structure preserved 1:1 with the English source; reviewed=False pending native
review (same gate as the short bios in 0021).

Kept as repo data files (not inline) because the 13 bios total ~130KB — too
large to embed readably in a Python literal. Guarded skip-if-absent so it
no-ops on a fresh DB where authors are seeded after migrate.
"""

from pathlib import Path

from django.db import migrations

DATA_DIR = Path(__file__).parent / "data" / "author_bios_es"


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")
    for path in sorted(DATA_DIR.glob("*.html")):
        slug = path.stem
        author = Author.objects.filter(slug=slug).first()
        if author is None:
            continue  # fresh DB: authors seeded after migrate — no-op here
        tr, _ = AuthorTranslation.objects.get_or_create(author=author, language="es")
        if not tr.bio_html:
            tr.bio_html = path.read_text(encoding="utf-8").strip()
            tr.reviewed = False
            tr.save(update_fields=["bio_html", "reviewed", "updated_at"])


def unapply(apps, schema_editor):
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")
    slugs = [p.stem for p in DATA_DIR.glob("*.html")]
    AuthorTranslation.objects.filter(language="es", author__slug__in=slugs).update(
        bio_html=""
    )


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0022_unpublish_copyrighted_books"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
