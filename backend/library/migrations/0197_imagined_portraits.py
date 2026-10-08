"""Portraits for three authors with no surviving likeness.

No portrait of Julian of Norwich, Maria W. Stewart or Zilpha Elaw is known to
exist, so their pages wore initials. Ochorus drew each one in the black-and-white
firelight style the founder chose for Brother Lawrence (0195): Julian as an
anchoress in veil and wimple by her cell window, Stewart in a dark dress with a
white collar, Elaw in a Methodist preacher's plain cap and white kerchief. Each
is credited as an imagined likeness so the page never passes it off as a
portrait from life.

Same mechanism as 0187 / 0195: ``author_sync`` fill-syncs ``photo_url`` but NOT
the credit fields, so the credit must be set here to reach the already-seeded
prod DB (a fresh DB gets it from ``authors.json``). Only a blank ``photo_url``
— or this portrait still missing its credit — is touched. Idempotent.
"""

from django.db import migrations

SLUGS = ("julian-of-norwich", "maria-w-stewart", "zilpha-elaw")
ATTRIBUTION = "Illustration by Ochorus (an imagined likeness)"


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug in SLUGS:
        photo_url = f"/portraits/{slug}.jpg"
        Author.objects.filter(slug=slug, photo_url="").update(
            photo_url=photo_url, photo_attribution=ATTRIBUTION, photo_source_url=""
        )
        # A deploy may already have filled photo_url without the credit.
        Author.objects.filter(
            slug=slug, photo_url=photo_url, photo_attribution=""
        ).update(photo_attribution=ATTRIBUTION)


def unapply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug in SLUGS:
        Author.objects.filter(slug=slug, photo_url=f"/portraits/{slug}.jpg").update(
            photo_url="", photo_attribution="", photo_source_url=""
        )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0196_merge_0195_book_hook_0195_brother_lawrence_portrait"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
