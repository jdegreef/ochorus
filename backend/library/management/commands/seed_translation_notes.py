"""Upsert translation notes — which verses were mined, which were self-rendered.

The translation pipeline works this out while it runs: a scripture reference
whose Swahili (or Arabic, or Ukrainian…) wording was recovered verbatim from our
own shipped corpus needs no review, and one the translator had to render itself
is the actual review task. Until now that distinction was written into a pull
request body, where the person who has to act on it never sees it.

``TranslationNote`` is not a fixture model and deliberately not part of the
content file. Content ships as one file per work precisely so parallel
translation jobs cannot collide; threading review metadata into those files would
reintroduce exactly that conflict, and would also mean a note could not be
corrected without touching the text. So notes ship as their own files and are
upserted here, the same shape ``seed_author_translations`` uses for bios.

File layout mirrors the content fixtures::

    fixtures/translation_notes/<kind>/<slug>.<language>.json

and each file describes ONE translation::

    {
      "kind": "sermon",
      "slug": "the-possibilities-of-faith",
      "language": "sw",
      "job_issue": 423,
      "pull_request": 897,
      "references": [
        {"reference": "Mark 9:23", "status": "mined",
         "source_file": "jesus-himself-2.sw.json", "block_index": 8},
        {"reference": "Acts 26:18", "status": "self_rendered"}
      ]
    }

Upsert is replace-per-translation: every row for a (kind, slug, language) is
dropped and rewritten from the file. That makes a re-run idempotent, and it means
removing a reference from the file actually removes it — a note that stayed
behind after being corrected would be worse than no note at all.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from library.models import ReviewOutcome, TranslationNote

NOTES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "translation_notes"

def notes_path(kind: str, slug: str, language: str) -> Path:
    """Where one translation's notes live. The canonical layout, stated once.

    ``handle`` globs rather than calling this, but the coverage gate in
    ``library.tests_translation_notes`` has to go the other way — from a shipped
    translation to the file it should have — and re-deriving the layout there
    would leave two places to change if it ever moves.
    """
    return NOTES_DIR / kind / f"{slug}.{language}.json"


VALID_KINDS = set(ReviewOutcome.Kind.values)
VALID_STATUS = set(TranslationNote.Status.values)


class Command(BaseCommand):
    help = "Upsert translation notes from the in-repo files (deploy step)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=None,
            help="Override the notes directory (used by tests).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        root = Path(opts["path"]) if opts.get("path") else NOTES_DIR
        if not root.exists():
            self.stdout.write("No translation-notes directory — nothing to seed.")
            return

        files = sorted(root.glob("*/*.json"))
        if not files:
            self.stdout.write("No translation notes found.")
            return

        written = skipped = 0
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                # One malformed note must not abort a deploy: the notes are
                # review metadata, not content, and losing the whole release over
                # a stray comma would be a worse failure than a missing chip.
                self.stderr.write(f"  ! {path.name}: unreadable ({exc}) — skipped")
                skipped += 1
                continue

            kind = data.get("kind") or path.parent.name
            slug = data.get("slug")
            language = data.get("language")
            if kind not in VALID_KINDS or not slug or not language:
                self.stderr.write(f"  ! {path.name}: missing kind/slug/language — skipped")
                skipped += 1
                continue

            rows = []
            for ref in data.get("references") or []:
                reference = (ref.get("reference") or "").strip()
                status = ref.get("status")
                if not reference or status not in VALID_STATUS:
                    self.stderr.write(
                        f"  ! {path.name}: bad reference entry {ref!r} — skipped"
                    )
                    skipped += 1
                    continue
                rows.append(
                    TranslationNote(
                        kind=kind,
                        slug=slug,
                        language=language,
                        reference=reference,
                        status=status,
                        source_file=(ref.get("source_file") or "").strip(),
                        block_index=ref.get("block_index"),
                        job_issue=data.get("job_issue"),
                        pull_request=data.get("pull_request"),
                    )
                )

            # Replace rather than merge — see the module docstring.
            TranslationNote.objects.filter(
                kind=kind, slug=slug, language=language
            ).delete()
            if rows:
                TranslationNote.objects.bulk_create(rows)
            written += len(rows)

        self.stdout.write(
            f"Translation notes: {written} reference(s) from {len(files)} file(s)"
            + (f", {skipped} skipped" if skipped else "")
        )
