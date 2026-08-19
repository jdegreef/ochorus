"""Record the Language bible fields' current state — no schema change.

0072 added `bible_licence`/`bible_attribution` carrying `default=""`, which the
model itself doesn't declare. Django therefore saw permanent drift and
`makemigrations --check` (a CI gate) failed on every branch until someone wrote
this down. Purely bookkeeping: a CharField default lives in application code,
not in the column, so this alters nothing in the database.

Unrelated to the content removal in 0073 — it simply came due, and CI cannot go
green while it is outstanding.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0073_remove_how_to_manage_a_library"),
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
