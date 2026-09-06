"""Repair `ministry-of-intercession` ch13's Luke ix. 15 citation.

The chapter quotes "He was praying alone" — Luke 9:18, the verse before Peter's
confession, which is what the sentence is about — under the reference "Luke ix.
15", the seating of the five thousand. The error is the SOURCE's, so the repair
and its evidence live on `source_fixes.fix_praying_alone_reference`.

Same shape and rationale as 0075: `seed_books` never rewrites an existing
book's chapter bodies, so without this the deployed rows keep the wrong
reference; the fixture is corrected in the same commit because a fresh database
loads it AFTER migrate runs. EVERY language — the Hindi translator reproduced
the citation faithfully, and the repair carries each edition's own form.

`body_text` is repaired by the SAME replacement rather than re-derived from the
corrected HTML — 0069's shape, and 0084 is why it matters. A historical model
runs no `save()` hook, and the local `<[^>]+>` → `" "` sub that 0066 and 0075
each wrote inline is subtly wrong (it spaces EVERY tag, and never unescapes),
so re-deriving with it would leave these two rows disagreeing with the fixture
in every one of ch13's 27 inline tags — silently and permanently, since
`backfill_body_text` only fills an EMPTY `body_text`. Replacing in place cannot
drift: it touches three characters. `word_count` is untouched for the same
reason — the swap is one token for one token.

`search_vector` IS nulled, because `body_text` changed and a stale vector would
leave search matching the old reference. The release chain's
`backfill_search_vectors` repairs NULLs.
"""

from __future__ import annotations

from django.db import migrations

from library.source_fixes import SOURCE_FIXES, apply_source_fixes

SLUG, ORDER = "ministry-of-intercession", 13


def repair(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")

    assert (SLUG, ORDER) in SOURCE_FIXES, f"{SLUG} ch{ORDER} is not registered"
    for chapter in Chapter.objects.filter(book__slug=SLUG, order=ORDER):
        fixed_html = apply_source_fixes(SLUG, ORDER, chapter.body_html)
        fixed_text = apply_source_fixes(SLUG, ORDER, chapter.body_text)
        if fixed_html == chapter.body_html and fixed_text == chapter.body_text:
            continue
        chapter.body_html = fixed_html
        chapter.body_text = fixed_text
        chapter.search_vector = None
        chapter.save(update_fields=["body_html", "body_text", "search_vector"])


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would restore a quotation printed under a reference that is not
    its verse. There is nothing to go back to that is worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0119_remove_preexisting_biography_articles")]
    operations = [migrations.RunPython(repair, noop)]
