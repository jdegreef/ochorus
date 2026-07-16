"""Mark house bylines so the Biographies shelf stays a shelf of people.

The Biographies page lists an author who has books even without a bio yet (so a
writer like R. A. Torrey isn't invisible). That rule would also admit
"Ochorus Originals" — the byline on the compiled anthologies — and the page
emits a schema.org ItemList of `Person`, so an imprint on it would assert to
search engines that a byline is a human. Flag it instead; its books stay
reachable from /books and its own author page.
"""

from django.db import migrations, models

IMPRINT_SLUGS = ["ochorus-originals"]


def flag_imprints(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=IMPRINT_SLUGS).update(is_imprint=True)


def unflag_imprints(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=IMPRINT_SLUGS).update(is_imprint=False)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0036_relabel_translated_sermons"),
    ]

    operations = [
        migrations.AddField(
            model_name="author",
            name="is_imprint",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(flag_imprints, unflag_imprints),
    ]
