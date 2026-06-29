"""Generate on-brand SVG covers for books that don't have a cover image.

Public-domain titles sourced from CCEL/Gutenberg have no cover (unlike the
ochorus.com PDFs). This makes a clean typographic cover from the book's title,
author, and accent colour, writes it to the frontend's static/covers/ folder,
and sets Book.cover_url to it.

    python manage.py generate_covers                  # all books missing a cover
    python manage.py generate_covers all-of-grace ... # specific slugs
    python manage.py generate_covers --force <slug>   # regenerate even if present
"""

from __future__ import annotations

import html
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from library.models import Book

COVERS_DIR = settings.BASE_DIR.parent / "frontend" / "static" / "covers"


def _darken(hex_color: str, factor: float = 0.55) -> str:
    h = (hex_color or "#3b5bdb").lstrip("#")
    if len(h) != 6:
        h = "3b5bdb"
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join(f"{max(0, int(c * factor)):02x}" for c in (r, g, b))


def _wrap(title: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in title.split():
        if line and len(line) + 1 + len(word) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def build_svg(title: str, subtitle: str, author: str, color: str) -> str:
    color = color or "#3b5bdb"
    # Smaller type for longer titles so they always fit the cover.
    font_size, max_chars = (58, 12) if len(title) <= 22 else (46, 16)
    line_h = font_size + 8
    lines = _wrap(title, max_chars)
    block_top = 360 - (len(lines) - 1) * line_h / 2
    title_tspans = "".join(
        f'<tspan x="300" y="{block_top + i * line_h:.0f}">{html.escape(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )
    divider_y = block_top + (len(lines) - 1) * line_h + 46
    sub = (
        f'<text x="300" y="{divider_y + 40:.0f}" text-anchor="middle" fill="#ffffff" '
        f'fill-opacity="0.85" font-family="Georgia, serif" font-style="italic" '
        f'font-size="22">{html.escape(subtitle)}</text>'
        if subtitle
        else ""
    )
    return f"""<svg viewBox="0 0 600 800" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.3" y2="1">
      <stop offset="0" stop-color="{color}"/>
      <stop offset="1" stop-color="{_darken(color)}"/>
    </linearGradient>
  </defs>
  <rect width="600" height="800" fill="url(#bg)"/>
  <rect x="26" y="26" width="548" height="748" fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="1.5"/>
  <text x="300" y="96" text-anchor="middle" fill="#ffffff" fill-opacity="0.7" font-family="Georgia, serif" font-size="19" letter-spacing="7">OCHORUS</text>
  <text text-anchor="middle" fill="#ffffff" font-family="Georgia, 'Times New Roman', serif" font-weight="600" font-size="{font_size}">{title_tspans}</text>
  <line x1="262" y1="{divider_y:.0f}" x2="338" y2="{divider_y:.0f}" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1.5"/>
  {sub}
  <text x="300" y="724" text-anchor="middle" fill="#ffffff" fill-opacity="0.82" font-family="Georgia, serif" font-size="22" letter-spacing="3">{html.escape(author.upper())}</text>
</svg>
"""


class Command(BaseCommand):
    help = "Generate SVG covers for books missing a cover image."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all missing a cover).")
        parser.add_argument("--force", action="store_true", help="Regenerate even if a cover exists.")

    def handle(self, *args, **opts):
        COVERS_DIR.mkdir(parents=True, exist_ok=True)
        qs = Book.objects.select_related("author")
        if opts["slugs"]:
            qs = qs.filter(slug__in=opts["slugs"])
        elif not opts["force"]:
            qs = qs.filter(cover_url="")

        for book in qs:
            if book.cover_url and not opts["force"] and not opts["slugs"]:
                continue
            svg = build_svg(book.title, book.subtitle, book.author.name, book.cover_color)
            (COVERS_DIR / f"{book.slug}.svg").write_text(svg, encoding="utf-8")
            book.cover_url = f"/covers/{book.slug}.svg"
            book.save(update_fields=["cover_url"])
            self.stdout.write(self.style.SUCCESS(f"  ✓ {book.slug}.svg  ({book.title})"))
