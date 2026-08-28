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

from library import english_audit
from library.catalog import BOOKS, BookEntry
from library.ingest import clean_html, clean_title, is_front_matter, soup, upsert_book

CCEL_BASE = "https://ccel.org/ccel/"
# summary_title: a sentence terminator followed by a dash, a space, or the end
# of the string ends the lead clause — unless it is an abbreviation's full stop,
# which would cut "Life of St. Antony. …" down to "Life of St".
_SENTENCE_END = re.compile(r"[.?!](?=\s*--|\s+\S|$)")
_ABBREVIATIONS = frozenset(
    # Saints and gospels, reference shorthand, and the honorifics Schaff uses.
    ["st", "ss", "mt", "mk", "lk", "jn"]
    + ["cf", "ch", "chap", "chaps", "vs", "viz", "etc", "no", "nos", "vol", "vols"]
    + ["p", "pp", "ib", "ibid", "ed", "eds", "trans", "al", "ad", "bc"]
    + ["fr", "dr", "mr", "mrs", "rev", "jr", "sr"]
)
_TITLE_CAP = 72   # characters; a contents-list line that still reads at a glance
_TITLE_MIN = 24   # never cut so short that the title says nothing
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
    # A section can be linked more than once: its TOC list entry, plus an
    # untitled "start reading" button above the list. Keep the longest title per
    # URL, and place each section at its first TITLED link — the button skips
    # the front matter and points at the first chapter, so ordering by first
    # sighting put Prayer and Praying Men's INTRODUCTION, real prose, second.
    #
    # A URL that is only ever linked untitled (an icon-only anchor, say) has no
    # titled position to use, so it keeps its document one rather than being
    # pushed to the end of the book. No CCEL work has one today.
    #
    # Verified against the real `toc_parts` path: no shipped book's chapter
    # order moves. That check matters — chapter order is a public contract
    # (`PlanDay.chapter_order`, saved positions, prerendered URLs) — and a
    # cruder comparison that skipped `toc_parts` wrongly said two books moved.
    anchors: list[tuple[str, str]] = []
    titles: dict[str, str] = {}
    for a in s.select("a[href]"):
        href = a.get("href", "")
        if not pattern.search(href):
            continue
        absolute = urljoin(toc_url, href)
        if absolute == toc_url:
            continue  # the TOC's self-link is not a section
        title = a.get_text(" ", strip=True)
        anchors.append((absolute, title))
        titles[absolute] = max(titles.get(absolute, ""), title, key=len)
    order: list[str] = []
    for absolute, title in anchors:
        if absolute in order or not (title or titles[absolute] == ""):
            continue
        order.append(absolute)

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


def summary_title(title: str) -> str:
    """The lead clause of an NPNF/ANF section summary, capped at a readable length.

    Schaff's editors head each section with a precis of its argument, not a
    title: *On the Incarnation*'s 57 sections average 232 characters and run to
    443. Unmodified they are useless as chapter titles and unusable in a
    contents list. The lead clause is almost always the real heading
    ("Introductory.--The subject of this treatise: …" → "Introductory").

    Some sections have no short lead — they are one long sentence — so the cut
    falls back to the first clause break and then to a word boundary. Six of
    the 57 land on the fallback; a mid-sentence cut reads better than 443
    characters, and the full summary is still the first thing in the chapter.
    """
    lead = title.strip()
    for m in _SENTENCE_END.finditer(title):
        candidate = title[: m.end()].strip()
        if len(candidate) < 5:
            continue
        # The word carrying the full stop: an abbreviation is not a sentence end.
        word = re.split(r"[\s(\u2014\u2013-]", candidate.rstrip(".?!"))[-1]
        if _norm(word) in _ABBREVIATIONS:
            continue
        lead = candidate
        break
    if len(lead) > _TITLE_CAP:
        for sep in (";", ":", "--", ","):
            i = lead.find(sep, _TITLE_MIN)
            if _TITLE_MIN <= i <= _TITLE_CAP:
                lead = lead[:i]
                break
    if len(lead) > _TITLE_CAP:
        lead = lead[:_TITLE_CAP].rsplit(" ", 1)[0]
    return lead.rstrip(" .,;:-").strip() or title


