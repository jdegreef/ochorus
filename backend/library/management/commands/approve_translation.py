"""Mark an AI translation as reviewed after a native speaker has approved it.

Flips source_type ai_unreviewed → ai_reviewed, which removes the "awaiting
review" badge in the reader. Ship the flip to prod like any data change.

Usage:
    manage.py approve_translation <slug> --language sw
"""

from django.core.management.base import BaseCommand, CommandError

from library import content_fixtures as cf
from library.models import Book


class Command(BaseCommand):
    help = "Mark an AI-translated book as reviewed (removes the unreviewed badge)."

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
            book = Book.objects.get(slug=slug, language=language)
        except Book.DoesNotExist:
            raise CommandError(f"no book {slug!r} in language {language!r}")
        if book.source_type == Book.SourceType.PUBLIC_DOMAIN:
            raise CommandError("that book is a public-domain original, not a translation")
        book.source_type = Book.SourceType.AI_REVIEWED
        book.save(update_fields=["source_type"])
        self.stdout.write(self.style.SUCCESS(f"✓ {book.title} ({language}) marked reviewed"))

        if no_fixture:
            return
        # Persist the approval into the committed fixture too, or a fresh-DB
        # rebuild would silently re-gate it to unreviewed (source_type is
        # create-only in the seed, so the live flip alone never round-trips).
        path = cf.book_fixture_path(slug, language)
        if path.exists():
            if cf.persist_source_type(path, Book.SourceType.AI_REVIEWED):
                self.stdout.write(f"  ↳ updated fixture {path.name} — commit it")
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ no fixture {path.name}: approval is DB-only and would be "
                    "lost on a rebuild. Serialize this book to a fixture and commit it."
                )
            )
