"""Fix three misspelled section titles in freedom-of-the-will (English edition).

Found by the Amharic translation (#3737), whose translators rendered the
evident sense and logged the English:

- ch6  "Self-Determing Power"       -> "Self-Determining Power"
- ch16 "Evidence of Gods Certain"   -> "Evidence of God’s Certain"
- ch31 "Stoical Doctrine of Faith"  -> "Stoical Doctrine of Fate" — Edwards'
  own heading (Part IV §6). The section answers the charge that Calvinism is
  Stoic *fatalism*, and its body speaks of "their doctrine of fate" throughout.

Chapter titles are not re-applied by the release chain the way
`BODY_CORRECTIONS` are, so like `0070_fix_millennium_title` this migration is
what reaches the stored rows; the fixture is corrected in the same commit for a
fresh build. Scoped to `language="en"`: the same order in a translated edition
holds a title in that language, and every translation already renders the
correct sense. `search_vector` is NULLed because the title feeds it and no
`save()` hook runs on historical models; the release backfill repairs NULLs.
"""

from __future__ import annotations

from django.db import migrations

SLUG = "freedom-of-the-will"
FIXES = {
    6: ("Self-Determing Power", "Self-Determining Power"),
    16: ("Evidence of Gods Certain", "Evidence of God’s Certain"),
    31: ("Stoical Doctrine of Faith", "Stoical Doctrine of Fate"),
}


def fix(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    for order, (old, new) in FIXES.items():
        for chapter in Chapter.objects.filter(
            book__slug=SLUG, book__language="en", order=order, title__contains=old
        ):
            chapter.title = chapter.title.replace(old, new)
            chapter.search_vector = None
            chapter.save(update_fields=["title", "search_vector"])


class Migration(migrations.Migration):
    dependencies = [("library", "0205_adminaction_email_automation")]

    # Deliberately irreversible: reversing would restore the misspellings.
    operations = [migrations.RunPython(fix, migrations.RunPython.noop)]
