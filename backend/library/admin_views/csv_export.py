"""Shared helpers for the admin CSV exports (content inventory, user directory).

A CSV opened in Excel/Sheets treats a cell that starts with ``= + - @`` (or a
tab/CR) as a formula, so a curated title or a reader-controlled display name that
happens to begin with one of those can execute on open. ``csv_safe`` neutralises
that; ``csv_response`` bakes in the UTF-8 BOM Excel needs to read non-ASCII text.
"""

from __future__ import annotations

# Leading characters a spreadsheet may interpret as the start of a formula.
_FORMULA_LEADERS = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value) -> str:
    """A CSV cell that a spreadsheet won't run as a formula.

    A value beginning ``= + - @`` (or a tab/CR) is prefixed with an apostrophe —
    otherwise Excel/Sheets may execute it when the admin opens the export. Used
    for any cell that isn't a fixed literal or a number: titles, author names,
    source URLs, reader display names.
    """
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in _FORMULA_LEADERS else s


def csv_response(text: str, filename: str):
    """A ``text/csv`` download of ``text``, prefixed with a UTF-8 BOM so Excel
    reads non-ASCII titles/names correctly rather than as mojibake."""
    from django.http import HttpResponse

    resp = HttpResponse("\ufeff" + text, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp
