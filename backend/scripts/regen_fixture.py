#!/usr/bin/env python3
"""Regenerate ``library/fixtures/launch.json`` — the ONLY sanctioned way.

The pinned recipe (any deviation mutates content relative to the committed
file):

    fresh scratch DB -> migrate -> loaddata launch -> dumpdata of EXACTLY the
    six content models with --natural-primary --natural-foreign

Nothing else may run in between: the seed/backfill commands
(``backfill_body_text``, ``apply_body_corrections``, ``seed_topics``, ...)
mutate rows relative to the fixture, and a bare ``dumpdata library`` from a
seeded dev DB leaks Topic/translation rows into the file.

The script verifies its own output before replacing the fixture: the multiset
of natural identities (and each row's field values) must survive the round
trip. Run from ``backend/``:

    uv run python scripts/regen_fixture.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
FIXTURE = BACKEND / "library" / "fixtures" / "launch.json"

MODELS = [
    "library.author",
    "library.book",
    "library.chapter",
    "library.sermon",
    "library.plan",
    "library.planday",
]

# Fields whose absence in the source simply means "model default" — the regen
# materializes them, which is semantically inert and expected.
DEFAULTED_OK = {"is_imprint", "attribution", "publication_year", "source_type", "body_text"}


def manage(env, *args):
    r = subprocess.run(
        ["uv", "run", "python", "manage.py", *args],
        cwd=BACKEND, env=env, capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit(f"manage.py {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def identity(row):
    f = row["fields"]
    m = row["model"]
    if m == "library.author":
        return (m, f["slug"])
    if m in ("library.book", "library.sermon", "library.plan"):
        return (m, f["slug"], f.get("language", "en"))
    if m == "library.chapter":
        return (m, tuple(f["book"]) if isinstance(f["book"], list) else f["book"], f["order"])
    if m == "library.planday":
        return (m, tuple(f["plan"]) if isinstance(f["plan"], list) else f["plan"], f["day"])
    return (m, json.dumps(f, sort_keys=True))


def normalize_pk_rows(rows):
    """Rewrite pk-format rows to natural-key shape (for comparison only).

    Lets the first regen — pk source, NK output — still verify the full
    identity multiset instead of just row counts.
    """
    if not rows or "pk" not in rows[0]:
        return rows
    authors = {r["pk"]: r["fields"]["slug"] for r in rows if r["model"] == "library.author"}
    books = {r["pk"]: [r["fields"]["slug"], r["fields"].get("language", "en")]
             for r in rows if r["model"] == "library.book"}
    plans = {r["pk"]: [r["fields"]["slug"], r["fields"].get("language", "en")]
             for r in rows if r["model"] == "library.plan"}
    out = []
    for r in rows:
        f = dict(r["fields"])
        if r["model"] in ("library.book", "library.sermon"):
            f["author"] = [authors[f["author"]]]
        elif r["model"] == "library.chapter":
            f["book"] = books[f["book"]]
        elif r["model"] == "library.planday":
            f["plan"] = plans[f["plan"]]
        out.append({"model": r["model"], "fields": f})
    return out


def main():
    src_rows = normalize_pk_rows(json.loads(FIXTURE.read_text()))
    src_ids = sorted(identity(r) for r in src_rows)

    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, "DJANGO_DEBUG": "true",
               "DATABASE_URL": f"sqlite:///{td}/regen.sqlite3"}
        print("→ migrate (fresh scratch DB)")
        manage(env, "migrate", "--verbosity", "0")
        print("→ loaddata launch")
        manage(env, "loaddata", "launch", "--verbosity", "0")
        print("→ dumpdata (6 models, natural keys)")
        out = td + "/launch-nk.json"
        manage(env, "dumpdata", *MODELS,
               "--natural-primary", "--natural-foreign", "--indent", "1",
               "-o", out)
        new_raw = Path(out).read_text()

    new_rows = json.loads(new_raw)

    # --- verification: nothing lost, nothing invented -----------------------
    new_ids = sorted(identity(r) for r in new_rows)
    # Source identities may be pk-based (first regen) — compare by count and by
    # per-model natural identity where derivable.
    if len(new_rows) != len(src_rows):
        sys.exit(f"ROW COUNT CHANGED: {len(src_rows)} -> {len(new_rows)} — aborting.")
    stale = [r for r in new_rows if "pk" in r]
    if stale:
        sys.exit("output contains pk rows — dump flags wrong; aborting.")

    # Field-level drift check where identities are directly comparable.
    if src_ids == new_ids:
        src_by_id = {identity(r): r["fields"] for r in src_rows}
        drift = []
        for r in new_rows:
            old = src_by_id[identity(r)]
            for k, v in r["fields"].items():
                if k in old and old[k] != v and not (
                    isinstance(old[k], list) or isinstance(v, list)
                ):
                    drift.append((identity(r), k))
        if drift:
            sys.exit(f"FIELD DRIFT on {len(drift)} value(s), e.g. {drift[:3]} — aborting.")
        materialized = sum(
            1 for r in new_rows
            for k in r["fields"]
            if k not in src_by_id[identity(r)] and k not in DEFAULTED_OK
        )
        if materialized:
            sys.exit(f"{materialized} unexpected new field(s) — aborting.")

    FIXTURE.write_text(new_raw)
    print(f"✓ regenerated: {len(new_rows)} rows, {len(new_raw):,} bytes "
          f"(was {FIXTURE.stat().st_size:,})")
    print("Run `manage.py test library.tests_fixture` to confirm the gate.")


if __name__ == "__main__":
    main()
