"""Mark an AI-translated sermon as reviewed after a native speaker approves it.

The sermon counterpart of ``approve_translation``. Flips source_type
ai_unreviewed → ai_reviewed, which removes the "awaiting review" badge on the
sermon page. Ship the flip to prod like any data change.

Both commands share ``_approve_source_type`` — see that module for why the
fixture write matters and why it warns rather than raises.

Usage:
    manage.py approve_sermon_translation <slug> --language sw
"""

from library import content_fixtures as cf
from library.management.commands._approve_source_type import ApproveSourceTypeCommand
from library.models import Sermon


class Command(ApproveSourceTypeCommand):
    help = "Mark an AI-translated sermon as reviewed (removes the unreviewed badge)."

    model = Sermon
    noun = "sermon"

    @staticmethod
    def fixture_path(slug: str, language: str):
        return cf.sermon_fixture_path(slug, language)
