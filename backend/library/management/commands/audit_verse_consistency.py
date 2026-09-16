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
        parser.add_argument(
            "--absorb",
            action="store_true",
            help=(
                "With --update-baseline: allow the re-pin to LOOSEN — accept new "
                "conflicts, or extra renderings of pinned ones. Say in the commit "
                "message why they are not being reconciled."
            ),
        )

    def handle(self, *args, **opts):
        # Checked before the scan, and as a CommandError so the exit code is
        # non-zero — a guard that reports after doing the work, and returns 0,
        # is one CI reads as success.
        if opts["update_baseline"] and opts["language"]:
            raise CommandError("--update-baseline needs the whole corpus; drop --language.")
        if opts["absorb"] and not opts["update_baseline"]:
            raise CommandError("--absorb only means anything with --update-baseline.")

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
            counts = verse_consistency.baseline_counts(found)
            # A re-pin may TIGHTEN freely; loosening is a decision someone has to
            # make on purpose. Refused as a CommandError so the exit code is
            # non-zero and nothing is written — see baseline_regressions for what
            # a silent absorb cost us between August and September.
            loosened = verse_consistency.baseline_regressions(counts)
            if loosened and not opts["absorb"]:
                raise CommandError(
                    f"This re-pin would LOOSEN the ratchet on {len(loosened)} "
                    "reference(s):\n  "
                    + "\n  ".join(loosened)
                    + "\n\nReconcile them — match the wording the language already "
                    "uses (this command, with --language <lang>, prints every "
                    "rendering) — or, if they must ship as they are, re-run with "
                    "--absorb and say in the commit message why."
                )
            verse_consistency.write_baseline(counts)
            if loosened:
                self.stdout.write(
                    self.style.WARNING(
                        f"\nAbsorbed {len(loosened)} new/widened conflict(s) into the pin."
                    )
                )
            self.stdout.write(
                self.style.SUCCESS(f"\nBaseline written to {verse_consistency.BASELINE_PATH.name}.")
            )
