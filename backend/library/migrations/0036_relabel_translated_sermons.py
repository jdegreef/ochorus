"""AI-translated sermons were mislabelled as public-domain originals.

``Sermon.source_type`` arrived in 0035 — *after* the Spanish sermons were
created (0025) and after the Luganda rows were seeded — so every translation
predating the field silently took the model default, ``public_domain``. Two
consequences:

* the reader saw **no** "awaiting native review" badge, so machine translation
  read as a trustworthy public-domain original;
* ``approve_sermon_translation`` refused them outright ("that sermon is a
  public-domain original, not a translation"), so they could never be reviewed.

A non-English sermon that shares its slug with an English one *is* a translation
of it — that is the same (slug, language) convention Book uses. Relabel exactly
those, and only where they still carry the default: never downgrade a row an
approver already marked reviewed, and never touch a genuine non-English original
(which would have no English sibling).
"""

from django.db import migrations


def relabel_translations(apps, schema_editor):
    Sermon = apps.get_model("library", "Sermon")
    en_slugs = set(Sermon.objects.filter(language="en").values_list("slug", flat=True))
    if not en_slugs:
        return  # fresh DB: English sermons are seeded after migrate — no-op
    Sermon.objects.filter(source_type="public_domain", slug__in=en_slugs).exclude(
        language="en"
    ).update(source_type="ai_unreviewed")


class Migration(migrations.Migration):
    dependencies = [("library", "0035_sermon_source_type")]

    operations = [
        migrations.RunPython(relabel_translations, migrations.RunPython.noop),
    ]
