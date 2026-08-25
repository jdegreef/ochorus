"""Row-level security on the profile table and Django's own framework tables.

The library and reading migrations cover the app's content and per-user rows;
this one closes the rest of the public schema, which is exposed to the anon key
by the Supabase Data API exactly like the app's own tables are. Django's
framework tables are not exempt from that just because Django created them:

- `accounts_userprofile` holds every reader's email, Supabase UID and display
  name.
- `auth_user` holds Django's mirror of the same (usernames are Supabase UIDs)
  plus password hashes for any Django-admin account.
- `django_session` holds live session keys for the Django admin — readable
  session data is a session-hijacking path.
- `auth_permission`, `auth_group` and the three join tables decide who may do
  what in the Django admin; anon-writable, they are a privilege-escalation
  path.
- `django_migrations` is how Django decides which migrations have run. An
  inserted row makes a future deploy skip a migration silently.
- `django_admin_log` and `django_content_type` complete the schema.

Mechanism as in library/0043: RLS with no policies denies all non-owner access,
and Django connects as the table owner so it bypasses RLS (no FORCE).
Postgres-only; SQLite dev has no RLS concept.

The dependencies below are what guarantee each table exists before it is
altered — this migration touches tables owned by four contrib apps, so it must
be ordered after their initial migrations.
"""

from django.db import migrations

TABLES = (
    "accounts_userprofile",
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
    "django_admin_log",
    "django_content_type",
    "django_migrations",
    "django_session",
)


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_userprofile_tts_rate_userprofile_tts_voice_uri"),
        ("admin", "__first__"),
        ("auth", "__first__"),
        ("contenttypes", "__first__"),
        ("sessions", "__first__"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
