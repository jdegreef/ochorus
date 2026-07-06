"""Apply body-text corrections + trailing-number cleanup to stored chapters.

The same fixes run automatically on every import; this command backfills rows
that were imported before the corrections existed. Idempotent — safe to re-run.
`Chapter.save()` re-derives body_text, so search stays in step.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.corrections import BODY_CORRECTIONS, apply_body_corrections
from library.ingest import strip_trailing_pagenum
from library.models import Chapter


class Command(BaseCommand):
    help = "Backfill body corrections + trailing-number strip over stored chapters."

    def handle(self, *args, **opts):
        fixed = 0
        for chapter in Chapter.objects.select_related("book").iterator(chunk_size=100):
            slug = chapter.book.slug
            new = strip_trailing_pagenum(chapter.body_html)
            if slug in BODY_CORRECTIONS:
                new = apply_body_corrections(slug, chapter.order, new)
            if new != chapter.body_html:
                chapter.body_html = new
                chapter.save()
                fixed += 1
                self.stdout.write(f"  fixed {slug}/{chapter.order}")
        msg = f"Corrected {fixed} chapters." if fixed else "Nothing to correct."
        self.stdout.write(self.style.SUCCESS(msg))
