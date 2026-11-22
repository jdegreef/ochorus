from django.db import migrations


class Migration(migrations.Migration):
    """Join the two 0224 leaves that landed on main in parallel."""

    dependencies = [
        ("library", "0224_author_start_with"),
        ("library", "0224_confirm_stale_book_translations_1"),
    ]

    operations = []
