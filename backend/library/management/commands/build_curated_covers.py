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

Cropping uses Pillow, so this runs anywhere the dependencies install. It is a
curation step run by hand — the deploy does not do it — but "by hand" should not
have meant "on a Mac", which is what shelling out to `sips` made it.
"""

from __future__ import annotations

import json
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from library.covers import art_url, keeps_english_designed
from library.curated_art import CURATED, CURATED_GROUND, Artwork
from library.models import Book

COVERS_DIR = settings.BASE_DIR.parent / "frontend" / "static" / "covers"
CACHE = settings.BASE_DIR.parent / ".cache" / "curated-art"
UA = {"User-Agent": "ochorus-cover-build/1.0 (+https://ochorus.com)"}

#: Hosts that 403 a bare programmatic request and relent given a Referer. The
#: Art Institute's IIIF server refuses any client that arrives without one — a
#: browser's own User-Agent included — and turns the same request from 403 to
#: 200 the moment `Referer: https://www.artic.edu/` is present. Only the pixel
#: host gates on this: the catalogue API at api.artic.edu answers any client,
#: which is what lets `_aic_image_url` reach the metadata to begin with. This
#: header is why curated_art.py's docstring no longer calls AIC's pixels
#: unreachable.
REFERERS = {"www.artic.edu": "https://www.artic.edu/"}
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
    headers = dict(UA)
    referer = REFERERS.get(urllib.parse.urlsplit(url).hostname)
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with _written_atomically(dest) as part:
        with urllib.request.urlopen(req, timeout=90) as r, part.open("wb") as f:
            shutil.copyfileobj(r, f)


#: Seconds to wait before each retry of a catalogue lookup.
_RETRY_WAITS = (3, 10, 30)


def _json(url: str) -> dict:
    """A collection's catalogue record, retried through burst rate-limiting.

    Every entry is checked against its live record on every run (see
    `_artwork_image`), which means one catalogue call per entry, back to back —
    the Met alone is ~40 in a row. Its API answers that pattern with a 403 on a
    request that succeeds seconds later: seen while writing this, on an object
    fetched cleanly minutes before. Without a retry the verification would turn
    into a command that fails at random, and a check people learn to re-run until
    it passes is not a check. So 403, 429 and 5xx get a patient retry; anything
    else, and a refusal that outlasts the waits, still fails loudly.
    """
    for wait in (*_RETRY_WAITS, None):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if wait is None or not (e.code in (403, 429) or e.code >= 500):
                raise
        except urllib.error.URLError:
            if wait is None:
                raise
        time.sleep(wait)
    raise AssertionError("unreachable")


def _verify(art: Artwork, artist, title, year, subjects) -> None:
    """Check a manifest entry against the collection's own record.

    Two jobs, both here because this is the one moment the authoritative JSON is
    in hand and nothing downstream ever sees it again.

    THE CREDIT. `curated_art.credit()` serves the artist, title and year to
    readers as provenance they can go and check, and until now nothing compared
    them to the source. Thirteen of sixty-six entries were wrong: `Pilgrim's
    Progress` was dated 1878 against the Met's 1869, titles had been quietly
    shortened, dates had lost their qualifier, and artists' names had been
    abridged. Recorded
    exactly as the collection records them, so a difference is a mistake rather
    than a house style.

    THE PORTRAIT RULE, from the collection's SUBJECT terms where it has them. A
    portrait on a cover reads as a picture OF the person the book is about,
    which is a claim the artwork cannot support.
    `test_no_curated_cover_is_a_portrait_of_its_subject` greps titles for
    "Portrait of", which misses the commonest museum convention by far — the
    sitter's name alone, "Elizabeth Farren".

    THE MET AND CHICAGO CAN ANSWER IT. The Met's `tags` and AIC's
    `subject_titles` are subject terms ("Portraits", "self-portraits" against
    our "Roads", "landscapes"). Cleveland publishes no genre
    field at all: `type` is the medium ("Painting") and `technique` the support,
    so a Gainsborough portrait and a Corot pond are indistinguishable there. A
    `cma` entry therefore passes None here and the title grep is the whole of
    its check — worth knowing before trusting it.
    """
    for field, ours, theirs in (
        ("artist", art.artist, artist or ""),
        ("title", art.title, title or ""),
        ("year", art.year, year or ""),
    ):
        if ours.strip() != theirs.strip():
            raise CommandError(
                f"{art.source}:{art.object_id} — the manifest's {field} is not the "
                f"collection's.\n  manifest: {ours!r}\n  {art.source + ':':9} {theirs!r}\n"
                f"credit() serves this to readers as provenance, so record theirs."
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
    # `_verify` — the title grep in the tests is the only portrait check here.
    _verify(art, (obj.get("creators") or [{}])[0].get("description", "").split(" (")[0],
            obj["title"], obj.get("creation_date"), None)
    images = obj.get("images") or {}
    for size in ("print", "web"):
        url = (images.get(size) or {}).get("url")
        if url:
            return url
    raise CommandError(f"Cleveland object {art.object_id} has no print or web image.")


def _aic_image_url(art: Artwork) -> str:
    """The Art Institute of Chicago's largest usable image URL for an object.

    Two hops, not one. The catalogue at api.artic.edu answers with the licence
    flag and an ``image_id`` — a UUID that is NOT the object id — and the pixels
    live on the IIIF server keyed by that UUID. ``full/1686,`` is the widest
    standard derivative the CDN serves without a per-object config lookup, and
    ample for a 600x800 crop; the fetch of those pixels needs a Referer (see
    ``REFERERS``), which the object id, being on the catalogue host, does not.

    That 1686 assumes the source is at least that wide — true of every museum
    scan, but a smaller original would 403 here (the server refuses a width it
    would have to upscale to, and ``full/full`` is blocked outright), which is a
    loud build-time failure to reland with a narrower size, not a silent wrong
    cover.
    """
    obj = _json(
        f"https://api.artic.edu/api/v1/artworks/{art.object_id}"
        "?fields=is_public_domain,image_id,artist_title,title,date_display,subject_titles"
    )["data"]
    if not obj.get("is_public_domain"):
        raise CommandError(f"AIC object {art.object_id} is NOT flagged public domain — refusing.")
    # AIC's `subject_titles` are real subject terms ("self-portraits" on a
    # self-portrait, "landscapes" on a Cole), so it gets the full portrait check.
    _verify(art, obj.get("artist_title"), obj.get("title"), obj.get("date_display"),
            obj.get("subject_titles") or [])
    image_id = obj.get("image_id")
    if not image_id:
        raise CommandError(f"AIC object {art.object_id} has no image.")
    return f"https://www.artic.edu/iiif/2/{image_id}/full/1686,/0/default.jpg"


#: Manifest ``source`` → the function that licence-checks it and returns a URL.
FETCHERS = {"met": _met_image_url, "cma": _cma_image_url, "aic": _aic_image_url}


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
    # the licence, the credit and the subject terms against the live record, and
    # gating it on a cache miss would mean each entry was checked exactly once —
    # on the day it was added, by the person who added it, against the record
    # they had just read. That is the moment it is least likely to be wrong. One
    # small JSON GET per entry, in a command run by hand a few times a year.
    url = fetch(art)
    raw = CACHE / f"{_cache_key(art)}.orig.jpg"
    if not raw.exists():
        _fetch(url, raw)
    return raw


def _crop_3x4(src: Path, key: str, focus: float = 0.5) -> Path:
    """Scale the artwork to COVER the 3:4 plate, then crop the overflow away.

    WHERE the crop is taken from is the artwork's own to say: `Artwork.focus`
    slides the window along whichever axis overflows, and defaults to the centre.

    Scaling to COVER — the larger of the two ratios — rather than to height.
    Height alone is right for the wide landscapes that make up most of this
    manifest, and wrong for anything taller than 3:4: a portrait scaled to 800px
    high comes out NARROWER than the 600px plate, and the crop that followed ran
    off the edge of the image. Nothing in the manifest is portrait today, which
    is the only reason that never fired. Cover-fit is the same arithmetic for a
    landscape and correct for the rest.

    PILLOW, NOT ``sips``. This used to shell out to macOS's ``sips`` twice, which
    made a curation step that anyone can run into one only a Mac can — the file
    said as much ("If it ever needs to run in CI, swap in Pillow") and the day it
    mattered was a cloud session that could reach the museums but had no ``sips``.
    Pillow is already a dependency; the fixture gates open these same JPEGs with
    it to measure their contrast.

    Bytes will not match ``sips``'s output for the same input — two encoders, and
    quality 55 does not mean the same thing to both. That changes nothing already
    committed, because a painting is cropped once and the result is cached and
    committed; only a work fetched from here on is encoded by this path.
    """
    # `focus` is IN THE CACHE KEY. It changes the pixels, and the cache is
    # consulted before anything is drawn — leave it out and re-running after
    # adjusting a crop hands back the old one, silently, forever.
    out = CACHE / f"{key}.{W}x{H}@{focus:.2f}.jpg"
    if out.exists():
        return out
    with Image.open(src) as im:
        # RGB explicitly: the collections serve the odd CMYK TIFF-derived JPEG
        # and a palettised PNG, and neither can be written as a JPEG as-is.
        im = im.convert("RGB")
        scale = max(W / im.width, H / im.height)
        im = im.resize(
            (max(W, round(im.width * scale)), max(H, round(im.height * scale))),
            Image.LANCZOS,
        )
        # Exactly one axis overflows — `scale` is the max of the two ratios, so
        # the other lands on its target — and `focus` slides the window along
        # whichever one it is. 0.5 is the centre crop this did before.
        left = round((im.width - W) * focus)
        top = round((im.height - H) * focus)
        im = im.crop((left, top, left + W, top + H))
        # Quality 55 is deliberate. These are 600x800 thumbnails behind a
        # scrim and a lot of type — the artefacts JPEG makes at this level are
        # invisible here, and it's the difference between a 235 KB cover and a
        # ~90 KB one. The designed covers on the same shelf are 19-51 KB.
        # Onto a scratch path, not straight onto the cached one: a run killed
        # mid-write would leave a half-written crop that `out.exists()` above
        # trusts forever.
        with _written_atomically(out) as part:
            im.save(part, "JPEG", quality=55, optimize=True)
    return out


class Command(BaseCommand):
    help = "Composite curated public-domain artwork covers for the flagship titles."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Curated slugs (default: all).")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        # BOTH curated tiers are fetched here, because fetching is the half
        # they share: same collections, same licence re-check, same 3:4 crop,
        # same one file per work. Where they part is who POINTS at that file,
        # which is the loop below and not this line.
        manifest = {**CURATED, **CURATED_GROUND}
        slugs = opts["slugs"] or list(manifest)
        unknown = [s for s in slugs if s not in manifest]
        if unknown:
            raise CommandError(f"Not in the curated manifest: {', '.join(unknown)}")

        wrote = 0
        for slug in slugs:
            art = manifest[slug]
            rows = list(Book.objects.select_related("author").filter(slug=slug))
            if not rows:
                self.stdout.write(self.style.WARNING(f"  – {slug}: no Book rows, skipping"))
                continue

            jpeg = _crop_3x4(_artwork_image(art), _cache_key(art), art.focus)
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
                    # THE ENGLISH ROW OF A `CURATED_GROUND` WORK IS NOT MOVED.
                    # That work has a hand-made English cover and came here only
                    # because no wordless picture could be cut out of it; the
                    # painting is for the translations. Repointing English at it
                    # would retire the designed cover, which is the whole thing
                    # this tier exists to avoid — and it would do it silently,
                    # since every other gate is satisfied by a row pointing at a
                    # painting that really is there.
                    if keeps_english_designed(slug) and book.language == "en":
                        continue
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
