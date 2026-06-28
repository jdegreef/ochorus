"""Load the launch library fixture, but only if the library is empty.

Run on every deploy (after `migrate`); it populates a fresh production database
on first boot and is a no-op thereafter. Idempotent and safe to re-run.
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand

from library.models import Book


class Command(BaseCommand):
    help = "Seed the library from fixtures/launch.json if no books exist yet."

    def handle(self, *args, **opts):
        if Book.objects.exists():
            self.stdout.write("Library already populated; skipping seed.")
            return
        self.stdout.write("Empty library — loading launch fixture…")
        call_command("loaddata", "launch", verbosity=1)
        self.stdout.write(self.style.SUCCESS(f"Seeded {Book.objects.count()} books."))
