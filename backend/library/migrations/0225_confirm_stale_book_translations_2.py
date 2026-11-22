"""Confirm 20 book translations current with their revised English (batch 2).

The last 11 stale books: After His Heart (an Ochorus Original whose English was
corrected in #9563), plus ten classics whose English was proofread (Confessions,
The Reformed Pastor, The Master's Indwelling, Wesley's and Whitefield's sermons,
Our Daily Walk, Spurgeon on Prayer, Revival Lectures, Amanda Smith, Finney's
Memoirs). Each change was checked against every stale translation. 27 had
followed the old English (a wrong Scripture reference, a dropped clause, a
misread word, an old chapter title) and are corrected in their fixture files in
the same PR, which re-baselines them on deploy. These 20 already rendered the
passage correctly, so only their baseline moves: the same effect as the admin's
"still matches" click (``translation_staleness.mark_current``).
"""

from django.db import migrations

CONFIRMED = {
    "amanda-smith-autobiography": ["es", "fr", "sw"],
    "confessions": ["es", "fr", "lg", "uk"],
    "finney-memoirs": ["es"],
    "revival-lectures": ["es", "sw"],
    "selected-sermons-whitefield": ["es", "fr"],
    "spurgeon-on-prayer": ["ar"],
    "the-reformed-pastor": ["ar", "es", "fr", "lg", "pt", "uk", "vi"],
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
    dependencies = [
        ("library", "0224_author_start_with"),
        ("library", "0224_confirm_stale_book_translations_1"),
    ]
    operations = [migrations.RunPython(confirm, migrations.RunPython.noop)]
