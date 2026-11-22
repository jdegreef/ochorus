"""Confirm 22 article translations current with their revised English.

The coverage matrix flagged 35 article translations "English changed": the
English of 12 articles was revised after they were translated (a corrected
Scripture reference, a fact fixed, a sentence reworded). Each change was checked
against every stale translation. 13 needed the new wording and are updated in
their fixture files in the same PR, which re-baselines them on deploy. These
22 already said what the revised English says, so only their baseline moves:
the same effect as the admin's "still matches" click
(``translation_staleness.mark_current``). A later English change flags them again.
"""

from django.db import migrations

CONFIRMED = {
    "a-brand-plucked-from-the-fire-guide": ["sw"],
    "a-retrospect-guide": ["sw"],
    "how-to-find-gods-will-for-your-life": ["ar", "es", "fr", "lg", "pt", "sw"],
    "jesus-himself-2-guide": ["ar"],
    "personal-revival-reviving-a-cold-heart": ["ar", "es", "fr", "pt"],
    "religious-experience-and-journal-guide": ["ar", "es", "fr", "pt"],
    "sinners-in-the-hands-of-an-angry-god-explained": ["ar", "es", "fr", "pt"],
    "the-person-and-work-of-the-holy-spirit-guide": ["ar"],
}


def confirm(apps, schema_editor):
    Model = apps.get_model("library", "Article")
    for slug, languages in CONFIRMED.items():
        en = (
            Model.objects.filter(slug=slug, language="en")
            .values_list("content_digest", flat=True)
            .first()
        )
        if not en:
            continue
        Model.objects.filter(slug=slug, language__in=languages).update(english_digest=en)


class Migration(migrations.Migration):
    dependencies = [("library", "0221_search_click_result_key")]
    operations = [migrations.RunPython(confirm, migrations.RunPython.noop)]
