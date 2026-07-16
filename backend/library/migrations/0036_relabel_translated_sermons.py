"""AI-translated sermons were mislabelled as public-domain originals.

``Sermon.source_type`` arrived in 0035 — *after* the Spanish sermons were
created (0025) and after the Luganda rows were seeded — so every translation
predating the field silently took the model default, ``public_domain``. Two
consequences:

* the reader saw **no** "awaiting native review" badge, so machine translation
  read as a trustworthy public-domain original;
* ``approve_sermon_translation`` refused them outright ("that sermon is a
  public-domain original, not a translation"), so they could never be reviewed.

A non-English sermon that shares its slug *and author* with an English one is a
translation of it — the same (slug, language) convention Book uses. Match on the
author too, not the slug alone: slug is unique per language, not per author, so a
native-language original could legitimately collide with an unrelated English
sermon's slug (an original Luganda sermon on rest, say, against Spurgeon's
"rest") and would otherwise be stamped as machine output.

Only rows still carrying the default are touched: never downgrade one an
approver already marked reviewed, and never touch a genuine non-English original.
"""

from django.db import migrations
from django.db.models import Q


def relabel_translations(apps, schema_editor):
    Sermon = apps.get_model("library", "Sermon")
    english = Sermon.objects.filter(language="en").values_list("slug", "author_id")
    if not english:
        return  # fresh DB: English sermons are seeded after migrate — no-op
    # Each translation must match one English sermon on BOTH slug and author.
    match = Q()
    for slug, author_id in english:
        match |= Q(slug=slug, author_id=author_id)
    Sermon.objects.filter(source_type="public_domain").exclude(language="en").filter(
        match
    ).update(source_type="ai_unreviewed")


class Migration(migrations.Migration):
    dependencies = [("library", "0035_sermon_source_type")]

    operations = [
        migrations.RunPython(relabel_translations, migrations.RunPython.noop),
    ]
