"""Ingest public-domain books from Project Gutenberg into the library.

Gutenberg HTML structure varies per book, so we pick the dominant chapter
divider empirically: a ``div.chapter`` wrapper if present, else the heading
level (h2..h5) that occurs most often. Front matter before the first chapter
(title page, contents) is dropped. PG license boilerplate is stripped, and so
is the back of the book: transcriber's notes, and everything after a closing
colophon or a publisher's catalogue imprint.

    python manage.py import_gutenberg                 # all Gutenberg books
    python manage.py import_gutenberg humility        # one book by slug
"""

from __future__ import annotations

import re
from html import escape

import requests
from django.core.management.base import BaseCommand, CommandError

from library import english_audit
from library.catalog import BOOKS, BookEntry
from library.ingest import (
    clean_fragment,
    clean_html,
    clean_title,
    display_line,
    drop_furniture,
    is_front_matter,
    soup,
    upsert_book,
    word_count,
)

USER_AGENT = "OchorusBot/0.1 (+https://ochorus.org; public-domain book reader)"
# A heading that is only a number — bare ("I.") or labelled ("CHAPTER IV.").
# Either way the real title lives in the next node and must be borrowed.
_ROMAN_OR_NUM = re.compile(r"^(?:chapter\s+)?[IVXLCDM\d]+\.?$", re.I)
# Sections shorter than this merge into the previous chapter (interleaved
# hymns/poems, e.g. Prevailing Prayer) or, before any chapter exists, are
# dropped as front matter (prefatory notes, epigraph poems). Real chapters
# in the library run 1,300+ words; the longest hymn coda is ~250.
_TINY_SECTION_WORDS = 300
# The outermost verse container, for the fallback walk. Not `ingest._VERSE_CLASS`:
# that also matches a stanza, which is a poem's part, not a poem.
_POEM = re.compile(r"poem|poetry|lg-container")
# The class PGDP transcribers put on the box holding their notes, as a whole
# class TOKEN. A substring won't do: `*=tnote` is inside every `footnote`, and
# footnotes are the author's. Across the library's 27 Gutenberg sources the
# three spellings mark 11 boxes and every one is a transcriber's note (errata,
# cover credit, "larger version of this map"); #65066's `tnotes` endnote shipped
# as Edwards's closing paragraphs because its heading was a centred div the
# importer never collected, and the sw edition translated it as his.
_TRANSCRIBER_NOTE = re.compile(r"^(?:tnotes?|transnote)$")
# Catalogued Gutenberg books whose layout this importer can't chapter, built by
# their own command instead. Skipped here so a stray run can't re-chapter them.
BUILT_ELSEWHERE = {
    "george-muller-of-bristol": "build_george_muller_of_bristol",
}


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
    # so cut at the universal end marker before parsing. The marker's wording
    # varies — newer files say "END OF THE", older ones "END OF THIS" — and a
    # miss leaves the whole licence footer in the last chapter (Unfailing
    # Springs #57109 leaked it as its only chapter).
    html = re.split(r"\*\*\*\s*END OF TH(?:E|IS) PROJECT GUTENBERG", html, flags=re.I)[0]
    # Cut the header at the START marker too. Pre-2019 mirrors carry no
    # `pgheader` class for the CSS strip below to catch, so without this the
    # licence preamble and title page import as the book's opening — invisible
    # on a book with real chapter headings (front matter is dropped), fatal on
    # one without, which becomes a single chapter of pure boilerplate.
    after = re.split(
        r"\*\*\*\s*START OF TH(?:E|IS) PROJECT GUTENBERG[^*]*\*\*\*",
        html, flags=re.I, maxsplit=1,
    )
    if len(after) > 1:
        html = after[1]
    s = soup(html)
    for el in s.select("[class*=pg-boilerplate], [class*=pgheader], [class*=pg-footer]"):
        el.decompose()
    # The transcriber's own notes — errata, "missing periods silently added" —
    # are the etext's apparatus, not the work. See _TRANSCRIBER_NOTE.
    for el in s.find_all(class_=_TRANSCRIBER_NOTE):
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
    # Daily devotionals run to hundreds of sections (365 + front matter);
    # extract_chapters folds those into month chapters afterwards.
    for lvl in range(1, 7):
        n = len(root.find_all(f"h{lvl}"))
        if 80 < n <= 400:
            return f"h{lvl}"
    return None


