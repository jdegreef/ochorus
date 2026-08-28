"""Re-derive the committed fixture's ``body_text`` from its ``body_html``.

``body_text`` is DERIVED, not authored: ``Chapter.save()`` and ``Sermon.save()``
both set it to ``html_to_text(body_html)``, and it is what full-text search
indexes and what snippets are rendered from. The fixture is the one place it can
drift, because ``loaddata`` writes it verbatim — it never calls ``save()`` — and
``backfill_body_text`` only fills an EMPTY one, so a value that is present but
wrong never self-corrects anywhere.

490 rows across 58 files had drifted, in four ways, none of them visible on a
page:

  * QUOTE MARKS — the sweep that converted `body_html` to curly left `body_text`
    on the old straight marks, so a work rendered « » and was indexed with ".
  * ENTITIES — `body_text` holding `man&#x27;s` where the rule gives `man's`.
    Search indexed the entity; a snippet would have shown it to the reader.
  * SPACING — `الخيرات. »` for `الخيرات.»`, from an older derivation that
    replaced every tag with a space instead of only the block-level ones.
  * EMPTY — 36 chapters of `the-inner-chamber.lg` carry no `body_text` at all.
    The deploy's `backfill_body_text` fills those, so they are the one class
    that does repair itself; they are here so the committed file agrees with
    the database rather than depending on a later step.

Not a one-shot: any future edit to a `body_html` in the fixture leaves its
`body_text` behind in exactly this way, and
`tests_fixture.BodyTextDerivationTests` fails until this is run. Dry-run by
default.

    manage.py rederive_body_text            # show what would change
    manage.py rederive_body_text --write    # do it

Every language, unlike `normalize_english_fixture`: this applies no rule of its
own and makes no judgement about the prose. It recomputes a derived column from
a source column, which is as true of Arabic or Luganda as of English.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from library.content_fixtures import BOOKS_DIR, SERMONS_DIR, render_rows
from library.text import html_to_text


class Command(BaseCommand):
    help = "Re-derive body_text from body_html across the committed fixture."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", help="Apply (default: dry-run).")

    def handle(self, *args, **opts):
        paths = sorted(BOOKS_DIR.glob("*.json")) + sorted(SERMONS_DIR.glob("*.json"))
        files = rows_fixed = 0

        for path in paths:
            rows = json.loads(path.read_text(encoding="utf-8"))
            fixed = 0
            for row in rows:
                fields = row.get("fields", {})
                body_html = fields.get("body_html")
                # `is None` and not falsy: a row whose body_text is "" is one of
                # the rows this exists to fill, and `not fields.get(...)` would
                # skip exactly those.
                if not body_html or fields.get("body_text") is None:
                    continue
                derived = html_to_text(body_html)
                if derived == fields["body_text"]:
                    continue
                fields["body_text"] = derived
                fixed += 1
            if not fixed:
                continue
            files += 1
            rows_fixed += fixed
            self.stdout.write(f"  {fixed:>4} rows  {path.name}")
            if opts["write"]:
                path.write_text(render_rows(rows), encoding="utf-8")

        verb = "re-derived" if opts["write"] else "would re-derive"
        tail = "" if opts["write"] else " (dry run — pass --write)"
        self.stdout.write(f"\n{verb} {rows_fixed} rows across {files} files{tail}")
