"""Lay production's DB-owned facts over a DB seeded from the repo.

    manage.py apply_build_facts build-facts.json [--max-missing N]

For the web build's local-API mode only (docs/build-without-prod-api.md): it
runs after ``release`` against the build's throwaway SQLite database. Refuses to
run against anything but SQLite, so it can never be pointed at production.

Fails when more than ``--max-missing`` rows named by the facts are absent here
(default 25): those are works production has and the repo does not — an admin
upload that never reached the fixture — and a build without them would drop
their pages from the site.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from library.build_facts import apply_facts


def _is_build_db() -> bool:
    """The build's DB is SQLite; production (and anything shared) is Postgres."""
    return connection.vendor == "sqlite"


class Command(BaseCommand):
    help = "Apply exported production facts to the build's local DB."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--max-missing", type=int, default=25)

    def handle(self, *args, **opts):
        if not _is_build_db():
            raise CommandError(
                "apply_build_facts only runs against the build's throwaway SQLite DB "
                f"(this one is {connection.vendor})."
            )
        try:
            with open(opts["path"], encoding="utf-8") as fh:
                facts = json.load(fh)
        except (OSError, ValueError) as e:
            raise CommandError(f"could not read build facts: {e}") from e
        try:
            report = apply_facts(facts)
        except ValueError as e:
            raise CommandError(f"build facts rejected: {e}") from e

        langs = report["languages"]
        self.stdout.write(f"• live languages: {', '.join(langs['live'])}")
        if langs["created"]:
            self.stdout.write(f"• admin-added languages: {', '.join(langs['created'])}")
        if langs["darkened"]:
            self.stdout.write(f"• not live in production yet: {', '.join(langs['darkened'])}")
        for label, n in sorted(report["changed"].items()):
            self.stdout.write(f"• {label}: {n} row(s) set from production")
        missing = report["missing"]
        total = sum(len(v) for v in missing.values())
        for label, keys in sorted(missing.items()):
            shown = ", ".join(keys[:10]) + (" …" if len(keys) > 10 else "")
            self.stdout.write(f"! production-only {label} ({len(keys)}): {shown}")
        if total > opts["max_missing"]:
            raise CommandError(
                f"{total} rows production has are missing from this checkout "
                f"(limit {opts['max_missing']}). Their pages would vanish from the "
                "site: land them in the fixture, or raise --max-missing knowingly."
            )
