"""Mark AI-translated author bios as reviewed after a native speaker approves.

Flips AuthorTranslation.reviewed False → True. Ship the flip to prod like any
data change.

Usage:
    manage.py approve_author_translation --language es            # all in es
    manage.py approve_author_translation andrew-murray --language sw
"""

from django.core.management.base import BaseCommand, CommandError

from library.models import AuthorTranslation


class Command(BaseCommand):
    help = "Mark AI-translated author bios as reviewed."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Author slugs (default: all in the language)")
        parser.add_argument("--language", required=True)

    def handle(self, slugs, language, **opts):
        qs = AuthorTranslation.objects.filter(language=language, reviewed=False)
        if slugs:
            qs = qs.filter(author__slug__in=slugs)
        rows = list(qs)
        if not rows:
            raise CommandError(f"no unreviewed author bios in language {language!r}")
        for tr in rows:
            tr.reviewed = True
            tr.save(update_fields=["reviewed"])
            self.stdout.write(self.style.SUCCESS(f"✓ {tr.author.slug} ({language}) reviewed"))
        self.stdout.write(self.style.SUCCESS(f"{len(rows)} bio(s) marked reviewed"))
