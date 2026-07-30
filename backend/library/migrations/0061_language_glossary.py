"""Add ``Language.glossary`` and backfill the built-in languages.

The theological glossary used to live in a dict in ``library/translation.py``.
It moves onto the row so that a language created from the **admin** is
translatable the moment it exists — the translate_* commands read the registry
now, not code.

The values below are inlined rather than imported from
``library/language_seed.py`` for the usual reason (a migration must not change
meaning when the app changes) and, more practically, because a fresh or test
database loads the fixture *after* migrate: without this backfill every
language would come up with an empty glossary and fail its readiness check.
``manage.py seed_languages`` re-asserts these on every deploy, so an edit to the
seed file still wins afterwards.
"""

from django.db import migrations, models

GLOSSARIES = {
    "es": {
        "justification": "justificación",
        "sanctification": "santificación",
        "atonement": "expiación",
        "grace": "gracia",
        "the flesh": "la carne",
        "abide": "permanecer",
        "the Holy Spirit": "el Espíritu Santo",
        "the Lord": "el Señor",
        "godliness": "piedad",
        "intercession": "intercesión",
        "surrender": "entrega / rendición"
    },
    "sw": {
        "justification": "kuhesabiwa haki",
        "sanctification": "utakaso",
        "atonement": "upatanisho",
        "grace": "neema",
        "the flesh": "mwili",
        "abide": "kukaa (ndani ya Kristo)",
        "the Holy Spirit": "Roho Mtakatifu",
        "the Lord": "Bwana",
        "godliness": "utauwa",
        "intercession": "maombezi",
        "surrender": "kujisalimisha"
    },
    "lg": {
        "justification": "okuweebwa obutuukirivu",
        "sanctification": "okutukuzibwa",
        "atonement": "okutangirira",
        "grace": "ekisa",
        "the flesh": "omubiri",
        "abide": "okubeera (mu Kristo)",
        "the Holy Spirit": "Omwoyo Omutukuvu",
        "the Lord": "Mukama",
        "godliness": "okutya Katonda",
        "intercession": "okwegayiririra abalala",
        "surrender": "okwewaayo"
    },
    "pt": {
        "justification": "justificação",
        "sanctification": "santificação",
        "atonement": "expiação",
        "grace": "graça",
        "the flesh": "a carne",
        "abide": "permanecer",
        "the Holy Spirit": "o Espírito Santo",
        "the Lord": "o Senhor",
        "godliness": "piedade",
        "intercession": "intercessão",
        "surrender": "entrega / rendição"
    },
    "ar": {
        "justification": "التبرير",
        "sanctification": "التقديس",
        "atonement": "الكفّارة",
        "grace": "النعمة",
        "the flesh": "الجسد",
        "abide": "الثبات",
        "the Holy Spirit": "الروح القدس",
        "the Lord": "الرب",
        "godliness": "التقوى",
        "intercession": "الشفاعة",
        "surrender": "التسليم"
    }
}


def backfill(apps, schema_editor):
    # The field is brand new, so every existing row is `{}` here — nothing an
    # admin typed can be overwritten by this.
    Language = apps.get_model("library", "Language")
    for code, glossary in GLOSSARIES.items():
        Language.objects.filter(code=code).update(glossary=glossary)


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0060_language_min_plans_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="language",
            name="glossary",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
