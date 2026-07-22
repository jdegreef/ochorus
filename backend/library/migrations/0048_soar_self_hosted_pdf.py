"""Point "Soar Like the Eagle" at the app's own copy of its PDF.

The download link pointed at ochorus.com's WordPress media. The author
supplied a reformatted PDF, which now ships with the frontend
(frontend/static/pdfs/soar-like-the-eagle.pdf) and is served from Ochorus
itself — so the file we control is the file readers get.

Seeds never update an existing book row, so the fixture change alone would
only reach fresh installs; this carries it to production. Idempotent: it
matches on the old external URL, so a re-run (or a row already switched) is
a no-op.
"""

from django.db import migrations

OLD_URL = "https://ochorus.com/wp-content/uploads/2025/08/Soar-Like-the-Eagle.pdf"
NEW_URL = "/pdfs/soar-like-the-eagle.pdf"


def forwards(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug="soar-like-the-eagle-3", pdf_url=OLD_URL).update(
        pdf_url=NEW_URL
    )


def backwards(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug="soar-like-the-eagle-3", pdf_url=NEW_URL).update(
        pdf_url=OLD_URL
    )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0047_sermon_summary"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
