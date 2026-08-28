"""Give four Spanish editions the quotation marks #1132 gave their fixtures.

#1132 widened the quote guard to count guillemets, which made three Spanish
books and one Spanish sermon visible for the first time — each mixing straight
marks in beside `« »` — and converted 299 marks in the committed fixture. That
edit reaches a fresh build and no running database: `seed_books` upserts the
Book row and deliberately never rewrites an existing book's chapters (it reports
the drift and moves on), which is the create-only rule that protects an
approver's review state and protects stale text just as effectively. Precedent
for repairing the rows here instead: 0066, 0069, 0075.

Not BODY_CORRECTIONS. That table is exact `(old, new)` pairs applied by slug,
and neither half fits: 299 literal pairs would be unreviewable, and a slug-keyed
entry runs against EVERY language's rows — `clothed-with-strength-and-dignity`
alone has eight editions, and the converter would give an English chapter's
straight quotes the Spanish outer mark. The repair is one-shot, language-scoped
and rule-shaped, which is what a data migration is for.

The decision itself is `library.quotes.convert`, shared with the fixture sweep
so the two can never disagree, and gated exactly as the sweep gates: a work is
converted only if its chapters TOGETHER still mix the two styles. On a database
that already holds the converted text that reads "curly" and this does nothing.

`assert_punctuation_only` runs on every row. The wording of a scripture
quotation is protected byte-for-byte; only the quote characters may move.

`search_vector` is NULLed on every row touched rather than left alone: these are
historical model instances, so no `save()` hook runs and the stored vector would
otherwise stay valid-looking but STALE. The release chain's
`backfill_search_vectors` repairs NULLs, so nulling is what puts them back in
step.
"""

from __future__ import annotations

import re

from django.db import migrations

from library.quotes import (
    assert_punctuation_only,
    convert,
    quote_style,
    uses_guillemets,
)

LANGUAGE = "es"
BOOK_SLUGS = [
    "clothed-with-strength-and-dignity",
    "jesus-himself-2",
    "prevailing-prayer",
]
SERMON_SLUGS = ["unfailing-springs"]


def _derive(html: str) -> tuple[str, int]:
    """What `save()` would have derived, which a historical model cannot run."""
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
    return text, len(text.split())


def repair(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    Sermon = apps.get_model("library", "Sermon")

    for slug in BOOK_SLUGS:
        chapters = list(
            Chapter.objects.filter(book__slug=slug, book__language=LANGUAGE).order_by("order")
        )
        # The work-level gate, not a per-chapter one. A chapter that happens to
        # be wholly straight-quoted inside a mixed book was converted by the
        # fixture sweep too — the sweep asks the question of the whole file.
        joined = "".join(c.body_html for c in chapters)
        if quote_style(joined) != "MIXED":
            continue
        # Asked of the WORK, exactly as the fixture sweep asks it of the file.
        outer = uses_guillemets(joined)
        for chapter in chapters:
            new, changed = convert(chapter.body_html, outer_guillemets=outer)
            if not changed:
                continue
            assert_punctuation_only(chapter.body_html, new, f"{slug}/{chapter.order}")
            chapter.body_html = new
            chapter.body_text, chapter.word_count = _derive(new)
            chapter.search_vector = None
            chapter.save(
                update_fields=["body_html", "body_text", "word_count", "search_vector"]
            )

    for sermon in Sermon.objects.filter(slug__in=SERMON_SLUGS, language=LANGUAGE):
        if quote_style(sermon.body_html) != "MIXED":
            continue
        new, changed = convert(
            sermon.body_html, outer_guillemets=uses_guillemets(sermon.body_html)
        )
        if not changed:
            continue
        assert_punctuation_only(sermon.body_html, new, sermon.slug)
        sermon.body_html = new
        sermon.body_text, sermon.word_count = _derive(new)
        sermon.search_vector = None
        sermon.save(update_fields=["body_html", "body_text", "word_count", "search_vector"])


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would put back a page that shows the reader both quote styles in
    the same paragraph. There is nothing to go back to that is worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0081_author_same_as")]
    operations = [migrations.RunPython(repair, noop)]
