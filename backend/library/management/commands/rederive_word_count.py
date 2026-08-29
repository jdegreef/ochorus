"""Re-derive the committed fixture's ``word_count`` from its ``body_html``.

``word_count`` is DERIVED, not authored: every importer sets it with
``text.word_count(body_html)`` — the number of whitespace-separated tokens
left once the tags are replaced by spaces — and the reader spends it on
per-chapter reading times, the length sort on the shelf, and the word totals
under a book and a reading plan.

For most of the corpus's life it was derived ONCE, and that is where these
rows come from. ``body_text`` was recomputed by ``Chapter.save()`` and
``Sermon.save()`` on every write; the count beside it was not, so an edit to a
body left the number describing the body it USED to have — and it self-corrected
nowhere, because ``loaddata`` writes the count verbatim and
``backfill_word_count`` deliberately fills only rows sitting at zero.

#1197 closed that write path — ``save()`` derives ``word_count`` now — but a
fixture row never passes through ``save()``, so the committed numbers are still
whatever was last written into them. That is what this repairs.

381 rows across 83 files were in that state, in two classes:

  * STALE (237 rows, all English) — the count still describes the ``body_html``
    as it stood before a later prose repair. Walk one back through its file's
    history and it fits exactly one earlier revision: the 20 drifted chapters of
    `the-inner-chamber.en` and the 29 of `the-unselfishness-of-god.en` were both
    last right before #854 closed their line-break hyphens, which fuses two
    half-words into one and drops the count by one — and nothing re-derived it.
  * MIS-DERIVED AT BIRTH (144 rows — every non-English row that drifted, across
    ar/es/hi/lg/pt/sw/uk) — the count equals ``len(html_to_text(body_html)
    .split())``, the OTHER text derivation in this codebase, the one
    ``body_text`` uses. It joins across inline tags where ``text.word_count``
    spaces them, so `لأجلك<em>.</em>` counts one token to the first rule and two
    to the second. These matched no revision: they were wrong in the commit that
    introduced them.

Not a one-shot: any future edit to a ``body_html`` in the fixture leaves its
``word_count`` behind in exactly this way, and
``tests_fixture.WordCountDerivationTests`` fails until this is run. Dry-run by
default.

    manage.py rederive_word_count            # show what would change
    manage.py rederive_word_count --write    # do it

Every language, like ``rederive_body_text`` and unlike
``normalize_english_fixture``: this applies no rule of its own and makes no
judgement about prose. It counts the words in a body, which is as true of
Arabic or Luganda as of English.

One deliberate difference from ``rederive_body_text``: this PATCHES the integer
in place rather than re-rendering the file through ``render_rows``. 17 of the 83
files predate the current renderer and carry their own indentation — drift the
corpus has looked at and chosen to leave alone — so re-rendering them buried a
381-number change under ~3,000 lines of reformatting in files this has no
business touching. The patch is checked, not hoped: the file is re-parsed
afterwards and must equal the rows this intended to write, or nothing is
written.
"""

from __future__ import annotations

import json
import re

from django.core.management.base import BaseCommand, CommandError

from library.content_fixtures import BOOKS_DIR, SERMONS_DIR
from library.text import word_count

#: Every stored ``word_count`` is a bare non-negative integer literal, so its
#: value can be replaced without re-serialising the row around it.
_WORD_COUNT = re.compile(r'(?:"word_count":\s*)(\d+)')


def repatch(text: str, rows: list[dict]) -> str:
    """``text`` with each row's ``word_count`` literal set to that row's value.

    Positional: the Nth ``"word_count":`` literal in the file belongs to the Nth
    row carrying that key, because JSON preserves array order. Guarded on both
    ends — the counts must line up going in, and the re-parsed result must equal
    ``rows`` coming out — so a body that happens to contain the same text fails
    loudly instead of writing the number into someone's prose.
    """
    slots = [r["fields"] for r in rows if "word_count" in r.get("fields", {})]
    matches = list(_WORD_COUNT.finditer(text))
    if len(matches) != len(slots):
        raise CommandError(
            f"{len(matches)} word_count literals for {len(slots)} rows — refusing "
            f"to patch positionally."
        )
    out = text
    # `strict`: the lengths are already guarded equal above — this makes a
    # future edit that breaks that pairing fail here rather than patch silently.
    for match, fields in zip(reversed(matches), reversed(slots), strict=True):
        out = out[: match.start(1)] + str(fields["word_count"]) + out[match.end(1) :]
    if json.loads(out) != rows:
        raise CommandError("patched file no longer parses to the intended rows.")
    return out


class Command(BaseCommand):
    help = "Re-derive word_count from body_html across the committed fixture."

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
                body_html = fields.get("body_html")
                # `is None` and not falsy: a row whose count is 0 is one of the
                # rows this exists to fill, and `not fields.get(...)` would skip
                # exactly those. A row with no `body_html` has nothing to derive
                # FROM — writing 0 would blank a count rather than repair it.
                if not body_html or fields.get("word_count") is None:
                    continue
                derived = word_count(body_html)
                if derived == fields["word_count"]:
                    continue
                fields["word_count"] = derived
                fixed += 1
            if not fixed:
                continue
            files += 1
            rows_fixed += fixed
            self.stdout.write(f"  {fixed:>4} rows  {path.name}")
            if opts["write"]:
                path.write_text(repatch(text, rows), encoding="utf-8")

        verb = "re-derived" if opts["write"] else "would re-derive"
        tail = "" if opts["write"] else " (dry run — pass --write)"
        self.stdout.write(f"\n{verb} {rows_fixed} rows across {files} files{tail}")
