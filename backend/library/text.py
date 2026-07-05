"""Plain-text derivation from chapter HTML.

One canonical place for the HTML→text rule so the stored ``Chapter.body_text``
(used by search) is always derived the same way — from the model's save(), the
backfill command, and the data migration.
"""

from __future__ import annotations

import html
import re

from django.utils.html import strip_tags

# Block-level tags become word boundaries so "…end.</p><p>Start…" doesn't fuse
# into "end.Start" in the text (which would break both matching and snippets).
_BLOCK_BREAK = re.compile(r"</(p|div|h[1-6]|li|blockquote|br)>|<br\s*/?>", re.I)
_WS = re.compile(r"\s+")


def html_to_text(body_html: str) -> str:
    spaced = _BLOCK_BREAK.sub(" \\g<0>", body_html)
    return _WS.sub(" ", html.unescape(strip_tags(spaced))).strip()
