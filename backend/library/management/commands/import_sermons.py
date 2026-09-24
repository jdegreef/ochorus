"""Ingest individual sermons from CCEL, Gutenberg, the web, and SermonIndex.

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

from library import english_audit
from library.corrections import settled_sermon_body
from library.ingest import QUOTES, clean_fragment, display_line, soup, word_count
from library.management.commands.import_gutenberg import content_root
from library.management.commands.import_web import NAV_TARGET
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


class AmbiguousSectionError(ValueError):
    """A Gutenberg `section` names several headings and no level picks one."""


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


def extract_gutenberg_section(html: str, section: str, level: str = "") -> str:
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

    Both editions also repeat their title at a second level, and they need
    opposite ones. 57109 wants the <h1>: its John 4 epigraph sits between it
    and a repeated <h2>Unfailing Springs</h2>. 23438's <h1>A Ribband of Blue</h1>
    is the VOLUME, and the study is <h3>A Ribband Of Blue.</h3> — the <h1> runs
    to the end of the book, front matter and all eight studies. Neither "first"
    nor "deepest" nor "last" suits both, so when several headings match, the
    catalog entry names the level (``SermonEntry.section_level``) and an
    unresolved tie raises rather than guessing.
    """
    s = content_root(html)

    wanted = _norm_heading(section)
    matches = [
        h for h in s.find_all(_HEADINGS) if _norm_heading(h.get_text(" ")) == wanted
    ]
    if level:
        matches = [h for h in matches if h.name == level]
    if not matches:
        return ""
    if len(matches) > 1:
        raise AmbiguousSectionError(
            f"{section!r} matches {len(matches)} headings "
            f"({', '.join(h.name for h in matches)}); set section_level"
        )
    start = matches[0]

    parts: list[str] = []
    subtitles = 0  # leading display-line headings, e.g. "A NEW YEAR'S ADDRESS."
    for el in start.find_all_next([*_HEADINGS, "p", "blockquote", "div"]):
        if el.name == start.name:
            break
        if el.find_parent("blockquote") is not None:
            continue  # already inside a collected blockquote
        if el.name == "div":
            # No poem handling here, so a verse line comes through as its own
            # block, as it always did.
            if line := display_line(el, verse_lines=True):
                if len(parts) == subtitles and line.startswith("<h"):
                    subtitles += 1
                parts.append(line)
            continue
        parts.append(str(el))

    # The first paragraph is usually the scripture epigraph in quotes — after
    # any display-line subtitle. Only those: a real heading in the source still
    # ends the search, as PG 57109's `<h2>J. Hudson Taylor</h2>` byline does,
    # so its John 4:10 text stays the `<p>` every edition shipped with.
    first = subtitles
    if first < len(parts) and parts[first].startswith("<p"):
        first_text = re.sub(r"<[^>]+>", "", parts[first]).strip()
        if first_text.startswith(QUOTES):
            inner = re.sub(r"^<p[^>]*>|</p>$", "", parts[first].strip())
            parts[first] = f"<blockquote>{inner}</blockquote>"
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
    # The masthead is not always paragraphs. Spurgeon's is; Wesley's puts the
    # preaching note in a <span class="mnote"> inside an <h2> and the reference
    # in an <h3>, so a <p>-only scan finds neither. Read the date from the
    # leading BLOCKS (headings included) or "Preached at St. Mary's, Oxford,
    # on June 18, 1738" is invisible.
    blocks = root.find_all(["p", "h2", "h3", "h4"])
    masthead_text = " ".join(b.get_text(" ", strip=True) for b in blocks[:_HEAD_WINDOW])
    preached_on = parse_preached_on(masthead_text)

    scripture_ref = ""
    quote_html = ""
    boundary = None  # index into `paragraphs`: the last masthead paragraph
    # Find the reference in any leading block. Looking only at <p> made Wesley's
    # <h3>Eph. 2:8</h3> invisible, so the scan ran on into the sermon and matched
    # the first in-body reference (Luke 4:34) — taking the whole opening section
    # as masthead and silently dropping it, with the wrong ref attached.
    ref_block = next(
        (b for b in blocks[:_HEAD_WINDOW] if b.find("a", class_="scripRef") is not None),
        None,
    )
    if ref_block is not None:
        ref = ref_block.find("a", class_="scripRef")
        scripture_ref = ref.get_text(" ", strip=True).rstrip(" .")
        if ref_block.name == "p":
            # Spurgeon: quotation and reference share one paragraph.
            quote_html = f"<blockquote>{ref_block.decode_contents()}</blockquote>"
            boundary = paragraphs.index(ref_block)
        else:
            # Wesley: the quotation is the paragraph just above the heading, so
            # the body starts at the first paragraph after it. find_all_previous
            # walks backwards in document order, so [0] is that paragraph.
            preceding = ref_block.find_all_previous("p")
            if preceding:
                last = preceding[0]
                if last.get_text(" ", strip=True).startswith(QUOTES):
                    quote_html = f"<blockquote>{last.decode_contents()}</blockquote>"
                boundary = paragraphs.index(last)
            else:
                boundary = -1

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

    # Site navigation ("Back to X Index Page"). The phrase is not always a
    # trailing bare paragraph: gospeltruth.net bolds it and leaves it INSIDE
    # the body's wrapping <blockquote>, so the end-anchored, paragraph-shaped
    # rule below walked past it and the sermon ended "...they SHALL. Back to
    # BOOTH INDEX Page".
    #
    # Two guards, because "back to"/"return to" is ordinary English and this
    # runs over sermons. It must ALSO name a navigation target (index, page,
    # top…) and be the last content element — only closing tags may follow.
    # Without both, this eats prose: "Back to our text, then" is a preacher's
    # transition, and "Return to the Lord thy God" (Joel 2:13) and "Return to
    # me, saith the Lord of hosts" (Zechariah 1:3) are scripture. All three
    # matched an earlier, looser version of this pattern.
    body = re.sub(
        r"<(p|b|i|em|strong)[^>]*>\s*(?:back|return)\s+to\b[^<]{0,80}?"
        rf"{NAV_TARGET}[^<]{{0,20}}</\1>\s*"
        r"(?=(?:</[a-z]+>\s*)*$)",
        "",
        body,
        flags=re.I,
    )
    # The bare trailing form, with the same navigation-target guard. Without it
    # this rule — which predates the wrapped one above — strips any final
    # paragraph opening "back to" or "return to", so a sermon closing on Joel
    # 2:13 ("Return to the Lord thy God") would lose its last line silently.
    body = re.sub(
        r"(?:<hr/>|\s)*(?:<p>)?\s*(?:back to|return to)[^<]{0,100}?"
        rf"{NAV_TARGET}[^<]{{0,20}}(?:</p>)?\s*$",
        "",
        body,
        flags=re.I,
    ).strip()
    # gospeltruth.net appends a fixed trailer AFTER the sermon: a "Return to
    # <year> Index Page" link, a copyright line, a nav menu, then a
    # certification-seal table — several elements, so the single-element nav
    # rules above can't reach past it. Cut from the first of those markers to the
    # end. None occurs in sermon prose, so it can only match the trailer.
    body = re.sub(
        r"<p>\s*(?:<[^>]+>\s*)*(?:Return to [^<]*Index Page"
        r"|Copyright\b[^<]*Gospel Truth"
        r"|This file is CERTIFIED BY GOSPEL TRUTH).*$",
        "",
        body,
        flags=re.I | re.S,
    ).strip()
    # A bare trailing "TOP" jump link (sermons.martinluther.us and others).
    body = re.sub(r"<p>\s*TOP\s*</p>\s*$", "", body, flags=re.I).strip()
    # BibleHub appends its own chrome after a sermon: a "Parallel Verses"
    # cross-reference block (and ad-slot comment paragraphs). Cut from it to the
    # end — the phrase is a template label, never sermon prose.
    body = re.sub(r"(?:<hr/>\s*)?Parallel Verses.*$", "", body, flags=re.I | re.S).strip()
    # A trailing volume-end marker from a collected edition ("END OF VOL. I.").
    body = re.sub(r"<p>\s*END OF VOL\.?\s*[IVXLC0-9]*\.?\s*</p>\s*$", "", body, flags=re.I).strip()
    return body


