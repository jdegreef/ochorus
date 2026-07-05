"""Fill Chapter.body_text for rows where it's empty.

Chapter.save() keeps body_text in step with body_html, but fixture loads
(loaddata in seed_if_empty) bypass custom save(), so freshly seeded rows arrive
without it. Run on every deploy (see the release command) — idempotent and a
no-op once everything is filled.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.models import Chapter
from library.text import html_to_text


class Command(BaseCommand):
    help = "Derive body_text from body_html for chapters missing it."

    def handle(self, *args, **opts):
        missing = Chapter.objects.filter(body_text="")
        count = 0
        for chapter in missing.iterator(chunk_size=200):
            Chapter.objects.filter(pk=chapter.pk).update(
                body_text=html_to_text(chapter.body_html)
            )
            count += 1
        if count:
            self.stdout.write(self.style.SUCCESS(f"Backfilled body_text for {count} chapters."))
        else:
            self.stdout.write("All chapters already have body_text.")
