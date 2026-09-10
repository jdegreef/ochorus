"""Upsert the curated author-page timeline milestones (a release step).

Idempotent and code-owned: the definitions in ``library/author_milestones.py``
are the source of truth, re-asserted on every deploy (like ``seed_topics``). A
slug that isn't in the library yet is simply skipped, so this can run ahead of
an author landing. ``milestones`` is not part of the FTS vector, so a plain
``update`` skips no search-vector backfill (see the ship-content-fix skill).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.author_milestones import AUTHOR_MILESTONES
from library.models import Author


class Command(BaseCommand):
    help = "Seed hand-curated life milestones onto the author-page timeline."

    def handle(self, *args, **opts):
        by_slug = {a.slug: a for a in Author.objects.filter(slug__in=AUTHOR_MILESTONES)}
        updated = skipped = 0
        for slug, events in AUTHOR_MILESTONES.items():
            author = by_slug.get(slug)
            if author is None:
                skipped += 1
                continue
            if author.milestones != events:
                Author.objects.filter(pk=author.pk).update(milestones=events)
                updated += 1
        self.stdout.write(
            f"Author milestones: {updated} set, "
            f"{len(AUTHOR_MILESTONES) - skipped - updated} already current, {skipped} not in library."
        )
