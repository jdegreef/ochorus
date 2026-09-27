"""Refresh the translation-staleness fingerprints (see library/translation_staleness).

Runs every deploy in ``release``, after the content seeds have settled every
book, sermon and article — so the fingerprints describe the text the site now
serves. Idempotent: a second run changes nothing. Reads the whole corpus's text
once (streamed), like ``apply_body_corrections`` does.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library import translation_staleness


class Command(BaseCommand):
    help = "Recompute content digests and re-baseline changed translations."

    def handle(self, *args, **options):
        for kind in translation_staleness.KINDS:
            c = translation_staleness.refresh(kind)
            self.stdout.write(
                f"  {kind}s: {c['updated']} digest(s) updated, "
                f"{c['rebaselined']} translation(s) re-baselined, "
                f"{c['stale']} translation(s) behind their English"
            )