def toc_parts(ref: str, part: str = "") -> list[tuple[str, list[tuple[str, str]]]]:
    """Group a two-level work by its parts: [(part_title, [(url, title), …]), …].

    ``part`` narrows the crawl to ONE work inside a multi-work volume, named by
    its section-stem prefix ("xvi.ii" is the Life of Antony inside npnf204).
    Grouping is then relative to that prefix — the part's own children become
    the chapters — so the same call shape serves a whole volume and one work
    out of it. See ``BookEntry.part`` for why volumes have to be addressed this
    way at all.

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
    if part:
        order = [u for u in order if stems[u] == part or stems[u].startswith(part + ".")]
        if not order:
            raise CommandError(f"part {part!r} matches no section of {ref}")
        # Restrict the parent test to the subtree too: a page is only a divider
        # relative to what is actually being imported.
        stems = {u: stems[u] for u in order}
    parents = _parent_urls(stems)
    # Stem → its divider page, so the part can take that page's real title
    # ("Book I") instead of its first leaf's ("Chapter I").
    divider = {stems[p]: p for p in parents}
    # Group one level below the part: with no part that is the first segment
    # ("ii.iv" → "ii"), and under part "xvi.ii" it is "xvi.ii.iii".
    depth = len(part.split(".")) if part else 0
    groups: dict[str, tuple[str, list[tuple[str, str]]]] = {}
    for url in order:
        if url in parents:
            continue
        key = ".".join(stems[url].split(".")[: depth + 1])
        parent = divider.get(key)
        groups.setdefault(key, (titles[parent] if parent else titles[url], []))
        groups[key][1].append((url, titles[url]))
    return list(groups.values())


def toc_sections(ref: str, part: str = "") -> list[tuple[str, str]]:
    """Return [(absolute_section_url, title), ...] from the work's TOC page.

    The flat view: ``toc_parts`` with its grouping discarded. Defined in terms
    of it so the two views can never disagree about what counts as a part
    divider or about section order.
    """
    return [leaf for _, leaves in toc_parts(ref, part) for leaf in leaves]


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


# A WELL-FORMED roman numeral below a thousand — a chapter counter, in other
# words. `_COUNTER` above spells its roman arm loosely as `[ivxlcdm]+`, which is
# safe only there because the word "chapter" sits beside it; alone that class
# also spells "civil", "mild", "livid", "mill", "dim" and "did", every one of
# which is a heading a book might really carry. The thousands place is dropped
# deliberately: `m{0,3}` would make this match "mix" (MIX is a real numeral,
# 1009), and no chapter is numbered past CMXCIX. Both bare-counter tests below
# use it. Same construction as `ingest._ROMAN_WORD`, lowercase for the `_norm`ed
# text `_restates` compares.
_ROMAN_STRICT = r"(?=[ivxlcd])(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})"


def _is_ordinal_heading(text: str) -> bool:
    t = text.strip().rstrip(".")
    return bool(
        re.fullmatch(rf"(the\s+)?{_COUNTER}\s+chapter", t, re.I)
        or re.fullmatch(rf"chapter\s+{_COUNTER}", t, re.I)
        # The counter ALONE — an untitled chapter heads its page with just the
        # numeral, as Purpose in Prayer's "<h2>I</h2>" does. Strict roman or
        # digits, never `_COUNTER`: its ordinal WORDS ("One", "Last") and its
        # loose roman class are both ordinary English.
        or re.fullmatch(rf"{_ROMAN_STRICT}|\d{{1,3}}", t, re.I)
    )


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# A chapter page's own heading numbers itself, and not always the way its TOC
# entry does: Bounds's TOC reads "1. Men of Prayer Needed" while the page's
# <h2> reads "1 Men of Prayer Needed". Both are the same restatement, and
# `clean_title` now drops the TOC's number, so the two only compare equal with
# the numbering set aside on each side.
#
# Roman numerals count too: every chapter of Prayer and Praying Men opens
# "<h2>III. ABRAHAM, THE MAN OF PRAYER</h2>" above prose the reader already sees
# titled. Strict, for the reason `_ROMAN_STRICT` gives.
_LEAD_COUNTER = re.compile(rf"^(?:\d{{1,3}}|{_ROMAN_STRICT})\s+")


def _restates(text: str, title: str) -> bool:
    """Does this heading merely repeat the chapter's own title, numbering aside?"""
    if not title:
        return False
    return _LEAD_COUNTER.sub("", _norm(text)) == _LEAD_COUNTER.sub("", _norm(title))


# A typographic rule set as its own paragraph — CCEL prints one under the
# running head on most Schaff section pages.
_RULE_LINE = re.compile(r"^[\s\u2014\u2013\-_*·.]+$")
_MAX_LEAD_NOISE = 4


