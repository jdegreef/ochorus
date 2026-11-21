"""Write the production-only facts a reader build needs (library/build_facts.py).

Run against PRODUCTION (its DATABASE_URL) to produce the file the web build's
local-API mode lays over a DB seeded from the repo:

    manage.py export_build_facts --out build-facts.json

Read-only: it runs SELECTs and writes nothing to the database. See
docs/build-without-prod-api.md.
"""

from __future__ import annotations

import json
import sys

from django.core.management.base import BaseCommand

from library.build_facts import export_facts


class Command(BaseCommand):
    help = "Export the DB-owned facts the reader build needs (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--out", help="File to write; stdout when omitted.")

    def handle(self, *args, **opts):
        facts = export_facts()
        text = json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if opts.get("out"):
            with open(opts["out"], "w", encoding="utf-8") as fh:
                fh.write(text)
            counts = ", ".join(
                f"{k} {len(v)}" for k, v in sorted(facts.items()) if isinstance(v, list)
            )
            self.stderr.write(f"✓ build facts → {opts['out']} ({counts})")
        else:
            sys.stdout.write(text + "\n")
