"""The indexes exist, and each one names a query that could not use what existed.

Every index added here serves a query whose leading column the model's existing
UNIQUE constraint does not match — which is why none of them could be served by
what was already there. `unique(slug, language)` cannot answer "published books
in this language, ordered for the shelf"; `unique(profile, kind, book_slug)`
cannot answer "how many readers per work"; `unique(topic, book_slug)` cannot
answer "which shelves is this book on".

What these tests DO check: the index reaches the database, on both backends, and
covers the columns the query filters and sorts by.

What they deliberately do NOT check: that the planner chooses it. With a handful
of test rows Postgres correctly prefers a sequential scan whatever indexes exist,
so an EXPLAIN assertion here would either be vacuous or force a plan the planner
is right to reject. Index CHOICE is a production-shaped question; index PRESENCE
is what a test can honestly hold.
"""

from __future__ import annotations

from django.db import connection
from django.test import TestCase

from .models import (
    AuthorTranslation,
    Book,
    Chapter,
    SearchQueryLog,
    Sermon,
    TopicBook,
    TopicSermon,
)


def _indexes(model) -> dict[str, list[str]]:
    """``{index name: [columns]}`` as the database actually has them."""
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor, model._meta.db_table
        )
    return {
        name: c["columns"]
        for name, c in constraints.items()
        if c.get("index") and not c.get("unique")
    }


class QueryIndexTests(TestCase):
    def assertIndexed(self, model, name, columns):
        found = _indexes(model)
        self.assertIn(
            name,
            found,
            f"{model.__name__} is missing {name}; it has {sorted(found)}",
        )
        self.assertEqual(
            found[name],
            columns,
            f"{name} covers {found[name]}, not {columns}",
        )

    def test_the_book_shelf_query_is_indexed(self):
        """BookListView: filter(is_published, language) → order_by(sort_order, title)."""
        self.assertIndexed(
            Book, "idx_book_shelf", ["language", "is_published", "sort_order", "title"]
        )

    def test_the_sermon_shelf_query_is_indexed(self):
        self.assertIndexed(
            Sermon,
            "idx_sermon_shelf",
            ["language", "is_published", "sort_order", "title"],
        )

    def test_topic_membership_is_indexed_by_slug(self):
        """"Which shelves is this book on?" runs on every book page."""
        self.assertIndexed(TopicBook, "idx_topicbook_slug", ["book_slug"])
        self.assertIndexed(TopicSermon, "idx_topicsermon_slug", ["sermon_slug"])

    def test_author_translations_are_indexed_by_language(self):
        self.assertIndexed(AuthorTranslation, "idx_authortr_language", ["language"])

    def test_the_search_log_is_indexed_by_language_and_time(self):
        """Popular searches and the admin report both filter on both columns."""
        self.assertIndexed(
            SearchQueryLog, "idx_searchlog_lang_at", ["language", "created_at"]
        )

    def test_the_unstamped_chapter_scan_is_indexed(self):
        """index_citations asks for this on every deploy."""
        self.assertIndexed(Chapter, "idx_chapter_uncited", ["citations_indexed_at"])

    def test_the_index_leads_with_a_column_the_unique_constraint_cannot(self):
        """The reason these are needed at all, stated as an assertion.

        Book's unique constraint is (slug, language). The shelf query never
        mentions `slug`, so a composite leading with it is unusable — which is
        why the shelf was a sequential scan despite "having an index".
        """
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, Book._meta.db_table
            )
        unique = [
            c["columns"] for c in constraints.values() if c.get("unique") and c["columns"]
        ]
        self.assertIn(["slug", "language"], unique)
        # The shelf query filters language + is_published; no unique index leads
        # with `language`, so none of them can serve it.
        self.assertFalse(
            any(cols[0] == "language" for cols in unique),
            "a unique index already leads with language — re-check whether "
            "idx_book_shelf is still earning its place",
        )
