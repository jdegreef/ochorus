"""Repair five mis-cited references and two chapter titles found by translators.

Translating is the one process that reads every sentence with attention, and
the ten-book batch in #983 surfaced these. The scripture references are defects
in the SOURCE — a quotation printed under a reference that is not its verse —
so they live in `library/source_fixes` and are keyed by `(slug, order)`; the
titles are extractor misses, so they live in `corrections.chapter_titles`.
Neither channel reaches a database on its own:

* `source_fixes` is consulted by the fixture and by migrations, and `seed_books`
  never rewrites an existing book's chapter bodies (it reports the drift and
  moves on) — that create-only rule is what protects an approver's review state,
  and it protects the stale text just as effectively.
* `chapter_titles` is consulted only while importing a PDF, so for a book
  already in the database it is inert. Precedent: 0070.

The fixture is corrected in the same commit, and that is not redundant: a fresh
database loads the fixture AFTER migrate runs, so this migration alone would
leave a rebuild holding the defects.

Chapter rows in EVERY language are repaired for the references. The translations
reproduced them faithfully — which is correct of a translator, and is what makes
them fixable here rather than silently papered over — and every edition prints
the numerals unlocalized, so one numeric repair covers all six. `source_fixes`
no-ops on any text it does not match, which is what keeps the three editions of
`jesus-himself-2` that resolved the Matthew 28:20 problem their own way from
being "repaired" out of correctness (see the note there).

The TITLE repair is scoped to English. `chapter_titles` is keyed by order, and
the same order in a translated edition holds a title in that language, so
applying an English title across languages would overwrite good translations.

`search_vector` is NULLed on every row touched rather than left alone: these are
historical model instances, so no `save()` hook runs and the stored vector would
otherwise stay valid-looking but STALE, leaving search matching the deleted
text. The release chain's `backfill_search_vectors` repairs NULLs, so nulling is
what puts them back in step.
"""

from __future__ import annotations

import re

from django.db import migrations

from library.source_fixes import SOURCE_FIXES, apply_source_fixes

# The entries this migration exists for. Deliberately a literal rather than all
# of SOURCE_FIXES: the earlier entries were already backfilled by 0066 and 0069,
# and re-running them would be a no-op that still rewrote every row's vector.
REFERENCE_REPAIRS = [
    ("jesus-himself-2", 2),
    ("the-inner-chamber", 15),
    ("the-inner-chamber", 23),
    ("he-holds-my-tomorrows", 7),
    ("he-holds-my-tomorrows", 8),
]

TITLE_REPAIRS = [
    (
        "the-unselfishness-of-god",
        12,
        "Friends testimonies Against Fiction, Music, And Art",
        "Friends' Testimonies Against Fiction, Music, And Art",
    ),
    ("the-unselfishness-of-god", 13, "Quaker scruples", "Quaker Scruples"),
]


def repair(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")

    for slug, order in REFERENCE_REPAIRS:
        assert (slug, order) in SOURCE_FIXES, f"{slug} ch{order} is not registered"
        for chapter in Chapter.objects.filter(book__slug=slug, order=order):
            fixed = apply_source_fixes(slug, order, chapter.body_html)
            if fixed == chapter.body_html:
                continue
            chapter.body_html = fixed
            # Chapter.save()'s hooks don't exist on the historical model, so
            # derive what they would have derived.
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fixed)).strip()
            chapter.body_text = text
            chapter.word_count = len(text.split())
            chapter.search_vector = None
            chapter.save(
                update_fields=["body_html", "body_text", "word_count", "search_vector"]
            )

    for slug, order, old, new in TITLE_REPAIRS:
        Chapter.objects.filter(
            book__slug=slug, book__language="en", order=order, title=old
        ).update(title=new, search_vector=None)


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would restore quotations printed under references that are not
    their verses. There is nothing to go back to that is worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0074_sync_language_bible_field_state")]
    operations = [migrations.RunPython(repair, noop)]
