"""Inventory a work's Scripture quotations, and check (or apply) a splice spec.

    manage.py requote_inventory book school-of-prayer                # summary + notes diff
    manage.py requote_inventory book school-of-prayer --json inv.json
    manage.py requote_inventory sermon the-dying-thief --chapter 1 --show needs_requote
    manage.py requote_inventory book school-of-prayer --check spec.json
    manage.py requote_inventory book school-of-prayer --check spec.json --apply

The inventory is the re-quote worker's first step — what wave 1 did by hand,
block by block, at most of a book's cost: every quotation in the translated
text (cited, uncited, recited without marks, and English quotations the
translation lost), aligned to the English block, with its OWB text, a status
guess and the diff against the notes file. ``library/requote.py`` explains each
detector and its limits.

A splice spec is a JSON list of edits, applied in order:

    [{"chapter": 3, "block": 6, "old": "«…»", "new": "«…»", "reference": "John 4:23"},
     {"chapter": 3, "block": "title", "old": "…", "new": "…", "reference": "Luke 11:1"},
     {"chapter": 5, "block": 2, "old": "…", "new": "…", "self_rendered": true}]

``chapter`` is the chapter's ``order`` (omit it, or null, for a sermon or bio);
``block`` the per-chapter block index the inventory prints. Optional:
``occurrences`` (a byte-identical repeat replaced in one go), ``slack``
(verses either side of the reference the OWB check may read), and
``self_rendered`` (skip the OWB check — critical-text and person cases).
``--check`` exits non-zero on any problem; ``--apply`` writes only when there
are none, in the file's existing layout, recomputing each chapter's
word_count. It does not touch the notes file.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from library import requote


class Command(BaseCommand):
    help = "Inventory a translated work's Scripture quotations against OWB; validate or apply a splice spec."

    def add_arguments(self, parser):
        parser.add_argument("kind", choices=["book", "sermon", "article", "bio"])
        parser.add_argument("slug")
        parser.add_argument("--language", default="am")
        parser.add_argument(
            "--json",
            dest="json_out",
            help="Write the full inventory (rows + notes diff) here.",
        )
        parser.add_argument(
            "--rev",
            help="Read the work and its notes as they stood at this git revision.",
        )
        parser.add_argument(
            "--chapter", type=int, help="Print rows of this chapter only."
        )
        parser.add_argument(
            "--show",
            choices=["all", "needs_requote", "missing", "none"],
            default="missing",
            help="Which rows to print (default: the quotations the notes miss).",
        )
        parser.add_argument(
            "--check",
            metavar="SPEC",
            help="Validate a splice spec (JSON list of edits).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="With --check: write the spliced fixture.",
        )

    def handle(
        self,
        *args,
        kind,
        slug,
        language,
        json_out,
        rev,
        chapter,
        show,
        check,
        apply,
        **opts,
    ):
        read = requote.git_reader(rev) if rev else requote.read_file
        try:
            work = requote.load_work(kind, slug, language, read)
        except FileNotFoundError as exc:
            raise CommandError(f"No {kind} {slug!r} in {language!r}: {exc}") from exc
        if check:
            if apply and rev:
                raise CommandError(
                    "--apply writes the working tree; don't combine it with --rev."
                )
            return self._check(work, Path(check), apply)
        if apply:
            raise CommandError("--apply needs --check SPEC.")

        result = requote.run_inventory(kind, slug, language, read)
        if json_out:
            Path(json_out).write_text(
                json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            self.stdout.write(f"Wrote {json_out}")
        s = result["summary"]
        self.stdout.write(
            f"{kind} {slug} ({language}): {s['quotations']} quotations — {s['already_owb']} already OWB, "
            f"{s['needs_requote']} to re-quote; {s['english_only']} English quotations with no match in the translation."
        )
        self.stdout.write(
            f"notes: {s['notes_rows']} rows — {s['missing_from_notes']} quotations missing, "
            f"{s['wrong_block']} at the wrong block, {s['unlocated_notes']} with no quotation found "
            f"(allusions, bare citations, or detector misses); {s['english_only_unnoted']} unnoted English-only."
        )
        rows = self._rows(result, show, chapter)
        for r in rows:
            flags = f" [{', '.join(r['flags'])}]" if r.get("flags") else ""
            where = f"ch{r['chapter']} " if r["chapter"] is not None else ""
            self.stdout.write(
                f"  {where}b{r['block_index']} {r['reference']} {r.get('kind', '')}/{r['status']}{flags}: {r['text'][:120]}"
            )
        for ch, shift in result["notes_diff"]["chapter_offsets"].items():
            if chapter is None or str(chapter) == ch:
                self.stdout.write(
                    f"  ch{ch}: the notes sit {abs(shift)} block(s) "
                    f"{'after' if shift < 0 else 'before'} the quotations they mean"
                )
        if show == "missing":
            for w in result["notes_diff"]["wrong_block"]:
                if chapter is None or w["chapter"] == chapter:
                    self.stdout.write(
                        f"  wrong block: {w['reference']} noted at ch{w['chapter']} b{w['notes_block']}, "
                        f"quoted at ch{w['found_chapter']} b{w['found_block']}"
                    )

    @staticmethod
    def _rows(result, show, chapter):
        if show == "none":
            return []
        if show == "missing":
            rows = result["notes_diff"]["missing"]
        elif show == "needs_requote":
            rows = [r for r in result["rows"] if r["status"] == requote.NEEDS_REQUOTE]
        else:
            rows = result["rows"]
        return [r for r in rows if chapter is None or r["chapter"] == chapter]

    def _check(self, work, spec_path: Path, apply: bool):
        try:
            edits = json.loads(spec_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"Can't read the spec: {exc}") from exc
        if not isinstance(edits, list):
            raise CommandError("A splice spec is a JSON list of edits.")
        problems, state = requote.validate(work, edits)
        for p in problems:
            self.stdout.write(f"  edit {p.edit} [{p.check}] {p.message}")
        self.stdout.write(f"{len(edits)} edits, {len(problems)} problems.")
        if problems:
            raise CommandError("Splice spec has problems; nothing written.")
        if apply:
            for path in requote.apply(work, state):
                self.stdout.write(f"Wrote {path}")
