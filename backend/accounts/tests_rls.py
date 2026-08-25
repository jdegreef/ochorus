"""Row-level security must cover the whole public schema — enforced, not remembered.

The Supabase Data API exposes the ``public`` schema to the anon key, which ships
in the reader's bundle, and RLS with no policies is what denies it
(backend/CLAUDE.md: "one reachable by the anon key without RLS is a data leak").
Six tables got a careful per-table RLS migration each; nineteen did not, because
nothing checked. The per-table migrations were guarded only by whoever
remembered the rule while adding a model.

This is that check. It reads the live catalogue of the test database — which is
built by running every migration — so it asserts what the database actually
looks like after a deploy, not what a list in a migration file claims.

Add a model and forget the RLS migration, and this fails with the exact ALTER
statement to write. That is the whole point: the next person does not have to
have read this file, or CLAUDE.md, or know Supabase's exposure model.

Postgres-only. SQLite has no RLS concept, so the dev run skips this and CI's
Postgres pass is what gates the merge.
"""

from __future__ import annotations

from unittest import skipUnless

from django.db import connection
from django.test import TestCase

# Roles the Supabase Data API authenticates its callers as. `service_role` is
# deliberately absent: it is a server-side secret, carries BYPASSRLS by design,
# and revoking from it would break Supabase internals rather than close a hole.
DATA_API_ROLES = ("anon", "authenticated")


def _public_tables_without_rls() -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND NOT c.relrowsecurity
            ORDER BY c.relname
            """
        )
        return [row[0] for row in cursor.fetchall()]


def _existing_roles() -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)",
            [list(DATA_API_ROLES)],
        )
        return [row[0] for row in cursor.fetchall()]


@skipUnless(connection.vendor == "postgresql", "RLS is a Postgres feature")
class RowLevelSecurityCoverageTests(TestCase):
    def test_every_public_table_has_row_level_security_enabled(self):
        missing = _public_tables_without_rls()
        self.assertEqual(
            missing,
            [],
            "These tables are reachable through the Supabase Data API with the "
            "anon key and nothing gates them:\n  "
            + "\n  ".join(missing)
            + "\n\nAdd a migration in the owning app enabling RLS on each, "
            "following accounts/0003_rls_core_tables.py:\n  "
            + "\n  ".join(
                f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY" for t in missing
            )
            + "\n\nRLS with no policies denies all non-owner access. Django "
            "connects as the table owner and bypasses it, so the app is "
            "unaffected.",
        )

    def test_every_model_table_has_row_level_security_enabled(self):
        """The catalogue check above, stated against the models it protects.

        Same underlying assertion, but it names the *model* whose table is
        exposed. A schema-level failure sends you looking through pg_class; this
        one hands you the app and class to write the migration for.
        """
        from django.apps import apps

        unprotected = set(_public_tables_without_rls())
        offenders = sorted(
            f"{model._meta.app_label}.{model.__name__} ({model._meta.db_table})"
            for model in apps.get_models()
            if model._meta.db_table in unprotected
        )
        self.assertEqual(
            offenders,
            [],
            "These models' tables have no row-level security:\n  "
            + "\n  ".join(offenders),
        )


@skipUnless(connection.vendor == "postgresql", "Postgres role catalogue")
class DataApiGrantTests(TestCase):
    """The second lock: the Data API roles hold no privileges on public.

    RLS gates the rows; this gates the reach. Skips on a plain Postgres (CI,
    and any non-Supabase deployment) where the roles do not exist — there it
    would assert nothing, and a vacuous pass is worse than an honest skip.
    """

    def test_data_api_roles_have_no_table_privileges(self):
        roles = _existing_roles()
        if not roles:
            self.skipTest("no Supabase Data API roles on this database")

        # Read the ACL straight out of the catalogue rather than through
        # information_schema.role_table_grants: that view only reports grants
        # whose grantor or grantee is a *currently enabled* role, so it can
        # return nothing for `anon` simply because the test connection is not a
        # member of it — a false pass on exactly the check that matters. A NULL
        # relacl means default privileges (owner only), which is the state we
        # want, and aclexplode yields no rows for it.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pg_get_userbyid(a.grantee) AS grantee,
                       c.relname,
                       a.privilege_type
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                CROSS JOIN LATERAL aclexplode(c.relacl) AS a
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND pg_get_userbyid(a.grantee) = ANY(%s)
                ORDER BY grantee, c.relname, a.privilege_type
                """,
                [roles],
            )
            grants = cursor.fetchall()

        self.assertEqual(
            grants,
            [],
            "The Supabase Data API roles still hold privileges on public "
            "tables:\n  "
            + "\n  ".join(f"{g} has {p} on {t}" for g, t, p in grants)
            + "\n\nSee accounts/0004_revoke_anon_public_schema.py.",
        )
