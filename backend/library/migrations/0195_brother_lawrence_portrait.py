"""Brother Lawrence's portrait: a black-and-white firelight illustration.

No usable likeness of Nicolas Herman could be sourced, so Ochorus made one — a
Discalced Carmelite lay brother, bald with a short grey beard, eyes lowered, lit
from the side by the friary kitchen fire (chosen by the founder from fifteen
styles). It is credited as an imagined likeness so the page never passes it
off as a portrait from life.

Same mechanism as 0187: ``author_sync`` fill-syncs ``photo_url`` but NOT the
credit fields, so the credit must be set here to reach the already-seeded prod
DB (a fresh DB gets it from ``authors.json``). Only a blank ``photo_url`` is
touched, so a portrait set in the admin since is left alone. Idempotent.
"""

from django.db import migrations

SLUG = "brother-lawrence"
PHOTO_URL = f"/portraits/{SLUG}.jpg"
ATTRIBUTION = "Illustration by Ochorus (an imagined likeness)"


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug=SLUG, photo_url="").update(
        photo_url=PHOTO_URL, photo_attribution=ATTRIBUTION, photo_source_url=""
    )
    # A deploy may already have filled photo_url without the credit.
    Author.objects.filter(slug=SLUG, photo_url=PHOTO_URL, photo_attribution="").update(
        photo_attribution=ATTRIBUTION
    )


def unapply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug=SLUG, photo_url=PHOTO_URL).update(
        photo_url="", photo_attribution="", photo_source_url=""
    )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0194_bookperson_chapter"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
