"""The bundled Bible texts, served from an on-disk SQLite file.

Why: the API runs one gunicorn worker on a 512 MB instance, and holding the
Bibles as Python dicts cost it resident memory for the life of the process —
OWB English ~11 MB (it answers every popover and /scripture/ page), the
ASV that `scripture._asv_text` reads through pythonbible ~15 MB (the sermon
page's opening-text check), OWB Amharic ~18 MB. Read from disk they cost a
connection's page cache per thread instead, and the OS page cache does the rest.

What: one read-only SQLite file holding, per Bible (``owb-<language>`` for each
``data/bible/owb-<language>-b.json.gz``, and ``asv``), every verse's text by
verse id, and OWB's joined verses (1 Kings 18:34 printed under 18:33). Its rows
are a verbatim copy of the committed bundles — the bundles stay the source of
truth, and ``scripture`` keeps the lookups' shape; see ``tests_bible_store``.

Where: ``<backend>/.cache/bible/bibles-<digest>.sqlite`` (``OCHORUS_BIBLE_STORE_DIR``
overrides the folder). The digest covers the bundles' bytes, the ASV package's
version and this module's ``SCHEMA``, so a changed bundle is a new file, never a
stale one. The image bakes it at build time (``manage.py build_bible_store`` in
the Dockerfile); anywhere else (dev, tests, CI) the first lookup builds it.
It is deliberately NOT under ``data/bible``: that folder is a content root
hashed into the reader digest (``content_sources.json``), and a generated
file there would move it.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
from importlib import metadata
from pathlib import Path

BIBLE_DIR = Path(__file__).resolve().parent / "data" / "bible"
STORE_DIR = Path(
    os.environ.get("OCHORUS_BIBLE_STORE_DIR") or Path(__file__).resolve().parent.parent / ".cache" / "bible"
)
ASV = "asv"
#: Bump when the tables change shape: it is part of the file's digest.
SCHEMA = 1

_lock = threading.Lock()
_local = threading.local()
_path: Path | None = None
_bibles: frozenset[str] | None = None


def _bundles() -> list[Path]:
    return sorted(BIBLE_DIR.glob("owb-*-b.json.gz"))


def _asv_version() -> str:
    try:
        return metadata.version("pythonbible-asv")
    except metadata.PackageNotFoundError:
        return "absent"


def digest() -> str:
    """Fingerprint of everything the store is built from."""
    h = hashlib.sha256(f"schema {SCHEMA}\nasv {_asv_version()}\n".encode())
    for path in _bundles():
        h.update(path.name.encode() + b"\0")
        with path.open("rb") as fh:
            while chunk := fh.read(1 << 16):
                h.update(chunk)
    return h.hexdigest()[:16]


def _asv_rows():
    """(id, text) for every verse the ASV has, through pythonbible's own
    ``get_verse_text`` — the call ``scripture._asv_text`` made — so the text
    is what it returned, byte for byte."""
    try:
        import pythonbible as bible
        from pythonbible.formatter import get_bible
        from pythonbible.versions import Version

        ids = sorted(get_bible(Version.AMERICAN_STANDARD, "plain_text_readers").verse_start_indices)
    except Exception:
        return
    for vid in ids:
        try:
            text = bible.get_verse_text(vid, version=Version.AMERICAN_STANDARD)
        except Exception:
            continue
        yield vid, text


def build(path: Path) -> None:
    """Write the store to ``path``, atomically (a temp file, then a rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".building-", suffix=".sqlite")
    os.close(fd)
    try:
        db = sqlite3.connect(tmp)
        db.executescript(
            """
            PRAGMA journal_mode = OFF;
            CREATE TABLE verse (bible TEXT NOT NULL, id INTEGER NOT NULL, text TEXT NOT NULL,
                                PRIMARY KEY (bible, id)) WITHOUT ROWID;
            CREATE TABLE joined (bible TEXT NOT NULL, id INTEGER NOT NULL, target INTEGER NOT NULL,
                                 PRIMARY KEY (bible, id)) WITHOUT ROWID;
            CREATE TABLE bible (name TEXT PRIMARY KEY) WITHOUT ROWID;
            """
        )
        for bundle in _bundles():
            name = "owb-" + bundle.name[len("owb-") : -len("-b.json.gz")]
            with gzip.open(bundle, "rt", encoding="utf-8") as fh:
                data = json.load(fh)
            db.execute("INSERT INTO bible VALUES (?)", (name,))
            db.executemany(
                "INSERT INTO verse VALUES (?, ?, ?)", ((name, int(k), v) for k, v in data["verses"].items())
            )
            db.executemany(
                "INSERT INTO joined VALUES (?, ?, ?)", ((name, int(k), int(v)) for k, v in data["joined"].items())
            )
            del data
        db.execute("INSERT INTO bible VALUES (?)", (ASV,))
        db.executemany("INSERT INTO verse VALUES (?, ?, ?)", ((ASV, vid, t) for vid, t in _asv_rows()))
        db.commit()
        db.execute("VACUUM")
        db.close()
        os.chmod(tmp, 0o644)  # mkstemp's 0600 would hide it from another user
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def ensure_built(directory: Path | None = None) -> Path:
    """The store's path, built first if this digest has none yet."""
    directory = directory or STORE_DIR
    path = directory / f"bibles-{digest()}.sqlite"
    if not path.is_file():
        try:
            build(path)
        except OSError:
            # A read-only checkout: build where the OS keeps temp files.
            path = Path(tempfile.gettempdir()) / "ochorus-bible" / path.name
            if not path.is_file():
                build(path)
        for old in path.parent.glob("bibles-*.sqlite"):
            if old != path:
                old.unlink(missing_ok=True)
    return path


