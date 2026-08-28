"""Generate house-style SVG plate grounds for books that have no artwork.

Public-domain titles sourced from CCEL/Gutenberg arrive with no cover (unlike
the ochorus.com PDFs, which have designed ones). This makes a plate from the
book's own accent colour and its topic's emblem — a GROUND, with no words on
it: `BookCover.svelte` sets the edition's title over it in the browser, in the
face its author's century is set in. See library/covers.py for why the type
lives there and not here.

    python manage.py generate_covers                   # every row missing a cover
    python manage.py generate_covers all-of-grace      # one work, all languages
    python manage.py generate_covers --force <slug>    # regenerate over an existing one
    python manage.py generate_covers --language es     # just one language
    python manage.py generate_covers --dry-run         # report, write nothing

PER-LANGUAGE OUTPUT
English writes ``/covers/<slug>.svg``; every other language writes
``/covers/<lang>/<slug>.svg``. Keeping English at the old path means the
existing generated covers keep their URLs and nothing 404s mid-deploy.

That layout was the fix for a real bug — one file per slug while the loop ran
over every language row meant the last row won and every locale showed the same
language. It costs nothing to keep and is no longer load-bearing: a ground has
no words, so these files are now identical across a work's languages. Pointing
every edition at one of them is a fixture change and its own PR.

NEVER OVERWRITES ARTWORK, of either kind:

  * a raster cover_url (.jpg/.png) — the designed covers, on-brand or inherited;
  * a slug in the CURATED manifest — the composited public-domain artwork.

The second guard was added when curated covers were ALSO .svg and the raster
check could not tell them apart — a `--force` run redrew all ten as plain
typographic plates, and on a developer's machine that overwrites committed
artwork and can be committed without anyone noticing. They are `.jpg` paintings
now, so the raster check catches the ones that carry a cover_url; the manifest
guard still earns its place for a curated work whose row has none yet, where
`is_generated("")` is True and the plate would be drawn over a book that
already has a painting. --force means "redraw the generated ones", never
"replace the art".
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from library.covers import (
    build_ground,
    cover_path,
    emblem_for_book,
    shares_a_ground,
)
from library.models import Book

COVERS_DIR = settings.BASE_DIR.parent / "frontend" / "static" / "covers"

# Anything not in this set is treated as artwork and never touched.
GENERATED_SUFFIX = ".svg"

# Re-exported: `cover_path` moved to library.covers when the fixture gate and
# scripts/localize_covers.py needed it too (both are Django-free), and callers
# importing it from here keep working.
__all__ = ["Command", "cover_path", "is_generated"]


def is_generated(cover_url: str) -> bool:
    """True when the cover is one of ours to redraw (or absent)."""
    return not cover_url or cover_url.endswith(GENERATED_SUFFIX)


class Command(BaseCommand):
    help = "Generate house-style SVG covers for books with no artwork."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all missing a cover).")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Redraw generated covers too (never replaces .jpg/.png artwork).",
        )
        parser.add_argument("--language", help="Restrict to one language code.")
        parser.add_argument(
            "--dry-run", action="store_true", help="Report what would change; write nothing."
        )

    def handle(self, *args, **opts):
        qs = Book.objects.select_related("author").order_by("slug", "language")
        if opts["slugs"]:
            qs = qs.filter(slug__in=opts["slugs"])
        if opts["language"]:
            qs = qs.filter(language=opts["language"])

        wrote = skipped_art = skipped_have = skipped_curated = 0
        for book in qs:
            if book.cover_url and not is_generated(book.cover_url):
                skipped_art += 1
                continue
            # A work with a SHARED GROUND reaches here whenever its row does
            # not already name the ground: the raster check above passes over
            # it, and `is_generated("")` is True — as it is for the dangling
            # `/covers/<lang>/<slug>.svg` that `translate_book` writes for a
            # brand-new translation. Its file comes from `build_curated_covers`
            # (curated) or `scripts/build_derived_grounds.py` (derived), never
            # from here.
            #
            # The designed-cover tiers are in here for a reason worth stating:
            # without them a freshly translated edition of such a work took the
            # plate below, which is the exact downgrade they exist to prevent —
            # and left a committed SVG that then hard-exits
            # `build_cover_assets`.
            if shares_a_ground(book.slug):
                skipped_curated += 1
                continue
            # Without --force, only fill the gaps.
            if book.cover_url and not opts["force"] and not opts["slugs"]:
                skipped_have += 1
                continue

            url, rel = cover_path(book.slug, book.language)
            svg = build_ground(book.cover_color, emblem=emblem_for_book(book.slug))
            if not opts["dry_run"]:
                dest = COVERS_DIR / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(svg, encoding="utf-8")
                if book.cover_url != url:
                    book.cover_url = url
                    book.save(update_fields=["cover_url"])
            wrote += 1
            self.stdout.write(f"  ✓ {rel}  ({book.language}) {book.title}")

        verb = "would write" if opts["dry_run"] else "wrote"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {wrote} · kept {skipped_art} artwork"
                f" · kept {skipped_curated} shared-ground · left {skipped_have} existing generated"
            )
        )
