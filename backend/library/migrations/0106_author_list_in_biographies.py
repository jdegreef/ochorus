"""Let a real person be kept off the Biographies shelf while their work stays.

The Biographies page lists an author who has books even without a bio (so a
writer like R. A. Torrey isn't invisible). That rule means clearing a bio does
NOT remove a contributor who has a book — their card simply loses its blurb and
stays on the shelf. `is_imprint` can't express "hide this one" either: it asserts
the byline is not a person (dropping their schema.org Person markup and
`same_as`), which is false for a real contributor.

So this adds `list_in_biographies` (default True — everyone stays listed) and
flags Hannah Buyinza off it at the owner's request. Her book,
Prayer – The Pulse of Life, stays on /books and her own author page stays
reachable; she just no longer appears on the Biographies shelf.

Same shape and guards as `0037_author_is_imprint`: the field ships in the fixture
too (a fresh DB is loaded from it AFTER migrate runs), and the flip is scoped to
one slug so re-runs are no-ops.
"""

from django.db import migrations, models

WITHHELD_SLUGS = ["hannah-buyinza"]


def withhold(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=WITHHELD_SLUGS).update(list_in_biographies=False)


def relist(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=WITHHELD_SLUGS).update(list_in_biographies=True)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0105_remove_hannah_buyinza_bio"),
    ]

    operations = [
        migrations.AddField(
            model_name="author",
            name="list_in_biographies",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(withhold, relist),
    ]