# A byline line in a transcribed masthead ("Pastor and author A.W. Tozer",
# "by Martyn Lloyd-Jones"). Guarded by a word-count cap at the call site so it
# can only match a short standalone line, never a sentence that opens "By …".
_SI_BYLINE = re.compile(r"^(pastor and author\b|by\s+[A-Z])", re.I)


def _si_core(text: str) -> str:
    """A heading normalised for comparison, stripped of surrounding quotes/punct."""
    return re.sub(r"^\W+|\W+$", "", _norm_heading(text))


def extract_sermonindex(html: str, title: str = "") -> str:
    """Return the sermon transcript from a SermonIndex v2 page.

    The redesigned SermonIndex (``div.sermon-page-v2``) wraps the transcript in
    ``div.sermon-v2-transcript-body`` — paragraphs only — surrounded by a great
    deal of AI-generated furniture: a ``sermon-v2-desc`` summary, a "Key Quotes"
    block, an FAQ, an outline, download buttons. All of that lives in SIBLING
    nodes, so taking the transcript body alone leaves every bit of it behind;
    ``clean_fragment`` then drops the wrapping div and its classes and keeps the
    paragraphs. Short devotional excerpts (Tozer's editorial snippets) share the
    same shape; the caller's word-count floor rejects them.

    Audio transcripts often open with a masthead the transcriber typed as its
    own short lines — the title, a byline, the date, a bare scripture reference.
    Those leading lines are dropped, but only while they look like masthead and
    only within the first few paragraphs: the scan stops at the first line of
    real prose, so it can never eat the sermon.
    """
    s = soup(html)
    body = s.select_one(".sermon-v2-transcript-body")
    if body is None:
        return ""
    paras = body.find_all("p")
    wanted = _si_core(title)
    start = 0
    for p in paras[:4]:
        t = p.get_text(" ", strip=True)
        words = len(t.split())
        # A masthead line is a fragment, not a sentence — none of these end in
        # terminal punctuation. That guard is what keeps a real opening sentence
        # that happens to name a month ("We began this last December.") or open
        # "By Faith …" from being mistaken for a byline or date and dropped.
        sentence = t.rstrip().endswith((".", "!", "?"))
        is_title = bool(wanted) and _si_core(t) == wanted
        is_byline = bool(_SI_BYLINE.match(t)) and words <= 6 and not sentence
        is_date = _DATE.search(t) is not None and words <= 9 and not sentence
        is_ref = (
            re.search(r"\b\d{1,3}:\d{1,3}\b", t) is not None
            and words <= 12
            and t[:1].isupper()
            and not sentence
        )
        if is_title or is_byline or is_date or is_ref:
            start += 1
        else:
            break
    html_body = "".join(str(p) for p in paras[start:])
    # A stray space before ? ! ; : is a transcription tic (English "sorrow ?",
    # "that day :"); collapse it. Deliberately NOT the comma or period — a
    # spaced ellipsis and abbreviations make those unsafe to touch blind — and
    # deliberately English-only, at import, so it never reaches a language whose
    # typography wants that space (French "sorrow ?").
    html_body = re.sub(r" +([?!;:])", r"\1", html_body)
    return clean_fragment(html_body)


