"""Drop the leading heading a chapter body uses to repeat its own title.

The reader renders the chapter title above the body, so a body that opens by
restating it prints the title twice — `all-of-grace` chapter 1 is titled "To
You" and its prose begins "<h2>TO YOU</h2>". 281 rows are in that state: 221
English chapters across 14 CCEL books, and the 60 chapters of the Spanish,
Hindi and Luganda editions of `all-of-grace`, translated from the English
bodies and carrying the duplication into their own script.

`import_ccel.extract_body` has dropped these on import since the rule was
written — a fresh import of any of these books has none — but `seed_books`
deliberately never re-syncs the chapters of a book it has already created
(chapter `order` is a public contract: PlanDay.chapter_order, readers' saved
positions, prerendered URLs), so no deploy would ever carry that fix to the
rows already in production. This is the backfill; the fixture is corrected in
the same commit, so `chapter_drift` reports nothing and a fresh build and the
deployed database agree.

`ingest.strip_restated_heading`, the same function the fixture went through, so
the two cannot disagree about which rows are affected. It expresses the
importer's rule over a body that is already STORED, which is not quite the same
text: `clean_html` keeps h2-h4 and unwraps everything else, so the books whose
source heading was an `<h1>` — Whitefield's sermons, the Cheque Book, Till He
Come — carry it as bare text in front of the first `<p>` rather than as an
element. 102 of the 221 English rows are that shape.

TRANSLATIONS FOLLOW THEIR ENGLISH TWIN rather than their own title, because
that is what they are: a translation is written from the English body and keeps
its markup block for block (`tests_translation_markup` enforces it), so the
block facing a restated English heading is the same restatement. Read against
its own title instead the rule agrees on 58 of the 60 and misses two: Hindi
chapter 4 heads "परमेश्वर वह है जो उनको धर्मी ठहरानेवाला है" over the title
"परमेश्वर वह है जो धर्मी ठहराता है", a paraphrase of the same line rather than a
repetition, and Luganda chapter 6 differs by a noun prefix. Those two would have
been the only chapters of the book still printing their title twice, and their
markup would no longer have lined up with the English.

RESTATEMENTS ONLY, not the whole of `extract_body`. The importer also drops a
leading ordinal heading ("Chapter I"), and 13 chapters of `confessions` carry
one — but that book is imported `group_parts`, where a leaf heading inside the
body is the structure the chapter is read by, and whether those 13 should go is
a judgement about that book rather than this defect. Left alone deliberately.

The roman-numbered restatements ARE in scope, which they were not when this was
written: PR #1176 taught `_LEAD_COUNTER` a strict roman numeral so the importer
would stop producing them, and that left the same stored/imported gap this
migration exists to close, one class over. 35 chapters of `way-into-holiest`
open "<h2>II. THE DIGNITY OF CHRIST</h2>" and are stripped here with the rest.

Three derived columns are put back in step, because a historical model's
`save()` runs none of the hooks the real `Chapter.save()` would:

* `body_text` — re-derived with `library.text.html_to_text`, the one canonical
  rule. It is what search indexes and what snippets render from, so a row left
  alone would keep matching a heading the page no longer shows.
* `word_count` — derived from `body_html` (`library.ingest.word_count`).
* `search_vector` and `citations_indexed_at` — NULLed. The release chain's
  `backfill_search_vectors` refills the first; `index_citations` is INCREMENTAL
  on the second, so a row that kept its stamp would keep citations extracted
  from text it no longer holds.
"""

from __future__ import annotations

from django.db import migrations

from library.ingest import (
    strip_leading_heading_element,
    strip_restated_heading,
    word_count,
)
from library.text import html_to_text

FIELDS = ["body_html", "body_text", "word_count", "search_vector", "citations_indexed_at"]


def _rewrite(chapter, body_html):
    chapter.body_html = body_html
    chapter.body_text = html_to_text(body_html)
    chapter.word_count = word_count(body_html)
    chapter.search_vector = None
    chapter.citations_indexed_at = None
    chapter.save(update_fields=FIELDS)


def strip_restatements(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    # `.only(...)`, not 0085's `.defer("search_vector")`: that migration compared
    # `body_text` against `body_html` and so had to load both, where this reads
    # the title and the body and DERIVES the rest. Deferring the vector alone
    # would still drag `body_text` across the wire — 39MB for the corpus, to
    # overwrite every byte of it on arrival — and `select_related("book")` on its
    # own fetches the whole Book row (~1.2KB each, repeated per chapter) for two
    # fields. Assigning a deferred field is a plain attribute set; only reading
    # one would refetch.
    rows = Chapter.objects.only(
        "id", "order", "title", "body_html", "book__slug", "book__language"
    ).select_related("book")

    stripped = set()
    for chapter in rows.filter(book__language="en").iterator(chunk_size=200):
        body = strip_restated_heading(chapter.body_html or "", chapter.title)
        if body == chapter.body_html:
            continue
        _rewrite(chapter, body)
        stripped.add((chapter.book.slug, chapter.order))

    # A translated edition is judged by its English twin, not by its own title
    # (see the module docstring). Nothing stripped in English decides nothing in
    # translation — which is also the right answer on a database holding no
    # English edition at all.
    if not stripped:
        return
    # Narrowed by the English pass rather than scanned: unfiltered this walks
    # every non-English chapter in the library (1,742 rows, 17MB of bodies) to
    # keep 60. The filter is a superset — the exact pair is still checked below.
    translations = rows.exclude(book__language="en").filter(
        book__slug__in={slug for slug, _ in stripped},
        order__in={order for _, order in stripped},
    )
    for chapter in translations.iterator(chunk_size=200):
        if (chapter.book.slug, chapter.order) not in stripped:
            continue
        body = strip_leading_heading_element(chapter.body_html or "")
        if body != chapter.body_html:
            _rewrite(chapter, body)


def noop(apps, schema_editor):
    """Deliberately irreversible — putting the heading back would only restore
    a page that prints its own title twice."""


class Migration(migrations.Migration):
    dependencies = [("library", "0091_purpose_in_prayer_chapter_titles")]
    operations = [migrations.RunPython(strip_restatements, noop)]
