"""Remove ``body_text`` from the committed fixture.

``body_text`` is DERIVED, not authored: ``Chapter.save()`` and ``Sermon.save()``
both set it to ``html_to_text(body_html)``, and on a fresh database
``backfill_body_text`` (the second step of ``manage.py release``) fills every row
that ``loaddata`` left empty. So the fixture has no reason to store it — and
storing it cost twice:

  * SIZE — it was ~49% of the fixture's bytes (the same prose as ``body_html``,
    minus the tags), carried by every clone, CI checkout and API image.
  * DRIFT — ``loaddata`` writes a stored value verbatim and the backfill only
    fills an EMPTY one, so a ``body_text`` left behind by an edit to
    ``body_html`` self-corrected nowhere. 490 rows across 58 files once drifted
    that way (quote marks, entities, Arabic spacing).

The name is kept from when this re-derived the column, so every playbook step
that says "then run ``rederive_body_text --write``" still converges: it now
drops the field instead. ``tests_fixture.BodyTextNotStoredTests`` fails while
any row carries it. Dry-run by default.

    manage.py rederive_body_text            # show what would change
    manage.py rederive_body_text --write    # do it
"""

from __future__ import annotations

import json
import re

from django.core.management.base import BaseCommand

from library.content_fixtures import BOOKS_DIR, SERMONS_DIR, render_rows

#: One stored `body_text` line. json.dumps escapes newlines, so the value never
#: spans lines in any formatting the fixture uses.
_LINE = re.compile(r'^[ \t]*"body_text": "(?:[^"\\\n]|\\.)*",?\n', re.M)


def without_body_text(text: str, expected: list[dict]) -> str:
    """`text` with its body_text lines cut, or re-rendered if cutting can't work.

    Cutting the lines leaves every other byte alone, so a hand-formatted file
    keeps its own layout and the diff is only the removal. The result is checked
    against `expected`; a file it doesn't reproduce (a body_text that was the
    last field, leaving a dangling comma) falls back to `render_rows`.
    """
    cut = _LINE.sub("", text)
    try:
        if json.loads(cut) == expected:
            return cut
    except json.JSONDecodeError:
        pass
    return render_rows(expected)


class Command(BaseCommand):
    help = "Drop the derived body_text column from the committed fixture."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", help="Apply (default: dry-run).")

    def handle(self, *args, **opts):
        paths = sorted(BOOKS_DIR.glob("*.json")) + sorted(SERMONS_DIR.glob("*.json"))
        files = rows_fixed = 0

        for path in paths:
            text = path.read_text(encoding="utf-8")
            rows = json.loads(text)
            fixed = 0
            for row in rows:
                fields = row.get("fields", {})
                if "body_text" in fields:
                    del fields["body_text"]
                    fixed += 1
            if not fixed:
                continue
            files += 1
            rows_fixed += fixed
            if opts["verbosity"] > 1:
                self.stdout.write(f"  {fixed:>4} rows  {path.name}")
            if opts["write"]:
                path.write_text(without_body_text(text, rows), encoding="utf-8")

        verb = "dropped body_text from" if opts["write"] else "would drop body_text from"
        tail = "" if opts["write"] else " (dry run — pass --write)"
        self.stdout.write(f"{verb} {rows_fixed} rows across {files} files{tail}")
