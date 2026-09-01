"""Invalidate caches and rebuild after a content change made directly in the DB.

Reader-visible content changed through the admin API (import publish, review
approval, go-live) or the deploy seeds is covered automatically: the API bumps
the content revision, and a deploy moves the content digest. A change made
DIRECTLY in the database — the documented urgent copyright pull, or a manual SQL
fix — bypasses both, so the public ETag would keep answering 304 against it and
the prerendered reader would stay stale. Run this after such a change: it bumps
the revision (busting every ETag so clients re-fetch) and fires the deploy hook
(so the static site rebuilds).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library import invalidation


class Command(BaseCommand):
    help = "Bump the content revision and rebuild after a direct-DB content change."

    def handle(self, *args, **options):
        result = invalidation.mark_content_changed(force=True)
        self.stdout.write("Content revision bumped.")
        style = self.style.SUCCESS if result and result.ok else self.style.WARNING
        detail = f"{result.status}: {result.detail}" if result else "no deploy hook fired"
        self.stdout.write(style(f"Deploy: {detail}"))
