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
    word_count,
)

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
# A heading that is only a number — bare ("I.") or labelled ("CHAPTER IV.").
# Either way the real title lives in the next node and must be borrowed.
_ROMAN_OR_NUM = re.compile(r"^(?:chapter\s+)?[IVXLCDM\d]+\.?$", re.I)
_SMALL_WORDS = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
# Sections shorter than this merge into the previous chapter (interleaved
# hymns/poems, e.g. Prevailing Prayer) or, before any chapter exists, are
# dropped as front matter (prefatory notes, epigraph poems). Real chapters
# in the library run 1,300+ words; the longest hymn coda is ~250.
_TINY_SECTION_WORDS = 300


def _titlecase(text: str) -> str:
    """Title-case an ALL-CAPS heading, apostrophe-safe ("GOD'S" -> "God's")."""
    words = text.lower().split()
    out = []
    for i, w in enumerate(words):
        out.append(w if (w in _SMALL_WORDS and i > 0) else w[:1].upper() + w[1:])
    return " ".join(out)


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
    # Some ebooks' license footers carry no boilerplate classes (e.g. #61883),
    # so cut at the universal end marker before parsing.
    html = re.split(r"\*\*\*\s*END OF THE PROJECT GUTENBERG", html, flags=re.I)[0]
    s = soup(html)
    for el in s.select("[class*=pg-boilerplate], [class*=pgheader], [class*=pg-footer]"):
        el.decompose()
    # Gutenberg wraps the work in a body or a single content div.
    return s.body or s


def pick_heading_tag(root) -> str | None:
    """Choose the chapter-divider heading level.

    Chapters are top-level divisions, so prefer the *highest* heading level
    (h1 before h2 …) whose count is in a sane chapter range — not merely the
    most frequent tag (which is usually a sub-section like "WHAT TO PRAY").
    (h1 is usually the one-off book title, so its count only lands in range
    when a book genuinely uses h1 per chapter — e.g. The Way to God.)
    """
    for lvl in range(1, 7):
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
                if extra.isupper():
                    extra = _titlecase(extra)
                sep = "" if title.endswith(".") else "."
                # clean_title strips the "Chapter N." label when a descriptive
                # title follows (bare "I." numerals are kept, as before).
                return clean_title(f"{title}{sep} {extra}"), sib
    if title.isupper():
        title = _titlecase(title)
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

    # Some books wrap each chapter in its own container, so a heading has NO
    # content siblings and every body above comes out empty (Prevailing
    # Prayer). Re-collect by walking the document between headings instead.
    if all(word_count(b) < 5 for _, b in out):
        out = []
        for h in heads:
            title, consumed = resolve_title(h)
            parts = []
            for el in h.find_all_next(["h1", "h2", "h3", "p", "blockquote", "ul", "ol", "div", "hr"]):
                if id(el) in head_ids:
                    break
                if el.name == "hr":
                    # A chapter-separator rule inside a section means we've
                    # crossed into back matter (publisher notices/catalogues
                    # after the final hymn in Prevailing Prayer).
                    if "chap" in " ".join(el.get("class", [])):
                        break
                    continue
                if el.name == "div":
                    # Only poems: verse-line divs become a blockquote with line
                    # breaks (stanzas separated by a blank line); every other
                    # div is just a container. Matches poem/poetry(-container).
                    classes = " ".join(el.get("class", []))
                    if re.search(r"poem|poetry", classes) and el.find_parent(
                        class_=re.compile("poem|poetry")
                    ) is None:
                        stanzas = []
                        for st in el.select("[class*=stanza]") or [el]:
                            lines = [
                                d.get_text(" ", strip=True)
                                for d in st.find_all("div", recursive=False)
                            ] or [st.get_text(" ", strip=True)]
                            stanzas.append("<br/>".join(l for l in lines if l))
                        parts.append(
                            "<blockquote>"
                            + "<br/><br/>".join(s for s in stanzas if s)
                            + "</blockquote>"
                        )
                    continue
                if el is consumed or el.find_parent("blockquote") is not None:
                    continue
                if el.find_parent(["ul", "ol"]) is not None:
                    continue  # list items arrive via their list
                if el.find_parent(class_=re.compile("poem|poetry")) is not None:
                    continue  # already captured via its poem div
                parts.append(str(el))
            out.append((title, clean_fragment("".join(parts))))
    return out


def extract_chapters(html: str) -> list[tuple[str, str]]:
    root = content_root(html)
    tag = pick_heading_tag(root)
    if tag is None:
        return [("", clean_html(root))]
    sections = [
        (t, b) for t, b in split_by_heading(root, tag) if not is_front_matter(t)
    ]
    # Tiny sections are not chapters: interleaved hymns/poems join the chapter
    # they follow (title kept as an <h3>); tiny sections BEFORE any chapter
    # (prefatory notes, epigraph poems) are front matter and dropped.
    merged: list[tuple[str, str]] = []
    for t, b in sections:
        if word_count(b) < _TINY_SECTION_WORDS:
            if merged:
                pt, pb = merged[-1]
                merged[-1] = (pt, f"{pb}<h3>{t}</h3>{b}")
            continue
        merged.append((t, b))
    return merged


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
