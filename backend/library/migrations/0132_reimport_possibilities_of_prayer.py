"""Replace possibilities-of-prayer's chapters with Bounds's clean CCEL text.

The English edition shipped from a badly degraded Internet Archive OCR scan
(`possibilitiesofp0000boun`): page numbers leaked into the prose ("IOI To answer
prayer", "specially with i39 praying people"), a running header was injected
mid-sentence, closing quotes garbled to `.,,`/`.,}`, words split or fused
("George Ben field", "hungryhearted"), and single letters misread throughout
("Prayei", "answet", "peopie"). Too damaged for BODY_CORRECTIONS string pairs —
like *The Bruised Reed*, the fix is a fresh source. The book was rebuilt from
CCEL's clean human transcription of the same 1923 Fleming H. Revell text
(`bounds/possibility`, `build_possibilities`), preserving the slug, author,
designed cover, sort_order and the sixteen chapters in the same order.

`seed_books` upserts the Book ROW (so the corrected attribution/source_url stay
in step) but deliberately never rewrites an existing book's chapters — chapter
``order`` is a public contract. So the fixture fix reaches fresh installs only;
this migration carries the corrected chapters to the live DB from the committed
fixture. The chapter COUNT and ORDER are unchanged (sixteen, same titles), so no
reading-plan (PlanDay) mapping or translation URL shifts — the Spanish edition
keeps its sixteen `/N/` chapters. Chapter has no inbound FKs (progress/marks are
localStorage slug+order), so delete-and-recreate of the English rows is safe and
leaves the untouched Spanish `Book` row and its chapters alone.

The Spanish edition was translated from the damaged English and so diverges from
the new markup; it is pinned in `tests_translation_markup.KNOWN_CHAPTER_GAPS`
awaiting a re-translation from the clean source.

Bodies are created through the SETTLED form (`settled_chapter_body`), exactly as
`seed_books` does on a fresh install, so prod and a fresh build converge and
`chapter_drift` then reports nothing. `bulk_create` bypasses `Chapter.save()`
(mirrors 0009/0123), so the two derived columns are set by hand: ``body_text``
via ``html_to_text`` (search/snippets render from it) and ``word_count`` via
``ingest.word_count``. ``search_vector`` is left NULL for
``backfill_search_vectors`` to refill on deploy.
"""

from __future__ import annotations

import json

from django.db import migrations

from library.content_fixtures import book_fixture_path

SLUG = "possibilities-of-prayer"


def reimport_chapters(apps, schema_editor):
    from library.corrections import settled_chapter_body
    from library.ingest import word_count
    from library.text import html_to_text

    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")

    try:
        book = Book.objects.get(slug=SLUG, language="en")
    except Book.DoesNotExist:
        # Fresh DB: the fixture loads after migrate, so seed_books will create
        # the book with the correct chapters. Nothing to do.
        return

    rows = json.loads(book_fixture_path(SLUG, "en").read_text(encoding="utf-8"))
    chapters = sorted(
        (r["fields"] for r in rows if r["model"] == "library.chapter"),
        key=lambda f: f["order"],
    )

    new_chapters = []
    for f in chapters:
        body = settled_chapter_body(SLUG, f["order"], f["body_html"])
        new_chapters.append(
            Chapter(
                book=book,
                order=f["order"],
                title=f["title"],
                body_html=body,
                body_text=html_to_text(body),
                word_count=word_count(body),
            )
        )

    book.chapters.all().delete()
    Chapter.objects.bulk_create(new_chapters)


def noop(apps, schema_editor):
    # Not reversible — the discarded chapters were a degraded OCR scan, not a
    # version worth restoring.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0131_merge_two_0130_leaves"),
    ]

    operations = [
        migrations.RunPython(reimport_chapters, noop),
    ]
