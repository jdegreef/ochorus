"""Stored full-text search vectors (Postgres only).

``Chapter.search_vector`` and ``Sermon.search_vector`` are tsvector columns,
GIN-indexed (migration 0041), so search reads are index lookups instead of
building ``to_tsvector`` over every row's body at query time. The stored
vector bakes in exactly the fields the old query-time SearchVector used —
including the related book title and author name — so recall and ranking are
unchanged ("wesley prayer" still matches Wesley's chapters by author name).

Kept fresh the same way ``body_text`` is:
- ``save()`` hooks refresh affected rows — a chapter/sermon refreshes itself,
  and because related text is baked in, ``Book.save()`` refreshes its
  chapters and ``Author.save()`` refreshes the author's chapters + sermons.
- ``backfill_search_vectors`` (release step) fills NULL vectors — fixture
  loads bypass ``save()``, exactly like ``backfill_body_text``. Its ``--all``
  flag rebuilds everything: the remedy after any save-bypassing write — a raw
  ``queryset.update()``, or a data migration's historical-model ``.save()``,
  neither of which runs these hooks (see backend/CLAUDE.md).
- Migration 0041 populates existing rows once on already-deployed databases.

Table names are spelled out in the SQL (matching migration 0041's index DDL);
these are Django's defaults and none of the models set ``db_table``.

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
# Both alias the updated table ``t`` so scope clauses ({extra}) are shared.
_CHAPTER_SQL = """
UPDATE library_chapter AS t
SET search_vector =
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(b.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(a.name, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.body_text, '')), 'C')
FROM library_book AS b
JOIN library_author AS a ON a.id = b.author_id
WHERE b.id = t.book_id AND b.language = %(language)s{extra}
"""

_SERMON_SQL = """
UPDATE library_sermon AS t
SET search_vector =
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.title, '')), 'A') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(a.name, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.scripture_ref, '')), 'B') ||
    setweight(to_tsvector(%(config)s::regconfig, coalesce(t.body_text, '')), 'C')
FROM library_author AS a
WHERE a.id = t.author_id AND t.language = %(language)s{extra}
"""


def _refresh(template: str, language: str, extra: str = "", **params) -> int:
    if connection.vendor != "postgresql":
        return 0
    params.update(config=config_for(language), language=language)
    with connection.cursor() as cursor:
        cursor.execute(template.format(extra=extra), params)
        return cursor.rowcount


def refresh_chapter(chapter) -> None:
    """Recompute one chapter's vector (called from Chapter.save)."""
    # Vendor check before touching chapter.book — on SQLite that relation
    # access could cost a SELECT just to feed a no-op.
    if connection.vendor != "postgresql":
        return
    _refresh(
        _CHAPTER_SQL, chapter.book.language, " AND t.id = %(id)s", id=chapter.pk
    )


def refresh_sermon(sermon) -> None:
    """Recompute one sermon's vector (called from Sermon.save)."""
    _refresh(_SERMON_SQL, sermon.language, " AND t.id = %(id)s", id=sermon.pk)


def refresh_book_chapters(book) -> None:
    """Recompute a book's chapters' vectors (called from Book.save).

    The book title is baked into each chapter's vector, so a retitle must
    ripple. On create this matches zero rows (no chapters yet) — free.
    """
    _refresh(
        _CHAPTER_SQL, book.language, " AND b.id = %(book_id)s", book_id=book.pk
    )


def refresh_author_works(author) -> None:
    """Recompute an author's chapters' + sermons' vectors (Author.save).

    The author name is baked into both; their works may span languages, so
    refresh per language (each language's rows use its own config).
    """
    if connection.vendor != "postgresql":
        return
    from .models import Book, Sermon

    # .order_by() clears Meta ordering — without it Django folds the ordering
    # columns into SELECT DISTINCT, returning each language once per row and
    # re-running the corpus-wide UPDATE N times.
    author_books = Book.objects.filter(author=author).order_by()
    for language in author_books.values_list("language", flat=True).distinct():
        _refresh(
            _CHAPTER_SQL, language, " AND a.id = %(author_id)s", author_id=author.pk
        )
    author_sermons = Sermon.objects.filter(author=author).order_by()
    for language in author_sermons.values_list("language", flat=True).distinct():
        _refresh(
            _SERMON_SQL, language, " AND a.id = %(author_id)s", author_id=author.pk
        )


def backfill(only_null: bool = True) -> tuple[int, int]:
    """Populate stored vectors; returns (chapters, sermons) rows updated.

    ``only_null=True`` (the release step) touches only rows loaddata created
    with no vector — idempotent and cheap on a healthy database. ``--all``
    rebuilds everything (after a save-bypassing bulk rename).
    """
    if connection.vendor != "postgresql":
        return (0, 0)
    extra = " AND t.search_vector IS NULL" if only_null else ""
    counts = []
    # Languages via raw SQL, not the ORM: migration 0041 calls this, and live
    # models there would drag post-0041 columns (e.g. Meta ordering fields)
    # into a query that replays against the 0041-era schema on a fresh chain.
    # Chapters carry no language column of their own — it lives on Book.
    for template, language_table in (
        (_CHAPTER_SQL, "library_book"),
        (_SERMON_SQL, "library_sermon"),
    ):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT DISTINCT language FROM {language_table}")
            languages = [row[0] for row in cursor.fetchall()]
        counts.append(sum(_refresh(template, lang, extra) for lang in languages))
    return (counts[0], counts[1])
