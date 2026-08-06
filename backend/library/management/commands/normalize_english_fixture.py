"""Apply the line-break hyphen rejoin to the committed English fixture.

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

This is a one-shot; there is nothing to run again once the fixture is clean, and
the rule in `corrections` is what keeps it that way. Dry-run by default.

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

FIELDS = ("body_html",)


def render(rows: list[dict]) -> str:
    """Byte-stable Django-fixture formatting — identical to regen_fixture.py."""
    return "[\n" + ",\n".join(json.dumps(r, indent=1, ensure_ascii=False) for r in rows) + "\n]\n"


class Command(BaseCommand):
    help = "Close line-break hyphens ('self- righteous') in the English fixture."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", help="Apply (default: dry-run).")

    def handle(self, *args, **opts):
        paths = sorted(BOOKS_DIR.glob("*.en.json")) + sorted(SERMONS_DIR.glob("*.en.json"))
        touched_files = repairs = 0

        for path in paths:
            rows = json.loads(path.read_text(encoding="utf-8"))
            slug = path.name[: -len(".en.json")]
            n = 0
            for row in rows:
                fields = row.get("fields", {})
                for key in FIELDS:
                    before = fields.get(key)
                    if not before:
                        continue
                    after = apply_body_corrections(slug, fields.get("order"), before)
                    if after != before:
                        # Count SITES, not files: the report should say how much
                        # text moved, not how many files were opened.
                        n += len(_HYPHEN_LINEBREAK.findall(before))
                        fields[key] = after
            if not n:
                continue
            touched_files += 1
            repairs += n
            self.stdout.write(f"  {n:4d}  {path.name}")
            if opts["write"]:
                path.write_text(render(rows), encoding="utf-8")

        summary = f"{repairs} hyphens across {touched_files} files"
        self.stdout.write(
            self.style.SUCCESS(f"\nrepaired {summary}")
            if opts["write"]
            else f"\nwould repair {summary} (dry run — pass --write)"
        )
