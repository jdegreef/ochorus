"""Composite the curated public-domain artwork covers (tier 3).

    python manage.py build_curated_covers            # every curated slug
    python manage.py build_curated_covers confessions
    python manage.py build_curated_covers --dry-run

For each slug in library/curated_art.py this downloads the Met's open-access
image, crops it to the cover's 3:4 box, and composites the house-style type
over it — once per language the book is published in, so the art is shared and
only the type changes.

Run rarely: the output SVGs are committed, and the artwork doesn't change. The
downloads are cached under .cache/curated-art/ so a re-run doesn't re-fetch.

Cropping uses `sips`, which ships with macOS. This is a curation step run by
hand on a developer's machine, not something the deploy does — the committed
SVGs are what production serves — so a macOS-only dependency is acceptable
here. If it ever needs to run in CI, swap in Pillow.
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from library.covers import build_art_svg, cover_path
from library.curated_art import CURATED, credit
from library.models import Book

COVERS_DIR = settings.BASE_DIR.parent / "frontend" / "static" / "covers"
CACHE = settings.BASE_DIR.parent / ".cache" / "curated-art"
MET_API = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{}"
UA = {"User-Agent": "ochorus-cover-build/1.0 (+https://ochorus.com)"}
W, H = 600, 800


def _fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r, dest.open("wb") as f:
        shutil.copyfileobj(r, f)


def _met_image(met_id: int) -> Path:
    """The full-size open-access image, cached. Re-verifies isPublicDomain on
    every fetch rather than trusting the manifest — the manifest records what
    we believed, the API is what's true."""
    raw = CACHE / f"{met_id}.orig.jpg"
    if raw.exists():
        return raw
    req = urllib.request.Request(MET_API.format(met_id), headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        obj = json.load(r)
    if not obj.get("isPublicDomain"):
        raise CommandError(f"Met object {met_id} is NOT flagged public domain — refusing.")
    src = obj.get("primaryImage") or obj.get("primaryImageSmall")
    if not src:
        raise CommandError(f"Met object {met_id} has no image.")
    _fetch(src, raw)
    return raw


def _crop_3x4(src: Path, met_id: int) -> Path:
    """Scale to the cover height, then centre-crop to width. Scaling by HEIGHT
    matters: most of these are wide landscapes, and fitting them to width first
    would leave a letterbox rather than filling the plate."""
    out = CACHE / f"{met_id}.{W}x{H}.jpg"
    if out.exists():
        return out
    with tempfile.TemporaryDirectory() as td:
        step = Path(td) / "step.jpg"
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "--resampleHeight", str(H), str(src), "--out", str(step)],
            check=True, capture_output=True,
        )
        # Quality 55 is deliberate. These are 600x800 thumbnails behind a
        # scrim and a lot of type — the artefacts JPEG makes at this level are
        # invisible here, and it's the difference between a 235 KB cover and a
        # ~90 KB one. The designed covers on the same shelf are 19-51 KB.
        subprocess.run(
            ["sips", "-c", str(H), str(W), "-s", "formatOptions", "55",
             str(step), "--out", str(out)],
            check=True, capture_output=True,
        )
    return out


class Command(BaseCommand):
    help = "Composite curated public-domain artwork covers for the flagship titles."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Curated slugs (default: all).")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        slugs = opts["slugs"] or list(CURATED)
        unknown = [s for s in slugs if s not in CURATED]
        if unknown:
            raise CommandError(f"Not in the curated manifest: {', '.join(unknown)}")

        wrote = 0
        for slug in slugs:
            art = CURATED[slug]
            rows = list(Book.objects.select_related("author").filter(slug=slug))
            if not rows:
                self.stdout.write(self.style.WARNING(f"  – {slug}: no Book rows, skipping"))
                continue

            jpeg = _crop_3x4(_met_image(art.met_id), art.met_id)
            b64 = base64.b64encode(jpeg.read_bytes()).decode("ascii")

            for book in rows:
                url, rel = cover_path(slug, book.language)
                svg = build_art_svg(
                    title=book.title,
                    subtitle=book.subtitle,
                    author=book.author.name,
                    jpeg_b64=b64,
                    language=book.language,
                    credit=credit(slug) or "",
                )
                if not opts["dry_run"]:
                    dest = COVERS_DIR / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(svg, encoding="utf-8")
                    if book.cover_url != url:
                        book.cover_url = url
                        book.save(update_fields=["cover_url"])
                wrote += 1
                kb = len(svg) // 1024
                self.stdout.write(f"  ✓ {rel:34s} {kb:4d} KB  {art.artist}")

        verb = "would write" if opts["dry_run"] else "wrote"
        self.stdout.write(self.style.SUCCESS(f"{verb} {wrote} curated covers"))
