"""Apply `apply_body_corrections` to the committed English fixture.

Uses `apply_body_corrections` rather than the bare rule, so the fixture gets the
same ordering as every other caller — declared repairs first, then the rule. A
work like `the-inner-chamber` declares "scales- only" -> "scales — only", where
the trailing hyphen is a flattened DASH and not a broken word; running the rule
first would close it to "scales-only" and lose the em dash.

`apply_body_corrections` runs on every import and on every deploy, so the
DATABASE repairs itself. The fixture does not: it is a committed file, it is
what a fresh build loads, and it is what `tests_english_audit.py` measures. Left
alone it would keep 434 defects that production no longer has, and the ratchet
would keep reporting them forever.

Not a one-shot. It was written for the 434-hyphen sweep, but a DECLARED repair
added later leaves the fixture stale in exactly the same way, so this runs again
whenever `BODY_CORRECTIONS` grows. It used to be unable to: it counted hyphen
SITES and skipped any file whose count was zero, so a declared pair on a
hyphen-free file was applied in memory and then dropped — silently, with the dry
run reporting "0 files". Ten book fixtures were stale that way. It now writes
whenever the text actually changed, and reports the two kinds separately.

Both body fields are normalized. `body_text` is DERIVED from `body_html`
(`Chapter.save()` keeps them in step), so correcting one and not the other
leaves the committed file disagreeing with itself — which is how 36 fixtures
came to carry a `body_text` that its own `body_html` no longer matched.
Production never saw it: `apply_body_corrections` calls `.save()`, which
recomputes `body_text` and refreshes the search vector. The fixture is the only
place it persists. Dry-run by default.

    manage.py normalize_english_fixture            # show what would change
    manage.py normalize_english_fixture --write    # do it

English only. The same defect exists in the translations (a translator renders
what is there), but their text is not this rule's to touch — a hyphen inside
Arabic or Luganda is a different question, and one this rule has never been
tested against.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from library.content_fixtures import BOOKS_DIR, SERMONS_DIR
from library.corrections import _HYPHEN_LINEBREAK, apply_body_corrections

FIELDS = ("body_html", "body_text")


def render(rows: list[dict]) -> str:
    """Byte-stable Django-fixture formatting — identical to regen_fixture.py."""
    return "[\n" + ",\n".join(json.dumps(r, indent=1, ensure_ascii=False) for r in rows) + "\n]\n"


class Command(BaseCommand):
    help = "Close line-break hyphens ('self- righteous') in the English fixture."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", help="Apply (default: dry-run).")

    def handle(self, *args, **opts):
        paths = sorted(BOOKS_DIR.glob("*.en.json")) + sorted(SERMONS_DIR.glob("*.en.json"))
        touched_files = hyphens = edits = 0

        for path in paths:
            rows = json.loads(path.read_text(encoding="utf-8"))
            slug = path.name[: -len(".en.json")]
            file_hyphens = file_edits = 0
            for row in rows:
                fields = row.get("fields", {})
                for key in FIELDS:
                    before = fields.get(key)
                    if not before:
                        continue
                    after = apply_body_corrections(slug, fields.get("order"), before)
                    if after == before:
                        continue
                    # Two counters, because they answer different questions and
                    # conflating them is what made this command silently skip
                    # files. EDITS decides whether the file is written — any
                    # change at all, declared pair or rule. HYPHENS is reporting
                    # only: how much text the rule moved. Counting sites alone
                    # meant a declared repair on a hyphen-free file scored zero
                    # and was dropped after being applied.
                    file_hyphens += len(_HYPHEN_LINEBREAK.findall(before))
                    file_edits += 1
                    fields[key] = after
            if not file_edits:
                continue
            touched_files += 1
            hyphens += file_hyphens
            edits += file_edits
            self.stdout.write(f"  {file_edits:4d} edits ({file_hyphens:4d} hyphens)  {path.name}")
            if opts["write"]:
                path.write_text(render(rows), encoding="utf-8")

        summary = f"{edits} fields ({hyphens} hyphen sites) across {touched_files} files"
        self.stdout.write(
            self.style.SUCCESS(f"\nrepaired {summary}")
            if opts["write"]
            else f"\nwould repair {summary} (dry run — pass --write)"
        )
