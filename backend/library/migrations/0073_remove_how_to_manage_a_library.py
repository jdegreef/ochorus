"""Remove "How to Manage a Library" and its author, Charlotte Akankwasa.

Withdrawn from the library at the owner's request. The work is removed
everywhere it exists rather than merely unpublished: an unpublish hides a book
from readers but keeps the rows, and the ask here is deletion.

Why a migration AND a fixture removal, as with every content correction here:
the two reach different databases. Deleting the fixture file covers a database
built from scratch (`seed_if_empty` loads the fixture after migrate runs), but
the seeds only ever create-or-update — they never delete — so on the existing
production database the rows would simply stay. This migration is what reaches
those. Neither alone is enough.

Chapters go with the book by CASCADE, and the author's `AuthorTranslation` rows
(the Spanish/Luganda/Swahili short bios, also removed from the seed data in this
commit) go with the author the same way.

The author is deleted only if nothing else of theirs remains. Charlotte
Akankwasa has this one book and no sermons today, so the guard is not doing
anything right now — but an author row is shared, and a future edition or sermon
attributed to them would otherwise be orphaned into a CASCADE by a migration
whose stated job was to remove one book.
"""

from __future__ import annotations

from django.db import migrations

BOOK_SLUG = "how-to-manage-a-library"
AUTHOR_SLUG = "charlotte-akankwasa"


def remove(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Sermon = apps.get_model("library", "Sermon")
    Author = apps.get_model("library", "Author")

    # Every language edition of the work (only `en` exists today).
    Book.objects.filter(slug=BOOK_SLUG).delete()

    author = Author.objects.filter(slug=AUTHOR_SLUG).first()
    if not author:
        return
    has_other_work = (
        Book.objects.filter(author=author).exists()
        or Sermon.objects.filter(author=author).exists()
    )
    if not has_other_work:
        author.delete()


class Migration(migrations.Migration):
    dependencies = [("library", "0072_language_bible_licence")]

    # Deliberately irreversible: the content it removes is gone from the fixture
    # in the same commit, so there is nothing for a reverse to restore from.
    operations = [migrations.RunPython(remove, migrations.RunPython.noop)]
