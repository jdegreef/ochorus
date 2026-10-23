"""Build Andrew Murray's *Abide in Christ* from an Internet Archive scan.

Neither CCEL nor Gutenberg carries the book — CCEL's Murray page names it in
the biography and links no text — so the source is the OCR layer of Henry
Altemus's Philadelphia printing of 1895 (`abideinchrist01murr`, Library of
Congress copy). Of the four pre-1929 scans on archive.org it has the cleanest
prose and the only day headings and chapter titles that survive OCR: the
Revell printings set each title in blackletter, which reads as "ail ge foijo
Ijabe come to JHm". (`abideinchristtho0000murr`, catalogued as Nisbet 1880, is
a 2013 large-print reprint and is not used.)

`import_archive` can't take it as a catalog entry, for two reasons:

* its chapter marker is CHAPTER/CHAP. with a roman numeral, and this book
  divides into "FIRST DAY." … "THIRTY-FIRST DAY."; and
* its licence gate refuses any copyright status other than NOT_IN_COPYRIGHT,
  and this item carries the Library of Congress's wording ("unaware of any
  copyright restrictions"). The printing is 1895, so the book is US public
  domain by date; `_public_domain` below checks exactly that.

So this command reuses the importer's fetch, metadata and reflow, and does
the splitting itself: the Preface (with the John 15:1–12 page that follows the
contents), then thirty-one days titled from the book's own Contents. Each day
opens with a running "ABIDE IN CHRIST" line and the title in capitals, both
dropped; then an epigraph, set in italics; then the prose, whose drop-cap
opener ("IT is") is title-cased. Footnotes are lifted from the foot of their
page and set after the day's text.

The OCR then needs about five hundred repairs — misread letters ("Avho",
"toith"), junk for punctuation ("^", "{"), wrong digits in references. They
live in `data/abide-in-christ/ocr_fixes.json`, each settled against the two
scans of the Revell printing (see `OCR_FIXES`).

Fixture-driven (`seed_books` creates it on deploy), idempotent, and no
`catalog.py` entry, so a stray `import_archive` can't mangle it.

    DJANGO_DEBUG=true uv run python manage.py build_abide_in_christ
"""

from __future__ import annotations

import html as _html
import json
import pathlib
import re
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_archive import (
    _BARE_NUM,
    PD_THROUGH_YEAR,
    _is_header,
    _reflow,
    fetch_text,
    metadata,
    printing_year,
)
from library.models import Author, Book, Chapter

SLUG = "abide-in-christ"
TITLE = "Abide in Christ"
SUBTITLE = "Thoughts on the Blessed Life of Fellowship with the Son of God"
AUTHOR_SLUG = "andrew-murray"
COVER_COLOR = "#2b5f4a"  # vine green — house-style cover ground
ITEM = "abideinchrist01murr"
SOURCE_URL = f"https://archive.org/details/{ITEM}"
PUBLICATION_YEAR = 1895

DESCRIPTION = (
    "Thirty-one short readings, one for each day of a month, on Christ’s words "
    "in John 15: “Abide in me, and I in you.” Murray writes for believers who "
    "came to Christ gladly and then found the first joy fading, and he argues "
    "that the answer is not more effort but a settled, daily resting in the "
    "Vine: Christ as wisdom, righteousness, strength and keeper, at every "
    "moment and in every trial. Most days close with a prayer."
)

ATTRIBUTION = (
    "Public domain — Henry Altemus’s Philadelphia printing of 1895, from the "
    "Library of Congress copy scanned by the Internet Archive "
    f"({SOURCE_URL})."
)

#: The thirty-one days, from the book's own Contents, title-cased. Day 12 takes
#: "Stablish" from its heading, where the Contents page reads "establish".
TITLES = [
    "All Ye Who Have Come to Him",
    "And Ye Shall Find Rest to Your Souls",
    "Trusting Him to Keep You",
    "As the Branch in the Vine",
    "As You Came to Him, by Faith",
    "God Himself Has United You to Him",
    "As Your Wisdom",
    "As Your Righteousness",
    "As Your Sanctification",
    "As Your Redemption",
    "The Crucified One",
    "God Himself Will Stablish You in Him",
    "Every Moment",
    "Day by Day",
    "At This Moment",
    "Forsaking All for Him",
    "Through the Holy Spirit",
    "In Stillness of Soul",
    "In Affliction and Trial",
    "That You May Bear Much Fruit",
    "So Will You Have Power in Prayer",
    "And in His Love",
    "As Christ in the Father",
    "Obeying His Commandments",
    "That Your Joy May Be Full",
    "And in Love to the Brethren",
    "That You May Not Sin",
    "As Your Strength",
    "And Not in Self",
    "As the Surety of the Covenant",
    "The Glorified One",
]

