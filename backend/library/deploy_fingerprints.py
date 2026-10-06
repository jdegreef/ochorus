"""Change detectors that let the release skip text it already checked.

Three release steps used to read the whole corpus (~170 MB of chapter and
sermon HTML) out of Supabase on every deploy to change nothing:
``apply_body_corrections``, ``refresh_translation_digests`` and seed_books'
chapter compare. That was roughly half a gigabyte of database egress per
deploy, dozens of times a day.

The fix is to hash in Postgres, not in Python. ``md5()`` runs where the text
lives, so a comparison ships 32 hex characters per row instead of the body,
and a step fetches a body only when its hash says the text moved.

A step that remembers what it checked stores a KEY on the row: the md5 of
``version + the text``, where ``version`` hashes the source of the code that
judged it. A row whose stored key differs from the key computed now changed
since (by any path, including a migration's ``.update()``) or was judged by
older code, so it is checked again. Everything else is skipped without being
read.

``keyed_md5`` (SQL) and ``keyed_md5_hex`` (Python) must agree byte for byte;
``DeployFingerprintTests`` pins that on both database backends.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType

from django.db.models import TextField, Value
from django.db.models.functions import MD5, Coalesce, Concat

#: Between parts, so ("ab", "c") and ("a", "bc") hash differently. A unit
#: separator can't occur in titles or HTML (translation_staleness uses it too).
SEP = "\x1f"


def md5_hex(text: str) -> str:
    """Python's twin of SQL ``md5(text)``. A change detector, not security."""
    return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()


def source_version(*modules: ModuleType) -> str:
    """A short hash of these modules' source files.

    Folded into a key so that changing the code that judged a row re-checks
    every row, without anyone having to remember to bump a number."""
    h = hashlib.sha256()
    for module in modules:
        h.update(Path(module.__file__).read_bytes())
    return h.hexdigest()[:16]


def keyed_md5(version: str, *fields: str) -> MD5:
    """SQL ``md5(version || SEP || field || SEP || field ...)``.

    A NULL field counts as empty, matching ``keyed_md5_hex``'s ``""``."""
    parts = [Value(version)]
    for name in fields:
        parts += [Value(SEP), Coalesce(name, Value(""), output_field=TextField())]
    return MD5(Concat(*parts, output_field=TextField()))


def keyed_md5_hex(version: str, *values: str | None) -> str:
    """Python's twin of ``keyed_md5``, for the row a step just judged."""
    return md5_hex(version + "".join(SEP + (v or "") for v in values))
