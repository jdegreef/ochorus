"""Clean scraped site-footer noise out of the Pulse of Life EN description.

The imported description carried WordPress boilerplate ("Back Ochorus ‍We
identify great Christian books… Explore About Us Books Biographies Contact")
after the genuine text. Guarded no-op when the book isn't present (fresh
installs seed from the already-clean fixture after migrate).
"""

from django.db import migrations

CLEAN = (
    "“Prayer – The Pulse of Life” is a book designed to offer deeper insights "
    "into the subject of prayer. While many are familiar with prayer, they "
    "often understand it in a worldly way, which is incorrect. This book draws "
    "insights from Scripture to deepen your understanding of prayer, enhance "
    "your spiritual growth, and position you for resounding success day by "
    "day, year by year. Contents: An Introduction to Prayer — Importance of "
    "Prayer — Types of Prayer — Praying With and in the Spirit — Cultivating "
    "the Spirit of Prayer — Prayer and Fasting — The First Fruit of Time — "
    "His Return — A Call to the Word — Testimonials — Prayer of Salvation."
)


def apply(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(
        slug="prayer-the-pulse-of-life",
        language="en",
        description__contains="Explore About Us",
    ).update(description=CLEAN)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0028_book_attribution_book_publication_year"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