_UNITS = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH",
          "EIGHTH", "NINTH"]
_TEENS = ["TENTH", "ELEVENTH", "TWELFTH", "THIRTEENTH", "FOURTEENTH",
          "FIFTEENTH", "SIXTEENTH", "SEVENTEENTH", "EIGHTEENTH", "NINETEENTH"]
ORDINALS = (
    _UNITS + _TEENS + ["TWENTIETH"] + [f"TWENTY-{u}" for u in _UNITS]
    + ["THIRTIETH", "THIRTY-FIRST"]
)
#: Letter-for-letter misreads the scanner made in a day heading.
_HEADING_OCR = {"FOUETH": "FOURTH"}
_DAY = re.compile(r"^\s*([A-Z][A-Z\-]+)\s+DAY[.,]?\s*$")
#: The running title the printer sets above each day's title ("ABIDE IN OHEIST",
#: "ABIDE m CHRIST" — the scanner rarely reads it whole).
_RUNNING = re.compile(r"^\s*ABIDE\s+\S+\s+\S+\s*$")
#: The line that ends an epigraph: its closing mark, a dash, then the reference
#: ("souls. '—Matt. xi. 28, 29.", "me. ' — John xv. 5.").
_REFERENCE = re.compile(r"['’*]\s*[—-]+\s*\S")
_REFERENCE_WRAPS = re.compile(r"['’*]\s*[—-]+\s*$")
#: The rest of a reference that wrapped mid-way: short, closing on a full stop,
#: carrying a chapter or verse number ("XV. 7.", "vii. 22.", "11.", "18.").
_REFERENCE_TAIL = re.compile(r"^(?=.{1,24}$)[^']*?(?:\d|\b[ivxlcIVXLC]+\.)[^']*\.\*?$")
#: A line that opens a further epigraph, which some days set two of.
_QUOTE_OPEN = re.compile(r"^\s*['‘*]")
_THE_END = re.compile(r"^\s*THE\s+END\.?\s*$")

#: The text the printer set after the last day, before THE END, in display caps
#: the scanner mangled (">ND -NOW, LITTLE CHILDREN, ABIDE IN HIM, THAI, …").
#: 1 John 2:28, as the page sets it.
CLOSING_VERSE = (
    "And now, little children, abide in him, that, when he shall appear, we "
    "may have confidence, and not be ashamed before him at his coming."
)


#: Days whose prose opens on a drop cap the scanner misread, by day:
#: (the opening as this scan reads it, as printed). The printed reading is the
#: Revell printing's (`abideinchristtho00murr`), the second witness. Several of
#: these days open on a quotation, which is also why the epigraph's end can't
#: be found by its quote mark there: the prose starts at the line that begins
#: with the misreading. Day 6 lost a whole line under its drop cap.
OPENINGS: dict[int, tuple[str, str]] = {
    2: ("ID EST for", "Rest for"),
    3: ("MOEE than", "More than"),
    6: ("'Y^ were still", "‘Ye are in Christ Jesus.’ The believers at Corinth were still"),
    7: ("JESUS OHEIST is", "Jesus Christ is"),
    9: ("' \"pAUL, unto the Church of God which is at Corinth, -L to",
        "‘Paul, unto the Church of God which is at Corinth, to"),
    10: ("HEKE we", "Here we"),
    11: ("' T AM crucified with Christ:' Thus the apostle exJ- presses",
         "‘I am crucified with Christ:’ Thus the apostle expresses"),
    14: ("^Y^HE day^s", "The day’s"),
    18: ("THEEE is", "There is"),
    26: ("^T IKE AS the Father loved me, even so I have -Li loved",
         "‘Like as the Father loved me, even so I have loved"),
    27: ("^\"yE know/ the apostle had said, *that He was manJ- ifested",
         "‘Ye know,’ the apostle had said, ‘that He was manifested"),
    28: ("TIIEEE is", "There is"),
}


