"""Drop the one-off ``default=""`` these two fields carry in migration state.

0072 added ``Language.bible_licence`` and ``bible_attribution`` with
``default=""`` so the AddField had something to backfill existing rows with,
but the model declares no default and the migration does not pass
``preserve_default=False``. So the recorded state and models.py disagree, and
``makemigrations --check`` — a required CI step — fails on every branch cut
from main, including ones that touch neither the model nor migrations.

State-only in practice: Django does not put a CharField default in the DB, so
this alters no column. Written as a new migration rather than a repair to 0072,
which has already deployed (backend/CLAUDE.md: migrations are immutable once
they have run against prod).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0072_language_bible_licence"),
    ]

    operations = [
        migrations.AlterField(
            model_name="language",
            name="bible_attribution",
            field=models.CharField(
                blank=True, help_text="Credit line shown to readers.", max_length=300
            ),
        ),
        migrations.AlterField(
            model_name="language",
            name="bible_licence",
            field=models.CharField(
                blank=True, help_text="Blank for a public-domain text.", max_length=60
            ),
        ),
    ]
