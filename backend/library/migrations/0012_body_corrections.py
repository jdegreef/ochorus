"""Ship the 2026-07 body-text repairs to the live library.

Two vehicles in one migration (prod is never re-seeded from the fixture):

1. Structural re-imports — the-key-in-my-hand (a phantom chapter split a real
   sentence; 16→15 chapters) and let-us-pray-2 (rebuilt boundaries + real
   titles). Their chapters are replaced wholesale from fixtures/launch.json,
   which was regenerated after the fixes (the 0009 re-chapterization pattern).
   Neither book backs a seeded reading plan, so no PlanDay references break.

2. In-place transforms — image-drop-cap first letters (around-the-wicket-gate),
   OCR letter-splits across 6 books, and absorbed trailing page/section numbers
   (till-he-come et al.). Applied with the same helpers the importers use
   (library.corrections.apply_body_corrections + ingest.strip_trailing_pagenum),
   so the migration and future imports produce identical text. Idempotent.

Word counts and body_text are re-derived for every touched row.
"""

import json
from pathlib import Path

from django.db import migrations

RECHAPTERIZED = ["the-key-in-my-hand", "let-us-pray-2"]

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "launch.json"


def apply(apps, schema_editor):
    from library.corrections import BODY_CORRECTIONS, apply_body_corrections
    from library.ingest import strip_trailing_pagenum
    from library.text import html_to_text

    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")

    # 1. Replace the re-imported books' chapters from the (fixed) fixture.
    try:
        data = json.loads(FIXTURE.read_text())
    except OSError:
        return  # split-fixture era: the monofile is gone; historical no-op
    if data and "pk" not in data[0]:
        # Natural-key-format fixture: corrections are already baked into the
        # fixture the seeds load — no-op (see content_sync).
        print("0012: natural-key fixture detected — historical backfill skipped")
        return
    fixture_books = {
        o["pk"]: o["fields"]["slug"]
        for o in data
        if o["model"] == "library.book" and o["fields"]["slug"] in RECHAPTERIZED
    }
    for book in Book.objects.filter(slug__in=RECHAPTERIZED, language="en"):
        rows = [
            o["fields"]
            for o in data
            if o["model"] == "library.chapter"
            and fixture_books.get(o["fields"]["book"]) == book.slug
        ]
        if not rows:  # fixture missing the book — leave prod untouched
            continue
        book.chapters.all().delete()
        Chapter.objects.bulk_create(
            Chapter(
                book=book,
                order=f["order"],
                title=f["title"],
                body_html=f["body_html"],
                body_text=f.get("body_text") or html_to_text(f["body_html"]),
                word_count=f["word_count"],
            )
            for f in sorted(rows, key=lambda f: f["order"])
        )

    # 2. In-place, idempotent text repairs everywhere else.
    for chapter in Chapter.objects.select_related("book").iterator(chunk_size=100):
        slug = chapter.book.slug
        if slug in RECHAPTERIZED:
            continue
        new = strip_trailing_pagenum(chapter.body_html)
        if slug in BODY_CORRECTIONS:
            new = apply_body_corrections(slug, chapter.order, new)
        if new != chapter.body_html:
            chapter.body_html = new
            chapter.body_text = html_to_text(new)
            chapter.word_count = len(chapter.body_text.split())
            chapter.save(
                update_fields=["body_html", "body_text", "word_count"]
            )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0011_backfill_gareth_bio"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