#: The footnotes, by day: the opening words of each as this scan reads them.
#: The printer sets them at the foot of a page, so the reflow would run them
#: into the prose; they are lifted out and set after the day's text, with the
#: in-text mark placed by the OCR fixes ("[*]").
FOOTNOTES: dict[int, list[str]] = {
    9: ["* Holiness may be called", "* I have felt so strongly"],
    22: ["* It is diflScult"],
    28: ["* The word power"],
    29: ["* The Highway of Holiness. An"],
}

#: Word and punctuation repairs, by chapter: (as this scan reads, as printed).
#: Settled against the two scans of the Revell printing (`abideinchristtho00murr`,
#: `abideinchristtho00murr_0`): where this scan reads a non-word or OCR junk
#: and both Revell copies agree on the reading, that reading is taken. The
#: rest are misreads the Revell scans share (R read as E or K: "Eemember",
#: "Kighteous") and reference digits, checked against the verse cited.
#: Spelling that differs between the printings ("labor"/"labour") is left as
#: this printing has it. Every pair must apply, so a changed scan fails loud.
OCR_FIXES = pathlib.Path(__file__).parent / "data" / SLUG / "ocr_fixes.json"
NOTE_MARK = "[*]"

#: What the scanner does everywhere, after OCR_FIXES: the vocative O read as a
#: zero ("0 my soul"), and a comma for the full stop in a reference ("Matt, v,
#: 48", "(marg,)").
PATTERNS = [
    (re.compile(r"(?<![\w.,:;–(\-])0(?=\s?[A-Za-z!])"), "O"),
    (re.compile(r"\b(Matt|Mark|Luke|John|Acts|Rom|Cor|COR|Gal|Eph|Phil|Col|Thess|Heb|Jas|Pet|"
                r"Ex|Sam|Ps|Isa|Jer|Ezek|comp|chap|ver|marg),(?=[ )])"), r"\1."),
    (re.compile(r"\b([ivxlc]+), (?=\d)"), r"\1. "),
    # Quotation marks: a space the scanner set inside an opening mark ("‘ Come"),
    # and a doubled close run into the next sentence ("‘Abide,’’As mighty").
    (re.compile(r"‘ (?=\w)"), "‘"),
    (re.compile(r"’’(?=[A-Z])"), "’ "),
]


def _public_domain(meta: dict) -> str:
    year = printing_year(meta)
    if year is None or year > PD_THROUGH_YEAR:
        raise CommandError(f"{ITEM}: printed {year}, not provably public domain.")
    return f"printed {year}, US public domain"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _markers(lines: list[str]) -> list[int]:
    """Line index of each day heading, checked against the ordinal sequence."""
    found: list[int] = []
    for i, line in enumerate(lines):
        m = _DAY.match(line)
        if not m:
            continue
        word = _HEADING_OCR.get(m.group(1), m.group(1))
        if word not in ORDINALS:
            continue  # "DAY BY DAY." — a day's own title, not a heading
        want = ORDINALS[len(found)] if len(found) < len(ORDINALS) else None
        if word != want:
            raise CommandError(f"line {i}: heading {word!r} where {want!r} was expected")
        found.append(i)
    if len(found) != len(TITLES):
        raise CommandError(f"found {len(found)} day headings, expected {len(TITLES)}")
    return found


def _quotes(text: str) -> str:
    """Typographic single quotes for the OCR's straight ones.

    The book quotes with single marks. The scanner also sets a space before a
    closing mark ("me. '") and reads an opening mark as "*" ("* Abide").
    """
    text = re.sub(r"(?<![\w.,;:!?])\*\s*(?=[A-Za-z])", "'", text)
    text = re.sub(r"([.,;:!?])\s+'(?=\s|$|—)", r"\1'", text)
    text = re.sub(r"(^|[\s(—\[{])'", r"\1‘", text)
    return text.replace("'", "’")


#: A line that ends a paragraph when a blank line follows: terminal punctuation,
#: then any closing quote or the scanner's stray "*". The importer's reflow
#: ends a paragraph only on bare punctuation, and this book closes many
#: paragraphs inside a quotation ("‘Abide in me.’").
_PARAGRAPH_END = re.compile(r"[.!?:;]['’\"*]*\s*$")


def _furniture(line: str) -> bool:
    text = line.strip()
    return not text or _is_header(text) or bool(_BARE_NUM.match(text))


