#!/usr/bin/env python3
"""Re-clean every Gutenberg-sourced work and diff the two sanitizers.

Project Gutenberg puts ``class="pginternal"`` on every internal link, so the
sanitizer's old blanket drop selector deleted the author's own cross-references
along with the navigation — text included. `library/sanitize.py` now decides by
the link's TEXT, and this is the corpus-wide check on that predicate.

It is not a spot-check: for every Gutenberg book and sermon the catalogs name it
runs the REAL extraction (``import_gutenberg.extract_chapters`` /
``import_sermons.extract_gutenberg_section``) twice over the same source — once
with the old blanket drop, once with the new predicate — and diffs the chapter
bodies. That keeps the measurement to what actually reaches a reader: the TOC
table, the transcriber's notes and the rest of the front matter the importer
already drops never enter the comparison.

For each body that changes it prints the text the new predicate admits, and
whether the SHIPPED English fixture (corrections applied — what a reader sees)
already contains it. A "MISSING" line is damage already on the shelf. Repair
those with `corrections.py` string pairs, as `ministry-of-intercession` has:
re-importing is NOT the channel — `ingest.upsert_book` deletes and recreates
every chapter, and restoring markup in English alone breaks the ordered-tag
parity with translations that `library/tests_translation_markup.py` enforces.

Sources are cached under --cache so re-runs don't re-hit gutenberg.org.

    uv run python scripts/audit_pginternal.py
    uv run python scripts/audit_pginternal.py --only ministry-of-intercession
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import json
import os
import sys
from functools import cache
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from library import corrections, sanitize  # noqa: E402
from library.catalog import BOOKS  # noqa: E402
from library.content_fixtures import (  # noqa: E402
    book_fixture_path,
    sermon_fixture_path,
)
from library.management.commands.import_gutenberg import (  # noqa: E402
    extract_chapters,
    fetch_html,
)
from library.management.commands.import_sermons import (  # noqa: E402
    extract_gutenberg_section,
)
from library.sermon_catalog import SERMONS  # noqa: E402
from library.text import text_of  # noqa: E402

# The shape the old blanket drop selector produced, and the shape it destroyed.
_PROBE = '<p>x<a class="pginternal" href="#n">Note A.</a>y</p>'


@contextlib.contextmanager
def blanket_drop():
    """Restore the OLD behaviour: every `pginternal` element decomposed.

    This reaches in and replaces a private predicate, so it is only as durable
    as that name. Inline the predicate or rename it and the patch becomes a
    no-op — and a no-op here does not fail, it reports every work UNCHANGED,
    which reads as good news. So the seam is checked on the way in: the probe is
    cleaned both ways and the run stops unless patching actually changed the
    result. Compared against the live unpatched output rather than a literal, so
    an unrelated change to how the sanitizer spaces its output cannot fake a
    broken harness.
    """
    unpatched = sanitize.clean_fragment(_PROBE)
    real = sanitize._is_pg_navigation
    sanitize._is_pg_navigation = lambda el: True
    try:
        if sanitize.clean_fragment(_PROBE) == unpatched:
            raise SystemExit(
                "audit harness is broken: patching sanitize._is_pg_navigation no "
                "longer changes cleaning, so every work would report 'unchanged'. "
                "Re-point blanket_drop at whatever now decides a pginternal "
                "element's fate."
            )
        yield
    finally:
        sanitize._is_pg_navigation = real


def works() -> list[tuple[str, str, str, str]]:
    """(kind, slug, gutenberg id, section) for every Gutenberg-sourced work."""
    out = [("book", b.slug, b.source_ref, "") for b in BOOKS if b.source == "gutenberg"]
    out += [("sermon", s.slug, s.source_ref, s.section)
            for s in SERMONS if s.source == "gutenberg"]
    return out


@cache
def source_html(book_id: str, cache: Path) -> str:
    """The ebook's HTML, fetched once per run and cached on disk between runs.

    Memoised because one ebook backs many sermons — PG #33520 carries six.
    """
    path = cache / f"pg{book_id}.html"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    html = fetch_html(book_id)
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return html


def extract(kind: str, html: str, section: str) -> list[tuple[str, str]]:
    if kind == "book":
        return extract_chapters(html)
    return [(section, extract_gutenberg_section(html, section))]


# How many preceding WORDS to carry as a probe. A recovered run is often a
# single word or a bracketed mark, and a bare "in" would "already ship" in every
# book — so the probe is the run WITH its context, which is what makes an "ok,
# already shipped" mean "this sentence reads right on the shelf" rather than
# "these letters occur somewhere in the book".
_PROBE_CONTEXT = 7


def added_runs(before: str, after: str) -> list[tuple[str, str]]:
    """(recovered run, run-with-context probe) for each insertion in `after`.

    Diffed by WORD, not by character. `SequenceMatcher` is quadratic in the
    sequence length, and over a ~30-symbol alphabet with `autojunk=False` every
    character matches thousands of positions — the character form spent ~10 of
    this script's ~15 minutes inside `find_longest_match`, and the corpus's long
    chapters are the worst of it (Brainerd's diary runs to 20,894 words). Words
    are ~5x shorter and far more distinct, and the runs come out as phrases,
    which is what the probe wants anyway.
    """
    if before == after:
        return []  # the common case, and not otherwise cheap
    a, b = before.split(), after.split()
    out: list[tuple[str, str]] = []
    for tag, _, _, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag not in ("insert", "replace"):
            continue
        run = " ".join(b[j1:j2]).strip()
        if run:
            out.append((run, " ".join(b[max(0, j1 - _PROBE_CONTEXT):j2]).strip()))
    return out


def shipped_text(kind: str, slug: str) -> str | None:
    """The English body a reader sees, corrections applied, tags stripped."""
    path = (book_fixture_path if kind == "book" else sermon_fixture_path)(slug, "en")
    if not path.exists():
        return None
    parts: list[str] = []
    for row in json.loads(path.read_text()):
        fields = row.get("fields") or {}
        body = fields.get("body_html")
        if not body:
            continue
        if kind == "book":
            body = corrections.settled_chapter_body(slug, fields.get("order"), body)
        else:
            body = corrections.settled_sermon_body(slug, body)
        parts.append(body)
    return text_of(" ".join(parts))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", action="append", default=[],
                    help="limit to these slugs (repeatable)")
    ap.add_argument("--cache", type=Path,
                    default=Path(os.environ.get("TMPDIR", "/tmp")) / "pg-source-cache",
                    help="directory for cached Gutenberg HTML")
    args = ap.parse_args()

    selected = [w for w in works() if not args.only or w[1] in args.only]
    if not selected:
        print("no matching Gutenberg works", file=sys.stderr)
        return 2

    failures: list[str] = []
    changed = 0
    missing: list[str] = []

    print(f"re-cleaning {len(selected)} Gutenberg-sourced works "
          "(old blanket drop vs new predicate)\n")
    for kind, slug, book_id, section in selected:
        try:
            html = source_html(book_id, args.cache)
        except Exception as exc:  # network / mirror trouble, not a finding
            failures.append(f"{slug} (#{book_id}): {exc}")
            print(f"  !! {slug:<44} #{book_id}  fetch failed: {exc}")
            continue

        with blanket_drop():
            old = extract(kind, html, section)
        new = extract(kind, html, section)

        if len(old) != len(new):
            # The predicate must not change how the book DIVIDES — only what a
            # body contains. A count change means a heading appeared/vanished.
            print(f"  ** {slug:<44} chapter count {len(old)} -> {len(new)}")

        diffs: list[tuple[str, list[tuple[str, str]]]] = []
        # strict=False: a count change is already reported above as an anomaly,
        # and comparing the bodies the two runs DO share is more useful than
        # raising.
        for (ot, ob), (nt, nb) in zip(old, new, strict=False):
            if ot != nt:
                # Titles come from `resolve_title`, which reads the heading
                # directly and never passes through the sanitizer — so this
                # should not move. Reported in place, like the count anomaly.
                print(f"  ** {slug:<44} title {ot!r} -> {nt!r}")
            runs = added_runs(text_of(ob), text_of(nb))
            if runs:
                diffs.append((nt, runs))

        if not diffs:
            print(f"  = {slug:<44} #{book_id:<7} unchanged")
            continue

        changed += 1
        body = shipped_text(kind, slug)
        print(f"  + {slug:<44} #{book_id:<7} {len(diffs)} body/bodies change")
        for title, runs in diffs:
            print(f"      [{title[:56]}]")
            for run, probe in runs:
                is_missing = body is not None and probe not in body
                if body is None:
                    mark = "no en fixture"
                elif is_missing:
                    mark = "MISSING from the shipped body"
                else:
                    mark = "ok, already shipped"
                print(f"        {run!r}  — {mark}")
                if is_missing:
                    missing.append(f"{slug} · {title}: …{probe!r}")
                    print(f"            context: …{probe}")

    print(f"\n{changed} of {len(selected)} works change; "
          f"{len(selected) - changed - len(failures)} are byte-identical.")

    if missing:
        print(f"\n{len(missing)} recovered text run(s) are NOT in the shipped "
              "bodies — already-shipped damage, repairable only via "
              "corrections.py string pairs (never a re-import):")
        for line in missing:
            print(f"    {line}")
    else:
        print("\nEvery recovered run is already present in the shipped English "
              "bodies — nothing beyond what corrections.py has repaired.")

    if failures:
        print(f"\n{len(failures)} source(s) could not be fetched:")
        for line in failures:
            print(f"    {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
