"""Ingest public-domain books from CCEL (ccel.org) into the library.

Usage:
    python manage.py import_ccel              # import the whole catalog
    python manage.py import_ccel humility     # import one book by slug
    python manage.py import_ccel --list       # list catalog slugs and exit

For each book we fetch the work's table of contents, follow each section page,
clean the HTML down to a safe subset, and upsert Author / Book / Chapter rows.
CCEL content is in the public domain; we record the source URL on each book.
"""

from __future__ import annotations

import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library.catalog import AUTHORS, BOOKS, BookEntry
from library.models import Author, Book, Chapter

CCEL_BASE = "https://ccel.org/ccel/"
USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
REQUEST_DELAY_SECONDS = 1.0  # be polite to CCEL

# HTML tags we keep in chapter bodies; everything else is unwrapped or dropped.
ALLOWED_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "em", "strong", "i", "b", "br", "hr",
    "ul", "ol", "li",
}


def fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def clean_html(node: Tag) -> str:
    """Reduce a parsed content node to a safe, attribute-free HTML subset."""
    for tag in node.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
        else:
            tag.attrs = {}
    html = node.decode_contents() if hasattr(node, "decode_contents") else str(node)
    # Collapse runs of whitespace and empty paragraphs.
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r"<p>\s*</p>", "", html)
    return html.strip()


def word_count(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html)
    return len(text.split())


# --- CCEL-specific scraping ---------------------------------------------------
# NOTE: selectors below are validated/tuned against the live site during the
# first ingestion run. Kept isolated here so refinement touches one place.

def discover_sections(toc_html: str, toc_url: str) -> list[str]:
    """Return absolute URLs of the work's section/chapter pages, in order."""
    soup = BeautifulSoup(toc_html, "lxml")
    urls: list[str] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = a["href"]
        if ".html" not in href and ".htm" not in href:
            continue
        absolute = urljoin(toc_url, href)
        if absolute in seen or absolute == toc_url:
            continue
        seen.add(absolute)
        urls.append(absolute)
    return urls


def extract_section(html: str) -> tuple[str, str]:
    """Return (title, cleaned_body_html) for one CCEL section page."""
    soup = BeautifulSoup(html, "lxml")
    content = (
        soup.select_one("#mainText")
        or soup.select_one(".text")
        or soup.select_one("div.book")
        or soup.body
    )
    if content is None:
        return ("", "")
    heading = content.find(["h1", "h2", "h3"])
    title = heading.get_text(strip=True) if heading else ""
    return (title, clean_html(content))


# --- Upsert -------------------------------------------------------------------

@transaction.atomic
def upsert_book(entry: BookEntry, sections: list[tuple[str, str]], language="en") -> Book:
    a = AUTHORS[entry.author_slug]
    author, _ = Author.objects.update_or_create(
        slug=a.slug,
        defaults={
            "name": a.name,
            "bio": a.bio,
            "birth_year": a.birth_year,
            "death_year": a.death_year,
        },
    )
    sort_order = next(i for i, b in enumerate(BOOKS) if b.slug == entry.slug)
    book, _ = Book.objects.update_or_create(
        slug=entry.slug,
        language=language,
        defaults={
            "author": author,
            "title": entry.title,
            "subtitle": entry.subtitle,
            "source_type": Book.SourceType.PUBLIC_DOMAIN,
            "source_url": urljoin(CCEL_BASE, entry.ccel_id),
            "cover_color": entry.cover_color,
            "sort_order": sort_order,
            "is_published": True,
        },
    )
    book.chapters.all().delete()
    order = 0
    for title, body in sections:
        if not body:
            continue
        order += 1
        Chapter.objects.create(
            book=book,
            order=order,
            title=title or f"Chapter {order}",
            body_html=body,
            word_count=word_count(body),
        )
    return book


class Command(BaseCommand):
    help = "Import public-domain books from CCEL into the library."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs to import (default: all).")
        parser.add_argument("--list", action="store_true", help="List catalog slugs and exit.")

    def handle(self, *args, **opts):
        if opts["list"]:
            for b in BOOKS:
                self.stdout.write(f"{b.slug:22} {b.title}  [{b.ccel_id}]")
            return

        wanted = opts["slugs"]
        entries = [b for b in BOOKS if not wanted or b.slug in wanted]
        if wanted and len(entries) != len(wanted):
            missing = set(wanted) - {b.slug for b in entries}
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(missing))}")

        for entry in entries:
            toc_url = urljoin(CCEL_BASE, entry.ccel_id + "/")
            self.stdout.write(f"→ {entry.title}  ({toc_url})")
            try:
                toc = fetch(toc_url)
                section_urls = discover_sections(toc, toc_url)
                sections: list[tuple[str, str]] = []
                for url in section_urls:
                    time.sleep(REQUEST_DELAY_SECONDS)
                    sections.append(extract_section(fetch(url)))
                book = upsert_book(entry, sections)
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"  fetch failed: {exc}"))
                continue
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters")
            )
