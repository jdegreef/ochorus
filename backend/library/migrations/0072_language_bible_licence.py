"""Record what a language's Bible is licensed under, and how it must be credited.

Additive and blank-by-default, which is the correct historical state: every
Bible in the registry before Hindi was public domain, so an empty pair means
"nothing owed" rather than "not filled in yet". ``seed_languages`` re-asserts
both fields on the next deploy, so the Hindi values arrive from
``library/language_seed.py`` without a data migration hard-coding them here.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0071_review_outcome_and_translation_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="language",
            name="bible_licence",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Blank for a public-domain text.",
                max_length=60,
            ),
        ),
        migrations.AddField(
            model_name="language",
            name="bible_attribution",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Credit line shown to readers.",
                max_length=300,
            ),
        ),
    ]
