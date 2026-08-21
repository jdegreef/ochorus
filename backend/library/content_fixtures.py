"""The split content-fixture layout (Stage 2 of the fixture architecture).

Content lives under ``library/fixtures/content/`` as one file per WORK, in
natural-key format (no integer pks — see Stage 1 / ``tests_fixture``):

    content/
      authors.json                    all Author rows (low churn, shared)
      books/<slug>.<language>.json    one Book row followed by its Chapters
      sermons/<slug>.<language>.json  one Sermon row
      plans.json                      Plan rows, each followed by its PlanDays

Why per work: parallel sessions add content constantly; separate files make
concurrent additions conflict-free by construction and diffs reviewable (a new
translation is one new file, not a 300-line splice into a 50 MB tail).

LOAD ORDER MATTERS. Every FK here is NOT NULL, and Django's forward-reference
deferral cannot bridge that — so ``ordered_fixture_paths()`` is the one source
of truth for ordering (authors first, then books, sermons, plans) and
``seed_if_empty`` passes ALL files to a single ``loaddata`` call in that order.
Within a book file the Book row precedes its Chapters; within plans.json each
Plan precedes its PlanDays.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "fixtures" / "content"

AUTHORS_FILE = CONTENT_DIR / "authors.json"
BOOKS_DIR = CONTENT_DIR / "books"
SERMONS_DIR = CONTENT_DIR / "sermons"
PLANS_FILE = CONTENT_DIR / "plans.json"


@lru_cache(maxsize=1)
def content_digest() -> str:
    """A fingerprint of the content fixtures this build shipped with.

    Published on ``/api/health/`` so the web build can tell whether the API is
    already serving the content it is about to prerender against
    (``frontend/scripts/await-api-release.mjs``).

    Why content and not the git commit: only the API's ``rootDir`` is
    ``backend/``, so Render skips its build when a commit touches nothing there.
    A frontend-only commit therefore deploys the web service ALONE, and the API
    legitimately keeps reporting an older SHA — a build that waited for the SHA
    to match would wait for a deploy that is never coming. The narrower question
    "does the API hold the content I am about to bake into static pages?" always
    has an answer, and for a frontend-only commit the answer is yes, instantly.

    Every ``*.json`` under ``content/``, by sorted relative path — deliberately
    a simpler rule than ``ordered_fixture_paths()``, because the reader of this
    digest is a JavaScript file that has to reproduce it exactly. ``tests_fixture``
    already rejects any file under ``content/`` that the layout does not load, so
    the two sets cannot drift apart.

    SCOPE: ``content/`` only, matching render.yaml's ``buildFilter``
    (``backend/library/fixtures/**``) — the gate covers exactly what
    auto-triggers a web build. Other seed data that reaches prerendered pages
    (``library/data/plan_translations/``, ``library/migrations/data/author_bios_*``)
    is outside BOTH, so a commit touching only those doesn't rebuild the reader
    at all and its pages stay on the previous prose until some later build. That
    is the pre-existing gap DEPLOYMENT.md describes for backend-only changes —
    widening this digest would not close it, since nothing would be watching.
    """
    h = hashlib.sha256()
    for path in sorted(CONTENT_DIR.rglob("*.json"), key=lambda p: p.relative_to(CONTENT_DIR).as_posix()):
        h.update(path.relative_to(CONTENT_DIR).as_posix().encode())
        h.update(b"\0")
        h.update(hashlib.sha256(path.read_bytes()).hexdigest().encode())
        h.update(b"\0")
    return h.hexdigest()[:16]


def work_filename(slug: str, language: str) -> str:
    """``<slug>.<language>.json`` — slugs are [a-z0-9-], so ``.`` is safe."""
    return f"{slug}.{language}.json"


def book_fixture_path(slug: str, language: str) -> Path:
    """The committed fixture file for a book edition (may not exist yet)."""
    return BOOKS_DIR / work_filename(slug, language)


def sermon_fixture_path(slug: str, language: str) -> Path:
    """The committed fixture file for a sermon edition (may not exist yet)."""
    return SERMONS_DIR / work_filename(slug, language)


def persist_fields(path: Path, values: dict[str, str]) -> bool:
    """Rewrite string fields of a work fixture's Book/Sermon row in place,
    returning True if the file changed.

    Textual, not load-modify-dump: the committed files aren't uniformly formatted
    (``regen_fixture`` uses records at column 0 / indent=1; a few are indent=2),
    and re-serialising would rewrite a whole file whose real change is one field,
    making a review-state flip read as a content edit.

    Safe as a whole-file substitution only for keys the row alone carries —
    ``source_type``, ``cover_url``, ``cover_color``; chapters have none of them —
    so exactly one match per key is asserted rather than assumed.

    All substitutions happen in memory and the file is written once, so a key
    that isn't there raises before anything lands: patching cover_url and
    cover_color as two writes could leave a file holding the first and not the
    second.
    """
    original = text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        pattern = rf'("{key}"\s*:\s*)"(?:[^"\\]|\\.)*"'
        text, n = re.subn(pattern, lambda m, v=value: m.group(1) + json.dumps(v), text)
        if n != 1:
            raise ValueError(f"{path.name}: expected exactly one {key}, found {n}")
    if text == original:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def persist_field(path: Path, key: str, value: str) -> bool:
    """One field of ``persist_fields``; True if the file changed."""
    return persist_fields(path, {key: value})


def persist_source_type(path: Path, source_type: str) -> bool:
    """Flip a work fixture's ``source_type`` in place; True if it changed.

    This is what makes an approval DURABLE. ``seed_books`` keeps ``source_type``
    create-only, so on an existing DB a live approval survives deploys — but a
    fresh-DB rebuild (``seed_if_empty`` loaddata) loads the fixture verbatim, so
    without writing the flip here the committed file would silently re-gate the
    translation back to unreviewed.
    """
    return persist_field(path, "source_type", source_type)


def ordered_fixture_paths() -> list[Path]:
    """Every content fixture file, in the only order loaddata can load them."""
    paths: list[Path] = []
    if AUTHORS_FILE.exists():
        paths.append(AUTHORS_FILE)
    for d in (BOOKS_DIR, SERMONS_DIR):
        if d.is_dir():
            paths.extend(sorted(d.glob("*.json")))
    if PLANS_FILE.exists():
        paths.append(PLANS_FILE)
    return paths


def load_all_rows() -> list[dict]:
    """All content rows across the split layout, in load order.

    The seed commands and the CI gate consume this. A corrupt file raises with
    its PATH named — with 119 files, "some file is broken" must never collapse
    into "no fixtures available".
    """
    rows: list[dict] = []
    for path in ordered_fixture_paths():
        try:
            rows.extend(json.loads(path.read_text()))
        except ValueError as exc:
            raise ValueError(f"corrupt content fixture {path}: {exc}") from exc
    return rows


def unexpected_files() -> list[Path]:
    """Files under content/ that the layout does NOT load.

    A fixture written to the wrong place (content/ root, a .json.new suffix, a
    nested dir) is silently invisible to loaddata AND the seeds — this is how
    the CI gate makes that loud.
    """
    sanctioned = set(ordered_fixture_paths())
    return sorted(
        p for p in CONTENT_DIR.rglob("*") if p.is_file() and p not in sanctioned
    )


def rows_by_file() -> dict[Path, list[dict]]:
    """Per-file rows, for checks that validate file-content coherence."""
    return {p: json.loads(p.read_text()) for p in ordered_fixture_paths()}


def authors_by_slug(rows: list[dict] | None = None) -> dict[str, dict]:
    """The fixture's author rows, keyed by slug — ``{slug: fields}``.

    "Pick the library.author rows out and key them by slug" was written inline
    seven times (both seed commands, migrations 0049/0051/0052/0053, the CI
    gate), so the definition of "which rows are authors" drifted per copy.
    Pass ``rows`` when you already have the whole fixture loaded — the seeds do,
    and re-reading authors.json there would be wasted I/O on every deploy.
    """
    if rows is None:
        rows = json.loads(AUTHORS_FILE.read_text())
    return {
        r["fields"]["slug"]: r["fields"]
        for r in rows
        if r.get("model") == "library.author"
    }
