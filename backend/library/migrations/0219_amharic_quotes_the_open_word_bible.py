"""Amharic quotes the Open Word Bible (founder decision, 2026-11-18).

* ``bible_code`` becomes ``owb-am``: translation jobs read the bundled OWB
  Amharic Balanced text (``data/bible/owb-am-b.json.gz``) through
  ``translation.fetch_chapter``, offline. Its label says so.
* The credit line names what Amharic readers actually see. The books quote the
  1962 Bible (© 1962, 2003 United Bible Societies) until they are re-quoted to
  OWB; everything else Amharic on the site (footer blessings, the About
  verses) is OWB, which is CC0 and owes nothing. The ULB the old line named is
  no longer quoted anywhere. The line must fit ``bible_attribution``'s 300
  characters (Postgres enforces it; SQLite does not).
* ``bible_licence`` records the 1962 text's terms, so the readiness check keeps
  requiring the credit while any book still quotes it.

Amharic's row is admin-owned, not ``language_seed``'s, so the credit and licence
are rewritten only from the exact values they replace; a hand edit is left
alone. The Bible code is set outright: that is the decision being applied.
"""

from django.db import migrations

CODE, LABEL = "owb-am", "Open Word Bible (OWB), Balanced"
OLD_CREDIT = (
    "Scripture quotations are from the Amharic Unlocked Literal Bible, "
    "© 2020 Door43 World Missions Community, licensed under "
    "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)."
)
NEW_CREDIT = (
    "Scripture quotations in Amharic books are from the Amharic Bible (1962), "
    "© 1962, 2003 United Bible Societies. Other Amharic Scripture here is from the "
    "Open Word Bible (https://openwordbible.org), dedicated to the public domain (CC0)."
)
OLD_LICENCE = "CC BY-SA 4.0"
NEW_LICENCE = "© 1962, 2003 United Bible Societies (book quotations)"


def forward(apps, schema_editor):
    Language = apps.get_model("library", "Language")
    rows = Language.objects.filter(code="am")
    rows.update(bible_code=CODE, bible_label=LABEL)
    rows.filter(bible_attribution=OLD_CREDIT).update(bible_attribution=NEW_CREDIT)
    rows.filter(bible_licence=OLD_LICENCE).update(bible_licence=NEW_LICENCE)


def backward(apps, schema_editor):
    Language = apps.get_model("library", "Language")
    rows = Language.objects.filter(code="am")
    rows.filter(bible_attribution=NEW_CREDIT).update(bible_attribution=OLD_CREDIT)
    rows.filter(bible_licence=NEW_LICENCE).update(bible_licence=OLD_LICENCE)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0218_merge_reindex_arabic_search_and_article_qa"),
    ]

    operations = [migrations.RunPython(forward, backward)]
