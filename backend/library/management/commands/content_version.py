"""Print (or bake) the reader-content digest.

The API publishes this on ``/api/health/`` and the web build waits for it to
match before prerendering (frontend/scripts/await-api-release.mjs), so being
able to ask for it by hand is how you tell "the reader is stale" from "the
reader is fine and something else is wrong".

``--write`` is the image build's use: computing the digest means reading ~90 MB
off disk, which is fine once during a build and not fine on a liveness probe.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.content_fixtures import BAKED_DIGEST_FILE, compute_content_digest


class Command(BaseCommand):
    help = "Print the reader-content digest; --write bakes it for the image."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write",
            action="store_true",
            help=f"Write it to {BAKED_DIGEST_FILE.name} for the running image to serve.",
        )

    def handle(self, *args, **opts):
        digest = compute_content_digest()
        if opts["write"]:
            BAKED_DIGEST_FILE.write_text(digest + "\n")
            self.stdout.write(f"{digest} → {BAKED_DIGEST_FILE}")
        else:
            self.stdout.write(digest)
