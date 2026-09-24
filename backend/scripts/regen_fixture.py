#!/usr/bin/env python3
"""Regenerate the split content fixtures — the ONLY sanctioned way.

Layout (see ``library/content_fixtures.py``): ``fixtures/content/`` with
``authors.json``, one ``books/<slug>.<language>.json`` per book (book row then
its chapters), one ``sermons/<slug>.<language>.json`` per sermon, one
``articles/<slug>.<language>.json`` per article, and ``plans.json``.
Natural-key format throughout — no integer pks.

The pinned recipe (any deviation mutates content relative to the committed
files):

    fresh scratch DB -> migrate -> loaddata (all content fixtures, in order)
    -> dumpdata of EXACTLY the content models in MODELS with
    --natural-primary --natural-foreign -> split into the layout

Nothing else may run in between: the seed/backfill commands mutate rows
relative to the fixtures, and a bare ``dumpdata library`` from a seeded dev DB
leaks Topic/translation rows.

The script verifies its own output before replacing anything: the multiset of
natural identities and every field value must survive the round trip. Run from
``backend/``:

    uv run python scripts/regen_fixture.py              # byte-stable
    uv run python scripts/regen_fixture.py --normalize  # canonical rewrite

By default a file whose rows round-trip unchanged keeps its exact bytes, and a
DEFAULTED_OK field the source never carried is not written — so on a healthy
fixture the regen is a no-op, and any diff it leaves is real. ``--normalize``
instead rewrites every file in ``render_rows`` format with those defaults
materialized (the pre-2026-09 behaviour; expect a diff across most files).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from library.content_fixtures import (  # noqa: E402  (path set above; no Django needed)
    ARTICLES_DIR,
    AUTHORS_FILE,
    BOOKS_DIR,
    CONTENT_DIR,
    PLANS_FILE,
    SERIES_FILE,
    SERMONS_DIR,
    load_all_rows,
    ordered_fixture_paths,
    render_rows,
    work_filename,
)

MODELS = [
    "library.author",
    "library.series",
    "library.seriestranslation",
    "library.book",
    "library.chapter",
    "library.sermon",
    "library.article",
    "library.plan",
    "library.planday",
]

# (model, field) pairs whose absence in the source simply means "model
# default" — the regen materializes them, which is semantically inert and
# expected. Keyed per model so allowlisting a field on one model doesn't
# silently wave the same name through on another.
DEFAULTED_OK = {
    ("library.author", "is_imprint"),
    ("library.book", "publication_year"),
    ("library.book", "attribution"),
    ("library.book", "source_type"),
    # Null for every book outside a series — hand-written rows omit them.
    ("library.book", "series"),
    ("library.book", "series_position"),
    # Blank for every book whose full title fits its cover.
    ("library.book", "cover_title"),
    ("library.chapter", "body_text"),
    ("library.sermon", "source_type"),
    ("library.sermon", "body_text"),
    ("library.sermon", "summary"),  # "In brief" TL;DR — blank default, fixture-owned
    ("library.author", "faq"),
    ("library.author", "list_in_biographies"),
    ("library.author", "milestones"),
    ("library.author", "photo_attribution"),
    ("library.author", "photo_source_url"),
    ("library.book", "about_html"),
    ("library.book", "pdf_url"),
    ("library.book", "qa"),
    ("library.sermon", "attribution"),
    ("library.sermon", "study_questions"),
    ("library.article", "source_type"),
}

# (model, field) pairs that dumpdata materializes but whose default is NOT
# inert in a fixture: a row that carries word_count must carry the one its
# body_html gives (tests_fixture), and loaddata leaves 0. Absent in the source
# means absent in the output — backfill_word_count fills them after load.
DROPPED_IF_ABSENT = {
    ("library.article", "word_count"),
}

# Hand-written fixtures spell timestamps their own way ("…00.000Z", or with
# microseconds); Django's serializer writes "…00Z" and truncates to
# milliseconds. Same instant, different string — compared as instants, and the
# source's spelling is kept on write so a regen doesn't churn every such file.
TIMESTAMP_FIELDS = {"created_at", "updated_at"}


def _ms(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.replace(microsecond=dt.microsecond // 1000 * 1000)


def same_value(field: str, old, new) -> bool:
    if old == new:
        return True
    if field in TIMESTAMP_FIELDS and isinstance(old, str) and isinstance(new, str):
        try:
            return _ms(old) == _ms(new)
        except ValueError:
            return False
    return False


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
    if m in ("library.author", "library.series"):
        return (m, f["slug"])
    if m in ("library.book", "library.sermon", "library.article", "library.plan"):
        return (m, f["slug"], f.get("language", "en"))
    if m == "library.seriestranslation":
        return (m, tuple(f["series"]), f["language"])
    if m == "library.chapter":
        return (m, tuple(f["book"]), f["order"])
    if m == "library.planday":
        return (m, tuple(f["plan"]), f["day"])
    return (m, json.dumps(f, sort_keys=True))


def split_layout(rows: list[dict]) -> dict[Path, list[dict]]:
    """Assign every dumped row to its file, preserving in-file load order."""
    by_model: dict[str, list[dict]] = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)

    files: dict[Path, list[dict]] = {
        AUTHORS_FILE: by_model.get("library.author", []),
        SERIES_FILE: by_model.get("library.series", [])
        + by_model.get("library.seriestranslation", []),
    }

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

    for a in by_model.get("library.article", []):
        f = a["fields"]
        files[ARTICLES_DIR / work_filename(f["slug"], f.get("language", "en"))] = [a]

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
    if not (CONTENT_DIR.is_dir() and ordered_fixture_paths()):
        sys.exit("no content fixtures found under fixtures/content/ — nothing to regenerate.")
    src_rows = load_all_rows()
    load_args = [str(p) for p in ordered_fixture_paths()]
    if src_rows and "pk" in src_rows[0]:
        sys.exit("source fixture is pk-format — regenerate from a natural-key layout.")
    src_ids = sorted(identity(r) for r in src_rows)

    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, "DJANGO_DEBUG": "true",
               "DATABASE_URL": f"sqlite:///{td}/regen.sqlite3"}
        print("→ migrate (fresh scratch DB)")
        manage(env, "migrate", "--verbosity", "0")
        print(f"→ loaddata ({len(load_args)} fixture file(s), ordered)")
        manage(env, "loaddata", *load_args, "--verbosity", "0")
        print(f"→ dumpdata ({len(MODELS)} models, natural keys)")
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
            if k in old and not same_value(k, old[k], v):
                drift.append((identity(r), k))
            elif k in TIMESTAMP_FIELDS and k in old:
                r["fields"][k] = old[k]
        for k in old:
            if k not in r["fields"]:
                drift.append((identity(r), "-" + k))
    if drift:
        sys.exit(f"FIELD DRIFT on {len(drift)} value(s), e.g. {drift[:3]} — aborting.")
    materialized = Counter(
        (r["model"], k)
        for r in new_rows
        for k in r["fields"]
        if k not in src_by_id[identity(r)]
        and (r["model"], k) not in DEFAULTED_OK | DROPPED_IF_ABSENT
    )
    if materialized:
        detail = ", ".join(f"{m}.{k}×{n}" for (m, k), n in sorted(materialized.items()))
        sys.exit(
            f"{len(materialized)} unexpected new field(s) across "
            f"{sum(materialized.values())} row(s) — aborting.\n"
            f"  {detail}\n"
            "If a field is a semantically-inert model default, add it to "
            "DEFAULTED_OK; otherwise exclude it from the dump."
        )

    # --- write the layout ----------------------------------------------------
    normalize = "--normalize" in sys.argv[1:]
    for r in new_rows:
        old = src_by_id[identity(r)]
        for k in [k for k in r["fields"] if k not in old]:
            if normalize and (r["model"], k) not in DROPPED_IF_ABSENT:
                continue
            del r["fields"][k]
    files = split_layout(new_rows)
    assert sum(len(v) for v in files.values()) == len(new_rows)
    # Write the full layout to a sibling temp dir, then swap — a crash mid-write
    # must never leave a half-empty content/ in the working tree.
    staging = CONTENT_DIR.with_name("content.regen-tmp")
    if staging.exists():
        shutil.rmtree(staging)
    rewritten = 0
    for path, rows in files.items():
        target = staging / path.relative_to(CONTENT_DIR)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not normalize and path.exists() and json.loads(path.read_text()) == rows:
            shutil.copy2(path, target)
        else:
            target.write_text(render_rows(rows))
            rewritten += 1
    shutil.rmtree(CONTENT_DIR)
    staging.rename(CONTENT_DIR)
    print(f"✓ regenerated: {len(new_rows)} rows across {len(files)} files "
          f"in {CONTENT_DIR.relative_to(BACKEND)}; {rewritten} rewritten")
    print("Run `manage.py test library.tests_fixture` to confirm the gate.")


if __name__ == "__main__":
    main()
