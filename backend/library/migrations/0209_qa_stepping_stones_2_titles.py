"""Fix three mis-cased chapter titles in stepping-stones-2 (English edition).

Found in the English proofreading pass. Each is an extractor title-casing slip
that lowered the letter after a hyphen, slash or full stop:

- ch13 "Type-a Specialist" -> "Type-A Specialist" — the chapter's own body (and
  ch5, ch12, ch16) reads "Type-A" every time; the audit's
  `title-case-vs-body` class flagged it.
- ch20 "Sidney, B.c"       -> "Sidney, B.C."  — British Columbia.
- ch21 "M/v Anastasis"     -> "M/V Anastasis" — the body writes "M/V
  Anastasis" throughout.

Chapter titles are not re-applied by the release chain the way
`BODY_CORRECTIONS` are, so like `0070_fix_millennium_title` (the same book)
this migration is what reaches the stored rows; the fixture is corrected in
the same commit for a fresh build. Scoped to `language="en"`: the same order in
a translated edition holds a title in that language. `search_vector` is NULLed
because the title feeds it and no `save()` hook runs on historical models; the
release backfill repairs NULLs.
"""

from __future__ import annotations

from django.db import migrations

SLUG = "stepping-stones-2"
FIXES = {
    13: ("Type-a Specialist", "Type-A Specialist"),
    20: ("Sidney, B.c", "Sidney, B.C."),
    21: ("M/v Anastasis", "M/V Anastasis"),
}


def fix(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    for order, (old, new) in FIXES.items():
        for chapter in Chapter.objects.filter(
            book__slug=SLUG, book__language="en", order=order, title=old
        ):
            chapter.title = new
            chapter.search_vector = None
            chapter.save(update_fields=["title", "search_vector"])


class Migration(migrations.Migration):
    dependencies = [("library", "0208_planday_entry_date")]

    # Deliberately irreversible: reversing would restore the mis-casing.
    operations = [migrations.RunPython(fix, migrations.RunPython.noop)]