def _raw_paragraphs(lines: list[str]) -> list[str]:
    """The importer's reflow, as plain-text paragraphs with the OCR's marks,
    run once per paragraph so one that ends on a quotation stays its own.

    A blank line ends a paragraph when the text before it ends one and the
    text after it does not run on in lowercase — a page can break after a
    comma the scanner read as a full stop ("the Divine life." / "are in")."""
    groups, cur, last = [], [], ""
    for i, line in enumerate(lines):
        if not line.strip() and _PARAGRAPH_END.search(last):
            nxt = next((x.strip() for x in lines[i + 1 :] if not _furniture(x)), "")
            if not nxt[:1].islower():
                groups.append(cur)
                cur, last = [], ""
                continue
        if not _furniture(line):
            cur.append(line)  # the paragraph is decided; the reflow only joins
            last = line
    groups.append(cur)
    return [_html.unescape(p) for g in groups for p in re.findall(r"<p>(.*?)</p>", _reflow(g))]


def _paragraphs(lines: list[str]) -> list[str]:
    return [_quotes(p) for p in _raw_paragraphs(lines)]


def _opening(first: str, order: int) -> str:
    """The prose's first words: the misread drop cap mended, or title-cased
    from the capitalised word the scanner makes of it ("IT is" → "It is")."""
    if order not in OPENINGS:
        return re.sub(r"^([A-Z]{2,})\b", lambda m: m.group(1).capitalize(), first, count=1)
    misread, printed = OPENINGS[order]
    if not first.startswith(misread):
        raise CommandError(f"day {order}: prose opens {first[:70]!r}, not {misread!r}")
    return printed + first[len(misread):]


def _prose_start(lines: list[str]) -> int | None:
    """Index of the first prose line: the line after the last epigraph's reference.

    A reference can wrap: after its dash ("souls. ' —" / "Phil. iii. 8, 9.") or
    inside itself ("— John" / "XV. 7."); either way the next line belongs to it.
    """
    start = None
    in_epigraph = True
    wrapped = False
    for j, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        if wrapped or (start is not None and not in_epigraph and _REFERENCE_TAIL.match(text)):
            start, wrapped = j + 1, False
            continue
        if not in_epigraph:
            if not _QUOTE_OPEN.match(line):
                return start
            in_epigraph = True
        if _REFERENCE_WRAPS.search(line):
            in_epigraph, wrapped = False, True
        elif _REFERENCE.search(line):
            in_epigraph, start = False, j + 1
    return start


def _lift_footnotes(lines: list[str], order: int) -> tuple[list[str], list[list[str]]]:
    """(the day's lines without its footnotes, each footnote's lines)."""
    notes = []
    for opening in FOOTNOTES.get(order, []):
        start = next((i for i, line in enumerate(lines) if _norm(line).startswith(opening)), None)
        if start is None:
            raise CommandError(f"day {order}: footnote {opening!r} not found")
        end = start + 1
        while end < len(lines) and not (_is_header(lines[end].strip()) or _BARE_NUM.match(lines[end].strip())):
            end += 1
        notes.append([re.sub(r"^\s*\*\s*", "", lines[start])] + lines[start + 1 : end])
        lines = lines[:start] + lines[end:]
    return lines, notes


Block = tuple[str, str]  # (kind, text): "p" prose, "i" epigraph/verse in italics, "h3", "note"


def _day(lines: list[str], order: int) -> list[Block]:
    """One day: the epigraph in italics, the prose, then any footnote."""
    lines, notes = _lift_footnotes(lines, order)
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and _RUNNING.match(lines[i]):
        i += 1
    # The title in capitals, up to the epigraph's opening mark. The scanner
    # lowercases a word now and then ("so WILL", "AND m HIS"), so the check
    # that it is this day's title is a close match, not an exact one.
    head = []
    while i < len(lines) and not _QUOTE_OPEN.match(lines[i]):
        if lines[i].strip():
            head.append(lines[i].strip())
        i += 1
    want = _norm(re.sub(r"[^a-z ]", "", TITLES[order - 1].lower()))
    got = _norm(re.sub(r"[^a-z ]", "", " ".join(head).lower()))
    if SequenceMatcher(None, want, got).ratio() < 0.85:
        raise CommandError(f"day {order}: title lines {head!r} do not read {TITLES[order - 1]!r}")
    rest = lines[i:]
    if order in OPENINGS:
        lead = " ".join(OPENINGS[order][0].split()[:2])
        start = next(
            (j for j, line in enumerate(rest)
             if line.strip() and _norm(" ".join(rest[j : j + 6])).startswith(lead)),
            None,
        )
    else:
        start = _prose_start(rest)
    if start is None:
        raise CommandError(f"day {order}: can't find where the prose starts")
    prose = _raw_paragraphs(rest[start:])
    prose[0] = _opening(prose[0], order)
    blocks: list[Block] = [("i", " ".join(_paragraphs(rest[:start])))]
    blocks += [("p", _quotes(p)) for p in prose]
    blocks += [("note", " ".join(_paragraphs(note))) for note in notes]
    return blocks


