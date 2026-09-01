"""Fire the web deploy hook if any content change is still un-deployed.

The leading-edge throttle in ``library/invalidation`` can leave the LAST change of
a burst un-deployed: its rebuild fired at the start of the throttle window and may
have read the DB before that last change landed, and nothing fires again until the
next change. This is the trailing-edge safety net — run it on a schedule (or by
hand) and it rebuilds once, only when there is genuinely an un-deployed change.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library import invalidation


class Command(BaseCommand):
    help = "Fire the web deploy hook if content changed since the last rebuild."

    def handle(self, *args, **options):
        result = invalidation.flush_deploy()
        if result is None:
            self.stdout.write("No un-deployed content changes; nothing to do.")
            return
        style = self.style.SUCCESS if result.ok else self.style.WARNING
        self.stdout.write(style(f"{result.status}: {result.detail}"))
