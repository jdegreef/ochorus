"""Repair the inverted Matthew 15 illustration in "Humility" ch09.

The fixture is corrected in the same commit, which covers a database built from
scratch. This covers the rows already in production, because `seed_books`
creates chapters only for a book it has never seen — for a book that already
exists it reports body drift and changes nothing. Without this migration the
fixture and production would simply disagree.

Chapter rows in EVERY language are repaired: the Luganda edition reproduced the
defect faithfully (correctly — a translator quietly fixing it would have hidden
the problem), so the same repair applies to each, and `library/source_fixes`
no-ops on any text it does not match. The Arabic edition was still in
translation when this shipped; its pair goes in `NAME_OF_DOG` when it lands,
and a later migration applies it.

`body_text` is repaired by the SAME string replacement rather than re-derived
from the corrected HTML: re-deriving would also normalise the entities and
whitespace the fixture stores, so production would drift from the fixture over
a change of three letters. The word count is unaffected — one word becomes one
word.

`search_vector` is NULLed on every row touched rather than left alone: these
are historical model instances, so no `save()` hook runs and the stored vector
would otherwise stay valid-looking but STALE, and a search for "dog" would keep
missing the passage that is now about one. The release chain's
`backfill_search_vectors` repairs NULLs, so nulling is what puts them back in
step.

Independent of 0068, which repaired the same book's ch10 drop cap: that was the
PDF extractor dropping a letter, this is the source text itself saying the wrong
word. `corrections.py` and `source_fixes.py` keep that distinction.
"""

from __future__ import annotations

from django.db import migrations

from library.source_fixes import fix_name_of_dog

SLUG = "humility-2"
ORDER = 9


def repair(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    for chapter in Chapter.objects.filter(book__slug=SLUG, order=ORDER):
        fixed_html = fix_name_of_dog(chapter.body_html)
        fixed_text = fix_name_of_dog(chapter.body_text)
        if fixed_html == chapter.body_html and fixed_text == chapter.body_text:
            continue
        chapter.body_html = fixed_html
        chapter.body_text = fixed_text
        chapter.search_vector = None
        chapter.save(update_fields=["body_html", "body_text", "search_vector"])


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would mean putting back a sentence that says the opposite of what
    the author wrote, in a chapter whose argument depends on it. There is
    nothing to go back to that is worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0068_restore_chapter_headings")]
    operations = [migrations.RunPython(repair, noop)]
