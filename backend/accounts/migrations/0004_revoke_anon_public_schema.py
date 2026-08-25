"""Revoke the anon / authenticated grants on the public schema.

RLS (0003 and its library/reading siblings) is the gate; this is the second
lock, and the one that makes the guarantee survive us. The RLS migrations close
the tables that exist today, but a new model ships a new table, and a table
born without RLS is open again — that is exactly how nineteen tables came to be
uncovered while six were carefully handled. Revoking the schema-level grants
from `anon` and `authenticated`, and revoking them from the DEFAULT PRIVILEGES
of the role Django creates tables as, means a table added tomorrow is closed
before anyone writes a migration for it.

Nothing in the product reads the database through those roles: the reader's
Supabase client is used only for `auth` (no PostgREST `.from()`, no `.rpc()`,
no realtime, no storage), and every byte of content reaches the reader through
the Django API, which connects as the table owner. So this is invisible to the
application and removes the Data API as an access path entirely.

Scope notes:
- TABLES and SEQUENCES only. FUNCTIONS are deliberately left alone: extensions
  installed into `public` expose functions there, and revoking EXECUTE broadly
  risks breaking Supabase internals for no gain — RLS already gates the data.
- Guarded on role existence, so this is a no-op on a plain Postgres (CI) and on
  any non-Supabase deployment.
- REVOKE clears the privileges *this* role granted. Anything granted by another
  role with grant option (some Supabase bootstrap runs as `supabase_admin`) can
  survive, which is why RLS above is the control and this is the second lock,
  not the first. accounts/tests_rls.py reports any survivors when the suite is
  pointed at a real Supabase database.
- ALTER DEFAULT PRIVILEGES applies to objects created by the current role,
  which is the role Django creates tables as — precisely the set we want.

Reverse is a deliberate no-op: the original Supabase grants are not knowable
from here, and a rollback of some unrelated later migration must not silently
re-open the schema to the anon key. Re-grant by hand if it is ever genuinely
wanted.
"""

from django.db import migrations

ROLES = ("anon", "authenticated")


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    # Which of the Data API roles this database actually has. Filtering our own
    # constant against pg_roles keeps the identifiers below ours, not the
    # database's — and REVOKE on a role that does not exist is a hard error, so
    # this is what makes the migration a no-op on plain Postgres.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", [list(ROLES)]
        )
        present = [row[0] for row in cursor.fetchall()]

    for role in present:
        schema_editor.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
        schema_editor.execute(
            f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role}"
        )
        schema_editor.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {role}"
        )
        schema_editor.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"REVOKE ALL ON SEQUENCES FROM {role}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_rls_core_tables"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
