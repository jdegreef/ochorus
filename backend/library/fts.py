"""Stored full-text search vectors (Postgres only).

``Chapter.search_vector`` and ``Sermon.search_vector`` are tsvector columns,
GIN-indexed (migration 0040), so search reads are index lookups instead of
building ``to_tsvector`` over every row's body at query time. The stored
vector bakes in exactly the fields the old query-time SearchVector used —
including the related book title and author name — so recall and ranking are
unchanged ("wesley prayer" still matches Wesley's chapters by author name).

Kept fresh three ways, mirroring the ``body_text`` pattern:
- ``Chapter.save()`` / ``Sermon.save()`` refresh the row (all normal writes:
  imports, admin uploads, corrections).
- ``backfill_search_vectors`` (release step) fills NULL vectors — fixture
  loads bypass ``save()``, exactly like ``backfill_body_text``.
- Migration 0040 populates existing rows once on already-deployed databases.

Known staleness edge: renaming an author or a book does NOT ripple into
already-stored chapter/sermon vectors (their vectors embed the old name).
Renames are rare and ship via imports/migrations that re-save chapters; after
a bare rename, run ``manage.py backfill_search_vectors --all``.

Everything here no-ops on SQLite (dev) — the SQLite search path uses
icontains and never reads these columns.
"""

from __future__ import annotations

from django.db import connection

# Postgres text-search configs by language (fall back to "simple", which
# matches exact words without stemming — right for lg/sw/etc.).
FTS_CONFIGS = {
    "en": "english",
    "fr": "french",
    "es": "spanish",
    "pt": "portuguese",
}


def config_for(language: str) -> str:
    return FTS_CONFIGS.get(language, "simple")


# Same weights as the old query-time vectors in search._search_postgres:
# chapter = title A + book title A + author B + body C;
# sermon = title A + author B + scripture_ref B + body C.
_CHAPTER_SQL = """
UPDATE {chapter} AS c
SET search_vector =
    setweight(to_tsvector(%(config)s::regconfig, coalesce(c.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(b.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(a.name, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(c.body_text, '')), 'C')
FROM {book} AS b
JOIN {author} AS a ON a.id = b.author_id
WHERE b.id = c.book_id AND b.language = %(language)s{extra}
"""

_SERMON_SQL = """
UPDATE {sermon} AS s
SET search_vector =
    setweight(to_tsvector(%(config)s::regconfig, coalesce(s.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(a.name, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(s.scripture_ref, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(s.body_text, '')), 'C')
FROM {author} AS a
WHERE a.id = s.author_id AND s.language = %(language)s{extra}
"""


def _tables():
    # Imported lazily: models.py imports this module for the save() hooks.
    from .models import Author, Book, Chapter, Sermon

    return {
        "chapter": Chapter._meta.db_table,
        "book": Book._meta.db_table,
        "sermon": Sermon._meta.db_table,
        "author": Author._meta.db_table,
    }


def _run(template: str, params: dict, extra: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(template.format(extra=extra, **_tables()), params)
        return cursor.rowcount


def refresh_chapter(chapter) -> None:
    """Recompute one chapter's vector (called from Chapter.save)."""
    if connection.vendor != "postgresql":
        return
    language = chapter.book.language
    _run(
        _CHAPTER_SQL,
        {"config": config_for(language), "language": language, "id": chapter.pk},
        extra=" AND c.id = %(id)s",
    )


def refresh_sermon(sermon) -> None:
    """Recompute one sermon's vector (called from Sermon.save)."""
    if connection.vendor != "postgresql":
        return
    _run(
        _SERMON_SQL,
        {
            "config": config_for(sermon.language),
            "language": sermon.language,
            "id": sermon.pk,
        },
        extra=" AND s.id = %(id)s",
    )


def backfill(only_null: bool = True) -> tuple[int, int]:
    """Populate stored vectors; returns (chapters, sermons) rows updated.

    ``only_null=True`` (the release step) touches only rows loaddata created
    with no vector — idempotent and cheap on a healthy database. ``--all``
    rebuilds everything (after an author/book rename).
    """
    if connection.vendor != "postgresql":
        return (0, 0)
    from .models import Book, Sermon

    chapters = 0
    extra = " AND c.search_vector IS NULL" if only_null else ""
    for language in Book.objects.values_list("language", flat=True).distinct():
        chapters += _run(
            _CHAPTER_SQL,
            {"config": config_for(language), "language": language},
            extra=extra,
        )
    sermons = 0
    extra = " AND s.search_vector IS NULL" if only_null else ""
    for language in Sermon.objects.values_list("language", flat=True).distinct():
        sermons += _run(
            _SERMON_SQL,
            {"config": config_for(language), "language": language},
            extra=extra,
        )
    return (chapters, sermons)
