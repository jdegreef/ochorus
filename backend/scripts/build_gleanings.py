#!/usr/bin/env python
"""Build "Gleanings Among the Sheaves" (Spurgeon, Gutenberg #42657) as 20
thematic chapters.

The source is 146 short standalone extracts with their own titles and no
grouping — a flat 146-entry book reads badly and trips the tiny-section
filters. This script fetches the 146 (via the same importer cleaning), then
regroups them under 20 themes, each chapter gathering its extracts as titled
``<h3>`` sub-sections in the book's original order. The theme mapping below is
the editorial content of this book and lives here so the build is reproducible.

Idempotent: re-running upserts the Book and replaces its chapters. Run with
``DJANGO_DEBUG=true uv run python scripts/build_gleanings.py`` from ``backend/``,
then serialise the fixture the usual way (see the book-import skill).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")
django.setup()

from django.utils.html import escape  # noqa: E402

from library.ingest import clean_fragment, clean_title, is_front_matter  # noqa: E402
from library.management.commands.import_gutenberg import (  # noqa: E402
    content_root,
    fetch_html,
    split_by_heading,
)
from library.models import Author, Book, Chapter  # noqa: E402

BOOK_ID = "42657"
SLUG = "gleanings-among-the-sheaves"
AUTHOR_SLUG = "charles-h-spurgeon"

# The 20 chapters, in reading order.
THEMES = [
    "The Promises of God",           # 1
    "Faith and Assurance",           # 2
    "In Sorrow and Affliction",      # 3
    "The Christian Warfare",         # 4
    "Strength in Weakness",          # 5
    "Communion with Christ",         # 6
    "The Love of Christ",            # 7
    "Grace and Salvation",           # 8
    "Looking unto Jesus",            # 9
    "The Joy of the Christian Life", # 10
    "Prayer",                        # 11
    "Holiness and the New Life",     # 12
    "Humility and Self-Examination", # 13
    "Providence and the Care of God",# 14
    "Peace and Rest",                # 15
    "Heaven and the Life to Come",   # 16
    "The Word of God",               # 17
    "Good Works and Diligence",      # 18
    "The Holy Spirit",               # 19
    "The Church and the World",      # 20
]

# Each of the 146 extracts (in source order) -> its theme number (1-20).
THEME_OF = {
    1: 1, 2: 3, 3: 4, 4: 3, 5: 4, 6: 3, 7: 18, 8: 7, 9: 3, 10: 15,
    11: 10, 12: 1, 13: 4, 14: 14, 15: 10, 16: 11, 17: 13, 18: 9, 19: 3, 20: 2,
    21: 7, 22: 2, 23: 14, 24: 8, 25: 12, 26: 5, 27: 18, 28: 8, 29: 3, 30: 10,
    31: 14, 32: 2, 33: 6, 34: 6, 35: 7, 36: 6, 37: 18, 38: 10, 39: 9, 40: 14,
    41: 9, 42: 12, 43: 12, 44: 3, 45: 10, 46: 14, 47: 16, 48: 18, 49: 8, 50: 11,
    51: 4, 52: 17, 53: 9, 54: 2, 55: 18, 56: 10, 57: 19, 58: 9, 59: 12, 60: 3,
    61: 13, 62: 16, 63: 16, 64: 16, 65: 19, 66: 15, 67: 14, 68: 8, 69: 17, 70: 15,
    71: 9, 72: 10, 73: 1, 74: 6, 75: 10, 76: 2, 77: 16, 78: 7, 79: 15, 80: 10,
    81: 2, 82: 20, 83: 10, 84: 7, 85: 13, 86: 13, 87: 18, 88: 8, 89: 1, 90: 3,
    91: 4, 92: 18, 93: 20, 94: 4, 95: 12, 96: 7, 97: 16, 98: 18, 99: 13, 100: 8,
    101: 18, 102: 3, 103: 13, 104: 10, 105: 3, 106: 17, 107: 16, 108: 10, 109: 12, 110: 3,
    111: 8, 112: 12, 113: 11, 114: 9, 115: 9, 116: 14, 117: 5, 118: 12, 119: 9, 120: 3,
    121: 3, 122: 13, 123: 13, 124: 4, 125: 13, 126: 12, 127: 20, 128: 5, 129: 4, 130: 9,
    131: 14, 132: 8, 133: 11, 134: 4, 135: 10, 136: 7, 137: 8, 138: 8, 139: 10, 140: 14,
    141: 6, 142: 13, 143: 1, 144: 3, 145: 2, 146: 16,
}


def gleanings() -> list[tuple[str, str]]:
    root = content_root(fetch_html(BOOK_ID))
    secs = [
        (clean_title(t), b)
        for t, b in split_by_heading(root, "h3")
        if t and not is_front_matter(t)
    ]
    if len(secs) != 146:
        raise SystemExit(f"expected 146 extracts, got {len(secs)}")
    return secs


def build() -> None:
    assert set(THEME_OF) == set(range(1, 147)), "mapping must cover 1..146 once"
    assert set(THEME_OF.values()) <= set(range(1, 21))
    secs = gleanings()

    author = Author.objects.get(slug=AUTHOR_SLUG)
    book, _ = Book.objects.update_or_create(
        slug=SLUG,
        language="en",
        defaults=dict(
            author=author,
            title="Gleanings Among the Sheaves",
            subtitle="Short Readings for Heart and Soul",
            source_type=Book.SourceType.PUBLIC_DOMAIN,
            source_url=f"https://www.gutenberg.org/ebooks/{BOOK_ID}",
            is_published=True,
        ),
    )
    book.chapters.all().delete()

    for theme_no, theme in enumerate(THEMES, 1):
        idx = [i for i in range(1, 147) if THEME_OF[i] == theme_no]
        # A chapter must not open with a sub-heading that only repeats the
        # chapter title (RestatedChapterHeadingTests): when an extract is titled
        # exactly like its theme, order it after the others so it never leads.
        idx.sort(key=lambda i: secs[i - 1][0].strip().casefold() == theme.casefold())
        parts = [f"<h3>{escape(secs[i - 1][0])}</h3>{secs[i - 1][1]}" for i in idx]
        body = clean_fragment("".join(parts))
        Chapter.objects.create(
            book=book, order=theme_no, title=theme, body_html=body
        )
    print(f"built {SLUG}: {book.chapters.count()} chapters")


if __name__ == "__main__":
    build()
