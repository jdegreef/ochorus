"""Fill word_count for rows that have prose but a zero count (chapters, sermons).

Unlike body_text, which Chapter.save()/Sermon.save() keep in step with
body_html, NOTHING recomputes word_count after creation: it is set once, by
``ingest.word_count`` at import time. So a row that arrives by any other route
— a fixture load (loaddata bypasses save()), a translation written straight to
body_html, a ``queryset.update()`` — keeps whatever count it was created with,
and a row created without one keeps zero forever.

That is not cosmetic. ``word_count`` drives the per-chapter reading-time
estimate in the TOC drawer and the length sort on the books shelf, so a zero
means a chapter with no reading time and a book that sorts as the shortest in
the library.

Run on every deploy (see the release command) — idempotent and a no-op once
everything is filled.

DELIBERATELY ONLY ZEROES, mirroring backfill_body_text's "fill what is empty"
contract: a stale non-zero count (body edited after creation) is a different
problem, and recomputing every row on every deploy would rewrite the whole
corpus to fix the few that drifted.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from library.ingest import word_count
from library.models import Chapter, Sermon


class Command(BaseCommand):
    help = "Derive word_count from body_html for chapters/sermons showing zero."

    def handle(self, *args, **opts):
        for model, label in ((Chapter, "chapters"), (Sermon, "sermons")):
            # A genuinely empty body SHOULD count zero, so those are left alone
            # rather than rewritten to the same value on every deploy.
            missing = model.objects.filter(word_count=0).exclude(
                Q(body_html="") | Q(body_html__isnull=True)
            )
            count = 0
            for row in missing.iterator(chunk_size=200):
                words = word_count(row.body_html)
                if not words:
                    continue  # markup with no words in it — zero is correct
                model.objects.filter(pk=row.pk).update(word_count=words)
                count += 1
            if count:
                self.stdout.write(
                    self.style.SUCCESS(f"Backfilled word_count for {count} {label}.")
                )
            else:
                self.stdout.write(f"All {label} already have a word_count.")
