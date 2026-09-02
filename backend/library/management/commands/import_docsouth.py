"""Ingest a public-domain book from a Documenting the American South page.

docsouth.unc.edu (UNC-Chapel Hill) serves each book as ONE clean, human-keyed
HTML page — not OCR. The transcribed text runs from the first inlined print-page
anchor (``<a name="slugN"> Page N</a>``) to the ``<!-- footer inside begins -->``
comment, each chapter/section marked ``<h3 align="center">``. Two autobiographies
share this exact shape — Richard Allen's and Amanda Berry Smith's — so this is a
small shared importer, not a per-book script.

Two things it does deliberately differently from ``import_gutenberg``:

* It does NOT borrow a descriptive title from the paragraph after a bare
  ``CHAPTER I.`` heading. docsouth chapter openings are bare numerals whose real
  titles live in the CONTENTS (supplied per book via
  ``corrections.chapter_titles``); ``resolve_title``'s borrow would swallow the
  chapter's first sentence and delete it from the body.
* It isolates the transcribed text from docsouth's own front-matter metadata
  (funding statement, source description, ``Electronic Edition`` title block —
  all set in ``<h3>`` like a chapter) by cutting from the first ``Page`` anchor,
  and from the trailing site nav by cutting at the footer comment.

    python manage.py import_docsouth                    # all docsouth books
    python manage.py import_docsouth amanda-smith-autobiography
"""

from __future__ import annotations

import re
import time
from html import unescape

import requests
from django.core.management.base import BaseCommand, CommandError

from library import english_audit
from library.catalog import BOOKS, BookEntry
from library.ingest import (
    _BARE_CHAPTER,
    clean_fragment,
    clean_title,
    is_front_matter,
    soup,
    upsert_book,
    word_count,
)

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
DELAY = 1.0  # be polite

# The transcribed book begins at the first inlined print-page anchor
# (``<a name="allen3"> Page 3</a>``) and ends where the site chrome resumes.
# Everything before the first anchor is docsouth's editorial front matter — the
# title/author/"Electronic Edition" block is set in <h3>, so it would otherwise
# import as phantom chapters.
_BOOK_START = re.compile(r'<a\s+name="[^"]*">\s*Page\b', re.I)
# The book text ends at docsouth's per-book navigation block — a
# `<div class="links">` of "Return to Menu Page…" links that sits just BEFORE
# the footer comment — so cut at whichever comes first. Cutting only at the
# footer comment let that nav div leak into the last chapter's body.
_BOOK_END = re.compile(r'<div\s+class="links"|<!--\s*footer inside begins', re.I)

# Each chapter/section opens with an <h3> divider. We split on it at the STRING
# level rather than walking BeautifulSoup siblings: the summary sub-headings are
# malformed ("<P align="center">…</P></P></FONT>"), and that mangled nesting
# reparents later headings under a <p>, so a sibling walk silently merges and
# drops chapters (Smith came out 31 of 38). The heading text itself can wrap
# across lines, so match lazily across newlines.
_H3 = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.I | re.S)


def fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _plain(fragment: str) -> str:
    """The visible text of an HTML fragment, entities decoded, spaces collapsed."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _is_allcaps(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def _promote_lead_title(body: str) -> tuple[str, str]:
    """Split off an ALL-CAPS lead paragraph as a chapter's descriptive title.

    docsouth prints a numbered chapter as "<h3>CHAPTER I.</h3>" followed by its
    real title as a centred small-caps sub-heading, then the prose — so the
    title arrives in the body. Only fired when the <h3> was a bare numeral (its
    cleaned title is empty), so a chapter with a genuine heading is untouched,
    and only for an all-caps lead so ordinary opening prose is never eaten.
    """
    m = re.match(r"\s*<p>(.*?)</p>", body, re.S)
    if not m:
        return body, ""
    text = _plain(m.group(1))
    if _is_allcaps(text) and len(text) <= 300:
        return body[m.end():].lstrip(), text
    return body, ""


def extract_sections(html: str) -> list[tuple[str, str]]:
    """Split a docsouth page into (title, body_html) sections at each <h3>.

    Raises ValueError if the book-text window can't be located — without the
    start marker the editorial front matter (title/author/source-description, all
    in <h3>) imports as phantom chapters, and the `< 3 sections` guard can't see
    it because that adds sections rather than removing them. Fail loud instead.
    """
    start = _BOOK_START.search(html)
    end = _BOOK_END.search(html)
    if not start or not end:
        raise ValueError(
            "docsouth page markers not found "
            "(first 'Page' anchor and/or '<!-- footer inside begins -->')"
        )
    html = html[start.start():end.start()]

    heads = list(_H3.finditer(html))
    # Each section body runs from its heading to the next heading (or the end).
    ends = [h.start() for h in heads[1:]] + [len(html)]
    sections: list[tuple[str, str]] = []
    for i, m in enumerate(heads):
        raw = _plain(m.group(1))
        # Front matter is gated on the RAW heading — clean_title strips a
        # trailing "Contents" etc., which would let it slip past the check.
        if is_front_matter(raw):
            continue
        # Parse each chapter body in isolation: the malformed paragraph nesting
        # is contained within one section here, so it can't swallow a heading.
        s = soup(html[m.end():ends[i]])
        for anchor in s.find_all("a", attrs={"name": True}):
            anchor.decompose()  # pagination anchors carry visible "Page N" text
        for el in s.find_all(["hr", "img"]):
            el.decompose()  # rules and illustration plates we don't host
        body = clean_fragment(str(s.body or s))
        # A bare numbered divider ("CHAPTER I.") carries no title of its own — its
        # real title leads the body as an all-caps sub-heading (promote it), or
        # none does and the reader names it "Chapter N". `_BARE_CHAPTER` also
        # keeps this from firing on a roman "Chapter I" that clean_title, unlike a
        # bare arabic "Chapter 3", leaves non-empty.
        if _BARE_CHAPTER.match(raw):
            body, promoted = _promote_lead_title(body)
            title = clean_title(promoted)
        else:
            title = clean_title(raw)
        sections.append((title, body))
    return sections


class Command(BaseCommand):
    help = "Import a public-domain book from a Documenting the American South page."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all docsouth books).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        entries = [b for b in BOOKS if b.source == "docsouth" and (not wanted or b.slug in wanted)]
        unknown = wanted - {b.slug for b in BOOKS}
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        for entry in entries:
            self._import_one(entry)

    def _import_one(self, entry: BookEntry):
        self.stdout.write(f"→ {entry.title}  (docsouth:{entry.source_ref})")
        try:
            time.sleep(DELAY)
            sections = extract_sections(fetch(entry.source_ref))
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  fetch failed: {exc}"))
            return
        except ValueError as exc:
            self.stderr.write(self.style.ERROR(f"  {exc} — skipped"))
            return
        sections = [(t, b) for t, b in sections if word_count(b) >= 5]
        if len(sections) < 3:
            self.stderr.write(
                self.style.ERROR(f"  only {len(sections)} sections found — aborted")
            )
            return
        book = upsert_book(entry, sections)
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
