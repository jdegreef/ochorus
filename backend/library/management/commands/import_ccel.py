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
    # more dotted segments so both flatten to the same chapter list.
    #
    # Segments are usually roman numerals, but CCEL also names parts with a
    # WORD — The Imitation of Christ is `imitation.ONE.1.html` … `.FOUR.18.html`
    # — so the class must accept any alphanumeric segment, not just [ivxlcdm0-9].
    # (A roman-only class silently matched just the two front/back-matter pages
    # of the Imitation and reported "✓ 2 chapters".) `toc` is excluded below:
    # the TOC page links to itself and now matches this wider pattern.
    pattern = re.compile(rf"{re.escape(work)}(?:\.[a-z0-9_]+)+\.html$", re.I)
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
        if absolute == toc_url:
            continue  # the TOC's self-link is not a section
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
    # Assumption: a parent page carries no prose of its own (true for the CCEL
    # part/chapter convention). If a future work puts an introduction ON the
    # parent page as well as chapters beneath it, that intro would be dropped —
    # revisit here (fetch + word-count the parent) if that book appears.
    def stem(url: str) -> str:
        name = url.rstrip("/").split("/")[-1]
        return name[len(work) + 1 : -len(".html")]

    stems = {url: stem(url) for url in order}
    parents = {
        url
        for url, st in stems.items()
        if any(other.startswith(st + ".") for other in stems.values())
    }
    return [(url, titles[url]) for url in order if url not in parents]


_LEADING_P = re.compile(r"\s*<p>(.*?)</p>", re.S)
# Opens an epigraph (or its dashed citation line) rather than a heading.
_EPIGRAPH_LEAD = ("'", '"', "‘", "“", "—", "–", "-")
_MAX_FOLD = 4


def _heading_line(text: str) -> bool:
    """ALL-CAPS, or ends in a colon — the marks of a heading, not a sentence."""
    letters = [c for c in text if c.isalpha()]
    return text.endswith(":") or (len(letters) > 1 and all(c.isupper() for c in letters))


def fold_leading_heading(html: str) -> str:
    """Fold a chapter's opening heading lines into one ``<h2>``.

    Most CCEL works mark the chapter heading as a real ``<h2>``. A few instead
    set it as consecutive one-line paragraphs — Murray's *Waiting on God* opens
    every chapter with "First Day." / "WAITING ON GOD:" / "<the title>." Left as
    paragraphs those render as three stray fragments under the chapter title,
    repeating it. Joined into a single ``<h2>`` they read as the day heading the
    print edition intended, and match how every other CCEL book renders.

    Only a run of **two or more** very short leading paragraphs qualifies, so a
    book that simply opens with one brief sentence is untouched. Three further
    guards keep it from eating prose, because CCEL also sets poetry and verse
    epigraphs one line per paragraph:

    - the run stops at a quoted or dashed line (an epigraph or its citation) and
      is capped, so it can never run away down the chapter;
    - something must survive it — a fold that would consume the whole body is
      refused outright;
    - at least one line must actually look like a heading (ALL-CAPS, or ending
      in a colon). Two short lines of narrative prose — "He was gone." / "She
      did not know." — are left alone.
    """
    parts: list[str] = []
    pos = 0
    while len(parts) < _MAX_FOLD and (m := _LEADING_P.match(html, pos)) is not None:
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if not text or len(text.split()) > 8 or text[:1] in _EPIGRAPH_LEAD:
            break
        parts.append(text)
        pos = m.end()
    if len(parts) < 2 or not html[pos:].strip():
        return html
    if not any(_heading_line(p) for p in parts):
        return html
    return f"<h2>{' '.join(parts)}</h2>" + html[pos:]


# A chapter body often opens by restating its own heading, e.g.
#   <h4>The Twenty-Second Chapter</h4><h3>Remember the Innumerable Gifts of God</h3>
# The reader already shows "Chapter 60" and the title above the prose, so both
# lines read as duplication. Drop a LEADING ordinal-chapter heading and a
# LEADING heading that restates the TOC title; stop at the first heading that
# is neither (Book III's "The Disciple" / "The Voice of Christ" speaker labels
# are real content and must survive).
# The counter in "The Twenty-Second Chapter" / "Chapter IV" / "Chapter 3":
# an English ordinal word (hyphenated compounds included), a roman numeral, or
# digits. Deliberately NOT `\w+` — that would also strip a real heading such as
# "Chapter Summary".
_COUNTER = (
    r"(?:\d+|[ivxlcdm]+|"
    r"(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)?[- ]?"
    r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|"
    r"eighteenth|nineteenth|twentieth|thirtieth|fortieth|fiftieth|sixtieth|"
    r"seventieth|eightieth|ninetieth|hundredth|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|last))"
)


def _is_ordinal_heading(text: str) -> bool:
    t = text.strip().rstrip(".")
    return bool(
        re.fullmatch(rf"(the\s+)?{_COUNTER}\s+chapter", t, re.I)
        or re.fullmatch(rf"chapter\s+{_COUNTER}", t, re.I)
    )


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def extract_body(html: str, title: str = "") -> str:
    s = soup(html)
    node = s.select_one("#theText") or s.select_one("[class*=contentSection]") or s.body
    if node is None:
        return ""
    content = node.select_one("[class*=book-content]") or node
    # Page-break markers are dropped by clean_html, but that runs last — and a
    # `<span class="pb">3</span>` sitting before the opening heading would count
    # as content here and block the duplicate-heading strip below. Remove them
    # first so the heading really is what leads the chapter.
    for pb in content.select("span.pb"):
        pb.decompose()
    for el in list(content.find_all(["h1", "h2", "h3", "h4", "h5"], recursive=True))[:2]:
        # Only consider headings that still lead the content, so a mid-chapter
        # heading is never touched. Empty markup (CCEL's `<span class="index">`
        # anchors, stray whitespace) doesn't count as content.
        if any(
            (prev.get_text(strip=True) if prev.name else (prev.string or "").strip())
            for prev in el.previous_siblings
        ):
            break
        text = el.get_text(" ", strip=True)
        if _is_ordinal_heading(text) or (title and _norm(text) == _norm(title)):
            el.decompose()
        else:
            break
    # fold_leading_heading then handles the other shape — works that set the
    # heading as consecutive one-line paragraphs rather than a real <h2>.
    return fold_leading_heading(clean_html(node))


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
                body = extract_body(fetch(url), title)
            except requests.RequestException as exc:
                self.stderr.write(self.style.WARNING(f"  skip {url}: {exc}"))
                continue
            chapters.append((title, body))

        book = upsert_book(entry, chapters)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
