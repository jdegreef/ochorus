"""Clean the scraped-junk description on Jesus Himself (en).

The source site's nav text ("Contents … Explore About Us Books Biographies
Contact") had been scraped into the book description; this trims it back to
the real blurb. The es/sw/lg pilot translations shipping in the same PR are
NEW (slug, language) fixture rows, so they arrive via the ``seed_books``
release step — per the ship-content-fix convention, only this existing-row
transform needs a migration.
"""

from django.db import migrations

DESCRIPTION = (
    "“Jesus Himself” is an enlightening exploration of Christian "
    "life through the Gospel of Luke. The book reveals the disciples’ "
    "transformation, from doubt to unwavering faith, emphasizing the need to "
    "conquer unbelief for a profound connection with Jesus. Filled with "
    "spiritual wisdom, it guides readers towards a satisfying relationship "
    "with their Savior, making Jesus their eternal companion."
)


def apply(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug="jesus-himself-2", language="en").update(
        description=DESCRIPTION
    )


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0018_moody_snippet_simpson"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
