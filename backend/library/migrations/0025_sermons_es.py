"""Spanish translations of all 25 sermons (Phase 2, workload 3).

Creates Sermon (slug, language="es") rows from the data shipped alongside this
migration — data/sermons_es/<slug>.html (format: title, a line ===TITLE-END===,
then body_html). Metadata (author, preached_on, source_url, sort_order) is
copied from the English Sermon row; scripture_ref has its book name mapped to
Spanish.

AI-drafted; Scripture quotations use Reina-Valera (1858) wording (pre-fetched
from the Take Root Bible API where the reference was explicitly cited). Pending
native review — Spanish sermons show no source_type badge (Sermon has none), so
review is tracked out-of-band.

Historical models skip Sermon.save(), so body_text and word_count are set
explicitly here. Guarded skip-if-absent so it no-ops on a fresh DB where the
English sermons are seeded (seed_sermons) after migrate.
"""

import re
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).parent / "data" / "sermons_es"

# EN book name (as it appears in scripture_ref) -> ES, for the card's reference.
BOOK_ES = {
    "Genesis": "Génesis", "Exodus": "Éxodo", "Job": "Job", "Psalm": "Salmo",
    "Psalms": "Salmos", "Proverbs": "Proverbios", "Isaiah": "Isaías",
    "Jeremiah": "Jeremías", "Ezekiel": "Ezequiel", "Daniel": "Daniel",
    "Malachi": "Malaquías", "Nehemiah": "Nehemías", "Matthew": "Mateo",
    "Mark": "Marcos", "Luke": "Lucas", "John": "Juan", "Acts": "Hechos",
    "Romans": "Romanos", "1 Corinthians": "1 Corintios",
    "2 Corinthians": "2 Corintios", "Colossians": "Colosenses",
    "1 Peter": "1 Pedro", "2 Peter": "2 Pedro", "1 Kings": "1 Reyes",
    "2 Kings": "2 Reyes", "Hebrews": "Hebreos", "Revelation": "Apocalipsis",
}


def _es_ref(ref: str) -> str:
    for en, es in sorted(BOOK_ES.items(), key=lambda kv: -len(kv[0])):
        if ref.startswith(en):
            return es + ref[len(en):]
    return ref


def apply(apps, schema_editor):
    from library.ingest import word_count
    from library.text import html_to_text

    Sermon = apps.get_model("library", "Sermon")
    for path in sorted(DATA.glob("*.html")):
        slug = path.stem
        src = Sermon.objects.filter(slug=slug, language="en").first()
        if src is None:
            continue  # fresh DB: English sermons seeded after migrate — no-op
        if Sermon.objects.filter(slug=slug, language="es").exists():
            continue  # idempotent
        raw = path.read_text(encoding="utf-8")
        title, body = raw.split("===TITLE-END===", 1)
        title, body = title.strip(), body.strip()
        Sermon.objects.create(
            slug=slug,
            language="es",
            author=src.author,
            title=title[:300],
            scripture_ref=_es_ref(src.scripture_ref),
            preached_on=src.preached_on,
            body_html=body,
            body_text=html_to_text(body),
            word_count=word_count(body),
            source_url=src.source_url,
            sort_order=src.sort_order,
            is_published=True,
        )


def unapply(apps, schema_editor):
    Sermon = apps.get_model("library", "Sermon")
    slugs = [p.stem for p in DATA.glob("*.html")]
    Sermon.objects.filter(language="es", slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0024_author_bios_sw_lg"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
