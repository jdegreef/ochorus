"""Drop the duplicate section titles from the Enchiridion's stored chapters.

`scripts/build_enchiridion.py` regroups the 124 tiny NPNF sections into 11
thematic chapters, giving each section an `<h3>` from its title. But every raw
NPNF section body ALSO opens with its own running title as a paragraph —
`<p> Chapter 114.—Having Dealt with Faith… </p>` — so each of the 122 sub-headings
rendered twice, the second with an ugly "Chapter N.—" prefix (#1320). The build
script now strips that leading title paragraph and the fixture was corrected in
#1349 — but `seed_books` never re-syncs the chapters of a book it has already
created (chapter `order` is a public contract), so the fix reached fresh installs
only. This is the backfill for the rows already in production; with the fixture
already corrected, `chapter_drift` reports nothing and a fresh build and the
deployed database agree.

The Enchiridion is English-only, so there are no translated twins to follow.

Three derived columns are put back in step, because a historical model's `save()`
runs none of the hooks the real `Chapter.save()` would (mirrors migration 0092):

* `body_text` — re-derived with `library.text.html_to_text` (what search indexes
  and snippets render from, so a stale row keeps matching a title the page no
  longer shows).
* `word_count` — re-derived from `body_html` (`library.ingest.word_count`).
* `search_vector` and `citations_indexed_at` — NULLed. `backfill_search_vectors`
  refills the first; `index_citations` is INCREMENTAL on the second.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from django.db import migrations

from library.ingest import word_count
from library.text import html_to_text

FIELDS = ["body_html", "body_text", "word_count", "search_vector", "citations_indexed_at"]
_CHAP_TITLE = re.compile(r"^\s*Chapter\s+\d+\.\s*[—-]")


def strip_duplicate_titles(body_html: str) -> str:
    """Drop each `<p>Chapter N.—…</p>` that immediately follows an `<h3>` — the
    running title the NPNF section repeats from the heading we already render."""
    soup = BeautifulSoup(f"<div>{body_html}</div>", "lxml").div
    kids = soup.find_all(recursive=False)
    for idx, k in enumerate(kids):
        if k.name == "h3" and idx + 1 < len(kids):
            nxt = kids[idx + 1]
            if nxt.name == "p" and _CHAP_TITLE.match(nxt.get_text()):
                nxt.decompose()
    return soup.decode_contents()


def strip_titles(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    rows = (
        Chapter.objects.only("id", "body_html", "book__slug", "book__language")
        .select_related("book")
        .filter(book__slug="enchiridion", book__language="en")
    )
    for chapter in rows.iterator(chunk_size=50):
        body = strip_duplicate_titles(chapter.body_html or "")
        if body == chapter.body_html:
            continue
        chapter.body_html = body
        chapter.body_text = html_to_text(body)
        chapter.word_count = word_count(body)
        chapter.search_vector = None
        chapter.citations_indexed_at = None
        chapter.save(update_fields=FIELDS)


def noop(apps, schema_editor):
    """Deliberately irreversible — putting the titles back would only restore a
    book that prints every section title twice."""


class Migration(migrations.Migration):
    dependencies = [("library", "0102_bookperson_rls")]
    operations = [migrations.RunPython(strip_titles, noop)]
