"""Mark an AI translation as reviewed after a native speaker has approved it.

Flips source_type ai_unreviewed → ai_reviewed, which removes the "awaiting
review" badge in the reader. Ship the flip to prod like any data change.

Usage:
    manage.py approve_translation <slug> --language sw
"""

from django.core.management.base import BaseCommand, CommandError

from library.models import Book


class Command(BaseCommand):
    help = "Mark an AI-translated book as reviewed (removes the unreviewed badge)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--language", required=True)

    def handle(self, slug, language, **opts):
        try:
            book = Book.objects.get(slug=slug, language=language)
        except Book.DoesNotExist:
            raise CommandError(f"no book {slug!r} in language {language!r}")
        if book.source_type == Book.SourceType.PUBLIC_DOMAIN:
            raise CommandError("that book is a public-domain original, not a translation")
        book.source_type = Book.SourceType.AI_REVIEWED
        book.save(update_fields=["source_type"])
        self.stdout.write(self.style.SUCCESS(f"✓ {book.title} ({language}) marked reviewed"))
