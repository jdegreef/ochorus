"""Translation staleness: has the English changed since a translation was made?

A translated Book, Sermon or Article is a copy of one English edition's text.
When that English is later corrected, extended or rewritten, the translation
still reads the old text — and nothing in the content records which English it
came from (the pipeline writes only the translated rows). This module keeps two
DB-only fingerprints per row, refreshed once per deploy after the seeds:

``content_digest``
    sha256 of the row's own text as it stands now (a book: every chapter's
    order, title and body; a sermon: title and body; an article: h1 and body).

``english_digest``
    On a translation only: the English edition's ``content_digest`` when this
    translation was last (re)made. A translation is **stale** when this no
    longer matches the English's current ``content_digest``.

A translation is (re)baselined — ``english_digest`` set to the English's current
digest — when it has none yet (new, or every translation on the first deploy
after this shipped), or when its OWN text changed this deploy (a re-translation,
or chapters topped up to match a longer English). Everything else leaves it
alone, so an English fix with no matching translation fix is exactly what makes
a translation stale.

Why DB-only rather than a field in the fixture: the fixture is written by many
parallel translation sessions, and a baseline for ~1,000 existing translations
would have meant rewriting every one of their files. The seeds own the text;
this owns the fingerprints, and the seeds never touch them.

Known limits, deliberately accepted:
- The first deploy assumes every existing translation matches today's English.
- An English change that ships in the SAME deploy as any change to a
  translation's own text re-baselines that translation (the usual case is an
  English-fix PR that fixes the translations alongside — which is right).
- Any English change counts, a typo fix included — except pure typography
  (``typographic_form``: dashes, quotation marks, ellipses, entities,
  whitespace), which is setting the same words differently. ``mark_current``
  re-baselines one translation once someone has checked it still matches.
"""

from __future__ import annotations

import hashlib
import html
import re
from collections.abc import Iterable

from django.db import transaction

from .models import Article, Book, Chapter, Sermon
from .originals import ORIGINAL_SOURCE_TYPE, is_original

KINDS = ("book", "sermon", "article")
_MODEL = {"book": Book, "sermon": Sermon, "article": Article}
_SEP = "\x1f"  # unit separator: can't occur in titles or HTML


#: Typography the fingerprint ignores. Each is a way of SETTING the same
#: words, not a change to them, and the corpus is repaired in exactly these
#: ways in bulk: #4936 set 4,460 typewriter dashes as em dashes and flagged
#: ~97 translations whose wording was untouched. A dash in any form (and the
#: space around it), a quotation mark in any style, an ellipsis spelled out
#: or as one glyph, an entity or its character, and runs of whitespace all
#: fingerprint alike. Letters, case, digits, words and markup still count — a
#: lowercased "GOD" or a restored paragraph IS a change a translation follows.
_DASH = re.compile(r"\s*(?:[—–―‒]|-{2,})+\s*")
_DOUBLE_QUOTE = re.compile(r"[“”„‟«»\"]")
_SINGLE_QUOTE = re.compile(r"[‘’‚‛]")
_SPACE = re.compile(r"\s+")


def typographic_form(text: str) -> str:
    """``text`` with its typography folded — what the fingerprint hashes."""
    t = html.unescape(text or "").replace("…", "...")
    t = _DASH.sub("—", t)
    t = _DOUBLE_QUOTE.sub('"', t)
    t = _SINGLE_QUOTE.sub("'", t)
    return _SPACE.sub(" ", t).strip()


def _update(h, part: str) -> None:
    h.update(typographic_form(part).encode("utf-8"))
    h.update(_SEP.encode())


def _digest(parts: Iterable[str]) -> str:
    h = hashlib.sha256()
    for p in parts:
        _update(h, p)
    return h.hexdigest()


