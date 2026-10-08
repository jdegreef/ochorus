"""Scene illustrations for four authors whose real photographs we can't yet fetch.

Jim Elliot, Elisabeth Elliot, Blasio Kigozi and Yona Kanamuzeyi were all
photographed, so an invented face would contradict the likeness readers can
find. Until the real photographs are sourced (the session network blocks
Wikimedia), each page wears a faceless scene in the black-and-white firelight
style: a figure seen from behind in a setting from the story — the beach on
the Curaray with the Piper, a desk by lamplight, dawn over Lake Muhazi from
Gahini hill, a lit church doorway at night. Credited "a scene, not a
likeness" so it never reads as a portrait. Replacing one with a real photo
later is an ordinary photo_url data migration (see write-biography).

Same mechanism as 0187 / 0197: ``author_sync`` fill-syncs ``photo_url`` but
NOT the credit fields, so the credit is set here for the seeded prod rows (a
fresh DB gets it from ``authors.json``). Only a blank ``photo_url`` — or this
image still missing its credit — is touched. Idempotent.
"""

from django.db import migrations

SLUGS = ("jim-elliot", "elisabeth-elliot", "blasio-kigozi", "yona-kanamuzeyi")
ATTRIBUTION = "Illustration by Ochorus (a scene, not a likeness)"


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
        ("library", "0197_imagined_portraits"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