def _is_leading_noise(text: str, title: str, book_title: str) -> bool:
    """Is this leading paragraph page furniture rather than the author's prose?

    The Schaff volumes open each section with the tail of the running head, a
    rule, and then the section's own name, all as plain paragraphs — Book I of
    *On the Priesthood* begins "treatise on the priesthood." / "————" / "Book
    I." before the first sentence. The existing duplicate-heading strip only
    looks at real ``<h1>``–``<h5>`` elements, so none of it was caught and the
    fragments rendered as a stray line at the top of every chapter.
    """
    if _RULE_LINE.match(text) or _is_ordinal_heading(text):
        return True
    normalised = _norm(text)
    if _restates(text, title):
        return True
    # The running head, which quotes the work's own title — in either
    # direction, since CCEL prints both the full title ("Life of Antony." above
    # the Preface) and a tail of it ("treatise on the priesthood."). Kept short
    # so a real opening sentence that happens to name the book survives.
    if not book_title or len(text.split()) > 10:
        return False
    work = _norm(book_title)
    return bool(normalised) and (work in normalised or normalised in work)


def is_contents_body(html: str) -> bool:
    """Does this section's body open with a table of contents?

    A volume's per-work contents page is sometimes filed under a title that
    says nothing about it — the Life of Antony's is titled "Prologue", so
    ``is_front_matter`` passes it and 630 words of section list import as
    chapter 1. Gate on the body instead: a real chapter does not open by
    announcing a table of contents.
    """
    blocks = re.findall(r"<p[^>]*>(.*?)</p>", html, re.S | re.I)[:3]
    return any(_norm(re.sub(r"<[^>]+>", " ", b)) == "table of contents" for b in blocks)


def extract_body(
    html: str, title: str = "", book_title: str = "", volume: bool = False
) -> str:
    """Clean one section page into a chapter body.

    A leading HEADING carrying `book_title` is furniture by definition, so it
    goes for every book. The same line as a leading <p> only goes for a `volume`
    import (`part=`) — see `_is_leading_noise` for why that gate has to stay.
    """
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
        if (
            _is_ordinal_heading(text)
            or _restates(text, title)
            or _restates(text, book_title)
        ):
            el.decompose()
        else:
            break
    # The same duplication, one tag down: leading <p> furniture (running head,
    # rule, restated section name). Bounded, and it stops at the first real line.
    #
    # Gated on `volume`, i.e. a `part` import, and deliberately so: this
    # furniture is a property of a Schaff VOLUME's section pages, and the books imported from per-work CCEL paths do not have it.
    # Run unconditionally it does real damage — measured against the committed
    # fixtures, it stripped 296 words from The Imitation of Christ (deleting the
    # chapter "True Comfort Is to Be Sought in God Alone" outright, whose body
    # is a single paragraph restating its title), 116 from Union and Communion
    # and 86 from All of Grace.
    for el in (list(content.find_all("p", recursive=True))[:_MAX_LEAD_NOISE] if volume else []):
        if any(
            (prev.get_text(strip=True) if prev.name else (prev.string or "").strip())
            for prev in el.previous_siblings
        ):
            break
        if _is_leading_noise(el.get_text(" ", strip=True), title, book_title):
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
        ref = f"{entry.source_ref}#{entry.part}" if entry.part else entry.source_ref
        self.stdout.write(f"→ {entry.title}  (ccel:{ref})")
        try:
            parts = toc_parts(entry.source_ref, entry.part)
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
                if entry.summary_titles:
                    leaf_title = summary_title(leaf_title)
                # Only a volume import carries the volume's page furniture.
                body = self._section_body(url, leaf_title, entry.title, bool(entry.part))
                if is_contents_body(body):
                    continue
                if not body:
                    continue
                # A single-leaf part is the whole chapter — no subheading needed.
                # Multi-leaf parts keep each leaf's heading, so the work's own
                # divisions stay visible and citable (Confessions is quoted as
                # Book VIII.12). <h3> matches import_gutenberg's joined sections.
                pieces.append(f"<h3>{leaf_title}</h3>{body}" if len(leaves) > 1 else body)
            if not pieces:
                continue
            chapter_title = clean_title(part_title)
            if entry.summary_titles:
                chapter_title = summary_title(chapter_title)
            chapters.append((chapter_title, "".join(pieces)))
            if entry.group_parts:
                self.stdout.write(f"    {part_title}: {len(pieces)} sections")

        book = upsert_book(entry, chapters)
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))

    def _section_body(
        self, url: str, title: str, book_title: str = "", volume: bool = False
    ) -> str:
        """Fetch and clean one TOC section; "" when the request fails."""
        try:
            time.sleep(DELAY)
            return extract_body(fetch(url), title, book_title, volume)
        except requests.RequestException as exc:
            self.stderr.write(self.style.WARNING(f"  skip {url}: {exc}"))
            return ""
