"""Replace the-bruised-reed's chapters with Pickering's 1838 reader edition.

The English edition shipped from Grosart's 1862 CRITICAL text
(`completeworksofr01sibbuoft`), and the apparatus is IN the prose: variant
sigla ("'…,' in A and B"), editor's glosses ("— G.") and Latin footnotes fused
mid-sentence through ten chapters, the next chapter's heading leaking into the
last one's tail, and ~200 OCR defects. That is why the book was pulled from the
Portuguese batch — a faithful translation reproduces the apparatus, and the
translators' cleanup broke tag parity. Like *Possibilities of Prayer* (0132),
the fix is a fresh source, not string pairs.

Rebuilt from Pickering's 1838 standalone printing (`bwb_C0-AVW-616`), a reader
edition with no apparatus at all, via `import_archive` with `part`/`part_end`
slicing it out of the three-work volume. The importer reports NO English
defects against Grosart's ~200. Slug, author, designed cover, description,
about_html, publication_year and sort_order are all preserved.

`seed_books` upserts the Book ROW but deliberately never rewrites an existing
book's chapters — chapter ``order`` is a public contract. So the fixture fix
reaches fresh installs only; this migration carries the corrected chapters to
the live DB from the committed fixture.

The chapter COUNT CHANGES, 27 to 28. That is not the re-import adding anything:
Grosart's scan lost the "CHAP. XVII." marker, so the shipped edition merged two
chapters and has carried chapters 17-27 under the WRONG TITLES ever since —
`corrections.chapter_titles` is keyed by order and lists all 28, so it silently
labelled each body with its neighbour's title. Pickering's marker survives
(`CHAP. XVII. :`, with a scanned colon), so the division and the titles now
agree with the print. A count change usually means checking reading-plan
mappings and translation parity; this book has no plan, no quotes and no
translation anchored to it, which is what made it the safe one to re-source
first. Chapter's inbound FKs (`ChapterCitation`, `Quote`) are both CASCADE and
both empty for this slug, so delete-and-recreate is safe — a hand-anchored row
on prod would not be, and there are none.

Bodies are created through the SETTLED form (`settled_chapter_body`), exactly
as `seed_books` does on a fresh install, so prod and a fresh build converge and
`chapter_drift` then reports nothing. `bulk_create` bypasses `Chapter.save()`
(mirrors 0009/0123/0132), so the derived columns are set by hand: ``body_text``
via ``html_to_text`` and ``word_count`` via ``ingest.word_count``.
``search_vector`` is left NULL for ``backfill_search_vectors`` to refill on
deploy — the prose changed wholesale, so a stale vector would keep search
matching the discarded apparatus.
"""

from __future__ import annotations

import json

from django.db import migrations

from library.content_fixtures import book_fixture_path

SLUG = "the-bruised-reed"


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
    # Not reversible — the discarded chapters were a critical edition whose
    # apparatus is the defect, not a version worth restoring.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0133_merge_20260908_1440"),
    ]

    operations = [
        migrations.RunPython(reimport_chapters, noop),
    ]
