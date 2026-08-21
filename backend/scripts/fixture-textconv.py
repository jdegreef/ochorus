#!/usr/bin/env python3
"""git textconv for content fixtures — see library/content_prose.py.

Wired up by .gitattributes plus one git-config line (which git deliberately
will not install from a repo; `manage.py content_diff --install` does it):

    git config diff.ochorus-content.textconv backend/scripts/fixture-textconv.py

Without that config the attribute is inert and diffs stay raw JSON — no error,
just the old behaviour.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.content_prose import render_file  # noqa: E402

if __name__ == "__main__":
    path = Path(sys.argv[1])
    # Never fail, for ANY reason: git prints textconv output AS the file, so an
    # exception here makes the file look empty and the diff look like a
    # deletion. A bare `except Exception` is the right shape for that contract —
    # a non-UTF-8 byte, a JSON array of non-objects, a field type nobody
    # anticipated. Falling back to the raw bytes is always safe: worst case the
    # reviewer sees the JSON they would have seen anyway.
    try:
        sys.stdout.write(render_file(path.read_text(encoding="utf-8")))
    except Exception as exc:  # noqa: BLE001 — see above
        try:
            sys.stdout.write(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            sys.stdout.write(f"<unreadable: {exc}>\n")
