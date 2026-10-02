"""Set typewriter dashes ("--") as em dashes in the committed content fixture.

The rule is `library.dashes.convert`, which `corrections.apply_body_corrections`
also runs first on every deploy — so production repairs its own rows (and a
re-import arrives repaired); this sweep brings the fixture, which is what a
fresh build loads, to the same settled text.

    uv run python scripts/normalize_dashes.py --check     # report only
    uv run python scripts/normalize_dashes.py             # rewrite in place

Every language, books and sermons, `body_html` AND `body_text`: the dash is a
transcription convention, and the translations copied it from the English they
were made from (904 in the Swahili alone).

IN PLACE, by design. `content_fixtures.render_rows` does not round-trip 292 of
the committed files (the known whitespace drift), so loading and re-serialising
would turn a one-character fix into a whole-file diff. Each field value is
rewritten where it stands in the raw JSON, which `-` never needs escaping in.
`body_text` is converted directly rather than re-derived, which lands on the
characters `html_to_text` would produce from the converted HTML in every case
but two: a run split across a tag ("26.-</i>-“", which the text joins into one)
and an unescaped `<…>` in the text. Neither is guessed at here —
`tests_fixture.BodyTextDerivationTests` fails on the row, and it is repaired by
hand (Brainerd ch11 was the one case). `word_count` cannot move: a dash replaces
a run of hyphens inside a whitespace-delimited token.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
CONTENT = BACKEND / "library" / "fixtures" / "content"

sys.path.insert(0, str(BACKEND))

from library.dashes import FIXTURE_BODY_FIELD as FIELD  # noqa: E402  (path set above)
from library.dashes import convert, count  # noqa: E402


def main() -> int:
    check = "--check" in sys.argv
    files = sorted(CONTENT.glob("books/*.json")) + sorted(CONTENT.glob("sermons/*.json"))
    touched = total = 0
    for path in files:
        raw = path.read_text(encoding="utf-8")
        n = sum(count(m.group(2)) for m in FIELD.finditer(raw))
        if not n:
            continue
        touched += 1
        total += n
        print(f"  {path.name:<56} {n:>6}")
        if not check:
            path.write_text(
                FIELD.sub(lambda m: m.group(1) + convert(m.group(2)) + m.group(3), raw),
                encoding="utf-8",
            )
    verb = "would set" if check else "set"
    print(f"{verb} {total} typewriter dashes across {touched} files")
    return 1 if check and total else 0


if __name__ == "__main__":
    raise SystemExit(main())