def _preface(lines: list[str]) -> list[Block]:
    """The Preface, then the John 15:1–12 page set before the first day."""
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("PREFACE"))
    contents = next(i for i, line in enumerate(lines) if line.strip().startswith("CONTENTS"))
    passage = next(i for i, line in enumerate(lines) if _norm(line).startswith("JOHN XV."))
    preface = _paragraphs(lines[start + 1 : contents])
    preface[0] = _opening(preface[0], 0)  # "DURING the life" → "During the life"
    return (
        [("p", p) for p in preface]
        + [("h3", "John xv. 1–12")]
        + [("p", v) for v in _paragraphs(lines[passage + 1 :])]
    )


def _chapters(text: str) -> list[tuple[str, list[Block]]]:
    lines = text.split("\n")
    marks = _markers(lines)
    end = next(
        (i for i in range(marks[-1], len(lines)) if _THE_END.match(lines[i])), len(lines)
    )
    out = [("Preface", _preface(lines[: marks[0]]))]
    for n, start in enumerate(marks):
        stop = marks[n + 1] if n + 1 < len(marks) else end
        block = lines[start + 1 : stop]
        if n + 1 == len(marks):
            # Cut the display-caps closing verse; it is set back cleanly below.
            verse = next(
                (j for j, line in enumerate(block) if "LITTLE" in line and "CHILDREN" in line),
                len(block),
            )
            block = block[: max(verse - 1, 0)]
        blocks = _day(block, n + 1)
        if n + 1 == len(marks):
            blocks.append(("i", CLOSING_VERSE))
        out.append((TITLES[n], blocks))
    return out


def _fixed(chapters: list[tuple[str, list[Block]]]) -> list[tuple[str, list[Block]]]:
    """Apply OCR_FIXES (every pair must change its chapter), then PATTERNS."""
    fixes = json.loads(OCR_FIXES.read_text(encoding="utf-8"))
    out = []
    for order, (title, blocks) in enumerate(chapters, start=1):
        pairs = fixes.get(str(order), [])
        used = [False] * len(pairs)
        mended = []
        for kind, text in blocks:
            for k, (bad, good) in enumerate(pairs):
                if bad in text:
                    text, used[k] = text.replace(bad, good), True
            text = _quotes(text)  # a fix can bring in a straight mark
            for pattern, repl in PATTERNS:
                text = pattern.sub(repl, text)
            mended.append((kind, text))
        unused = [pairs[k][0] for k, u in enumerate(used) if not u]
        if unused:
            raise CommandError(f"ch {order}: OCR fixes that no longer match: {unused[:5]!r}")
        out.append((title, mended))
    return out


def _html_body(blocks: list[Block]) -> str:
    def mark(text: str) -> str:
        return _esc(text).replace(NOTE_MARK, "<sup>*</sup>")
    parts = []
    for kind, text in blocks:
        if kind == "h3":
            parts.append(f"<h3>{_esc(text)}</h3>")
        elif kind == "i":
            parts.append(f"<p><i>{mark(text)}</i></p>")
        elif kind == "note":
            parts.append(f"<p><sup>*</sup> {mark(text)}</p>")
        else:
            parts.append(f"<p>{mark(text)}</p>")
    return "".join(parts)


def _esc(text: str) -> str:
    return _html.escape(text, quote=False)


class Command(BaseCommand):
    help = "Build Andrew Murray's Abide in Christ from an Internet Archive scan (dev DB)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — seed the library first."
            ) from None

        why = _public_domain(metadata(ITEM).get("metadata", {}))
        chapters = _fixed(_chapters(fetch_text(ITEM)))

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": SOURCE_URL,
            "publication_year": PUBLICATION_YEAR,
        }
        book, was_created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": book_sort_order(SLUG),
            },
        )
        book.chapters.all().delete()
        for order, (title, blocks) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(_html_body(blocks)))
            wc = word_count(body)
            if wc < 200:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {TITLE!r} — {book.chapter_count} chapters ({why})"
        ))
