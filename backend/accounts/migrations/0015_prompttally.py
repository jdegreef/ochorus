from django.db import migrations, models


def enable_rls(apps, schema_editor):
    # An analytics table only Django touches: RLS with no policies denies the
    # Supabase anon/authenticated roles; Django owns the table and bypasses it.
    # Postgres-only (SQLite dev has no RLS). See backend/CLAUDE.md.
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE accounts_prompttally ENABLE ROW LEVEL SECURITY")


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE accounts_prompttally DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0014_userprofile_palette"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromptTally",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day", models.DateField()),
                ("source", models.CharField(max_length=32)),
                (
                    "kind",
                    models.CharField(choices=[("seen", "Seen"), ("started", "Started")], max_length=10),
                ),
                ("count", models.PositiveIntegerField(default=0)),
            ],
            options={
                "indexes": [models.Index(fields=["day"], name="prompttally_day_idx")],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("day", "source", "kind"), name="uniq_prompttally_day_source_kind"
                    )
                ],
            },
        ),
        migrations.RunPython(enable_rls, disable_rls),
    ]
