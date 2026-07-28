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


def _toc_entries(ref: str) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Parse the work's TOC once: (ordered urls, url→title, url→stem)."""
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

    def stem(url: str) -> str:
        name = url.rstrip("/").split("/")[-1]
        return name[len(work) + 1 : -len(".html")]

    return order, titles, {url: stem(url) for url in order}


def _parent_urls(stems: dict[str, str]) -> set[str]:
    """URLs whose stem is a strict prefix of another's — the part dividers.

    In a two-level work the one-level parent (`<work>.i.html`) is a part-divider
    / half-title page whose children (`<work>.i.ii.html`) hold the real prose.
    Single-level works have no such parents, so this is empty for them.
    Assumption: a parent page carries no prose of its own (true for the CCEL
    part/chapter convention). If a future work puts an introduction ON the
    parent page as well as chapters beneath it, that intro would be dropped —
    revisit here (fetch + word-count the parent) if that book appears.
    """
    return {
        url
        for url, st in stems.items()
        if any(other.startswith(st + ".") for other in stems.values())
    }


def toc_parts(ref: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Group a two-level work by its parts: [(part_title, [(url, title), …]), …].

    The grouped view of the TOC, for works whose real reading unit is the PART,
    not the leaf section. Augustine's *Confessions* is the case this exists for:
    CCEL splits it into 278 leaf sections of 150–900 words, titled "Chapter I" …
    "Chapter XXXVIII" — and those titles repeat in all thirteen Books, so
    imported flat the book is unreadable and carries 13 sets of duplicate
    chapter titles. Grouped, it is the thirteen Books everyone actually cites,
    each a normal chapter-length read.

    Leaf sections with no parent (front matter, a lone appendix) come back as
    their own single-child part, so nothing is silently dropped.

    Note for later: under ``group_parts`` a leaf title becomes an ``<h3>``
    inside the chapter body, so ``corrections.chapter_titles`` — which is keyed
    by chapter order — can no longer address it. A leaf-title fix in a grouped
    book has to be a general ``clean_title`` rule. If a second grouped book
    needs per-leaf corrections, that is the point to add a hook rather than
    widen ``clean_title`` again.
    """
    order, titles, stems = _toc_entries(ref)
    parents = _parent_urls(stems)
    # Stem → its divider page, so the part can take that page's real title
    # ("Book I") instead of its first leaf's ("Chapter I").
    divider = {stems[p]: p for p in parents}
    groups: dict[str, tuple[str, list[tuple[str, str]]]] = {}
    for url in order:
        if url in parents:
            continue
        # "ii.iv" → part key "ii"; a single-segment stem is its own part.
        key = stems[url].split(".")[0]
        parent = divider.get(key)
        groups.setdefault(key, (titles[parent] if parent else titles[url], []))
        groups[key][1].append((url, titles[url]))
    return list(groups.values())


def toc_sections(ref: str) -> list[tuple[str, str]]:
    """Return [(absolute_section_url, title), ...] from the work's TOC page.

    The flat view: ``toc_parts`` with its grouping discarded. Defined in terms
    of it so the two views can never disagree about what counts as a part
    divider or about section order.
    """
    return [leaf for _, leaves in toc_parts(ref) for leaf in leaves]


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
            parts = toc_parts(entry.source_ref)
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"  TOC fetch failed: {exc}"))
            return
        if not parts:
            self.stderr.write(self.style.ERROR("  no sections found in TOC"))
            return
        if not entry.group_parts:
            # The flat import is the degenerate grouped one: every leaf is its
            # own chapter, titled by itself. One loop then serves both modes, so
            # a fix to the crawl, the front-matter rule or the error handling
            # can't land in only half of them.
            parts = [(t, [(u, t)]) for _, leaves in parts for u, t in leaves]

        chapters: list[tuple[str, str]] = []
        for part_title, leaves in parts:
            # Gate front matter on the RAW title — clean_title strips a trailing
            # "Contents", which would turn a "Contents" TOC section into an empty
            # title that slips past is_front_matter and leaks in as a chapter.
            if is_front_matter(part_title):
                continue
            pieces: list[str] = []
            for url, leaf_title in leaves:
                if is_front_matter(leaf_title):
                    continue
                leaf_title = clean_title(leaf_title)
                body = self._section_body(url, leaf_title)
                if not body:
                    continue
                # A single-leaf part is the whole chapter — no subheading needed.
                # Multi-leaf parts keep each leaf's heading, so the work's own
                # divisions stay visible and citable (Confessions is quoted as
                # Book VIII.12). <h3> matches import_gutenberg's joined sections.
                pieces.append(f"<h3>{leaf_title}</h3>{body}" if len(leaves) > 1 else body)
            if not pieces:
                continue
            chapters.append((clean_title(part_title), "".join(pieces)))
            if entry.group_parts:
                self.stdout.write(f"    {part_title}: {len(pieces)} sections")

        book = upsert_book(entry, chapters)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))

    def _section_body(self, url: str, title: str) -> str:
        """Fetch and clean one TOC section; "" when the request fails."""
        try:
            time.sleep(DELAY)
            return extract_body(fetch(url), title)
        except requests.RequestException as exc:
            self.stderr.write(self.style.WARNING(f"  skip {url}: {exc}"))
            return ""