def resolve_title(heading):
    """Return (title, consumed_node).

    For a bare-numeral heading (Humility's "<h5>I.</h5>") the real title is the
    next node; we fold it into the title and return it as `consumed_node` so the
    caller can omit it from the body (otherwise it duplicates as the first line).
    """
    # A heading that puts the chapter numeral on its OWN line above the title
    # ("<h2>I<br/>BEGINNING RIGHT</h2>", "<h2>CHAPTER VII.<br/>…</h2>") fuses under
    # a space separator to "I BEGINNING RIGHT", which no roman-prefix rule can
    # safely strip — dropping the leading "I" would also wreck "I AM THE WAY". The
    # <br/> is the reliable signal: split on it and, when the first line is a bare
    # numeral / "CHAPTER N" marker, keep only the descriptive remainder.
    # A heading that puts the chapter numeral on its OWN line above the title
    # ("<h2>I<br/>BEGINNING RIGHT</h2>", "<h2>CHAPTER VII.<br/>…</h2>") — split it
    # on the <br/>s ONLY. Splitting on get_text's node boundaries instead would
    # make a phantom line out of any inline element in the heading (a page-anchor
    # span, a styled first letter), so the <br/> markup is the reliable signal.
    lines = [soup(seg).get_text(" ", strip=True)
             for seg in re.split(r"<br\s*/?>", heading.decode_contents(), flags=re.I)]
    # A "Contents"/"Table of Contents" TOC-return link often trails the heading on
    # its own line (<small class="toclink"><a>Contents</a></small>, e.g. Murray's
    # #29296) — navigation, not the title, so drop it: that keeps a bare "CHAPTER
    # VI" heading a bare counter (as the old fused path did via clean_title's
    # trailing-"Contents" strip) rather than mistaking the link for a title.
    lines = [ln for ln in lines
             if ln and ln.lower().rstrip(".") not in {"contents", "table of contents"}]
    if len(lines) >= 2 and _ROMAN_OR_NUM.match(lines[0]):
        # Trailing punctuation set OUTSIDE the title's span is its own text node
        # ("<small><span>…of God</span>?</small>"), so the join leaves a space
        # before it — drop that before cleaning.
        remainder = re.sub(r"\s+([?!,;:])", r"\1", " ".join(lines[1:]))
        remainder = clean_title(remainder)
        if remainder and not _ROMAN_OR_NUM.match(remainder):
            return remainder, None
    # clean_title now handles ALL-CAPS -> Title Case itself, so headings/siblings
    # need no separate title-casing here.
    title = clean_title(heading.get_text(" ", strip=True))
    if _ROMAN_OR_NUM.match(title):
        sib = heading.find_next(["h3", "h4", "p"])
        if sib:
            extra = clean_title(sib.get_text(" ", strip=True))
            if extra:
                sep = "" if title.endswith(".") else "."
                # clean_title strips the "Chapter N." label when a descriptive
                # title follows (bare "I." numerals are kept, as before).
                return clean_title(f"{title}{sep} {extra}"), sib
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
            # A centred display line would reach clean_fragment as a bare div
            # and be unwrapped to loose text; give it its block. Wrappers and
            # furniture pass through as before.
            line = display_line(sib) if getattr(sib, "name", None) == "div" else ""
            parts.append(line or str(sib))
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
                    # A poem's verse-line divs become a blockquote with line
                    # breaks (stanzas separated by a blank line).
                    classes = " ".join(el.get("class", []))
                    if _POEM.search(classes) and el.find_parent(class_=_POEM) is None:
                        # Read a copy with the furniture gone, as the sanitizer
                        # would: PG 65066 sets every correction twice (an
                        # `htmlonly` and an `epubonly` copy), which read
                        # "SENSUAL mind; mind;". And join a line's text as
                        # written — a separator puts a space inside
                        # "<span>ALL</span>." wherever markup meets a stop.
                        poem = soup(str(el)).find("div")
                        drop_furniture(poem)
                        stanzas = []
                        for st in poem.select("[class*=stanza], div.group") or [poem]:
                            lines = [
                                escape(" ".join(d.get_text().split()), quote=False)
                                for d in st.find_all("div", recursive=False)
                            ] or [escape(" ".join(st.get_text().split()), quote=False)]
                            stanzas.append("<br/>".join(line for line in lines if line))
                        parts.append(
                            "<blockquote>"
                            + "<br/><br/>".join(s for s in stanzas if s)
                            + "</blockquote>"
                        )
                    # Any other div is a container (its blocks arrive on their
                    # own) or a centred display line, kept as its block — unless
                    # something already collected carries it.
                    elif el is not consumed and el.find_parent(
                        ["blockquote", "ul", "ol", "table"]
                    ) is None and el.find_parent(class_=_POEM) is None:
                        if line := display_line(el):
                            parts.append(line)
                    continue
                if el is consumed or el.find_parent("blockquote") is not None:
                    continue
                if el.find_parent(["ul", "ol"]) is not None:
                    continue  # list items arrive via their list
                if el.find_parent(class_=_POEM) is not None:
                    continue  # already captured via its poem div
                parts.append(str(el))
            out.append((title, clean_fragment("".join(parts))))
    return out


