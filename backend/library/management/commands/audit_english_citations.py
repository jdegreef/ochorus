"""Report Scripture citations in the English editions that don't match their quotation.

    manage.py audit_english_citations                    # every English edition
    manage.py audit_english_citations humility-2         # one work (all its editions)
    manage.py audit_english_citations --tier modern      # only the Modern English editions
    manage.py audit_english_citations --json out.json    # machine-readable, for a fix pass

Read-only. The engine and the reasoning are in `library/english_citations.py`.
Findings are grouped by who owns the mistake: a `pd` original's miscitation is
the author's text and is reported only (see the `english-qa` skill); a `modern`
or `house` finding marked FIX is unambiguous and ours to correct — edit the
citation in that edition's fixture file. Translated editions are never read:
fix the English, and let a propagation pass carry it.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from library import english_citations as ec


class Command(BaseCommand):
    help = "Report English Scripture citations that don't match the words they quote."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Limit to these works.")
        parser.add_argument(
            "--tier", choices=("pd", "modern", "house"), help="Only this provenance."
        )
        parser.add_argument(
            "--fixable",
            action="store_true",
            help="Only the unambiguous, ours-to-fix findings.",
        )
        parser.add_argument(
            "--json",
            dest="json_path",
            help="Also write every finding to this JSON file.",
        )

    def handle(self, *args, **opts):
        if opts["slugs"]:
            known = {r.work for r in ec.records(opts["slugs"])}
            if missing := sorted(set(opts["slugs"]) - known):
                raise CommandError(f"No English edition of: {', '.join(missing)}")
        pairs, findings = ec.audit(opts["slugs"], opts["tier"])
        if opts["fixable"]:
            findings = [f for f in findings if f.fixable]

        by_work: dict[str, list[ec.Finding]] = {}
        for f in findings:
            by_work.setdefault(
                f"{f.record.work} [{f.record.language}, {f.record.tier}]", []
            ).append(f)
        for work in sorted(by_work):
            self.stdout.write(self.style.WARNING(f"\n{work}"))
            for f in by_work[work]:
                mark = "FIX " if f.fixable else "    "
                if f.kind == "book-spelling":
                    self.stdout.write(
                        f"  {mark}{f.record.where}: book name “{f.printed}” → {f.suggestion} {' '.join(f.notes)}"
                    )
                    continue
                target = f" → {f.replacement}" if f.fixable else ""
                if f.carried:
                    target = " [the original prints the same: the author's]"
                reads = f" — reads like {f.suggestion}" if f.suggestion else ""
                self.stdout.write(
                    f"  {mark}{f.record.where}: {f.kind}: cites {f.printed}{reads}{target} "
                    f"(cited {f.cited:.2f}, rival {f.rival:.2f}, next {f.runner_up:.2f}"
                    + "".join(f"; {n}" for n in f.notes)
                    + ")"
                )
                self.stdout.write(f"        “{f.quote[:110]}”")

        kinds = Counter(f.kind for f in findings)
        tiers = Counter(f.record.tier for f in findings)
        fixable = sum(f.fixable for f in findings)
        self.stdout.write(
            f"\n{pairs} quote+citation pairs · {len(findings)} findings across {len(by_work)} editions"
            f" · {fixable} fixable\n  by kind: {dict(sorted(kinds.items()))}\n  by tier: {dict(sorted(tiers.items()))}"
        )
        if opts["json_path"]:
            Path(opts["json_path"]).write_text(
                json.dumps(
                    [f.as_dict() for f in findings], ensure_ascii=False, indent=1
                )
                + "\n",
                encoding="utf-8",
            )
