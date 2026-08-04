"""Ingest individual public-domain sermons from CCEL into the library.

CCEL sermon pages (e.g. Spurgeon's Sermons volumes) share one shape inside
``div#theText .book-content``:

    <h1>The Immutability of God</h1>
    <p>A Sermon</p> <p>(No. 1)</p>
    <p>Delivered on Sabbath Morning, January 7th, 1855, by the</p>
    <p>REV. C.H. SPURGEON</p> <p>At New Park Street Chapel, Southwark.</p>
    <p>“I am the Lord, I change not; …”—<a class="scripRef">Malachi 3:6</a></p>
    <p>…the sermon itself…</p>

The importer drops the masthead, parses the preached-on date and the scripture
reference, keeps the scripture quotation as an opening <blockquote>, and
upserts a full-text ``Sermon`` row per catalog entry.

    python manage.py import_sermons                      # whole sermon catalog
    python manage.py import_sermons the-ravens-cry       # one sermon by slug
"""

from __future__ import annotations

import datetime
import re
import time
from functools import lru_cache

import requests
from django.core.management.base import BaseCommand, CommandError

from library.corrections import apply_body_corrections
from library.ingest import clean_fragment, soup, word_count
from library.management.commands.import_gutenberg import content_root
from library.management.commands.import_web import extract_page as extract_web_page
from library.management.commands.import_web import fetch as fetch_web
from library.models import Author, Sermon
from library.sermon_catalog import SERMON_AUTHORS, SERMONS, SermonEntry

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
DELAY = 0.8  # be polite to CCEL

# Mastheads vary in case ("January 7th, 1855" vs "MARCH 12, 1865").
_DATE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})",
    re.I,
)
# The masthead + scripture quote sit in the first paragraphs, but blank
# spacer <p>s push the quote as far down as index ~14. Scan generously.
_HEAD_WINDOW = 20

# Sermon headings appear at whatever level the edition chose; see
# extract_gutenberg_section.
_HEADINGS = ["h1", "h2", "h3", "h4"]


# Cached by URL: one Gutenberg ebook can back many sermons (33520 carries six,
# and this book has eight studies), and without this each one re-downloads the
# whole ebook and re-parses it. CCEL pages have a unique URL each, so they are
# unaffected. The politeness sleep stays in the caller — `fetch_web` is a
# separate function and would lose its delay if it moved in here.
@lru_cache(maxsize=16)
def fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def _norm_heading(text: str) -> str:
    """Normalise a heading for matching: whitespace, quotes, trailing dot."""
    t = re.sub(r"\s+", " ", text).strip().rstrip(".")
    return t.replace("‘", "'").replace("’", "'").replace(
        "“", '"'
    ).replace("”", '"').casefold()


def extract_gutenberg_section(html: str, section: str) -> str:
    """Return the body of one heading-delimited sermon from a Gutenberg edition.

    Collects paragraph-level elements between the matching heading and the next
    heading AT THE SAME LEVEL. A leading quotation paragraph (the scripture
    epigraph) becomes a blockquote, mirroring the CCEL shape.

    Two editions fix the rule between them. A single-sermon ebook titles its
    sermon <h1> (Taylor's *Unfailing Springs*, PG 57109) but puts an
    <h2>J. Hudson Taylor</h2> byline straight after it — so delimiting on "same
    or higher" would stop at the byline and return nothing. A collection gives
    the volume the <h1> and each study an <h3> (Taylor's *A Ribband of Blue*,
    PG 23438) — so searching h1 only found nothing at all. Hence: match any
    level, delimit on the same tag.
    """
    s = content_root(html)

    wanted = _norm_heading(section)
    start = next(
        (h for h in s.find_all(_HEADINGS) if _norm_heading(h.get_text(" ")) == wanted),
        None,
    )
    if start is None:
        return ""

    parts: list[str] = []
    for el in start.find_all_next([*_HEADINGS, "p", "blockquote"]):
        if el.name == start.name:
            break
        if el.find_parent("blockquote") is not None:
            continue  # already inside a collected blockquote
        parts.append(str(el))

    # The first paragraph is usually the scripture epigraph in quotes.
    if parts:
        first_text = re.sub(r"<[^>]+>", "", parts[0]).strip()
        if first_text.startswith(("\u201c", '"', "\u2018", "'")):
            inner = re.sub(r"^<p[^>]*>|</p>$", "", parts[0].strip())
            parts[0] = f"<blockquote>{inner}</blockquote>"
    return clean_fragment("".join(parts))


def parse_preached_on(text: str) -> datetime.date | None:
    m = _DATE.search(text)
    if not m:
        return None
    month, day, year = m.groups()
    try:
        return datetime.datetime.strptime(
            f"{month.title()} {day} {year}", "%B %d %Y"
        ).date()
    except ValueError:
        return None


def extract(html: str) -> tuple[str, str, datetime.date | None]:
    """Return (body_html, scripture_ref, preached_on) from a CCEL sermon page.

    Everything up to and including the scripture-quotation paragraph is the
    masthead; the quotation itself is kept as an opening blockquote. If no
    scripRef paragraph exists, the body starts after the last masthead-looking
    paragraph and scripture_ref is left empty.
    """
    s = soup(html)
    root = s.select_one("#theText .book-content") or s.select_one("#theText")
    if root is None:
        return "", "", None

    for h1 in root.find_all("h1"):
        h1.decompose()

    paragraphs = root.find_all("p")
    masthead_text = " ".join(
        p.get_text(" ", strip=True) for p in paragraphs[:_HEAD_WINDOW]
    )
    preached_on = parse_preached_on(masthead_text)

    scripture_ref = ""
    quote_html = ""
    boundary = None  # index of the scripture paragraph
    for i, p in enumerate(paragraphs[:_HEAD_WINDOW]):
        ref = p.find("a", class_="scripRef")
        if ref is not None:
            scripture_ref = ref.get_text(" ", strip=True).rstrip(" .")
            quote_html = f"<blockquote>{p.decode_contents()}</blockquote>"
            boundary = i
            break

    if boundary is None:
        # No scripture line — drop obvious masthead lines and keep the rest.
        boundary = -1
        for i, p in enumerate(paragraphs[:8]):
            t = p.get_text(" ", strip=True)
            if not t or re.match(r"^(A Sermon|\(No\.|Delivered|REV\.|At )", t, re.I):
                boundary = i
    body_parts = [str(p) for p in paragraphs[boundary + 1 :]]
    body = clean_fragment(quote_html + "".join(body_parts))
    return body, scripture_ref, preached_on


