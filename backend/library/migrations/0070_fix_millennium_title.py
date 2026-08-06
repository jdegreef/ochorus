"""Fix the misspelled chapter title "Into A New Millenium" (stepping-stones-2 ch30).

The spelling correction lives in `corrections.py` under `chapter_titles`, which
covers a database built from scratch — but ONLY through the importer. Unlike
`BODY_CORRECTIONS`, which the release chain re-applies to stored rows every
deploy via `apply_body_corrections`, `chapter_titles` is consulted only while
importing a PDF. So for a book already in the database it is inert, and the
fixture and production would simply disagree. This migration is what reaches
the existing row.

The fixture is corrected in the same commit, and that is not redundant: a fresh
database loads the fixture AFTER migrate runs, so this migration alone would
leave a rebuild holding the misspelling.

Scoped to the English edition. `chapter_titles` is keyed by chapter order, and
the same order in a translated edition holds a title in that language — the
Luganda edition of this chapter is "Okuyingira mu Mulembe Omuggya" and the
Swahili "Kuingia Katika Milenia Mpya", both spelled correctly and neither equal
to the English string. Applying an English title by order across languages
would overwrite good translations with English, so the filter is load-bearing
rather than defensive.

`search_vector` is NULLed because the title feeds it: these are historical model
instances, so no `save()` hook runs and the stored vector would stay
valid-looking but stale, leaving a search for "millennium" matching the
misspelling instead. The release chain's `backfill_search_vectors` repairs
NULLs, which is what puts the row back in step.

Found by the English audit rather than by a reader — see the audit notes on
`corrections.py`. The body of this chapter spells the word correctly, which is
what settles that the title is the defect and not a variant spelling.
"""

from __future__ import annotations

from django.db import migrations

SLUG = "stepping-stones-2"
ORDER = 30
OLD = "Into A New Millenium"
NEW = "Into A New Millennium"


def fix(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    rows = Chapter.objects.filter(
        book__slug=SLUG, book__language="en", order=ORDER, title=OLD
    )
    for chapter in rows:
        chapter.title = NEW
        chapter.search_vector = None
        chapter.save(update_fields=["title", "search_vector"])


class Migration(migrations.Migration):
    dependencies = [("library", "0069_repair_humility_name_of_dog")]

    # Deliberately irreversible: reversing would restore a misspelling.
    operations = [migrations.RunPython(fix, migrations.RunPython.noop)]
