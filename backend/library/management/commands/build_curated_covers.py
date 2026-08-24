"""Fetch the curated public-domain artwork (cover tier 3).

    python manage.py build_curated_covers            # every curated slug
    python manage.py build_curated_covers confessions
    python manage.py build_curated_covers --dry-run

For each slug in library/curated_art.py this downloads that entry's open-access
image, crops it to the cover's 3:4 box, and writes ONE painting per work to
``covers/art/<slug>.jpg``. Every language points at that file and ``BookCover``
draws the edition's title over it in HTML.

ONE FETCHER PER COLLECTION, in ``FETCHERS`` below, keyed by the manifest's
``source``. Each does the same two jobs: re-check the licence flag on the live
object, and hand back a URL for the largest usable image.

ADDING A COLLECTION is three edits, not one: a ``Source`` in
``curated_art.SOURCES`` (how to cite it), a fetcher here, and its ``FETCHERS``
entry. The two tables cannot merge — ``curated_art`` is imported on the request
path by the serializer and must stay free of ``urllib`` and of this command —
so ``test_every_source_can_actually_be_fetched`` is what stops a manifest entry
whose pixels nothing knows how to fetch. Miss the ``SOURCES`` half instead and
``credit()`` raises a KeyError inside a serializer.

It used to composite the type into an SVG, once per (slug, language), because
an SVG served through <img> cannot fetch a sibling file — so the painting had to
be embedded in each one and `waiting-on-god` shipped six copies of it. Drawing
the type in HTML also means the title is set in the brand serif and shaped for
its own script, neither of which an <img>-served SVG can do.

Run rarely: the output is committed and the artwork doesn't change. Downloads
are cached under .cache/curated-art/ so a re-run doesn't re-fetch. Afterwards
run ``scripts/build_cover_assets.py`` to give the new painting its webp
variants — the fixture gate will tell you if you forget.

Cropping uses `sips`, which ships with macOS. This is a curation step run by
hand on a developer's machine, not something the deploy does. If it ever needs
to run in CI, swap in Pillow.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from library.covers import art_url
from library.curated_art import CURATED, Artwork
from library.models import Book

COVERS_DIR = settings.BASE_DIR.parent / "frontend" / "static" / "covers"
CACHE = settings.BASE_DIR.parent / ".cache" / "curated-art"
UA = {"User-Agent": "ochorus-cover-build/1.0 (+https://ochorus.com)"}
W, H = 600, 800


def _fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r, dest.open("wb") as f:
        shutil.copyfileobj(r, f)


def _json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def _met_image_url(object_id: int) -> str:
    """The Met's largest open-access image URL for an object."""
    obj = _json(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}")
    # Re-verified on every fetch rather than trusted from the manifest: the
    # manifest records what we believed, the API is what is true.
    if not obj.get("isPublicDomain"):
        raise CommandError(f"Met object {object_id} is NOT flagged public domain — refusing.")
    src = obj.get("primaryImage") or obj.get("primaryImageSmall")
    if not src:
        raise CommandError(f"Met object {object_id} has no image.")
    return src


def _cma_image_url(object_id: int) -> str:
    """The Cleveland Museum's largest usable image URL for an object.

    `print` (a few thousand px) rather than `full`, which is a TIFF `sips` would
    have to transcode for no gain at 600x800; `web` is the fallback for objects
    with no print derivative. Both are on their open-access CDN.
    """
    obj = _json(f"https://openaccess-api.clevelandart.org/api/artworks/{object_id}")["data"]
    if obj.get("share_license_status") != "CC0":
        raise CommandError(
            f"Cleveland object {object_id} is "
            f"{obj.get('share_license_status')!r}, not CC0 — refusing."
        )
    images = obj.get("images") or {}
    for size in ("print", "web"):
        url = (images.get(size) or {}).get("url")
        if url:
            return url
    raise CommandError(f"Cleveland object {object_id} has no print or web image.")


#: Manifest ``source`` → the function that licence-checks it and returns a URL.
FETCHERS = {"met": _met_image_url, "cma": _cma_image_url}


def _cache_key(art: Artwork) -> str:
    """What this artwork's cached files are named after.

    `<source>-<id>`, not the bare id: two collections number their objects
    independently, so `150354` means one thing to Cleveland and another to the
    Met, and a shared key would serve one museum's painting for the other's.

    A function rather than an f-string at each site because the download and
    the crop are cached separately — spelled twice, a change to the scheme
    would leave the two caches keying different objects, which is the exact
    collision this is here to prevent.
    """
    return f"{art.source}-{art.object_id}"


def _artwork_image(art: Artwork) -> Path:
    """The source image for one manifest entry, downloaded once and cached."""
    fetch = FETCHERS.get(art.source)
    if fetch is None:
        raise CommandError(f"No fetcher for source {art.source!r} — see FETCHERS.")
    raw = CACHE / f"{_cache_key(art)}.orig.jpg"
    if not raw.exists():
        _fetch(fetch(art.object_id), raw)
    return raw


def _crop_3x4(src: Path, key: str) -> Path:
    """Scale to the cover height, then centre-crop to width. Scaling by HEIGHT
    matters: most of these are wide landscapes, and fitting them to width first
    would leave a letterbox rather than filling the plate."""
    out = CACHE / f"{key}.{W}x{H}.jpg"
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

            jpeg = _crop_3x4(_artwork_image(art), _cache_key(art))
            url, rel = art_url(slug)

            # ONE painting per work, with no type in it. Every language points at
            # this file and BookCover draws the title over it, so the reader
            # downloads the artwork once however many locales they read in — and
            # the title is set by the browser, in the brand serif, shaped for its
            # own script. It used to be composited per language into an SVG data
            # URI: six copies of one painting for `waiting-on-god`, each 72 KB,
            # each a separate download.
            if not opts["dry_run"]:
                dest = COVERS_DIR / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(jpeg.read_bytes())
                for book in rows:
                    if book.cover_url != url:
                        book.cover_url = url
                        book.save(update_fields=["cover_url"])
            wrote += 1
            kb = jpeg.stat().st_size // 1024
            self.stdout.write(
                f"  ✓ {rel:34s} {kb:4d} KB  {art.artist} · {len(rows)} editions share it"
            )

        verb = "would write" if opts["dry_run"] else "wrote"
        self.stdout.write(self.style.SUCCESS(f"{verb} {wrote} curated covers"))
