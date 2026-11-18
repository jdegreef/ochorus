"""Credit both Bibles Amharic quotes, not only the ULB.

The Amharic BOOKS quote the 1962 Bible (© 1962, 2003 United Bible Societies);
the site's own Scripture (footer blessings) is the Amharic Unlocked Literal
Bible. ``Language.bible_attribution`` named only the ULB, so every Amharic
book download carried a credit for a text it barely quotes and none for the
one it does. The footer line in ``frontend/src/lib/bibleCredit.ts`` changes
in the same commit, to the same string.

Amharic's row is owned by the admin, not ``language_seed``, so this only
rewrites the value it is replacing: a line someone has since edited by hand
is left alone. Reversible to the old line on the same terms.
"""

from django.db import migrations

OLD = (
    "Scripture quotations are from the Amharic Unlocked Literal Bible, "
    "© 2020 Door43 World Missions Community, licensed under "
    "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)."
)
NEW = (
    "Scripture quotations in Amharic books are from the Amharic Bible (1962), "
    "© 1962, 2003 United Bible Societies. Other Scripture on this site is from "
    "the Amharic Unlocked Literal Bible, © 2020 Door43 World Missions Community, "
    "licensed under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)."
)


def _swap(frm, to):
    def run(apps, schema_editor):
        Language = apps.get_model("library", "Language")
        Language.objects.filter(code="am", bible_attribution=frm).update(bible_attribution=to)

    return run


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0218_merge_reindex_arabic_search_and_article_qa"),
    ]

    operations = [migrations.RunPython(_swap(OLD, NEW), _swap(NEW, OLD))]
