"""Mark an AI-translated article as reviewed after a native speaker approves it.

The article counterpart of ``approve_translation`` / ``approve_sermon_translation``.
Flips source_type ai_unreviewed → ai_reviewed, which removes the "awaiting
review" badge on the article page. Ship the flip to prod like any data change.

All three share ``_approve_source_type`` — see that module for why the fixture
write matters and why it warns rather than raises. An article names its headline
``h1`` (it has no author, hence no ``title``), so ``title_field`` points there.

Usage:
    manage.py approve_article_translation <slug> --language es
"""

from library import content_fixtures as cf
from library.management.commands._approve_source_type import ApproveSourceTypeCommand
from library.models import Article


class Command(ApproveSourceTypeCommand):
    help = "Mark an AI-translated article as reviewed (removes the unreviewed badge)."

    model = Article
    noun = "article"
    title_field = "h1"

    @staticmethod
    def fixture_path(slug: str, language: str):
        return cf.article_fixture_path(slug, language)
