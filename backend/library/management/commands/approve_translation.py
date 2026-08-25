"""Mark an AI translation as reviewed after a native speaker has approved it.

Flips source_type ai_unreviewed → ai_reviewed, which removes the "awaiting
review" badge in the reader. Ship the flip to prod like any data change.

The work is in ``_approve_source_type``, shared with the sermon command — they
were the same file twice, and the fixture round-trip they both depend on is
subtle enough that it should exist once. See that module.

Usage:
    manage.py approve_translation <slug> --language sw
"""

from library import content_fixtures as cf
from library.management.commands._approve_source_type import ApproveSourceTypeCommand
from library.models import Book


class Command(ApproveSourceTypeCommand):
    help = "Mark an AI-translated book as reviewed (removes the unreviewed badge)."

    model = Book
    noun = "book"

    @staticmethod
    def fixture_path(slug: str, language: str):
        return cf.book_fixture_path(slug, language)