# 19th-century texts often close with the publisher's back catalogue — an imprint
# page ("PUBLISHED BY GOULD AND LINCOLN … 12mo, cloth, $1.25") followed by more
# priced-book pages. These carry the divider heading like a chapter but are not
# the work. The one clean signal is the ALL-CAPS imprint: a book price ($x.xx) or
# a binding word (octavo/quarto/cloth) each fire on real prose — a parable's
# "$10.00", or Portuguese "décimo quarto versículo" — but "PUBLISHED BY <NAME>"
# in caps does not. So the imprint marks where the catalogue BEGINS, and
# everything from there to the end goes (the continuation pages have no imprint of
# their own). Scanned only in the trailing sections, so an imprint quoted
# mid-text can't truncate the book.
_AD_IMPRINT = re.compile(r"PUBLISHED BY\s+[A-Z]")


def _catalogue_start(sections: list[tuple[str, str]]) -> int | None:
    """Index of the trailing publisher-catalogue's first section, or None.

    A section BEGINS the catalogue only when the imprint stands at its head — the
    whole section is the ad. A real chapter that merely appends a publisher notice
    at its tail (some Gutenberg texts fold the ad into the last chapter) keeps its
    prose and is left alone. Scanned only across the trailing sections, so an
    imprint quoted mid-book can't truncate the work.
    """
    for i in range(max(0, len(sections) - 5), len(sections)):
        head = re.sub(r"<[^>]+>", " ", sections[i][1])[:200]
        if _AD_IMPRINT.search(head):
            return i
    return None


# The printer's colophon, standing alone as a block. What follows it in the LAST
# section is the back of the printed book, not the work: #73032 ran Bounds's
# final paragraph straight into it and then nine pages of Revell's catalogue,
# which `_catalogue_start` never sees because no heading divides them from the
# chapter. The whole block must be the colophon, so a sentence that merely
# mentions where a book was printed can't truncate anything.
_COLOPHON = re.compile(
    r"<p>(?:<[bi]>)?\s*Printed in (?:the )?(?:United States(?: of America)?|U\.\s?S\.\s?A\.)"
    r"\.?\s*(?:</[bi]>)?</p>",
    re.I,
)


def _cut_at_colophon(body: str) -> str:
    """The last section's body up to a standalone colophon block, if it has one."""
    m = _COLOPHON.search(body)
    return body[: m.start()].rstrip() if m else body


_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTH_DAY = re.compile(rf"^({'|'.join(_MONTHS)})\s+\d{{1,2}}\.?$", re.I)


def group_daily_entries(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Fold a 365-entry daily devotional into 12 month chapters.

    Each day keeps its heading as an <h3> above its entry. Sections that
    aren't month-day entries (title page, publisher's note) are dropped.
    """
    months: dict[str, list[str]] = {}
    for t, b in sections:
        m = _MONTH_DAY.match(t.strip())
        if not m:
            continue
        months.setdefault(m.group(1).title(), []).append(
            f"<h3>{clean_title(t)}</h3>{b}"
        )
    return [(month, "".join(months[month])) for month in _MONTHS if month in months]


def extract_chapters(html: str) -> list[tuple[str, str]]:
    root = content_root(html)
    tag = pick_heading_tag(root)
    if tag is None:
        return [("", clean_html(root))]
    sections = [
        (t, b) for t, b in split_by_heading(root, tag) if not is_front_matter(t)
    ]
    # A year-long daily devotional (e.g. Days of Heaven Upon Earth): hundreds
    # of "January 1."-style sections become 12 month chapters.
    if len(sections) > 80:
        daily = sum(1 for t, _ in sections if _MONTH_DAY.match(t.strip()))
        if daily > len(sections) * 0.8:
            return group_daily_entries(sections)
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
    # Drop the publisher's back catalogue, if any, off the end. `cut` is falsy
    # both when there is none and at index 0 — a whole work is never a catalogue,
    # so 0 means leave it be, never slice the book to nothing.
    cut = _catalogue_start(merged)
    if cut:
        merged = merged[:cut]
    if merged:
        title, body = merged[-1]
        merged[-1] = (title, _cut_at_colophon(body))
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
            if entry.slug in BUILT_ELSEWHERE:
                self.stdout.write(f"→ {entry.title}: skipped — built by `{BUILT_ELSEWHERE[entry.slug]}`")
                continue
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
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        self.stdout.write(self.style.SUCCESS(f"  ✓ {book.chapter_count} chapters"))
