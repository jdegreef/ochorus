"""Replace the-secret-of-guidance's chapters with Meyer's genuine PD text.

The book shipped as a damaged AI *paraphrase* stored in place of Meyer's
public-domain prose — a modern rewrite masquerading as the 1896 original, which
the content model forbids (a modern edition must be a separate, labelled Modern
English edition, never the PD original). Worse, the paraphrase silently DELETED
author content: it dropped chapter V, "Why Sign the Pledge?" entirely (8 stored
chapters against the genuine 9), and left the nonsense sentence "Not possible to
remove the adverb." four times where real Meyer sentences had been, alongside
garbled scripture ("Oh that I knew where find him!"), "pcher" for "pitcher", and
more. A model that drops sentences and leaves a fingerprint has likely dropped
others smoothly, so the text was re-imported from Meyer's genuine CCEL edition
(`meyer/guidance`) rather than patched.

`seed_books` upserts the Book ROW (so the corrected description, publication_year
and restored source stay in step) but deliberately never rewrites an existing
book's chapters — chapter ``order`` is a public contract, and the same
create-only rule that protects an approver's review state is what stops the seed
overwriting bodies. So the fixture fix reaches fresh installs only; this
migration carries the corrected 9-chapter set to the live DB by replacing the
stored chapters from the committed fixture.

Chapter has no inbound FKs (reading progress/marks live in localStorage keyed by
slug+order), and the book is English-only with no reading plan mapping its
chapters, so delete-and-recreate is safe — no translation parity or PlanDay to
follow.

Bodies are created through the SETTLED form (`settled_chapter_body`), exactly as
`seed_books` does on a fresh install, so prod and a fresh build converge; with
the fixture already corrected, `chapter_drift` then reports nothing. `bulk_create`
bypasses the real `Chapter.save()` hooks (mirrors the delete-and-recreate
precedent 0009), so the two columns those hooks derive are set by hand:

* ``body_text`` — derived with ``library.text.html_to_text`` (search and snippets
  render from it, so a stale copy would keep matching the paraphrase).
* ``word_count`` — derived from ``body_html`` (``library.ingest.word_count``).

``search_vector`` and ``citations_indexed_at`` are left at their create-time NULL
default; ``backfill_search_vectors`` refills the first on deploy and
``index_citations`` is INCREMENTAL on the second.
"""

from __future__ import annotations

import json

from django.db import migrations

from library.content_fixtures import book_fixture_path

SLUG = "the-secret-of-guidance"


def reimport_chapters(apps, schema_editor):
    # Real helpers — pure functions, not models — so the stored form matches
    # exactly what Chapter.save() and seed_books would produce.
    from library.corrections import settled_chapter_body
    from library.ingest import word_count
    from library.text import html_to_text

    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")

    try:
        book = Book.objects.get(slug=SLUG, language="en")
    except Book.DoesNotExist:
        # Fresh DB: the fixture loads after migrate, so the book isn't here yet
        # and seed_books will create it with the correct chapters. Nothing to do.
        return

    rows = json.loads(book_fixture_path(SLUG, "en").read_text(encoding="utf-8"))
    chapters = sorted(
        (r["fields"] for r in rows if r["model"] == "library.chapter"),
        key=lambda f: f["order"],
    )

    book.chapters.all().delete()
    Chapter.objects.bulk_create(
        Chapter(
            book=book,
            order=f["order"],
            title=f["title"],
            body_html=(body := settled_chapter_body(SLUG, f["order"], f["body_html"])),
            body_text=html_to_text(body),
            word_count=word_count(body),
        )
        for f in chapters
    )


def noop(apps, schema_editor):
    # Not reversible — the discarded chapters were a damaged AI paraphrase, not
    # a version worth restoring.
    pass


class Migration(migrations.Migration):
    # Depends on both current leaves, so this is the single tip (no separate
    # merge migration needed). Ordered after 0121_recase_chapter_titles, which
    # recases the paraphrase's stored titles just before this replaces them.
    dependencies = [
        ("library", "0121_recase_chapter_titles"),
        ("library", "0122_quotetopic_rls"),
    ]

    operations = [
        migrations.RunPython(reimport_chapters, noop),
    ]
