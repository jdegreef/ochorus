"""Bake the on-disk Bible store (``library/bible_store.py``) for the image.

The Dockerfile runs this so a fresh container's first Scripture lookup reads a
file that is already there, instead of building it (seconds, and the memory of
the very dicts the store exists to keep out of the worker) on a live request.
Anywhere else the first lookup builds it; running this by hand is harmless.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library import bible_store


class Command(BaseCommand):
    help = "Build the SQLite copy of the bundled Bibles the API reads verses from."

    def handle(self, *args, **opts):
        self.stdout.write(str(bible_store.ensure_built()))
