"""Confirm 64 sermon translations current with their corrected English.

The coverage matrix flagged 74 sermon translations "English changed": the
English of 25 sermons was proofread after they were translated (OCR slips such
as "Sis-ters", "pythians", "a live pound note", a dropped "I"). Each change was
checked against every stale translation. Ten translations had followed the
defect and are corrected in their fixture files in the same PR, which
re-baselines them on deploy. These 64 had already rendered the passage
correctly (a translator does not carry "Sis-ters" or a misread name across),
so their text stays as it is and only their baseline moves: the same effect as
the admin's "still matches" click (``translation_staleness.mark_current``).

Each row is re-baselined only to its English edition's current digest, so a
later English change still flags it again.
"""

from django.db import migrations

CONFIRMED = {
    "all-sufficiency": ["sw"],
    "all-with-one-accord": ["fr"],
    "causes-of-backsliding": ["sw"],
    "come-thou-into-the-ark": ["es", "fr", "pt", "sw"],
    "come-unto-him": ["fr", "sw"],
    "comfort-for-the-desponding": ["fr"],
    "do-you-pray": ["fr", "vi"],
    "enduring-persecution-for-christ": ["es"],
    "how-to-contemplate-christs-holy-sufferings": ["sw"],
    "pauls-first-prayer": ["ar", "es", "lg", "pt", "sw"],
    "safety-fulness-and-sweet-refreshment-in-christ": ["pt", "sw"],
    "the-death-of-self": ["pt"],
    "the-golden-key-of-prayer": ["ar", "es", "fr", "hi", "lg", "pt", "sw"],
    "the-joy-of-the-lord": ["ar", "es", "fr", "hi", "lg", "pt", "sw"],
    "the-lord-our-righteousness": ["sw"],
    "the-new-birth": ["ar", "es", "pt", "sw"],
    "the-possibilities-of-faith": ["am", "ar", "es", "fr", "hi", "lg", "pt", "sw"],
    "the-power-of-feeble-faith": ["fr", "sw"],
    "unto-us-a-child-is-born": ["fr", "ko"],
    "walking-with-god": ["es", "fr", "pt", "sw"],
    "what-have-i-to-do-any-more-with-idols": ["sw"],
    "witnessing-for-christ": ["am", "ar", "es", "fr", "hi", "sw"],
}


def confirm(apps, schema_editor):
    Sermon = apps.get_model("library", "Sermon")
    for slug, languages in CONFIRMED.items():
        en = (
            Sermon.objects.filter(slug=slug, language="en")
            .values_list("content_digest", flat=True)
            .first()
        )
        if not en:
            continue
        Sermon.objects.filter(slug=slug, language__in=languages).update(english_digest=en)


class Migration(migrations.Migration):
    dependencies = [("library", "0219_amharic_quotes_the_open_word_bible")]
    operations = [migrations.RunPython(confirm, migrations.RunPython.noop)]
