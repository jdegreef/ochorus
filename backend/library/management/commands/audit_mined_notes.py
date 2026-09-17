"""Check every `mined` claim against the file it cites.

    manage.py audit_mined_notes              # census + any contradicted claims
    manage.py audit_mined_notes --json out.json

The review queue turns these rows into "N verses checked", and a reviewer skips
what it says is checked — so a `mined` row that isn't verbatim hides work rather
than doing it. ``library/mined_verification`` explains what is and is not
checkable; the census this prints is half the answer, because most mined rows
cite a Bible edition rather than a file and cannot be tested from the repo.

Reads the committed fixtures, not the database — the fixture is what ships, so a
drifted local DB cannot make this lie. Same shape as ``audit_english`` and
``audit_verse_consistency`` on purpose.

The CI gate lives in ``library.tests_mined_verification``; this command is the
human view of the same audit.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from library import mined_verification


class Command(BaseCommand):
    help = "Verify that every `mined` scripture note matches the file it cites."

    def add_arguments(self, parser):
        parser.add_argument("--json", dest="json_out", help="Write findings to this path.")

    def handle(self, *args, **opts):
        findings, census = mined_verification.audit()

        self.stdout.write(mined_verification.format_census(census))

        if findings:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(f"{len(findings)} contradicted claim(s):")
            )
            for f in findings:
                self.stdout.write(f"  {f}")
        else:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("No contradicted claims."))

        if opts["json_out"]:
            Path(opts["json_out"]).write_text(
                json.dumps(
                    {
                        "census": dict(census),
                        "findings": [
                            {
                                "notes_file": f.notes_file,
                                "reference": f.reference,
                                "source_file": f.source_file,
                                "translation": f.translation,
                                "source": f.source,
                            }
                            for f in findings
                        ],
                    },
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )
