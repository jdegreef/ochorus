#!/usr/bin/env python3
"""Regenerate the split content fixtures — the ONLY sanctioned way.

Layout (see ``library/content_fixtures.py``): ``fixtures/content/`` with
``authors.json``, one ``books/<slug>.<language>.json`` per book (book row then
its chapters), one ``sermons/<slug>.<language>.json`` per sermon, and
``plans.json``. Natural-key format throughout — no integer pks.

The pinned recipe (any deviation mutates content relative to the committed
files):

    fresh scratch DB -> migrate -> loaddata (all content fixtures, in order)
    -> dumpdata of EXACTLY the six content models with
    --natural-primary --natural-foreign -> split into the layout

Nothing else may run in between: the seed/backfill commands mutate rows
relative to the fixtures, and a bare ``dumpdata library`` from a seeded dev DB
leaks Topic/translation rows.

The script verifies its own output before replacing anything: the multiset of
natural identities and every field value must survive the round trip. Run from
``backend/``:

    uv run python scripts/regen_fixture.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.content_fixtures import (  # noqa: E402  (path set above; no Django needed)
    AUTHORS_FILE,
    BOOKS_DIR,
    CONTENT_DIR,
    PLANS_FILE,
    SERMONS_DIR,
    load_all_rows,
    ordered_fixture_paths,
    work_filename,
)

LEGACY_MONOFILE = BACKEND / "library" / "fixtures" / "launch.json"

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
        return (m, tuple(f["book"]), f["order"])
    if m == "library.planday":
        return (m, tuple(f["plan"]), f["day"])
    return (m, json.dumps(f, sort_keys=True))


def render(rows: list[dict]) -> str:
    """Byte-stable Django-fixture formatting (records at column 0, indent=1)."""
    return "[\n" + ",\n".join(
        json.dumps(r, indent=1, ensure_ascii=False) for r in rows
    ) + "\n]\n"


def split_layout(rows: list[dict]) -> dict[Path, list[dict]]:
    """Assign every dumped row to its file, preserving in-file load order."""
    by_model: dict[str, list[dict]] = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)

    files: dict[Path, list[dict]] = {AUTHORS_FILE: by_model.get("library.author", [])}

    chapters_by_book: dict[tuple, list[dict]] = {}
    for r in by_model.get("library.chapter", []):
        chapters_by_book.setdefault(tuple(r["fields"]["book"]), []).append(r)
    for b in by_model.get("library.book", []):
        f = b["fields"]
        key = (f["slug"], f.get("language", "en"))
        chs = sorted(chapters_by_book.pop(key, []), key=lambda c: c["fields"]["order"])
        files[BOOKS_DIR / work_filename(*key)] = [b] + chs
    if chapters_by_book:
        sys.exit(f"orphan chapters for {sorted(chapters_by_book)[:3]} — aborting.")

    for s in by_model.get("library.sermon", []):
        f = s["fields"]
        files[SERMONS_DIR / work_filename(f["slug"], f.get("language", "en"))] = [s]

    days_by_plan: dict[tuple, list[dict]] = {}
    for r in by_model.get("library.planday", []):
        days_by_plan.setdefault(tuple(r["fields"]["plan"]), []).append(r)
    plan_rows: list[dict] = []
    for p in by_model.get("library.plan", []):
        f = p["fields"]
        key = (f["slug"], f.get("language", "en"))
        plan_rows.append(p)
        plan_rows.extend(sorted(days_by_plan.pop(key, []), key=lambda d: d["fields"]["day"]))
    if days_by_plan:
        sys.exit(f"orphan plan days for {sorted(days_by_plan)[:3]} — aborting.")
    files[PLANS_FILE] = plan_rows

    return files


def main():
    # Source of truth: the split layout, or the legacy monofile on first run.
    if CONTENT_DIR.is_dir() and ordered_fixture_paths():
        src_rows = load_all_rows()
        load_args = [str(p) for p in ordered_fixture_paths()]
    elif LEGACY_MONOFILE.exists():
        src_rows = json.loads(LEGACY_MONOFILE.read_text())
        load_args = ["launch"]
    else:
        sys.exit("no content fixtures found — nothing to regenerate.")
    if src_rows and "pk" in src_rows[0]:
        sys.exit("source fixture is pk-format — Stage 1's regen must run first.")
    src_ids = sorted(identity(r) for r in src_rows)

    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, "DJANGO_DEBUG": "true",
               "DATABASE_URL": f"sqlite:///{td}/regen.sqlite3"}
        print("→ migrate (fresh scratch DB)")
        manage(env, "migrate", "--verbosity", "0")
        print(f"→ loaddata ({len(load_args)} fixture file(s), ordered)")
        manage(env, "loaddata", *load_args, "--verbosity", "0")
        print("→ dumpdata (6 models, natural keys)")
        out = td + "/dump-nk.json"
        manage(env, "dumpdata", *MODELS,
               "--natural-primary", "--natural-foreign", "--indent", "1",
               "-o", out)
        new_rows = json.loads(Path(out).read_text())

    # --- verification: nothing lost, nothing invented -----------------------
    if len(new_rows) != len(src_rows):
        sys.exit(f"ROW COUNT CHANGED: {len(src_rows)} -> {len(new_rows)} — aborting.")
    if any("pk" in r for r in new_rows):
        sys.exit("output contains pk rows — dump flags wrong; aborting.")

    new_ids = sorted(identity(r) for r in new_rows)
    if src_ids != new_ids:
        gone = [i for i in src_ids if i not in set(new_ids)][:3]
        added = [i for i in new_ids if i not in set(src_ids)][:3]
        sys.exit(f"IDENTITY SET CHANGED — lost {gone}, gained {added} — aborting.")

    # Field-level drift: every value (including natural-key FK references —
    # a wrong-author regen must not pass) must survive the round trip.
    src_by_id = {identity(r): r["fields"] for r in src_rows}
    drift = []
    for r in new_rows:
        old = src_by_id[identity(r)]
        for k, v in r["fields"].items():
            if k in old and old[k] != v:
                drift.append((identity(r), k))
        for k in old:
            if k not in r["fields"]:
                drift.append((identity(r), "-" + k))
    if drift:
        sys.exit(f"FIELD DRIFT on {len(drift)} value(s), e.g. {drift[:3]} — aborting.")
    materialized = sum(
        1 for r in new_rows
        for k in r["fields"]
        if k not in src_by_id[identity(r)] and k not in DEFAULTED_OK
    )
    if materialized:
        sys.exit(f"{materialized} unexpected new field(s) — aborting.")

    # --- write the layout ----------------------------------------------------
    files = split_layout(new_rows)
    assert sum(len(v) for v in files.values()) == len(new_rows)
    if CONTENT_DIR.is_dir():
        shutil.rmtree(CONTENT_DIR)
    for path, rows in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(rows))
    if LEGACY_MONOFILE.exists():
        LEGACY_MONOFILE.unlink()
        print("✓ removed legacy launch.json")
    print(f"✓ regenerated: {len(new_rows)} rows across {len(files)} files "
          f"in {CONTENT_DIR.relative_to(BACKEND)}")
    print("Run `manage.py test library.tests_fixture` to confirm the gate.")


if __name__ == "__main__":
    main()
