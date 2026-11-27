"""Is this upload a work the library already has?

An import picks a fresh slug when its title's slug is taken (``-2``, ``-3``…),
so publishing the same book twice never errors — it quietly makes a second
copy. That has happened: ``corrections.RETIRED_BOOKS`` exists to bury the
copies. This finds the likely originals BEFORE publish, so the admin sees them
and decides, instead of a reader finding two of everything.

Matching is deliberately simple and cheap: the same kind, in the same
language, with a title that reads the same once case, punctuation, accents
and a leading article are set aside, or is very close to it. A shared
author makes a near miss count. It is a prompt to look, never a block on its
own — the publish endpoint lets the admin go ahead once they have seen it.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from .models import Book, Sermon

#: How close two normalised titles must be to be worth showing. 1.0 is equal.
SAME_AUTHOR_RATIO = 0.8
ANY_AUTHOR_RATIO = 0.92
LIMIT = 5

_ARTICLE = re.compile(r"^(?:the|a|an)\s+")


def normalise(title: str) -> str:
    """``"The Pilgrim's Progress"`` → ``"pilgrims progress"``.

    An edition suffix such as "(For Teens)" is KEPT: a young-reader edition is
    a separate work by the slug convention, not a copy of the full text."""
    t = unicodedata.normalize("NFKD", title or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return _ARTICLE.sub("", t)


def similar_works(
    kind: str, title: str, language: str, author_slug: str = ""
) -> list[dict]:
    """The existing works this upload is likely a copy of, closest first."""
    from .corrections import RETIRED_BOOKS

    wanted = normalise(title)
    if not wanted:
        return []
    model = Book if kind == "book" else Sermon
    rows = model.objects.filter(language=language).values_list(
        "slug", "title", "author__slug", "author__name", "is_published"
    )
    out = []
    for slug, other, a_slug, a_name, published in rows:
        if kind == "book" and slug in RETIRED_BOOKS:
            continue
        ratio = SequenceMatcher(None, wanted, normalise(other)).ratio()
        same_author = bool(author_slug) and a_slug == author_slug
        if ratio >= (SAME_AUTHOR_RATIO if same_author else ANY_AUTHOR_RATIO):
            out.append(
                {
                    "kind": kind,
                    "slug": slug,
                    "title": other,
                    "author": a_name,
                    "same_author": same_author,
                    "is_published": published,
                    "match": round(ratio, 2),
                    "admin_path": f"/admin/{'books' if kind == 'book' else 'sermons'}/{slug}",
                }
            )
    out.sort(key=lambda r: (-r["match"], not r["same_author"]))
    return out[:LIMIT]
