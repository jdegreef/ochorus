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
from contextlib import contextmanager
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


@contextmanager
def _written_atomically(dest: Path):
    """Yield a scratch path, and move it onto `dest` only if the block finishes.

    BOTH caches in this file decide they already have something with
    `Path.exists()`, and neither re-reads the bytes. So anything that writes
    straight to a cached path turns an interruption into a permanent lie: the
    file is there, so every later run skips the work and uses it.

    Not hypothetical. A Met transfer dropped mid-stream while this batch was
    being curated and left a 163 KB `.orig.jpg` with no JPEG end marker — which
    the next run would have accepted as the painting, cropped, and committed.
    The crop step has exactly the same shape (`sips` writing in place), so it
    gets the same treatment rather than waiting for its turn to fail.

    `Path.replace` is atomic within a filesystem, and the scratch file sits
    beside its destination to stay on one.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    try:
        yield part
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)


def _fetch(url: str, dest: Path) -> None:
    """Download to `dest`, whole or not at all."""
    req = urllib.request.Request(url, headers=UA)
    with _written_atomically(dest) as part:
        with urllib.request.urlopen(req, timeout=90) as r, part.open("wb") as f:
            shutil.copyfileobj(r, f)


def _json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def _verify(art: Artwork, artist, title, year, subjects) -> None:
    """Check a manifest entry against the collection's own record.

    Two jobs, both done here because this is the moment the authoritative JSON
    is in hand and nothing downstream ever sees it again.

    THE CREDIT. `credit()` serves the artist, title and year to readers as
    provenance they can go and check, and nothing else compares them to the
    source. Four entries carried quietly wrong values — a date off by nine
    years, three titles silently shortened — for as long as this was unchecked.
    Recorded exactly as the museum records them, so a mismatch is a mistake
    rather than a house style.

    THE PORTRAIT RULE, from the collection's own SUBJECT terms where it has
    them. `test_no_curated_cover_is_a_portrait_of_its_subject` greps titles for
    "Portrait of", which misses the commonest museum convention by far — the
    sitter's name alone, "Elizabeth Farren" — so where the record can answer
    the question properly, ask it.

    ONLY THE MET CAN. Its `tags` are subject terms ("Portraits", "Women"
    against our "Roads", "Landscapes"). Cleveland publishes no genre field at
    all: its `type` is the medium ("Painting") and `technique` the support, so
    a Gainsborough portrait and a Corot pond are indistinguishable there. For a
    `cma` entry this receives None and the title grep is the whole of the check
    — worth knowing before trusting it. Checked: a Met portrait is refused
    here, and the same object from Cleveland would not be.
    """
    for field, ours, theirs in (
        ("artist", art.artist, artist or ""),
        ("title", art.title, title or ""),
        ("year", art.year, year or ""),
    ):
        if ours.strip() != theirs.strip():
            raise CommandError(
                f"{art.source}:{art.object_id} — the manifest's {field} is not the "
                f"collection's.\n  manifest: {ours!r}\n  {art.source}:      {theirs!r}\n"
                f"The credit is served to readers as provenance, so record theirs."
            )
    if any("portrait" in term.lower() for term in (subjects or ())):
        raise CommandError(
            f"{art.source}:{art.object_id} is tagged {sorted(subjects)} — a portrait on a "
            f"cover reads as a picture OF the person the book is about, which is a claim "
            f"the artwork cannot support."
        )


def _met_image_url(art: Artwork) -> str:
    """The Met's largest open-access image URL for a manifest entry."""
    obj = _json(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{art.object_id}")
    # Re-verified on every fetch rather than trusted from the manifest: the
    # manifest records what we believed, the API is what is true.
    if not obj.get("isPublicDomain"):
        raise CommandError(f"Met object {art.object_id} is NOT flagged public domain — refusing.")
    _verify(art, obj.get("artistDisplayName"), obj["title"], obj.get("objectDate"),
            [t["term"] for t in (obj.get("tags") or []) if t.get("term")])
    src = obj.get("primaryImage") or obj.get("primaryImageSmall")
    if not src:
        raise CommandError(f"Met object {art.object_id} has no image.")
    return src


def _cma_image_url(art: Artwork) -> str:
    """The Cleveland Museum's largest usable image URL for an object.

    `print` (a few thousand px) rather than `full`, which is a TIFF `sips` would
    have to transcode for no gain at 600x800; `web` is the fallback for objects
    with no print derivative. Both are on their open-access CDN.
    """
    obj = _json(f"https://openaccess-api.clevelandart.org/api/artworks/{art.object_id}")["data"]
    if obj.get("share_license_status") != "CC0":
        raise CommandError(
            f"Cleveland object {art.object_id} is "
            f"{obj.get('share_license_status')!r}, not CC0 — refusing."
        )
    # No subject terms: Cleveland publishes the medium, not the genre. See
    # `_verify` — the title grep in the test is the only portrait check here.
    _verify(art, (obj.get("creators") or [{}])[0].get("description", "").split(" (")[0],
            obj["title"], obj.get("creation_date"), None)
    images = obj.get("images") or {}
    for size in ("print", "web"):
        url = (images.get(size) or {}).get("url")
        if url:
            return url
    raise CommandError(f"Cleveland object {art.object_id} has no print or web image.")


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
    # ALWAYS, even when the bytes are already cached. The fetcher is what checks
    # the licence, the credit and the classification against the live record,
    # and gating it on a cache miss would mean each entry was checked exactly
    # once — on the day it was added, by the person who added it, against the
    # record they had just read. That is the moment it is least likely to be
    # wrong. One small JSON GET per entry, in a command run by hand a few times
    # a year, buys the guarantee every other run.
    url = fetch(art)
    raw = CACHE / f"{_cache_key(art)}.orig.jpg"
    if not raw.exists():
        _fetch(url, raw)
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
        # Onto a scratch path, not straight onto the cached one: `sips` writes
        # in place, and a run killed here would leave a half-written crop that
        # `out.exists()` above trusts forever.
        with _written_atomically(out) as part:
            subprocess.run(
                ["sips", "-c", str(H), str(W), "-s", "formatOptions", "55",
                 str(step), "--out", str(part)],
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