def extract_web_sermon(html: str, title: str, body_starts: str = "") -> str:
    """A standalone sermon on an arbitrary web page.

    Builds on the web-book chapter extractor, then removes sermon-page
    furniture: spacer paragraphs, title/byline headings and paragraphs (leading
    or repeated mid-body above an appended hymn), a third-person introduction
    before the sermon proper (cut via the catalog's ``body_starts`` marker),
    and a trailing "Back to <site>" link.
    """

    def _text(fragment: str) -> str:
        t = re.sub(r"&nbsp;", " ", re.sub(r"<[^>]+>", " ", fragment))
        return re.sub(r"\s+", " ", t).strip()

    body = extract_web_page(html, "", title)
    body = re.sub(r"<p>(?:\s|&nbsp;|\xa0)*</p>", "", body)

    # Title/byline furniture, wherever it appears ("<h2>HIMSELF</h2>",
    # "<p><b>The Power of Stillness</b></p>", "<h4>by A. B. Simpson</h4>").
    def _is_furniture(m: re.Match) -> str:
        t = _text(m.group(0)).strip(" .")
        if t.casefold() == title.strip(" .").casefold():
            return ""
        if re.match(r"^by\s.{0,60}$", t, re.I):
            return ""
        return m.group(0)

    body = re.sub(r"<(h[1-6]|p)>.{0,160}?</\1>", _is_furniture, body, flags=re.S)

    # Cut a third-person introduction: the sermon starts at the marker.
    if body_starts:
        m = re.search(rf"<p>\s*(?:<[^>]+>\s*)*{re.escape(body_starts)}", body)
        if m:
            body = body[m.start():]

    # Trailing site-navigation text, inside or outside a paragraph.
    body = re.sub(
        r"(?:<hr/>|\s)*(?:<p>)?\s*(?:back to|return to)[^<]{0,100}(?:</p>)?\s*$",
        "",
        body,
        flags=re.I,
    ).strip()
    return body


class Command(BaseCommand):
    help = "Import public-domain sermons from CCEL, Gutenberg, and the web."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Sermon slugs (default: all).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        entries = [e for e in SERMONS if not wanted or e.slug in wanted]
        unknown = wanted - {e.slug for e in SERMONS}
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        for entry in entries:
            self._import_one(entry)

    def _author(self, entry: SermonEntry) -> Author:
        author = Author.objects.filter(slug=entry.author_slug).first()
        if author:
            return author
        a = SERMON_AUTHORS[entry.author_slug]
        return Author.objects.create(
            slug=a.slug,
            name=a.name,
            bio=a.bio,
            birth_year=a.birth_year,
            death_year=a.death_year,
        )

    def _import_one(self, entry: SermonEntry):
        self.stdout.write(f"→ {entry.title}  ({entry.source}:{entry.source_ref})")
        try:
            time.sleep(DELAY)
            if entry.source == "gutenberg":
                url = (
                    "https://www.gutenberg.org/cache/epub/"
                    f"{entry.source_ref}/pg{entry.source_ref}-images.html"
                )
                body = extract_gutenberg_section(fetch(url), entry.section)
                scripture_ref, preached_on = "", None
            elif entry.source == "web":
                body = extract_web_sermon(
                    fetch_web(entry.source_ref), entry.title, entry.body_starts
                )
                scripture_ref, preached_on = "", None
            else:
                body, scripture_ref, preached_on = extract(fetch(entry.source_ref))
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  fetch failed: {exc}"))
            return
        if word_count(body) < 300:
            self.stderr.write(
                self.style.ERROR(f"  extracted only {word_count(body)} words — skipped")
            )
            return

        # Source defects, the same way books fix theirs: BODY_CORRECTIONS is
        # keyed by slug and sermons have slugs, so this reuses the book table
        # rather than inventing a second one. Re-applied on every import, so a
        # hand-edited fixture can't drift from what the importer produces.
        body = apply_body_corrections(entry.slug, order=None, body_html=body)

        if entry.scripture_ref:
            scripture_ref = entry.scripture_ref
        if entry.preached_on:
            preached_on = datetime.date.fromisoformat(entry.preached_on)

        source_url = (
            f"https://www.gutenberg.org/ebooks/{entry.source_ref}"
            if entry.source == "gutenberg"
            else entry.source_ref
        )
        sermon, _ = Sermon.objects.update_or_create(
            slug=entry.slug,
            language="en",
            defaults={
                "author": self._author(entry),
                "title": entry.title,
                "scripture_ref": scripture_ref,
                "preached_on": preached_on,
                "body_html": body,
                "word_count": word_count(body),
                "source_url": source_url,
                "sort_order": SERMONS.index(entry),
                "is_published": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ {sermon.word_count} words · {scripture_ref or 'no ref'}"
                f" · {preached_on or 'no date'}"
            )
        )
