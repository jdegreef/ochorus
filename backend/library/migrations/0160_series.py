"""Series: a named run of separate works (Brave for God, Rooted, Key Teachings).

Schema only. The rows and each book's membership live in the fixture
(`content/series.json`, and `series` / `series_position` on the book rows):
seed_if_empty loads them on a fresh DB and seed_books upserts them on every
deploy, so there is no data step here to fall out of step with the fixture.

RLS on the new table for the reason every table has it (see 0113_topicarticle_rls
and accounts/tests_rls). Postgres-only; SQLite dev has no RLS concept.
"""

import django.db.models.deletion
from django.db import migrations, models


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_series ENABLE ROW LEVEL SECURITY")


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE library_series DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0159_fix_all_of_grace_lg_drink'),
    ]

    operations = [
        migrations.CreateModel(
            name='Series',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=160, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'series',
                'ordering': ['sort_order', 'title'],
            },
        ),
        migrations.AddField(
            model_name='book',
            name='series_position',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='book',
            name='series',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='books', to='library.series'),
        ),
        migrations.AddConstraint(
            model_name='book',
            constraint=models.UniqueConstraint(deferrable=models.Deferrable['DEFERRED'], fields=('series', 'language', 'series_position'), name='uniq_book_series_volume'),
        ),
        migrations.AddConstraint(
            model_name='book',
            constraint=models.CheckConstraint(condition=models.Q(('series_position__isnull', True), models.Q(('series__isnull', False), ('series_position__gte', 1)), _connector='OR'), name='book_series_position_needs_series'),
        ),
        migrations.RunPython(enable_rls, disable_rls),
    ]