def _book_digests() -> dict[int, str]:
    """book_id → digest over its chapters in order. Streamed, one book at a
    time: the corpus is hundreds of MB and must never be held in memory."""
    out: dict[int, str] = {}
    current: int | None = None
    h = None
    rows = (
        Chapter.objects.order_by("book_id", "order")
        .values_list("book_id", "order", "title", "body_html")
        .iterator(chunk_size=200)
    )
    for book_id, order, title, body in rows:
        if book_id != current:
            if h is not None:
                out[current] = h.hexdigest()
            current, h = book_id, hashlib.sha256()
        for p in (str(order), title, body):
            _update(h, p)
    if h is not None:
        out[current] = h.hexdigest()
    return out


def _row_digests(kind: str) -> dict[int, str]:
    if kind == "book":
        digests = _book_digests()
        # A book with no chapters still gets a (constant) digest, so it is
        # comparable rather than "unknown".
        for pk in Book.objects.values_list("pk", flat=True):
            digests.setdefault(pk, _digest(()))
        return digests
    title = "title" if kind == "sermon" else "h1"
    rows = (
        _MODEL[kind]
        .objects.order_by()
        .values_list("pk", title, "body_html")
        .iterator(chunk_size=200)
    )
    return {pk: _digest((t, body)) for pk, t, body in rows}


def _is_translation(row) -> bool:
    # An original-language edition (Pascal's own French) is not a copy of the
    # English — the English is the translation — so it has no English baseline
    # and is never stale. See `library.originals`.
    return row.language != "en" and not is_original(row.language, row.source_type)


def refresh(kind: str) -> dict[str, int]:
    """Recompute every row's ``content_digest`` for one kind and (re)baseline the
    translations that need it. Returns counts for the deploy log."""
    model = _MODEL[kind]
    new = _row_digests(kind)
    rows = list(
        model.objects.only("pk", "slug", "language", "source_type", "content_digest", "english_digest")
    )
    english = {r.slug: new[r.pk] for r in rows if r.language == "en"}

    touched = []
    rebaselined = 0
    for r in rows:
        own_changed = r.content_digest != new[r.pk]
        r.content_digest = new[r.pk]
        if _is_translation(r):
            en = english.get(r.slug, "")
            if en and (not r.english_digest or own_changed) and r.english_digest != en:
                r.english_digest = en
                rebaselined += 1
                own_changed = True
        if own_changed:
            touched.append(r)
    with transaction.atomic():
        # bulk_update, not save(): these fields feed no search vector or hook,
        # and save() would also bump updated_at for every row on every deploy.
        model.objects.bulk_update(
            touched, ["content_digest", "english_digest"], batch_size=500
        )
    stale = sum(
        1
        for r in rows
        if _is_translation(r) and r.slug in english and r.english_digest != english[r.slug]
    )
    return {"updated": len(touched), "rebaselined": rebaselined, "stale": stale}


def stale_languages(kind: str) -> dict[str, list[str]]:
    """slug → languages whose translation predates the current English. Cheap:
    reads only the stored digests, never the text."""
    model = _MODEL[kind]
    english = dict(
        model.objects.filter(language="en").exclude(content_digest="").values_list(
            "slug", "content_digest"
        )
    )
    out: dict[str, list[str]] = {}
    for slug, lang, baseline in (
        model.objects.exclude(language="en")
        .exclude(source_type=ORIGINAL_SOURCE_TYPE)
        .exclude(english_digest="")
        .values_list("slug", "language", "english_digest")
    ):
        en = english.get(slug)
        if en and en != baseline:
            out.setdefault(slug, []).append(lang)
    return out


def mark_current(kind: str, slug: str, language: str) -> bool:
    """Someone checked this translation against the current English and it still
    holds (e.g. the English change was a typo fix): re-baseline it. Survives
    deploys — the refresh only re-baselines on a change to the translation's own
    text. Returns False when there's no such translation or English edition."""
    model = _MODEL[kind]
    en = (
        model.objects.filter(slug=slug, language="en")
        .values_list("content_digest", flat=True)
        .first()
    )
    if not en or language == "en":
        return False
    return bool(
        model.objects.filter(slug=slug, language=language).update(english_digest=en)
    )
