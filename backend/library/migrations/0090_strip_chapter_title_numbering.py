"""Drop the numbering a stored chapter title carries in front of its own name.

The reader renders `{order}. {title}` — TocDrawer, SearchDrawer and the notebook
all do — so a chapter stored as "1. The God of Our Salvation" reaches the page
as "3. 1. The God of Our Salvation", the two numbers disagreeing because front
matter occupies the first orders. 245 rows are in that state: `waiting-on-god`,
31 chapters in each of en/ar/es/hi/pt/sw (186), and the 59 English chapters of
`selected-sermons-whitefield`, styled "01. ", "02. " …

The importer stopped producing them — `clean_title` gained `_NUMBER_PREFIX`
alongside the Power Through Prayer import — but `seed_books` deliberately does
NOT sync the chapters of a book it has already created (chapter `order` is a
public contract: PlanDay.chapter_order, readers' saved positions, prerendered
URLs), so no deploy will ever carry that fix to the rows already in production.
This is the backfill; the fixture is corrected in the same commit, and
`tests_fixture.ChapterTitleNumberingTests` keeps both from drifting back.

TITLE ONLY. `order` is not read and not written — every one of those contracts
keys off it, and a chapter that changes its number is a reader losing their
place.

`strip_numbering_prefix`, not the whole of `clean_title`. Running the full
cleaner over the corpus was measured: it changes these 245 rows and 28 others,
of a different class entirely and long predating this — and two of those 28 it
would damage, taking the stop off "Sidney, B.C." and the apostrophe out of
"Friends' Testimonies". Applying the one rule that is actually wrong here
touches exactly the 245 and gives them the same text the full cleaner would.

`search_vector` is NULLed on every row written. The chapter's title is weight A
in its own stored tsvector (library/fts.py), and a historical model's `save()`
runs none of the hooks the real `Chapter.save()` would — so a retitled row would
keep matching searches for the number it no longer shows. The release chain's
`backfill_search_vectors` refills NULLs on the next deploy.
"""

from __future__ import annotations

from django.db import migrations

from library.ingest import strip_numbering_prefix


def strip_numbering(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    # `.only()`, not 0085's `.defer("search_vector")`: that migration compared
    # `body_text` against `body_html` and so had to load both, where this reads
    # nothing but the title. Deferring the vector alone would still drag the two
    # body columns across the wire — ~79MB for the corpus, to look at 89KB of
    # titles. Assigning a deferred field is a plain attribute set; only reading
    # one would refetch.
    for ch in Chapter.objects.only("id", "title").iterator(chunk_size=2000):
        stripped = strip_numbering_prefix(ch.title)
        if stripped == ch.title:
            continue
        ch.title = stripped
        ch.search_vector = None
        ch.save(update_fields=["title", "search_vector"])


def noop(apps, schema_editor):
    """Deliberately irreversible — the numerals were noise, and putting them
    back would only restore "3. 1. The God of Our Salvation"."""


class Migration(migrations.Migration):
    dependencies = [("library", "0089_verse_review_rls")]
    operations = [migrations.RunPython(strip_numbering, noop)]
