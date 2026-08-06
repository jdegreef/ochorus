"""Scan the English corpus for import defects, and ratchet the baseline.

Replaces `scripts/audit_english.py`, which hardcoded an absolute path and could
only ever be run by hand. The checks themselves live in `library.english_audit`
so `import_ochorus` can run the same code on one freshly-imported book.

    manage.py audit_english                        # whole English corpus
    manage.py audit_english --slug humility-2      # one work
    manage.py audit_english --class anachronism    # one class, all of it
    manage.py audit_english --json out.json        # machine-readable
    manage.py audit_english --update-baseline      # after fixing things

Reads the committed fixture, not the database: the fixture is what ships, what
a fresh build loads, and what the CI ratchet in `tests_english_audit.py`
measures — so a local database that has drifted cannot make this lie.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from library import english_audit
from library.english_audit import BASELINE_PATH


class Command(BaseCommand):
    help = "Scan the English fixture for import-defect classes."

    def add_arguments(self, parser):
        parser.add_argument("--slug", help="Only this book/sermon slug.")
        parser.add_argument("--class", dest="klass", help="Only this finding class.")
        parser.add_argument(
            "--limit", type=int, default=8, help="Examples per class (0 = all)."
        )
        parser.add_argument("--json", dest="json_out", help="Write findings to this path.")
        parser.add_argument(
            "--update-baseline",
            action="store_true",
            help="Rewrite the CI ratchet baseline from this run (whole corpus only).",
        )

    def handle(self, *args, **opts):
        findings = english_audit.audit_fixtures(opts["slug"])
        self.stdout.write(
            english_audit.format_report(findings, opts["limit"], opts["klass"])
        )

        if opts["json_out"]:
            Path(opts["json_out"]).write_text(
                json.dumps(
                    [
                        {"class": f.label, "where": f.where, "block": f.block, "excerpt": f.excerpt}
                        for f in findings
                    ],
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )

        if opts["update_baseline"]:
            if opts["slug"]:
                self.stderr.write(
                    self.style.ERROR(
                        "--update-baseline needs the whole corpus; drop --slug."
                    )
                )
                return
            english_audit.write_baseline(english_audit.counts(findings))
            self.stdout.write(
                self.style.SUCCESS(f"\nBaseline written to {BASELINE_PATH.name}.")
            )
