"""Confirm the Originals' translations current, again, now that the English is deployed.

0228 did this for After His Heart and The Prayers Jesus Learned (whose English
quotations moved to the revised Open Word Bible wording in #10080), but it
shipped in the same deploy as #10080 itself: ``release`` runs ``migrate``
before ``seed_books``, so 0228 copied the OLD English ``content_digest`` and the
translations stayed flagged stale. The English is now seeded with the new
text, so the same re-baseline takes this time. Each translation quotes its own
language's Scripture, not the English wording, so none needs editing: the same
effect as the admin's "still matches" click (``translation_staleness.mark_current``).
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
    dependencies = [("library", "0228_confirm_originals_owb_quotes")]
    operations = [migrations.RunPython(confirm, migrations.RunPython.noop)]
