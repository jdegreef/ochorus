"""Name every work whose title shows nothing, before 0181 forbids one.

The admin coverage matrix showed a Spurgeon book as just its author: its title
was blank. 0181 adds a CHECK constraint against that, and would fail the
deploy's migrate on any such row, so this gives each one a stand-in first: its
slug, words capitalised ("gleanings-among-the-sheaves" -> "Gleanings Among The
Sheaves"). A fixture work gets its real title back from seed_books /
seed_sermons a few steps later in `release`; any other is now named, listed and
fixable with "Fix title". Each one is printed to the deploy log.

A separate migration from the constraints on purpose: on Postgres, updating rows
of a table with deferred constraints and then ALTERing it in one transaction can
fail with "pending trigger events".

The renames go through .update(), which skips save(), so the derived search
columns are nulled here (backend/CLAUDE.md) and backfill_search_vectors rebuilds
them with the new title.

Blankness is judged as library.text.is_blank_title judges it — copied, not
imported, since a migration must not change when the app code does.
"""

import re
import unicodedata

from django.db import migrations

_BLANK_LETTERS = frozenset("͏ᅟᅠㅤﾠ")


def _blank(title):
    return all(
        unicodedata.category(c)[0] in "CZ" or c.isspace() or c in _BLANK_LETTERS
        for c in str(title or "")
    )


def _stand_in(model, pk, slug):
    words = " ".join(w.capitalize() for w in re.split(r"[-_\s]+", slug or "") if w)
    return words[:300] or f"Untitled {model.lower()} {pk}"


def name_untitled_works(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    for model, field in (("Book", "title"), ("Sermon", "title"), ("Plan", "title"), ("Article", "h1")):
        Model = apps.get_model("library", model)
        rows = Model.objects.values_list("pk", "slug", "language", field).iterator()
        for pk, slug, language, value in rows:
            if not _blank(value):
                continue
            stand_in = _stand_in(model, pk, slug)
            extra = {"search_vector": None} if model == "Sermon" else {}
            Model.objects.filter(pk=pk).update(**{field: stand_in}, **extra)
            if model == "Book":  # the book title is baked into its chapters' vectors
                Chapter.objects.filter(book_id=pk).update(search_vector=None)
            print(f"\n  named untitled {model} {slug} ({language}): {stand_in!r}", end="")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0179_typographic_translation_digests"),
    ]

    operations = [
        migrations.RunPython(name_untitled_works, migrations.RunPython.noop),
    ]
