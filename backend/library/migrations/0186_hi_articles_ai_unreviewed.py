"""Re-gate the 23 Hindi study-guide articles as ai_unreviewed.

PR #4724 shipped them without a ``source_type`` key, so ``seed_articles``
created each row with the model default, ``public_domain`` — presenting an
unreviewed AI translation as an original, with no "awaiting native review"
badge. The fixture now carries ``ai_unreviewed``, but ``source_type`` is
create-only in the seed, so the live rows need this one-off flip.

Only rows still at ``public_domain`` move: an ``ai_reviewed`` row was approved
by a native reviewer and is left alone. A fresh install has no rows yet and
gets the right value from the fixture.
"""

from django.db import migrations

SLUGS = (
    "a-brand-plucked-from-the-fire-guide",
    "a-call-to-the-unconverted-guide",
    "a-retrospect-guide",
    "a-serious-call-guide",
    "a-short-and-easy-method-of-prayer-guide",
    "all-of-grace-guide",
    "amanda-smith-autobiography-guide",
    "days-of-heaven-upon-earth-guide",
    "divine-healing-guide",
    "feasting-at-the-table-guide",
    "freedom-of-the-will-guide",
    "gleanings-among-the-sheaves-guide",
    "godliness-guide",
    "he-holds-my-tomorrows-guide",
    "holy-in-christ-guide",
    "how-to-pray-so-god-answers",
    "jesus-himself-2-guide",
    "power-through-prayer-guide",
    "prayer-and-praying-men-guide",
    "prevailing-prayer-guide",
    "purity-of-heart-guide",
    "purpose-in-prayer-guide",
    "revival-lectures-guide",
)


def regate(apps, schema_editor):
    Article = apps.get_model("library", "Article")
    Article.objects.filter(
        language="hi", slug__in=SLUGS, source_type="public_domain"
    ).update(source_type="ai_unreviewed")


class Migration(migrations.Migration):
    dependencies = [("library", "0185_c_s_lewis_biography_author")]

    operations = [migrations.RunPython(regate, migrations.RunPython.noop)]
