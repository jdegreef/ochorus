"""Ingest public-domain books from Project Gutenberg into the library.

Gutenberg HTML structure varies per book, so we pick the dominant chapter
divider empirically: a ``div.chapter`` wrapper if present, else the heading
level (h2..h5) that occurs most often. Front matter before the first chapter
(title page, contents) is dropped. PG license boilerplate is stripped.

    python manage.py import_gutenberg                 # all Gutenberg books
    python manage.py import_gutenberg humility        # one book by slug
"""

from __future__ import annotations

import re

import requests
from django.core.management.base import BaseCommand, CommandError

from library.catalog import BOOKS, BookEntry
from library.ingest import (
    clean_fragment,
    clean_html,
    clean_title,
    is_front_matter,
    soup,
    upsert_book,
)

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
_ROMAN_OR_NUM = re.compile(r"^[IVXLCDM\d]+\.?$", re.I)


def fetch_html(book_id: str) -> str:
    urls = [
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}-images.html",
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.html",
        f"https://www.gutenberg.org/ebooks/{book_id}.html.images",
    ]
    last = None
    for url in urls:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        if resp.status_code == 200 and len(resp.text) > 2000:
            return resp.text
        last = resp
    if last is not None:
        last.raise_for_status()
    raise requests.RequestException(f"no HTML found for Gutenberg #{book_id}")


def content_root(html: str):
    """Parse, drop PG boilerplate, return the element holding the book body."""
    s = soup(html)
    for el in s.select("[class*=pg-boilerplate], [class*=pgheader]"):
        el.decompose()
    # Gutenberg wraps the work in a body or a single content div.
    return s.body or s


def pick_heading_tag(root) -> str | None:
    """Choose the chapter-divider heading level.

    Chapters are top-level divisions, so prefer the *highest* heading level
    (h2 before h3 …) whose count is in a sane chapter range — not merely the
    most frequent tag (which is usually a sub-section like "WHAT TO PRAY").
    """
    for lvl in range(2, 7):
        n = len(root.find_all(f"h{lvl}"))
        if 3 <= n <= 80:
            return f"h{lvl}"
    return None


def resolve_title(heading):
    """Return (title, consumed_node).

    For a bare-numeral heading (Humility's "<h5>I.</h5>") the real title is the
    next node; we fold it into the title and return it as `consumed_node` so the
    caller can omit it from the body (otherwise it duplicates as the first line).
    """
    title = clean_title(heading.get_text(" ", strip=True))
    if _ROMAN_OR_NUM.match(title):
        sib = heading.find_next(["h3", "h4", "p"])
        if sib:
            extra = clean_title(sib.get_text(" ", strip=True))
            if extra:
                sep = "" if title.endswith(".") else "."
                return f"{title}{sep} {extra}", sib
    return title, None


def split_by_heading(root, tag) -> list[tuple[str, str]]:
    """Split into chapters at each `tag` heading, in document order.

    Non-mutating: each chapter's body is the heading's following siblings,
    serialized and re-parsed. Assumes headings and their content share a parent
    (the usual Gutenberg layout).
    """
    heads = root.find_all(tag)
    if not heads:
        return [("", clean_html(root))]
    head_ids = {id(h) for h in heads}
    out: list[tuple[str, str]] = []
    for h in heads:
        title, consumed = resolve_title(h)
        parts: list[str] = []
        for sib in h.next_siblings:
            if getattr(sib, "name", None) and id(sib) in head_ids:
                break
            if consumed is not None and sib is consumed:
                continue  # folded into the title; don't repeat it in the body
            parts.append(str(sib))
        out.append((title, clean_fragment("".join(parts))))
    return out


def extract_chapters(html: str) -> list[tuple[str, str]]:
    root = content_root(html)
    tag = pick_heading_tag(root)
    if tag is None:
        return [("", clean_html(root))]
    sections = split_by_heading(root, tag)
    return [(t, b) for t, b in sections if not is_front_matter(t)]


class Command(BaseCommand):
    help = "Import public-domain books from Project Gutenberg into the library."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all Gutenberg books).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        entries = [b for b in BOOKS if b.source == "gutenberg" and (not wanted or b.slug in wanted)]
        if wanted:
            unknown = wanted - {b.slug for b in BOOKS}
            wrong = wanted - {b.slug for b in entries} - unknown
            if unknown:
                raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
            if wrong:
                raise CommandError(f"Not Gutenberg-sourced: {', '.join(sorted(wrong))}")

        for entry in entries:
            self._import_one(entry)

    def _import_one(self, entry: BookEntry):
        self.stdout.write(f"→ {entry.title}  (gutenberg:#{entry.source_ref})")
        try:
            html = fetch_html(entry.source_ref)
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  fetch failed: {exc}"))
            return
        chapters = extract_chapters(html)
        book = upsert_book(entry, chapters)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
