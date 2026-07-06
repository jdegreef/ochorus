"""Fill body_text for rows where it's empty (chapters and sermons).

Chapter.save() / Sermon.save() keep body_text in step with body_html, but
fixture loads (loaddata in seed_if_empty) bypass custom save(), so freshly
seeded rows arrive without it. Run on every deploy (see the release command) —
idempotent and a no-op once everything is filled.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.models import Chapter, Sermon
from library.text import html_to_text


class Command(BaseCommand):
    help = "Derive body_text from body_html for chapters/sermons missing it."

    def handle(self, *args, **opts):
        for model, label in ((Chapter, "chapters"), (Sermon, "sermons")):
            missing = model.objects.filter(body_text="")
            count = 0
            for row in missing.iterator(chunk_size=200):
                model.objects.filter(pk=row.pk).update(
                    body_text=html_to_text(row.body_html)
                )
                count += 1
            if count:
                self.stdout.write(
                    self.style.SUCCESS(f"Backfilled body_text for {count} {label}.")
                )
            else:
                self.stdout.write(f"All {label} already have body_text.")
