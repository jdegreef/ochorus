"""Ingest public-domain books from CCEL (ccel.org) into the library.

CCEL serves each work as static per-section pages with a table-of-contents page
at ``<work>.toc.html``. Chapter prose lives in ``div#theText``; chapter titles
come from the TOC. CCEL content is public domain; we record the source URL.

    python manage.py import_ccel                 # all CCEL books in the catalog
    python manage.py import_ccel all-of-grace    # one book by slug
"""

from __future__ import annotations

import re
import time
from urllib.parse import urljoin

import requests
from django.core.management.base import BaseCommand, CommandError

from library.catalog import BOOKS, BookEntry
from library.ingest import clean_html, clean_title, is_front_matter, soup, upsert_book

CCEL_BASE = "https://ccel.org/ccel/"
USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
DELAY = 0.8  # be polite to CCEL


def fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def work_base(ref: str) -> str:
    """ccel work path 'spurgeon/grace' -> 'https://ccel.org/ccel/spurgeon/grace/grace.'"""
    work = ref.rstrip("/").split("/")[-1]
    return urljoin(CCEL_BASE, f"{ref}/{work}.")


def toc_sections(ref: str) -> list[tuple[str, str]]:
    """Return [(absolute_section_url, title), ...] from the work's TOC page."""
    base = work_base(ref)
    work = ref.rstrip("/").split("/")[-1]
    toc_url = base + "toc.html"
    s = soup(fetch(toc_url))
    # Section files are `<work>.iii.html`, but works split into parts use a
    # two-level scheme (`<work>.i.ii.html` = part i, chapter ii). Match one or
    # more dotted roman/numeric segments so both flatten to the same chapter list.
    pattern = re.compile(rf"{re.escape(work)}(?:\.[ivxlcdm0-9]+)+\.html$", re.I)
    # A section can be linked more than once (e.g. an untitled "start reading"
    # button plus the titled TOC entry). Keep the longest title per URL, and
    # preserve first-seen order.
    order: list[str] = []
    titles: dict[str, str] = {}
    for a in s.select("a[href]"):
        href = a.get("href", "")
        if not pattern.search(href):
            continue
        absolute = urljoin(toc_url, href)
        title = a.get_text(" ", strip=True)
        if absolute not in titles:
            order.append(absolute)
            titles[absolute] = title
        elif len(title) > len(titles[absolute]):
            titles[absolute] = title
    # In a two-level work the one-level parent (`<work>.i.html`) is just a
    # part-divider / half-title page whose children (`<work>.i.ii.html`) hold the
    # real prose — drop any section whose stem is a strict prefix of another's.
    # Single-level works have no such parents, so this is a no-op for them.
    def stem(url: str) -> str:
        name = url.rstrip("/").split("/")[-1]
        return name[len(work) + 1 : -len(".html")]

    stems = {url: stem(url) for url in order}
    parents = {
        url
        for url, st in stems.items()
        if any(other != st and other.startswith(st + ".") for other in stems.values())
    }
    return [(url, titles[url]) for url in order if url not in parents]


def extract_body(html: str) -> str:
    s = soup(html)
    node = s.select_one("#theText") or s.select_one("[class*=contentSection]") or s.body
    return clean_html(node) if node else ""


class Command(BaseCommand):
    help = "Import public-domain books from CCEL into the library."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all CCEL books).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        entries = [b for b in BOOKS if b.source == "ccel" and (not wanted or b.slug in wanted)]
        if wanted:
            unknown = wanted - {b.slug for b in BOOKS}
            wrong = wanted - {b.slug for b in entries} - unknown
            if unknown:
                raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
            if wrong:
                raise CommandError(f"Not CCEL-sourced: {', '.join(sorted(wrong))}")

        for entry in entries:
            self._import_one(entry)

    def _import_one(self, entry: BookEntry):
        self.stdout.write(f"→ {entry.title}  (ccel:{entry.source_ref})")
        try:
            sections = toc_sections(entry.source_ref)
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  TOC fetch failed: {exc}"))
            return
        if not sections:
            self.stderr.write(self.style.ERROR("  no sections found in TOC"))
            return

        chapters: list[tuple[str, str]] = []
        for url, title in sections:
            # Gate front matter on the RAW title — clean_title strips a trailing
            # "Contents", which would turn a "Contents" TOC section into an empty
            # title that slips past is_front_matter and leaks in as a chapter.
            if is_front_matter(title):
                continue
            title = clean_title(title)
            try:
                time.sleep(DELAY)
                body = extract_body(fetch(url))
            except requests.RequestException as exc:
                self.stderr.write(self.style.WARNING(f"  skip {url}: {exc}"))
                continue
            chapters.append((title, body))

        book = upsert_book(entry, chapters)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
