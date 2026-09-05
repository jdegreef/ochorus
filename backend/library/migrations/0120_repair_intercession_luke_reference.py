"""Repair `ministry-of-intercession` ch13's Luke ix. 15 citation.

The chapter quotes "And it came to pass that He was praying alone" — Luke 9:18,
the verse before Peter's confession, which is what the sentence is about — under
the reference "Luke ix. 15", which is the seating of the five thousand. The
error is in the SOURCE (the 1898 Nisbet printing has it, and Gutenberg carries
it forward), so the repair lives in `library/source_fixes` keyed by
`(slug, order)`; see the note there.

`source_fixes` reaches no database on its own. `seed_books` never rewrites an
existing book's chapter bodies — it reports the drift and moves on, the same
create-only rule that protects an approver's review state — so without this
migration the rows already in production keep the wrong reference. The fixture
is corrected in the same commit, which is not redundant: a fresh database loads
the fixture AFTER migrate runs, so this migration alone would leave a rebuild
holding the defect. Precedent: 0066, 0069, 0075.

EVERY language, not just English. The Hindi translator reproduced the citation
faithfully as "(लूका 9:15)" — which is correct of a translator — and each
edition's own form is listed in the repair, so an edition it does not match
no-ops. This is the only chapter the entry touches.

`search_vector` is NULLed on every row written: these are historical model
instances, so no `save()` hook runs and the stored vector would otherwise stay
valid-looking but STALE, leaving search matching the deleted text. The release
chain's `backfill_search_vectors` repairs NULLs, which is what puts them back in
step. `body_text` and `word_count` are derived here for the same reason.

The six dropped `(Note A.)`-`(Note F.)` cross-references found in the same
audit are NOT here: those are extractor damage, so they live in
`corrections.BODY_CORRECTIONS`, which `apply_body_corrections` applies to every
stored body on every deploy — no migration needed.
"""

from __future__ import annotations

import re

from django.db import migrations

from library.source_fixes import SOURCE_FIXES, apply_source_fixes

SLUG, ORDER = "ministry-of-intercession", 13


def repair(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")

    assert (SLUG, ORDER) in SOURCE_FIXES, f"{SLUG} ch{ORDER} is not registered"
    for chapter in Chapter.objects.filter(book__slug=SLUG, order=ORDER):
        fixed = apply_source_fixes(SLUG, ORDER, chapter.body_html)
        if fixed == chapter.body_html:
            continue
        chapter.body_html = fixed
        # Chapter.save()'s hooks don't exist on the historical model, so derive
        # what they would have derived.
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fixed)).strip()
        chapter.body_text = text
        chapter.word_count = len(text.split())
        chapter.search_vector = None
        chapter.save(
            update_fields=["body_html", "body_text", "word_count", "search_vector"]
        )


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would restore a quotation printed under a reference that is not
    its verse. There is nothing to go back to that is worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0119_remove_preexisting_biography_articles")]
    operations = [migrations.RunPython(repair, noop)]
