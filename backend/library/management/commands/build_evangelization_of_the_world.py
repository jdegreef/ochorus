"""Build John R. Mott's *The Evangelization of the World in This Generation* (1900).

Source: the Internet Archive scan ``evangelizationof00mottuoft`` (University of
Toronto copy; the 1901 printing of the Student Volunteer Movement's 1900 text,
"Copyright, 1900" on its verso, NOT_IN_COPYRIGHT). The Google scan of a 1900
printing, ``evangelizationw00mottgoog``, is the same setting page for page (same
folios, same line breaks) and was the witness the text was proof-read against.

Why not ``import_archive``: nothing in this book says "CHAPTER". Each chapter
opens on a fresh page under a roman numeral and a two-to-four-line ALL-CAPS
title, and the running heads are ALL-CAPS lines with no page number (the folio
sits alone at the foot), so the importer's marker regex finds nothing and its
header test (which needs a digit) keeps every running head as prose. And Mott
cites his sources in some 270 footnotes, set in small type at the foot of the
page, which a text-layer reflow runs straight into the paragraphs.

So this reads the scan's ``_djvu.xml`` — the OCR WITH its coordinates — and uses
the page geometry the text layer throws away:

* **Running heads / chapter heads** are the ALL-CAPS lines at the top of a
  page. A page whose top carries two or more of them (or a numeral and one) is a
  chapter opening; there are exactly nine, which is asserted.
* **Folios** are the lone short token at the foot of the page.
* **Footnotes** are the trailing run of lines set tighter than the body (the
  small type's line pitch is ~54 units against the body's ~76), opening after a
  gap on a reference mark. A set-off poem is set in the same small type, so the
  LAST gap inside such a run is where the notes begin. A note that runs over
  onto the next page (it does not end on a full stop or a number) lets that
  page's tight tail start without a mark. Mott's citations are dropped with
  their in-text reference marks (the OCR's ``^``/``*``/stray digit after the
  closing quote); the importers have no footnote apparatus to carry them.
* **Paragraphs** are read off the compositor's first-line indent (~50 units in
  from the page's text margin), which also catches the paragraphs that open at
  the top of a page — exactly where a blank-line heuristic is blind.
* **Marginalia** (a reader's pencil marks at a few page edges, a library
  stamp) are the words that lie wholly outside the text block.

End-of-line hyphens are closed up, except where the book itself sets the word
hyphenated mid-line ("to-day", "fellow-students", "non-Christian"), so the
join follows Mott's own spelling rather than a guess. The compositor's thin
space before ``; : ? !`` (which OCR reads as a word space) is closed up.

Dropped: the front matter (title pages, acknowledgment, contents), the
Bibliography and the Analytical Index, every running head, folio and footnote.

OCR misreadings in the text are corrected by literal pairs in
``corrections.BODY_CORRECTIONS["evangelization-of-the-world"]`` (applied here
through ``settled_chapter_body`` and on every deploy), each checked against the
witness scan — see the english-qa skill's "second printing" method.

Fixture-driven like every other book: ``seed_books`` creates it (and resolves
the existing ``john-r-mott`` author from ``authors.json``) on deploy from
``fixtures/content/books/evangelization-of-the-world.en.json``. This command
GENERATES that fixture's rows reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_evangelization_of_the_world
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from xml.etree import ElementTree as ET

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_archive import USER_AGENT
from library.models import Author, Book, Chapter

SLUG = "evangelization-of-the-world"
TITLE = "The Evangelization of the World in This Generation"
SUBTITLE = ""
AUTHOR_SLUG = "john-r-mott"
ARCHIVE_ID = "evangelizationof00mottuoft"
PUBLICATION_YEAR = 1900
COVER_COLOR = "#2f5d62"  # deep sea-green — house-style cover ground

DESCRIPTION = (
    "The book behind the watchword of the Student Volunteer Movement. Writing "
    "in 1900, when thousands of college men and women had pledged themselves "
    "to foreign missions, John R. Mott sets out what \"the evangelization of "
    "the world in this generation\" means — not the conversion of the world, "
    "but giving every person living an adequate opportunity to know Jesus "
    "Christ as Saviour and to become His real disciple. He grounds the "
    "obligation in men's need and Christ's command, weighs the difficulties "
    "honestly, and argues its possibility from the first generation of "
    "Christians, from modern missionary achievements, from the Church's "
    "resources and from the witness of missionary leaders, before naming what "
    "it will take: a praying, self-sacrificing, missionary Church."
)

ATTRIBUTION = (
    "Public domain — John R. Mott, The Evangelization of the World in This "
    "Generation (New York: Student Volunteer Movement for Foreign Missions, "
    "1900). Text from the Internet Archive scan evangelizationof00mottuoft (the "
    "1901 printing), proof-read against the 1900 printing "
    "evangelizationw00mottgoog. Mott's footnote citations, the bibliography and "
    "the index are omitted; the wording is unchanged."
)

# The book's own Contents, in order. Nine chapter openings must be found.
CHAPTERS = [
    "Definition, or, What Is Meant by the Evangelization of the World in This Generation",
    "The Obligation to Evangelize the World",
    "Difficulties in the Way of Evangelizing the World",
    "The Possibility of Evangelizing the World in This Generation in View of the "
    "Achievements of the First Generation of Christians",
    "The Possibility of Evangelizing the World in This Generation in View of Some "
    "Modern Missionary Achievements",
    "The Possibility of Evangelizing the World in This Generation in View of the "
    "Opportunities, Facilities and Resources of the Church",
    "The Possibility of Evangelizing the World Within a Generation as Viewed by "
    "Leaders in the Church",
    "Factors Essential to the Evangelization of the World in This Generation",
    "The Evangelization of the World in This Generation as a Watchword",
]

# ---- page geometry ------------------------------------------------------------

#: A folio: one short token, with whatever specks the scanner kept around it.
_FOLIO = re.compile(r"^[^A-Za-z0-9]*[0-9A-Za-z]{1,4}[^A-Za-z0-9]*$")
#: How a footnote line opens: a reference mark the OCR read as punctuation, a
#: digit or a stray letter ("'", "*", "^", "2", "J \"").
_NOTE_MARK = re.compile(r"^(?:[^A-Za-z0-9\s(\[]{1,3}|[\da-z](?=\s)|[A-Z]\s+[\"'])\s*\S")
#: A chapter numeral line above the title ("II", "Ill" for III).
_NUMERAL = re.compile(r"^[IVXl|]{1,4}$")
#: The foot of the page: a folio below this is a folio, not a stray line.
_FOOT = 2150
#: Chapter and running heads sit in the top part of the page.
_HEAD_ZONE = 900
#: A footnote line in small type is shorter than a body line's ascender-to-
#: descender height (35-45 against 43-56 units).
_SMALL_LINE = 40
#: Paragraph indent window, in units from the page's text margin. A continuation
#: line whose first "word" is a hyphen-joined pair ("tion, that") carries the
#: pair's box, so it can sit further in; it is excluded separately.
_INDENT = (25, 90)
#: A line ending this far short of the measure closes its paragraph.
_SHORT_LINE = 150
#: A side-head centred on the measure sits this far in (a poem line, ~90).
_CENTRED = 180
#: A line that can close a paragraph: a stop, then at most a reference mark.
_ENDS_SENTENCE = re.compile(r"[.!?:;\"')—][\s^*■•«»'\"\d]*$")


class Line:
    __slots__ = ("top", "bottom", "left", "right", "words")

    def __init__(self, words: list[tuple[int, int, int, int, str]]):
        self.words = words  # (left, bottom, right, top, text)
        self.top = min(w[3] for w in words)
        self.bottom = max(w[1] for w in words)
        self.left = min(w[0] for w in words)
        self.right = max(w[2] for w in words)

    @property
    def text(self) -> str:
        return " ".join(" ".join(w[4].split()) for w in self.words if w[4].strip())


def fetch_xml(item_id: str) -> bytes:
    url = f"https://archive.org/download/{item_id}/{item_id}_djvu.xml"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=180)
    resp.raise_for_status()
    return resp.content


def parse_pages(xml: bytes | str) -> list[list[Line]]:
    root = ET.fromstring(xml)
    pages = []
    for obj in root.iter("OBJECT"):
        lines = []
        for line in obj.iter("LINE"):
            words = []
            for w in line.iter("WORD"):
                left, bottom, right, top = map(int, w.get("coords").split(",")[:4])
                words.append((left, bottom, right, top, w.text or ""))
            if words:
                lines.append(Line(words))
        pages.append(lines)
    return pages


def _letters(text: str) -> str:
    return re.sub(r"[^A-Za-z]", "", text)


def _is_caps(text: str) -> bool:
    letters = _letters(text)
    return len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) >= 0.8


def _is_junk(line: Line) -> bool:
    """A library stamp or a pencil mark: no real word, mostly not letters."""
    text = line.text
    chars = re.sub(r"\s", "", text)
    if not chars:
        return True
    if not re.search(r"[A-Za-z]{3,}|\d{2,}", text) and not _FOLIO.match(chars):
        return True
    return len(_letters(text)) / len(chars) < 0.5 and not re.search(r"\d", text)


def _drop_marginalia(lines: list[Line]) -> list[Line]:
    """Words lying wholly outside the text block are a reader's marks."""
    if len(lines) < 8:
        return lines
    lefts = sorted(ln.left for ln in lines)
    rights = sorted(ln.right for ln in lines)
    margin, rmargin = lefts[len(lefts) // 4], rights[(len(rights) * 3) // 4]
    out = []
    for ln in lines:
        words = [w for w in ln.words if w[2] >= margin - 10 and w[0] <= rmargin + 25]
        if words:
            out.append(Line(words))
    return out


class Page:
    """One scanned page, split into head, body and notes."""

    def __init__(self, index: int, lines: list[Line]):
        self.index = index
        lines = _drop_marginalia([ln for ln in lines if not _is_junk(ln)])
        if lines and lines[-1].top > _FOOT and _FOLIO.match(lines[-1].text.replace(" ", "")):
            lines = lines[:-1]
        self.lines = lines
        self.head: list[Line] = []
        self.body: list[Line] = lines
        self.notes: list[Line] = []
        self.margin = 0

    def split(self, note_runs_on: bool) -> None:
        lines = self.lines
        k = 0
        while k < min(len(lines), 6) and lines[k].top < _HEAD_ZONE and (
            _is_caps(lines[k].text) or _NUMERAL.match(lines[k].text.replace(" ", ""))
        ):
            k += 1
        self.head, lines = lines[:k], lines[k:]
        start = self._notes_start(lines, note_runs_on)
        self.body, self.notes = lines[:start], lines[start:]
        lefts = sorted(ln.left for ln in self.body)
        self.margin = lefts[len(lefts) // 4] if lefts else 0

    @staticmethod
    def _notes_start(lines: list[Line], note_runs_on: bool) -> int:
        n = len(lines)
        if n < 5:
            return n
        pitch = statistics.median(lines[i].top - lines[i - 1].top for i in range(1, n))
        # the trailing run set tighter than the body
        s = n - 1
        while s > 1 and lines[s].top - lines[s - 1].top < pitch * 0.85:
            s -= 1
        if s < n - 1:
            if lines[s].top - lines[s - 1].top <= pitch:
                return n
            # a poem above the notes is set in the same small type: the notes
            # begin at the LAST gap inside the run
            gaps = [j for j in range(s, n) if lines[j].top - lines[j - 1].top > pitch * 0.95]
            j = gaps[-1]
            if _NOTE_MARK.match(lines[j].text) or note_runs_on:
                return j
            return n
        # a one-line note
        last = lines[-1]
        gap = last.top - lines[-2].top
        small = last.bottom - last.top < _SMALL_LINE
        if (gap > pitch * 1.05 or small) and _NOTE_MARK.match(last.text):
            return n - 1
        return n

    @property
    def note_runs_on(self) -> bool:
        """Does this page's last note continue on the next page?"""
        return bool(self.notes) and not re.search(r"[.)\d]\W{0,2}$", self.notes[-1].text.rstrip())

    @property
    def is_chapter_opening(self) -> bool:
        caps = [ln for ln in self.head if _is_caps(ln.text)]
        numeral = any(_NUMERAL.match(ln.text.replace(" ", "")) for ln in self.head)
        return len(caps) >= 2 or (len(caps) == 1 and numeral)

    @property
    def is_bibliography(self) -> bool:
        return bool(self.head) and _letters(self.head[0].text).upper().startswith("BIBLIOG")


def chapter_pages(xml: bytes | str) -> list[list[Page]]:
    """The pages of each of the nine chapters, in order."""
    pages = [Page(i, lines) for i, lines in enumerate(parse_pages(xml))]
    runs_on = False
    for page in pages:
        page.split(runs_on)
        runs_on = page.note_runs_on
    bib = next((p.index for p in pages if p.is_bibliography), None)
    if bib is None:
        raise CommandError("no Bibliography page found — the scan changed.")
    # The title page and contents are caps too; the body starts past them.
    openings = [p.index for p in pages[:bib] if p.is_chapter_opening and p.index > 12]
    if len(openings) != len(CHAPTERS):
        raise CommandError(
            f"found {len(openings)} chapter openings, expected {len(CHAPTERS)} — the scan changed."
        )
    bounds = [*openings, bib]
    return [pages[a:b] for a, b in zip(bounds[:-1], bounds[1:], strict=True)]


# ---- text -------------------------------------------------------------------

#: The OCR's renderings of a superscript reference mark; never Mott's text.
_MARK_CHARS = re.compile(r"[\^■•«»]")
_WORD = re.compile(r"[A-Za-z]+")


def _clean_tokens(tokens: list[str]) -> list[str]:
    """Drop footnote reference marks; attach free-standing quotation marks.

    The OCR spaces a quotation mark off its word ('" Preach the gospel."') and
    renders a superscript reference as ^ * ' " or a digit after the closing
    punctuation ('gospel." *', 'doctor.^', 'reached." 2').
    """
    out: list[str] = []
    for i, raw in enumerate(tokens):
        tok = _MARK_CHARS.sub("", raw)
        if not tok:
            continue
        nxt = _MARK_CHARS.sub("", tokens[i + 1]) if i + 1 < len(tokens) else ""
        prev = out[-1] if out else ""
        if re.fullmatch(r"[*'\"]{1,3}|\d", tok) and re.search(r"[.,;:!?\"]$", prev):
            opener = tok == '"' and re.match(r"[A-Za-z']", nxt) and not prev.endswith('"')
            if not opener and (
                not re.match(r"[A-Za-z]", nxt) or tok in ("*", "'") or tok.isdigit() or prev.endswith('"')
            ):
                continue  # a reference mark
        # an opening double quote read as ** / *' / ''
        if re.fullmatch(r"\*\*|\*'|''|\"", tok) and re.match(r"[A-Za-z']", nxt):
            out.append('"')
            continue
        # a mark glued to the closing punctuation: 'doctor.*', 'earth."*'
        tok = re.sub(r"(?<=[.,;:!?\"])(?:\*+|'\"|''|\d)$", "", tok)
        tok = re.sub(r"(?<=\")[*']+$", "", tok)
        tok = tok.replace("''", '"')
        if tok:
            out.append(tok)
    # A free-standing mark closes the quotation that is open, else opens one;
    # the state is tracked per mark and per paragraph.
    merged: list[str] = []
    is_open = {'"': False, "'": False}
    i = 0
    while i < len(out):
        tok = out[i]
        if tok in is_open:
            nxt = out[i + 1] if i + 1 < len(out) else ""
            if not is_open[tok] and re.match(r"[A-Za-z0-9'\"(\[$]", nxt):
                merged.append(tok + nxt)
                is_open[tok] = True
                _track(merged[-1][1:], is_open)
                i += 2
                continue
            if merged:
                merged[-1] += tok
                is_open[tok] = False
                i += 1
                continue
        merged.append(tok)
        _track(tok, is_open)
        i += 1
    return merged


def _track(tok: str, is_open: dict[str, bool]) -> None:
    """Follow the quotation marks glued to a word."""
    if tok.startswith('"'):
        is_open['"'] = True
    elif tok.startswith("'") and _WORD.match(tok[1:]):
        is_open["'"] = True
    core = tok.rstrip(".,;:!?)—-")
    if core.endswith('"') and len(core) > 1:
        is_open['"'] = False
    if re.search(r"[.,;:!?]'", tok):
        is_open["'"] = False


#: Line-end compounds the book never sets mid-line, read off the page images:
#: these keep their hyphen ("slave-trade", not "slavetrade"). Every other
#: unattested line-end hyphen is a syllable break and closes up.
_KEEP_HYPHEN = frozenset({
    "eighty-three", "high-minded", "one-tenth", "single-handed", "slave-trade", "where-ever",
})
_HYPHEN_PREFIXES = frozenset({"non", "self"})


class Hyphenation:
    """Close an end-of-line hyphen, unless the book hyphenates that word."""

    def __init__(self, chapters: list[list[Page]]):
        self.hyphenated: Counter[str] = Counter()
        self.closed: Counter[str] = Counter()
        for pages in chapters:
            for page in pages:
                for ln in page.body:
                    for tok in ln.text.split()[:-1]:  # mid-line only
                        word = re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", tok).lower()
                        if re.fullmatch(r"[a-z]+-[a-z]+", word):
                            self.hyphenated[word] += 1
                        elif word:
                            self.closed[word] += 1

    def join(self, stem: str, nxt: str) -> str:
        """``stem`` has had its hyphen removed ("evan"), ``nxt`` opens the next line."""
        if stem.endswith(",") or stem[-1:].isdigit():  # "$75,-" / "000"
            return stem + nxt
        m = _WORD.match(nxt)
        head = re.sub(r"^[^A-Za-z]+", "", stem).lower()
        if head == "mc":  # "Mc-" / "Giffert": a name, not a compound
            return stem + nxt
        if not m or m.group(0)[:1].isupper():  # "non-" / "Christian"
            return f"{stem}-{nxt}"
        tail = m.group(0).lower()
        if self.hyphenated[f"{head}-{tail}"] and not self.closed[head + tail]:
            return f"{stem}-{nxt}"
        if head in _HYPHEN_PREFIXES or f"{head}-{tail}" in _KEEP_HYPHEN:
            return f"{stem}-{nxt}"
        return stem + nxt


#: A speck the scanner read in the white space after a line's last word
#: ("force. r^ 4 (> y"): no two letters together, or a character no word has.
_STRONG_SPECK = re.compile(r"[<>\\|{}]|^[A-Za-z]\^$|^\(.*\^")


def _is_speck(token: str) -> bool:
    return not re.search(r"[A-Za-z]{2}", token) or (
        bool(_STRONG_SPECK.search(token)) and not re.search(r"[A-Za-z]{4}", token)
    )


def _drop_trailing_specks(tokens: list[str]) -> list[str]:
    """Cut a line's trailing run of specks when one is unmistakably not text.

    A backslash glued to a quotation mark is a speck on the mark, so the
    backslash goes and the mark stays; a lone lowercase letter after a
    sentence's closing quote is a speck too ('Christ." i').
    """
    tokens = [re.sub(r"\\(?=['\"])", "", t) for t in tokens]
    k = len(tokens)
    while k and _is_speck(tokens[k - 1]):
        k -= 1
    tail = tokens[k:]
    if any(_STRONG_SPECK.search(t) for t in tail):
        return tokens[:k]
    if len(tail) == 1 and re.fullmatch(r"[b-z]", tail[0]) and k and tokens[k - 1].endswith('."'):
        return tokens[:k]
    return tokens


def reflow(pages: list[Page], hyphens: Hyphenation) -> str:
    """A chapter's body lines as ``<p>`` paragraphs."""
    paras: list[list[str]] = []
    cur: list[str] = []
    open_hyphen = False
    ended = ended_short = False
    for page in pages:
        rights = sorted(ln.right for ln in page.body)
        measure = rights[(len(rights) * 3) // 4] if rights else 0
        for ln in page.body:
            tokens = _drop_trailing_specks(ln.text.split())
            if not tokens:
                continue
            indent = ln.left - page.margin
            pair_box = " " in ln.words[0][4].strip()
            indented = _INDENT[0] <= indent <= _INDENT[1] and not pair_box
            # A flush line after a paragraph's short last line: the italic
            # side-heads ("Factors on the home field.") are set flush left.
            flush_after_end = ended_short and indent < _INDENT[0]
            # a centred side-head ("Factors on the home field.")
            centred = ended_short and indent > _CENTRED and ln.right < measure - _SHORT_LINE
            if (indented or flush_after_end or centred) and not open_hyphen and cur and ended:
                paras.append(cur)
                cur = []
            # A paragraph ends on a stop (a trailing reference mark does not
            # count: 'commandments." ^'); the second line of a two-line
            # side-head is indented but continues it.
            ended = bool(_ENDS_SENTENCE.search(" ".join(tokens)))
            ended_short = ended and ln.right < measure - _SHORT_LINE
            if open_hyphen and cur:
                cur.append(hyphens.join(cur.pop()[:-1], tokens[0]))
                tokens = tokens[1:]
            cur.extend(tokens)
            open_hyphen = bool(cur) and re.search(r"[A-Za-z0-9,]-$", cur[-1]) is not None
    if cur:
        paras.append(cur)
    out = []
    for tokens in paras:
        text = " ".join(_clean_tokens(tokens))
        # the compositor's thin space before ; : ? ! — OCR reads it as a word space
        text = re.sub(r"(?<=[A-Za-z0-9\"')\]]) +([;:?!])", r"\1", text)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if text:
            out.append(f"<p>{text}</p>")
    return "".join(out)


def build_chapters(xml: bytes | str) -> list[tuple[str, str]]:
    chapters = chapter_pages(xml)
    hyphens = Hyphenation(chapters)
    return [(title, reflow(pages, hyphens)) for title, pages in zip(CHAPTERS, chapters, strict=True)]


class Command(BaseCommand):
    help = "Build Mott's The Evangelization of the World in This Generation (dev DB)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} missing — `loaddata library/fixtures/content/authors.json`"
            ) from None

        chapters = build_chapters(fetch_xml(ARCHIVE_ID))

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{ARCHIVE_ID}",
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 1500:
                raise CommandError(f"ch {order} ({title[:40]!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:60]:60} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"
        ))
