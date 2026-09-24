"""Carry Stepping Stones' four new chapters (40–43) to the live library.

#3104 added Gareth Evans's 2026 chapters to the fixture of every edition that
already existed (en, fr, hi, lg, pt, sw) and took "THE END" off chapter 39. But
`seed_books` upserts the Book ROW and never touches an existing book's chapters
(chapter ``order`` is a public contract), so the fixture change reached fresh
installs only: production kept 39 chapters in those six editions. The es, ar
and uk editions were created after #3104, with all 43, and are already right.

This syncs each of the six editions to its fixture, by ``order``:

- chapters 40–43 are CREATED;
- a chapter whose title or settled body differs from the fixture is UPDATED —
  chapter 39's ending, plus curly-quote repairs that landed in the fixture
  earlier but never reached prod (en 4/20/21/27, lg 4/19/20/21/27);
- nothing is deleted or renumbered, so readers' saved positions, plan days and
  prerendered URLs are untouched.

Bodies go through ``settled_chapter_body``, as `seed_books` does on a fresh
install, so prod and a fresh build converge and ``chapter_drift`` goes quiet.
Historical models run no ``save()`` hook, so the derived columns are set by
hand (mirrors 0134): ``body_text`` and ``word_count`` are derived, the citation
stamp is cleared for ``index_citations``, and ``search_vector`` is left NULL for
``backfill_search_vectors`` — both run later in the same release.
"""

from __future__ import annotations

import json

from django.db import migrations

from library.content_fixtures import book_fixture_path

SLUG = "stepping-stones-2"
LANGUAGES = ("en", "fr", "hi", "lg", "pt", "sw")


def sync_chapters(apps, schema_editor):
    from library.corrections import settled_chapter_body
    from library.ingest import word_count
    from library.text import html_to_text

    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")

    for language in LANGUAGES:
        try:
            book = Book.objects.get(slug=SLUG, language=language)
        except Book.DoesNotExist:
            # Fresh DB: seed_books creates the book with every chapter.
            continue

        rows = json.loads(
            book_fixture_path(SLUG, language).read_text(encoding="utf-8")
        )
        existing = {c.order: c for c in book.chapters.all()}
        for f in (r["fields"] for r in rows if r["model"] == "library.chapter"):
            body = settled_chapter_body(SLUG, f["order"], f["body_html"])
            chapter = existing.get(f["order"])
            if chapter is None:
                chapter = Chapter(book=book, order=f["order"])
            elif chapter.title == f["title"] and chapter.body_html == body:
                continue
            chapter.title = f["title"]
            chapter.body_html = body
            chapter.body_text = html_to_text(body)
            chapter.word_count = word_count(body)
            chapter.citations_indexed_at = None
            chapter.search_vector = None
            chapter.save()


def noop(apps, schema_editor):
    # Not reversible: the chapters it adds are the author's own, and the rows
    # it updates only lose defects.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0161_seriestranslation"),
    ]

    operations = [
        migrations.RunPython(sync_chapters, noop),
    ]
