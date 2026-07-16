"""Mark an AI-translated sermon as reviewed after a native speaker approves it.

The sermon counterpart of ``approve_translation``. Flips source_type
ai_unreviewed → ai_reviewed, which removes the "awaiting review" badge on the
sermon page. Ship the flip to prod like any data change.

Usage:
    manage.py approve_sermon_translation <slug> --language sw
"""

from django.core.management.base import BaseCommand, CommandError

from library.models import Book, Sermon


class Command(BaseCommand):
    help = "Mark an AI-translated sermon as reviewed (removes the unreviewed badge)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--language", required=True)

    def handle(self, slug, language, **opts):
        try:
            sermon = Sermon.objects.get(slug=slug, language=language)
        except Sermon.DoesNotExist:
            raise CommandError(f"no sermon {slug!r} in language {language!r}")
        if sermon.source_type == Book.SourceType.PUBLIC_DOMAIN:
            raise CommandError("that sermon is a public-domain original, not a translation")
        sermon.source_type = Book.SourceType.AI_REVIEWED
        sermon.save(update_fields=["source_type"])
        self.stdout.write(self.style.SUCCESS(f"✓ {sermon.title} ({language}) marked reviewed"))
