"""Run the pre-deploy / release steps in a single command.

Render's `preDeployCommand` runs one executable (not a shell), so we can't chain
`migrate && seed_if_empty` with `&&`. This command runs both in order: apply
migrations, then seed the library from the committed fixture if the DB is empty.
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Apply migrations, then seed the library if empty (deploy step)."

    def handle(self, *args, **opts):
        self.stdout.write("→ migrate")
        call_command("migrate", interactive=False, verbosity=1)
        self.stdout.write("→ seed_if_empty")
        call_command("seed_if_empty")
        # Fixture loads bypass Chapter.save(), so derive search text afterwards.
        self.stdout.write("→ backfill_body_text")
        call_command("backfill_body_text")
        # Idempotent text repairs (no-op when the fixture is already fixed).
        self.stdout.write("→ apply_body_corrections")
        call_command("apply_body_corrections")
        self.stdout.write("→ seed_plans")
        call_command("seed_plans")
        # Upsert fixture sermons into an already-seeded DB (new/updated ones).
        self.stdout.write("→ seed_sermons")
        call_command("seed_sermons")
