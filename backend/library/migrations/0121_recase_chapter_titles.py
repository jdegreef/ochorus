"""Lowercase the little words in Title-Cased chapter titles.

The PDF import capitalized every word, so minor words English title case keeps
lowercase came out wrong — "The Glory Of The Creature", "Humility In The Life Of
Jesus". `seed_books` deliberately never syncs an existing book's chapters
(chapter `order` is a public contract), so no deploy carries a fixture title fix
to rows already in production. This is the backfill; the fixture is corrected in
the same commit, and `tests_fixture` keeps the two from drifting back.

ENGLISH ONLY — `recase_title`'s minor-word list is English, and the gate only
recognises English Title Case; a translated title must not be touched by an
English rule. TITLE ONLY — `order` is never read or written.

`search_vector` is NULLed on every row written: the title is weight A in the
chapter's stored tsvector (library/fts.py), and a historical model's `save()`
runs none of the real hooks, so a retitled row would keep matching searches for
its old casing. The release chain's `backfill_search_vectors` refills NULLs on
the next deploy. See 0090 for the same shape.
"""

from __future__ import annotations

from django.db import migrations

from library.titlecase import recase_title


def recase(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    qs = Chapter.objects.filter(book__language="en").only("id", "title")
    for ch in qs.iterator(chunk_size=2000):
        fixed = recase_title(ch.title)
        if fixed == ch.title:
            continue
        ch.title = fixed
        ch.search_vector = None
        ch.save(update_fields=["title", "search_vector"])


def noop(apps, schema_editor):
    """Deliberately irreversible — restoring "The Glory Of The Creature" would
    only put the defect back."""


class Migration(migrations.Migration):
    dependencies = [("library", "0120_repair_intercession_luke_reference")]
    operations = [migrations.RunPython(recase, noop)]
