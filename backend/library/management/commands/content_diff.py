"""Show what actually changed in a content fixture, as prose.

The review promise this serves: an AI translation ships ``ai_unreviewed`` until
a human approves it. Reading a fixture diff in git is how that review is
supposed to happen, and raw it is unreadable — a chapter body is one JSON line,
so a one-word fix prints 36 KB of escaped HTML with the change hidden inside
(measured on ``humility-2.en.json``). Through here the same change is 1.3 KB and
says "chapter 12, paragraph 2".

``.gitattributes`` wires the same rendering into ``git diff`` itself, but git
will not let a repository install the textconv it needs (arbitrary code on
clone), so that takes a one-time opt-in — ``--install`` does it. This command
needs no configuration, which is what makes it usable in CI and on a fresh
clone.
"""

from __future__ import annotations

import difflib
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from library.content_fixtures import CONTENT_DIR
from library.content_prose import render_file

REPO_ROOT = Path(__file__).resolve().parents[4]
TEXTCONV = REPO_ROOT / "backend" / "scripts" / "fixture-textconv.py"


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if proc.returncode:
        raise CommandError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


class Command(BaseCommand):
    help = "Diff content fixtures as readable prose instead of raw JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "paths", nargs="*",
            help="Fixture paths or slugs to limit to (default: everything changed).",
        )
        parser.add_argument(
            "--base", default="HEAD",
            help="Compare against this ref (default HEAD, i.e. your working tree).",
        )
        parser.add_argument(
            "--context", type=int, default=1,
            help="Paragraphs of context around each change (default 1).",
        )
        parser.add_argument(
            "--install", action="store_true",
            help="Teach this clone's git to use the same rendering in `git diff`.",
        )

    def handle(self, *args, **opts):
        if opts["install"]:
            return self._install()

        base = opts["base"]
        changed = self._changed_fixtures(base, opts["paths"])
        if not changed:
            self.stdout.write("No content fixture changes.")
            return

        total = 0
        for rel in changed:
            before = self._blob(base, rel)
            after = self._working_copy(rel)
            hunks = list(
                difflib.unified_diff(
                    render_file(before).splitlines(),
                    render_file(after).splitlines(),
                    fromfile=f"{base}:{rel}",
                    tofile=f"working:{rel}",
                    n=opts["context"],
                    lineterm="",
                )
            )
            if not hunks:
                # Reformatting only — the bytes moved, the prose did not. Worth
                # saying out loud: it means the change ships no content edit.
                self.stdout.write(self.style.WARNING(f"~ {rel}: formatting only"))
                continue
            total += 1
            for line in hunks:
                self.stdout.write(self._colour(line))
            self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(f"{total} fixture(s) with prose changes.")
            if total
            else "No prose changes (formatting only)."
        )

    # --- helpers ------------------------------------------------------------

    def _colour(self, line: str) -> str:
        if line.startswith("+") and not line.startswith("+++"):
            return self.style.SUCCESS(line)
        if line.startswith("-") and not line.startswith("---"):
            return self.style.ERROR(line)
        if line.startswith("@@"):
            return self.style.HTTP_INFO(line)
        return line

    def _changed_fixtures(self, base: str, paths: list[str]) -> list[str]:
        rel_root = CONTENT_DIR.relative_to(REPO_ROOT).as_posix()
        names = _git("diff", "--name-only", base, "--", rel_root).split()
        if not paths:
            return names
        # A bare slug is the useful shorthand — nobody types the full path.
        return [n for n in names if any(p in n for p in paths)]

    def _blob(self, ref: str, rel: str) -> str:
        proc = subprocess.run(
            ["git", "show", f"{ref}:{rel}"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        # A file that did not exist at `ref` is a new work: diff against empty
        # rather than failing, so adding a translation still renders.
        return proc.stdout if proc.returncode == 0 else ""

    def _working_copy(self, rel: str) -> str:
        path = REPO_ROOT / rel
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def _install(self):
        if not TEXTCONV.is_file():
            raise CommandError(f"{TEXTCONV} is missing")
        _git("config", "diff.ochorus-content.textconv", str(TEXTCONV))
        self.stdout.write(
            self.style.SUCCESS("Installed. `git diff` now renders content fixtures as prose.")
        )
        self.stdout.write(
            "Local to this clone — git will not install a textconv from a repository, "
            "since that would run its code on clone."
        )
