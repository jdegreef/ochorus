"""Remove Hannah Buyinza's bio, keeping her book (Prayer – The Pulse of Life).

Withdrawn at the owner's request. Only the biography goes — the author row and
her book stay, so she remains the book's attributed author but no longer appears
in the Biographies section.

Why a migration AND fixture/seed removals (as with every content correction
here): the two reach different databases, and for a bio-CLEAR neither seed step
does the job on the existing production DB —

- Fresh DB: `seed_if_empty` loads the fixture (now `bio: ""`) after migrate, and
  `seed_author_translations` finds no `hannah-buyinza.short.txt` files (deleted
  in this commit), so nothing is created. This migration no-ops there — the
  author row does not exist yet at migrate time.
- Existing DB: the seeds only ever FILL, never blank. `author_sync.sync_author`
  skips an empty fixture `bio` (its guard is "a new bio exists"), and
  `seed_author_translations` "leaves the stored value alone" for a missing file.
  So the live short bio and its es/sw/lg `AuthorTranslation` rows would simply
  stay. This migration is what clears them.

The author is NOT deleted — she has a book. Only the English short `bio` and the
translated bios (`AuthorTranslation`) are removed; `bio_html` was already empty.
"""

from __future__ import annotations

from django.db import migrations

AUTHOR_SLUG = "hannah-buyinza"


def remove_bio(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")

    author = Author.objects.filter(slug=AUTHOR_SLUG).first()
    if not author:
        return  # fresh DB — the fixture (empty bio) supplies the row after this
    AuthorTranslation.objects.filter(author=author).delete()
    if author.bio or author.bio_html:
        author.bio = ""
        author.bio_html = ""
        author.save(update_fields=["bio", "bio_html"])


class Migration(migrations.Migration):
    dependencies = [("library", "0104_east_african_revival_biography_authors")]

    # Reverse is a no-op, not a restore: the bio is gone from the fixture and the
    # seed data in the same commit, so there is nothing to put back (a rebuild
    # reseeds from the fixture, which no longer carries it).
    operations = [migrations.RunPython(remove_bio, migrations.RunPython.noop)]