class Command(BaseCommand):
    help = "Import sermons from CCEL, Gutenberg, the web, and SermonIndex."

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
                body = extract_gutenberg_section(
                    fetch(url), entry.section, entry.section_level
                )
                scripture_ref, preached_on = "", None
            elif entry.source == "web":
                body = extract_web_sermon(
                    fetch_web(entry.source_ref), entry.title, entry.body_starts
                )
                scripture_ref, preached_on = "", None
            elif entry.source == "sermonindex":
                body = extract_sermonindex(fetch_web(entry.source_ref), entry.title)
                scripture_ref, preached_on = "", None
            else:
                body, scripture_ref, preached_on = extract(fetch(entry.source_ref))
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  fetch failed: {exc}"))
            return
        except AmbiguousSectionError as exc:
            self.stderr.write(self.style.ERROR(f"  {exc}"))
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
        body = settled_sermon_body(entry.slug, body)

        if entry.scripture_ref:
            scripture_ref = entry.scripture_ref
        if entry.preached_on:
            preached_on = datetime.date.fromisoformat(entry.preached_on)

        source_url = (
            f"https://www.gutenberg.org/ebooks/{entry.source_ref}"
            if entry.source == "gutenberg"
            else entry.source_ref
        )
        fields = {
            "author": self._author(entry),
            "title": entry.title,
            "scripture_ref": scripture_ref,
            "preached_on": preached_on,
            "body_html": body,
            "source_url": source_url,
            "sort_order": SERMONS.index(entry),
        }
        sermon, _ = Sermon.objects.update_or_create(
            slug=entry.slug,
            language="en",
            defaults=fields,
            # is_published is workflow-owned once the sermon exists: an urgent
            # unpublish (a copyright pull) happens directly in the DB, and
            # re-asserting True on every re-import would silently resurrect it.
            # CREATE-ONLY, matching seed_sermons.CREATE_ONLY_FIELDS.
            create_defaults={**fields, "is_published": True},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ {sermon.word_count} words · {scripture_ref or 'no ref'}"
                f" · {preached_on or 'no date'}"
            )
        )
        english_audit.report(self, english_audit.audit_sermon(sermon), sermon.slug)
