"""Portrait for Gareth Evans — supplied by the user (his own photo), converted
to black-and-white and self-hosted like the other author portraits. Idempotent."""

from django.db import migrations


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug="gareth-evans").update(
        photo_url="/portraits/gareth-evans.jpg"
    )


def revert(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug="gareth-evans").update(photo_url="")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0015_author_portraits"),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
