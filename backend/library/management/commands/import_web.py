"""Ingest public-domain books from arbitrary websites, one page per chapter.

For sources with no CCEL/Gutenberg edition (e.g. the Ambrose University
Alliance Studies archive of A. B. Simpson). Each ``source="web"`` book in the
catalog lists its chapters explicitly in ``catalog.WEB_CHAPTERS`` as
``(title, url, anchor)`` — explicit lists beat scraping brittle 1990s-era
index pages with stub files.

Extraction is deliberately simple: everything inside <p> tags (old archives
put bare <P> directly in <body>), starting after ``<a name="anchor">`` when an
anchor is given. A leading scripture epigraph (a short quoted first paragraph)
becomes a blockquote, mirroring the other importers.

    python manage.py import_web                     # all web-sourced books
    python manage.py import_web the-fourfold-gospel # one book by slug
"""

from __future__ import annotations

import re
import time

import requests
from django.core.management.base import BaseCommand, CommandError

from library import english_audit
from library.catalog import BOOKS, WEB_CHAPTERS, BookEntry
from library.ingest import clean_fragment, soup, upsert_book, word_count

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
DELAY = 1.0  # be polite to small archive hosts


def fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    # Old archives often declare (or silently use) legacy encodings; requests'
    # apparent_encoding sniffs the body instead of trusting a missing header.
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


# What a navigation phrase points AT: a section word or a bare site/domain name.
# Shared with the sermon importer, which strips the same furniture in wrapped
# form (see import_sermons.extract_web_sermon).
NAV_TARGET = r"(?:index|page|top|home|menu|contents|[\w-]+\.(?:com|org|net|edu))"

# A trailing navigation paragraph. Four of these phrases name themselves, but
# "back to" and "return to" are ordinary English, and this runs over devotional
# prose — so those two must ALSO name a navigation target. Unguarded, the rule
# deleted any closing paragraph that opened with them, including scripture:
# "Return to the Lord thy God" (Joel 2:13) and "Return to me, saith the Lord of
# hosts" (Zechariah 1:3) both matched. Silent loss of a work's last line.
_NAV_TAIL = re.compile(
    r"<p>[^<]{0,80}(?:"
    r"table of contents|home page|next chapter|previous chapter"
    rf"|(?:back|return) to[^<]{{0,60}}?{NAV_TARGET}"
    r")[^<]{0,80}</p>\s*$",
    re.I,
)


def extract_page(html: str, anchor: str = "", title: str = "") -> str:
    """Return a chapter body from a (possibly 1990s-era) archive page.

    These pages mix <P>, <LI>, and bare text separated by <BR>, so structure is
    normalised at the string level: cut at the anchor if given, drop the <BIG>
    title furniture, turn <BR> runs into paragraph breaks, then let
    clean_fragment's re-parse sort out the nesting.
    """
    if anchor:
        m = re.search(rf"<a\s[^>]*name=[\"']?{re.escape(anchor)}[\"']?", html, re.I)
        if m:
            html = html[m.start():]
    s = soup(html)
    for el in s.find_all(["big", "script", "style", "title"]):
        el.decompose()
    body = str(s.body or s)
    body = re.sub(r"(?:<br\s*/?>\s*)+", "</p><p>", body, flags=re.I)
    body = clean_fragment(body)
    while True:
        trimmed = _NAV_TAIL.sub("", body).strip()
        if trimmed == body:
            break
        body = trimmed
    # Drop leading title furniture. These pages repeat the chapter's own title
    # above the text in varying shapes — "<b>III. CHRIST OUR HEALER.</b><hr/>",
    # or "<b>II.</b><p>CHRIST OUR SANCTIFIER.</p>" — with comments and rules
    # around it. Iteratively strip rules, bare-numeral bolds, and a leading
    # paragraph/bold that is just the title itself.
    if title:
        want = title.strip(" .").casefold()
        while True:
            prev = body
            body = re.sub(r"^(?:\s|<hr/>|<!--.*?-->)+", "", body, flags=re.S)
            body = re.sub(r"^<b>\s*[IVXLCDM\d]+\.?\s*</b>", "", body)
            m = re.match(r"^<(p|b)>\s*([^<]{0,120}?)\s*</\1>", body)
            if m and re.sub(r"^[IVXLCDM\d]+\.\s*", "", m.group(2).strip(" .")).casefold() == want:
                body = body[m.end():]
            if body == prev:
                break
        body = body.strip()
    # A short, quote-wrapped opening paragraph is the scripture epigraph.
    m = re.match(r"^<p>(.{0,300}?)</p>", body)
    if m and m.group(1).strip().startswith(("“", '"', "&ldquo;", "‘")):
        body = f"<blockquote>{m.group(1)}</blockquote>" + body[m.end():]
    return body


class Command(BaseCommand):
    help = "Import public-domain books from per-chapter web pages."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Book slugs (default: all web books).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        entries = [b for b in BOOKS if b.source == "web" and (not wanted or b.slug in wanted)]
        unknown = wanted - {b.slug for b in BOOKS}
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        for entry in entries:
            self._import_one(entry)

    def _import_one(self, entry: BookEntry):
        self.stdout.write(f"→ {entry.title}  (web:{entry.source_ref})")
        listed = WEB_CHAPTERS.get(entry.slug)
        if not listed:
            self.stderr.write(self.style.ERROR("  no WEB_CHAPTERS entry — skipped"))
            return
        chapters: list[tuple[str, str]] = []
        for title, url, anchor in listed:
            try:
                time.sleep(DELAY)
                body = extract_page(fetch(url), anchor, title)
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"  fetch failed for {title!r}: {exc}"))
                return
            if word_count(body) < 300:
                self.stderr.write(
                    self.style.ERROR(f"  {title!r}: only {word_count(body)} words — aborted")
                )
                return
            chapters.append((title, body))
        book = upsert_book(entry, chapters)
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
