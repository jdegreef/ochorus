"""SeriesTranslation: a series' name in each language, shipped in series.json.

Schema only (seed_books upserts the rows), plus RLS on the new table for the
reason every table has it (see 0160_series and accounts/tests_rls).
"""

import django.db.models.deletion
from django.db import migrations, models


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_seriestranslation ENABLE ROW LEVEL SECURITY")


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_seriestranslation DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0160_series'),
    ]

    operations = [
        migrations.CreateModel(
            name='SeriesTranslation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(max_length=10)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('series', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='library.series')),
            ],
            options={
                'ordering': ['series', 'language'],
                'constraints': [models.UniqueConstraint(fields=('series', 'language'), name='uniq_series_translation')],
            },
        ),
        migrations.RunPython(enable_rls, disable_rls),
    ]
