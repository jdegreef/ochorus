"""Scan the English corpus for import defects, and ratchet the baseline.

Replaces `scripts/audit_english.py`, which hardcoded an absolute path (so it ran
nowhere but one laptop) and which nothing invoked. The checks themselves live in
`library.english_audit` so every importer can run the same code on one freshly
written work.

    manage.py audit_english                        # whole English corpus
    manage.py audit_english humility-2             # one work
    manage.py audit_english --class anachronism    # one class, all of it
    manage.py audit_english --json out.json        # machine-readable
    manage.py audit_english --update-baseline      # after fixing things

Reads the committed fixture, not the database: the fixture is what ships, what a
fresh build loads, and what the CI ratchet in `tests_english_audit.py` measures
— so a local database that has drifted cannot make this lie.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from library import english_audit


class Command(BaseCommand):
    help = "Scan the English fixture for import-defect classes."

    def add_arguments(self, parser):
        # Positional, like every other slug-taking command in this directory
        # (import_ochorus, import_ccel, translate_author, …).
        parser.add_argument("slugs", nargs="*", help="Book/sermon slugs (default: all).")
        parser.add_argument("--class", dest="klass", help="Only this finding class.")
        # NOT --limit: import_ochorus already uses that name for "only the first
        # N books", and the same flag meaning different things in one app is how
        # you get a script that silently does the wrong thing.
        parser.add_argument(
            "--examples", type=int, default=8, help="Examples per class (0 = all)."
        )
        parser.add_argument("--json", dest="json_out", help="Write findings to this path.")
        parser.add_argument(
            "--update-baseline",
            action="store_true",
            help="Rewrite the CI ratchet baseline from this run (whole corpus only).",
        )

    def handle(self, *args, **opts):
        # Checked before the 5s scan, and as a CommandError so the exit code is
        # non-zero — a guard that reports after doing all the work, and returns
        # 0, is one CI will read as success.
        if opts["update_baseline"] and opts["slugs"]:
            raise CommandError("--update-baseline needs the whole corpus; drop the slug.")

        findings = []
        for slug in opts["slugs"] or [None]:
            findings.extend(english_audit.audit_fixtures(slug))
        self.stdout.write(
            english_audit.format_report(findings, opts["examples"], opts["klass"])
        )

        if opts["json_out"]:
            Path(opts["json_out"]).write_text(
                json.dumps(
                    [
                        {
                            "class": f.label,
                            "where": f.where,
                            "work": f.work,
                            "block": f.block,
                            "excerpt": f.excerpt,
                        }
                        for f in findings
                    ],
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )

        if opts["update_baseline"]:
            english_audit.write_baseline(english_audit.counts_by_work(findings))
            self.stdout.write(
                self.style.SUCCESS(f"\nBaseline written to {english_audit.BASELINE_PATH.name}.")
            )
