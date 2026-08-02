"""Generate house-style SVG covers for books that have no artwork.

Public-domain titles sourced from CCEL/Gutenberg arrive with no cover (unlike
the ochorus.com PDFs, which have designed ones). This makes a typographic cover
from the book's own title, author and accent colour — see library/covers.py for
the design and why it looks the way it does.

    python manage.py generate_covers                   # every row missing a cover
    python manage.py generate_covers all-of-grace      # one work, all languages
    python manage.py generate_covers --force <slug>    # regenerate over an existing one
    python manage.py generate_covers --language es     # just one language
    python manage.py generate_covers --dry-run         # report, write nothing

PER-LANGUAGE OUTPUT
English writes ``/covers/<slug>.svg``; every other language writes
``/covers/<lang>/<slug>.svg``. Keeping English at the old path means the 31
existing generated covers keep their URLs and nothing 404s mid-deploy.

This is the fix for a real bug: the previous version looped over every Book row
(one per language) and wrote them ALL to ``<slug>.svg``, so the last row
processed won and every locale showed the same language. Regenerating now gives
each row a cover in its own language.

NEVER OVERWRITES ARTWORK. A row whose cover_url is a raster (.jpg/.png) is left
alone even under --force: those are designed covers, on-brand or inherited, and
they are the one thing this command must not clobber. --force means "redraw the
generated ones", not "replace the art".
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from library.covers import build_svg
from library.models import Book

COVERS_DIR = settings.BASE_DIR.parent / "frontend" / "static" / "covers"

# Anything not in this set is treated as artwork and never touched.
GENERATED_SUFFIX = ".svg"


def cover_path(slug: str, language: str) -> tuple[str, str]:
    """(relative url, path under COVERS_DIR) for a generated cover."""
    if language == "en":
        return f"/covers/{slug}.svg", f"{slug}.svg"
    return f"/covers/{language}/{slug}.svg", f"{language}/{slug}.svg"


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

        wrote = skipped_art = skipped_have = 0
        for book in qs:
            if book.cover_url and not is_generated(book.cover_url):
                skipped_art += 1
                continue
            # Without --force, only fill the gaps.
            if book.cover_url and not opts["force"] and not opts["slugs"]:
                skipped_have += 1
                continue

            url, rel = cover_path(book.slug, book.language)
            svg = build_svg(
                title=book.title,
                subtitle=book.subtitle,
                author=book.author.name,
                color=book.cover_color,
                language=book.language,
            )
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
                f"{verb} {wrote} · kept {skipped_art} artwork · left {skipped_have} existing generated"
            )
        )
