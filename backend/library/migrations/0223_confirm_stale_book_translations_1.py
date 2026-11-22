"""Confirm 181 book translations current with their proofread English.

45 books had their English proofread after they were translated (OCR slips such
as "Arctæus", "the Ornament" for "the firmament", a dropped line), which left
their translations flagged "English changed". Each change was checked against
every stale translation of these books. 21 had followed the old English and
are corrected in their fixture files in the same PR, which re-baselines them on
deploy. These 181 already rendered the passage correctly, so only their baseline
moves: the same effect as the admin's "still matches" click
(``translation_staleness.mark_current``). A later English change flags them again.

The other 11 stale books (After His Heart, Confessions, The Reformed Pastor, ...)
are not in this list; they are handled separately.
"""

from django.db import migrations

CONFIRMED = {
    "a-retrospect": ["es", "sw"],
    "a-retrospect-children": ["es", "fr", "pt", "sw"],
    "a-retrospect-teens": ["am", "sw"],
    "absolute-surrender-teens": ["am", "fr"],
    "all-things-for-good": ["am", "fr", "lg", "sw", "vi"],
    "baptism-with-the-holy-spirit": ["am", "ar", "es", "hi", "ko", "lg", "pt", "vi"],
    "cheque-book": ["ar", "hi", "ko", "uk"],
    "elisabeth-elliot-a-life-children": ["es", "fr"],
    "enchiridion": ["am", "es"],
    "epistles-of-ignatius": ["am", "es", "fr", "hi", "ko", "lg", "pt", "sw", "vi"],
    "evening-by-evening": ["am", "es"],
    "ever-increasing-faith": ["es", "fr", "ko", "vi"],
    "first-epistle-of-clement": ["am", "es", "fr", "lg", "pt", "sw"],
    "freedom-of-the-will": ["es", "fr"],
    "george-muller-of-bristol": ["am", "es", "fr"],
    "godliness": ["am", "ko"],
    "growing-in-wisdom": ["am", "ar", "es", "fr", "hi", "ko", "lg", "pt", "sw", "uk", "vi"],
    "how-to-succeed-in-the-christian-life": ["am", "es", "fr", "hi", "ko", "vi"],
    "humility-2": ["am", "ar", "es", "fr", "hi", "ko", "lg", "pt", "sw", "uk", "vi"],
    "jesus-teacher-of-prayer": ["hi", "ko"],
    "key-teachings-of-richard-baxter": ["am", "es", "fr", "pt"],
    "life-of-antony": ["am", "es"],
    "mortification-of-sin": ["am", "es"],
    "necessity-of-prayer": ["am", "es", "fr", "ko", "lg", "pt", "sw", "vi"],
    "on-the-incarnation": ["es", "fr", "ko", "lg", "pt", "sw", "vi"],
    "on-the-priesthood": ["am", "es"],
    "pensees": ["es", "hi", "ko", "vi"],
    "plain-account-christian-perfection": ["am", "es", "fr", "lg"],
    "power-through-prayer": ["am", "ar", "es", "hi", "pt", "sw", "uk"],
    "purity-of-heart": ["am", "ar", "uk", "vi"],
    "religious-affections": ["es"],
    "rise-up-men-of-god-2": ["es", "fr", "lg", "pt"],
    "susanna-wesley-clarke": ["am", "ar", "es", "fr", "uk"],
    "the-fourfold-gospel": ["am", "es", "fr", "hi", "lg", "pt", "sw"],
    "the-imitation-of-christ": ["am", "ar", "fr", "ko", "sw", "uk", "vi"],
    "the-life-of-trust": ["es", "sw"],
    "the-life-of-trust-teens": ["am"],
    "the-practice-of-the-presence-of-god": ["es", "fr", "hi", "ko", "vi"],
    "the-way-to-god": ["am", "ko", "uk"],
    "till-he-come": ["pt"],
    "true-vine": ["am", "ar", "es", "fr", "hi", "ko", "lg", "pt", "sw", "vi"],
    "union-and-communion": ["ar", "uk"],
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
        Model.objects.filter(slug=slug, language__in=languages).update(english_digest=en)


class Migration(migrations.Migration):
    dependencies = [("library", "0222_confirm_stale_article_translations")]
    operations = [migrations.RunPython(confirm, migrations.RunPython.noop)]
