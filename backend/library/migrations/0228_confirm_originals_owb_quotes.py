"""Confirm the Originals' translations current after their OWB quote refresh.

#10080 brought the English Scripture quotations of After His Heart and The
Prayers Jesus Learned into line with the revised Open Word Bible wording
(Matthew 4:4, 8:9, 2 Timothy 4:1, Genesis 32:10). Each translation quotes
its own language's Scripture, not the English, so none of them follows the
changed wording and only their baseline moves: the same effect as the admin's
"still matches" click (``translation_staleness.mark_current``). Coram Deo has
no translations.
"""

from django.db import migrations

CONFIRMED = {
    "after-his-heart": [
        "am",
        "ar",
        "es",
        "fr",
        "hi",
        "ja",
        "ko",
        "lg",
        "pt",
        "ru",
        "sw",
        "uk",
        "vi",
    ],
    "the-prayers-jesus-learned": ["am", "es", "fr", "ko", "pt"],
}


def confirm(apps, schema_editor):
    Model = apps.get_model("library", "Book")
    for slug, languages in CONFIRMED.items():
        en = (
            Model.objects.filter(slug=slug, language="en")
            .values_list("content_digest", flat=True)
            .first()
        )
        if not en:
            continue
        Model.objects.filter(slug=slug, language__in=languages).update(
            english_digest=en
        )


class Migration(migrations.Migration):
    dependencies = [("library", "0227_confirm_stale_book_translations_2")]
    operations = [migrations.RunPython(confirm, migrations.RunPython.noop)]
