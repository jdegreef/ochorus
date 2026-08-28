"""Apply body-text corrections + trailing-number cleanup to stored works.

The same fixes run automatically on every import; this command backfills rows
that were imported before the corrections existed. Idempotent — safe to re-run.
`save()` re-derives body_text and word_count, so search and the reading-time
estimates stay in step with the body this rewrites.

Covers chapters AND sermons. Sermons joined BODY_CORRECTIONS when the sermon
importer started using it; until this ran over them too, a sermon entry in the
table was inert in production — the corrected text only ever reached prod if
someone happened to regenerate the fixture in the same session.

Every work is visited, not only those with a declared entry, because
`apply_body_corrections` now also carries the line-break hyphen rejoin — a rule
rather than a list. That is what lets 429 stored defects across 39 works repair
themselves on the next deploy instead of needing a migration.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.corrections import apply_body_corrections
from library.ingest import strip_trailing_pagenum
from library.models import Chapter, Sermon


class Command(BaseCommand):
    help = "Backfill body corrections + trailing-number strip over chapters and sermons."

    def handle(self, *args, **opts):
        fixed = 0
        # Defer the two heaviest columns. This command reads only body_html
        # and writes it back; body_text and word_count are re-derived by
        # Chapter.save() (which assigns them, un-deferring body_text so it IS
        # written), and the tsvector is refreshed by fts.refresh_chapter's own
        # UPDATE — none of the three needs to be fetched. Together the deferred
        # two are roughly two thirds of the bytes this scan pulled, on EVERY
        # deploy, to change nothing in the steady state.
        for chapter in (
            Chapter.objects.select_related("book")
            .defer("body_text", "search_vector")
            .iterator(chunk_size=100)
        ):
            slug = chapter.book.slug
            new = strip_trailing_pagenum(chapter.body_html)
            # Unconditional: `apply_body_corrections` now carries the line-break
            # hyphen rejoin, which is a RULE and applies to every work, not only
            # the 22 with a hand-written entry. For a slug with no entry the rest
            # of the call is a no-op.
            new = apply_body_corrections(slug, chapter.order, new)
            if new != chapter.body_html:
                chapter.body_html = new
                chapter.save()
                fixed += 1
                self.stdout.write(f"  fixed {slug}/{chapter.order}")
        sermons_fixed = 0
        # Every sermon, not just those with an entry — same reason as above.
        for sermon in Sermon.objects.defer("body_text", "search_vector").iterator(
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
