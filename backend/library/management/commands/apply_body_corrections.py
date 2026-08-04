"""Apply body-text corrections + trailing-number cleanup to stored works.

The same fixes run automatically on every import; this command backfills rows
that were imported before the corrections existed. Idempotent — safe to re-run.
`save()` re-derives body_text, so search stays in step.

Covers chapters AND sermons. Sermons joined BODY_CORRECTIONS when the sermon
importer started using it; until this ran over them too, a sermon entry in the
table was inert in production — the corrected text only ever reached prod if
someone happened to regenerate the fixture in the same session.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.corrections import BODY_CORRECTIONS, apply_body_corrections
from library.ingest import strip_trailing_pagenum
from library.models import Chapter, Sermon


class Command(BaseCommand):
    help = "Backfill body corrections + trailing-number strip over chapters and sermons."

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
        sermons_fixed = 0
        for sermon in Sermon.objects.filter(slug__in=BODY_CORRECTIONS).iterator(
            chunk_size=100
        ):
            # order=None: sermons have no chapters, so no drop-cap may apply.
            new_html = apply_body_corrections(sermon.slug, None, sermon.body_html)
            if new_html != sermon.body_html:
                sermon.body_html = new_html
                sermon.save()
                sermons_fixed += 1
                self.stdout.write(f"  fixed sermon {sermon.slug}/{sermon.language}")

        parts = []
        if fixed:
            parts.append(f"{fixed} chapters")
        if sermons_fixed:
            parts.append(f"{sermons_fixed} sermons")
        msg = f"Corrected {', '.join(parts)}." if parts else "Nothing to correct."
        self.stdout.write(self.style.SUCCESS(msg))
