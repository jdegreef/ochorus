"""Mark an AI-translated sermon as reviewed after a native speaker approves it.

The sermon counterpart of ``approve_translation``. Flips source_type
ai_unreviewed → ai_reviewed, which removes the "awaiting review" badge on the
sermon page. Ship the flip to prod like any data change.

Usage:
    manage.py approve_sermon_translation <slug> --language sw
"""

from django.core.management.base import BaseCommand, CommandError

from library import content_fixtures as cf
from library.models import Book, Sermon


class Command(BaseCommand):
    help = "Mark an AI-translated sermon as reviewed (removes the unreviewed badge)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--language", required=True)
        parser.add_argument(
            "--no-fixture",
            action="store_true",
            help="Flip only the DB row; don't update the committed fixture file.",
        )

    def handle(self, slug, language, no_fixture=False, **opts):
        try:
            sermon = Sermon.objects.get(slug=slug, language=language)
        except Sermon.DoesNotExist:
            raise CommandError(f"no sermon {slug!r} in language {language!r}")
        if sermon.source_type == Book.SourceType.PUBLIC_DOMAIN:
            raise CommandError("that sermon is a public-domain original, not a translation")
        sermon.source_type = Book.SourceType.AI_REVIEWED
        sermon.save(update_fields=["source_type"])
        self.stdout.write(self.style.SUCCESS(f"✓ {sermon.title} ({language}) marked reviewed"))

        if no_fixture:
            return
        # Persist the approval into the committed fixture too, or a fresh-DB
        # rebuild would silently re-gate it to unreviewed (source_type is
        # create-only in the seed, so the live flip alone never round-trips).
        path = cf.sermon_fixture_path(slug, language)
        if not path.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ no fixture {path.name}: approval is DB-only and would be "
                    "lost on a rebuild. Serialize this sermon to a fixture and commit it."
                )
            )
            return
        # The DB flip is the primary action and has already succeeded; a fixture
        # write failure (unexpected match count, read-only filesystem) must warn,
        # not raise — a traceback here would read to an automated caller as "the
        # approval failed" and trigger a retry.
        try:
            if cf.persist_source_type(path, Book.SourceType.AI_REVIEWED):
                self.stdout.write(f"  ↳ updated fixture {path.name} — commit it")
        except (ValueError, OSError) as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ DB approved, but couldn't update fixture {path.name}: {exc}. "
                    "Set source_type to ai_reviewed there by hand and commit it."
                )
            )
