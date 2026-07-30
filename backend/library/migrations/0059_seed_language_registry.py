"""Populate the Language registry so a fresh database has it immediately.

``seed_languages`` re-asserts identity on every deploy, but a *fresh* database —
including the one every test run builds — only has what migrations put there,
and `_language_entry` now reads this table for every serialized language label.
Without this, a new environment would render bare codes until the first deploy
seed, and the test suite would have no languages at all.

The rows are inlined rather than imported from ``library.translation``: a
migration is a historical snapshot and must keep replaying the same way even
after that module changes. Ongoing corrections flow through the seed instead.

Status here mirrors what the site advertised when this landed; it is create-only
in the seed thereafter, so an admin's launch is never walked back by a deploy.
"""

from django.db import migrations

LANGUAGES = [
    # code, name, native, bible_code, bible_label, rtl, is_source, status, order
    ("en", "English", "English", "", "", False, True, "live", 0),
    ("es", "Spanish", "Español", "rv1858", "Reina-Valera (1858/1862)", False, False, "live", 1),
    ("sw", "Swahili", "Kiswahili", "swhonen", "Swahili Union-tradition (open)", False, False, "live", 2),
    ("lg", "Luganda", "Luganda", "lug", "Luganda Bible (open)", False, False, "live", 3),
    ("pt", "Portuguese", "Português", "porbrbsl", "Bíblia Livre para o Mundo (public domain)", False, False, "live", 4),
    # Arabic is wired end-to-end but has no content yet, so it starts as a draft.
    ("ar", "Arabic", "العربية", "arb-vd", "Van Dyck (1865)", True, False, "draft", 5),
]


def forwards(apps, schema_editor):
    Language = apps.get_model("library", "Language")
    for (
        code,
        name,
        native,
        bible_code,
        bible_label,
        rtl,
        is_source,
        status,
        order,
    ) in LANGUAGES:
        # get_or_create, not create: the seed may already have run in a
        # deploy that applied this migration mid-chain.
        Language.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "native_name": native,
                "bible_code": bible_code,
                "bible_label": bible_label,
                "rtl": rtl,
                "is_source": is_source,
                "status": status,
                "sort_order": order,
            },
        )


def backwards(apps, schema_editor):
    # Reversible for local rollbacks; only removes the rows this added.
    Language = apps.get_model("library", "Language")
    Language.objects.filter(code__in=[row[0] for row in LANGUAGES]).delete()


class Migration(migrations.Migration):
    dependencies = [("library", "0058_language_registry")]

    operations = [migrations.RunPython(forwards, backwards)]
