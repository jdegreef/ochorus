"""Give three Spanish books the quotation marks #1132 gave their fixtures.

#1132 widened the quote guard to count guillemets, which made three Spanish
books visible for the first time — each mixing straight marks in beside `« »` —
and converted their fixtures. That edit reaches a fresh build and no running
database: `seed_books` upserts the Book row and deliberately never rewrites an
existing book's CHAPTERS (it reports the drift and moves on), the create-only
rule that protects an approver's review state and protects stale text just as
effectively. Precedent for repairing the rows here instead: 0066, 0069, 0075.

Books only. #1132 converted a Spanish SERMON too, and it needs nothing:
`seed_sermons` upserts `body_html` and calls a real `save()` — only
`source_type` and `is_published` are create-only there — so its fixture edit
arrives on the next deploy anyway, and through the model's own hooks, which
re-derive `body_text` and refresh the vector better than this can.

Not BODY_CORRECTIONS. That table is exact `(old, new)` pairs applied by SLUG,
and neither half fits: 299 literal pairs would be unreviewable, and a slug-keyed
entry runs against every language's rows — `clothed-with-strength-and-dignity`
alone has eight editions, and the converter would give an English chapter's
straight quotes the Spanish outer mark. One-shot, language-scoped and
rule-shaped is what a data migration is for.

THE SLUGS ARE NAMED RATHER THAN DISCOVERED, and the other half of this same
change is why. A migration that scanned for any work still mixing the two
styles would find `susanna-wesley-clarke.en` — 796 straight marks and ten
OCR-damaged guillemets, which reads as mixed and as « »-quoting — and would
convert an English book's 796 marks to « ». It cannot know the guillemets are
damage rather than style, because the repair that tells it so is
`apply_body_corrections`, which runs LATER in the release chain. Four slugs are
reviewable by reading them; a scan is not.

`library.quote_marks.convert_work` makes the decision, shared with the fixture sweep
so a fresh build and a repaired database cannot land on different text, and
gated as that sweep gates: a work is converted only if its chapters TOGETHER
still mix the two styles, so on a database already holding the repair this
writes nothing at all — not even a save, which would null a vector that is
still valid and queue the row for a needless rebuild.

`search_vector` is NULLed on every row it DOES touch: these are historical model
instances, so no `save()` hook runs and the stored vector would otherwise stay
valid-looking but STALE. The release chain's `backfill_search_vectors` repairs
NULLs, so nulling is what puts them back in step.

One thing this cannot do on its own: move the content digest. `library/
migrations/data` is a content root but migration MODULES are not, so the
prerendered Spanish pages rebuild only because `corrections.py` changed in the
same commit. Shipping a repair like this without a content-root change would
leave the database correct and the pages stale.
"""

from __future__ import annotations

from django.db import migrations

from library.ingest import word_count
from library.quote_marks import convert_work
from library.text import html_to_text

LANGUAGE = "es"
BOOK_SLUGS = [
    "clothed-with-strength-and-dignity",
    "jesus-himself-2",
    "prevailing-prayer",
]


def _derive(html: str) -> tuple[str, int]:
    """What `save()` would have derived, which a historical model cannot run.

    `html_to_text`, not a local `<[^>]+>` → `" "` sub. 0066 and 0075 each wrote
    that sub inline and it is subtly wrong in two ways: it spaces EVERY tag, so
    an inline `<i>…</i>` before a comma yields "cristiano , refiriéndose"; and
    it never unescapes, so `&amp;` and `&mdash;` stay escaped in the column
    search indexes. `backfill_body_text` only fills an EMPTY `body_text`, so
    neither would ever self-correct. `library/text.py` exists to be the one
    canonical rule — the model's `save()`, the backfill and the migrations.
    """
    text = html_to_text(html)
    return text, word_count(html)


def repair(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")

    for slug in BOOK_SLUGS:
        # `defer`, per `apply_body_corrections`: this reads only `body_html` and
        # OVERWRITES the other two, so fetching them pulls bytes across the wire
        # to be thrown away. Assigning a deferred field un-defers it, and the
        # explicit `update_fields` is what writes it back.
        chapters = list(
            Chapter.objects.filter(book__slug=slug, book__language=LANGUAGE)
            .defer("body_text", "search_vector")
            .order_by("order")
        )
        repaired, changed = convert_work([c.body_html for c in chapters], slug)
        if not changed:
            continue
        for chapter, new in zip(chapters, repaired, strict=True):
            if new == chapter.body_html:
                continue
            chapter.body_html = new
            chapter.body_text, chapter.word_count = _derive(new)
            chapter.search_vector = None
            chapter.save(
                update_fields=["body_html", "body_text", "word_count", "search_vector"]
            )


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would put back a page that shows the reader both quote styles in
    the same paragraph. There is nothing to go back to that is worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0083_quote_rls")]
    operations = [migrations.RunPython(repair, noop)]
