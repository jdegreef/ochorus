"""Report references a language renders more than one way, and pin the ratchet.

    manage.py audit_verse_consistency                      # whole corpus
    manage.py audit_verse_consistency --language lg        # one language
    manage.py audit_verse_consistency --json out.json      # machine-readable
    manage.py audit_verse_consistency --update-baseline    # after reconciling

Reads the committed fixture, not the database — the fixture is what ships and
what the CI ratchet measures, so a drifted local DB cannot make this lie. Same
reasoning as `audit_english`, and the same shape on purpose.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from library import verse_consistency


class Command(BaseCommand):
    help = "Find verses a language quotes inconsistently across works."

    def add_arguments(self, parser):
        parser.add_argument("--language", help="Only this language code.")
        parser.add_argument("--json", dest="json_out", help="Write findings to this path.")
        parser.add_argument(
            "--update-baseline",
            action="store_true",
            help="Re-pin the CI ratchet from this run (whole corpus only).",
        )

    def handle(self, *args, **opts):
        # Checked before the scan, and as a CommandError so the exit code is
        # non-zero — a guard that reports after doing the work, and returns 0,
        # is one CI reads as success.
        if opts["update_baseline"] and opts["language"]:
            raise CommandError("--update-baseline needs the whole corpus; drop --language.")

        found = verse_consistency.conflicts()
        self.stdout.write(verse_consistency.format_report(found, opts["language"]))

        if opts["json_out"]:
            Path(opts["json_out"]).write_text(
                json.dumps(
                    [
                        {
                            "language": lang,
                            "reference": ref,
                            "renderings": [
                                {"text": r.text, "where": r.where} for r in renderings
                            ],
                        }
                        for (lang, ref), renderings in sorted(found.items())
                    ],
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )

        if opts["update_baseline"]:
            verse_consistency.write_baseline(verse_consistency.baseline_counts(found))
            self.stdout.write(
                self.style.SUCCESS(f"\nBaseline written to {verse_consistency.BASELINE_PATH.name}.")
            )