def _resolve() -> Path:
    global _path, _bibles
    if _path is None:
        with _lock:
            if _path is None:
                path = ensure_built()
                db = _open(path)
                _bibles = frozenset(name for (name,) in db.execute("SELECT name FROM bible"))
                _local.db = (path, os.getpid(), db)
                _path = path
    return _path


def _open(path: Path) -> sqlite3.Connection:
    # immutable=1: the file never changes once renamed into place, so SQLite
    # skips locking; a small page cache, since the OS caches the file anyway.
    db = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    db.execute("PRAGMA cache_size = -512")
    return db


def _db() -> sqlite3.Connection:
    """This thread's read-only connection (gunicorn serves on four threads)."""
    path = _resolve()
    held = getattr(_local, "db", None)
    # Keyed on the pid too: a connection must not cross a fork.
    if held is None or held[:2] != (path, os.getpid()):
        held = (path, os.getpid(), _open(path))
        _local.db = held
    return held[2]


def has(bible: str) -> bool:
    _resolve()
    return bible in _bibles


def text(bible: str, verse_id: int) -> str | None:
    """The text stored under one verse id, or None when there is none."""
    row = _db().execute("SELECT text FROM verse WHERE bible = ? AND id = ?", (bible, verse_id)).fetchone()
    return row[0] if row else None


def joined_to(bible: str, verse_id: int) -> int | None:
    """The id an OWB joined verse is printed under, or None when it isn't joined."""
    row = _db().execute("SELECT target FROM joined WHERE bible = ? AND id = ?", (bible, verse_id)).fetchone()
    return row[0] if row else None


def between(bible: str, low: int, high: int) -> list[tuple[int, str]]:
    """(id, text) for every stored verse with ``low < id < high``, in id order."""
    return _db().execute(
        "SELECT id, text FROM verse WHERE bible = ? AND id > ? AND id < ? ORDER BY id", (bible, low, high)
    ).fetchall()


def reset() -> None:
    """Forget the resolved file (tests point ``STORE_DIR`` elsewhere)."""
    global _path, _bibles
    with _lock:
        _path = _bibles = None
        _local.__dict__.clear()
