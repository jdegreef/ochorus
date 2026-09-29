"""Take Henry Blackaby's biography off the site (for now), at the founder's request.

Unlike Hannah Buyinza (``0105``), Blackaby has no work of his own: he is a
biography-only author (``0115``), a chapter subject in ``men-of-prayer-2``. With
the bio gone his author page would be an empty dead end, so the whole row goes —
its ``AuthorTranslation``s and ``BookPerson`` link cascade with it. The
Men of Prayer chapter about him is the book's own text and stays.

Why a migration AND fixture/seed removals: the fixture row, the book-people
membership, the milestones and the translated Q&A files are removed in the same
commit, so a fresh DB never creates him. But the seeds only ever create or fill,
never delete, so on the existing DB the row would simply stay — this migration
is what removes it.

To bring the bio back, revert the commit that added this migration's
fixture/seed removals and add a migration that re-creates the row the way
``0115`` does.
"""

from __future__ import annotations

from django.db import migrations

AUTHOR_SLUG = "henry-blackaby"


def remove_author(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug=AUTHOR_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [("library", "0168_correct_reviewed_hyde_translations")]

    # Reverse is a no-op, not a restore: the bio is gone from the fixture and the
    # seed data in the same commit, so there is nothing to put back.
    operations = [migrations.RunPython(remove_author, migrations.RunPython.noop)]
