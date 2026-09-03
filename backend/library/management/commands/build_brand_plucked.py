"""Build *A Brand Plucked from the Fire* — Julia A. J. Foote's 1879 memoir.

Internet Archive OCR (`brandpluckedfrom00footrich`, printed 1879, public domain)
is a clean scan, but two things defeat the generic `import_archive`: the
decorative chapter-title lines OCR into garbage ("Tu", "Public ||fllot|f"), and
two chapter markers are mis-scanned romans ("CHAPTER XL" for XI, "CHAPTER XXL"
for XXI) — the second reads as 40 and breaks the marker sequence, merging a
chapter. Her thirty chapters are cleanly marked, though, and her Contents page
lists every real title, so this command splits on the markers in document order
and applies those titles. The reflow reuses `import_archive`, extended to drop a
bare running header and rejoin OCR word-splits ("let ters" → "letters").

Fixture-driven: `seed_books` creates it (and the author, from `authors.json`) on
the next deploy. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_brand_plucked
"""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_archive import (
    _BARE_NUM,
    _HYPHEN_EOL,
    _HYPHEN_SPACE,
    _NON_LETTER,
    _WS,
    _is_header,
    fetch_text,
)
from library.models import Author, Book, Chapter

SLUG = "a-brand-plucked-from-the-fire"
TITLE = "A Brand Plucked from the Fire"
SUBTITLE = "An Autobiographical Sketch"
AUTHOR_SLUG = "julia-foote"
ARCHIVE_ID = "brandpluckedfrom00footrich"
COVER_COLOR = "#8c3a1b"  # ember red-brown — house-style cover ground

AUTHOR_STUB = {"name": "Julia A. J. Foote", "birth_year": 1823, "death_year": 1900}

DESCRIPTION = (
    "The memoir of a holiness evangelist who would not be silenced. Born to "
    "formerly enslaved parents, Julia Foote was converted at fifteen, sanctified "
    "soon after, and called to preach when almost no church would let a woman "
    "into the pulpit. Excommunicated for preaching and undaunted, she travelled "
    "for decades and became the first woman ordained a deacon in the A.M.E. Zion "
    "Church. Her sketch is a plain, fervent account of grace, opposition, and "
    "the full salvation she preached to the end."
)

ATTRIBUTION = (
    "Public domain — first published 1879. Text from the Internet Archive scan "
    "brandpluckedfrom00footrich; chapter titles are taken from the book's own "
    "Contents (the scan's decorative title lines are illegible)."
)

# Her thirty chapters, from the 1879 Contents page. Order IS the reading order.
TITLES = [
    "Birth and Parentage",
    "Learning the Alphabet",
    "The Primes — Going to School",
    "My Teacher Hung for Crime",
    "An Undeserved Whipping",
    "First and Last Dancing",
    "My Conversion",
    "A Desire for Knowledge — Inward Foes",
    "Various Hopes Blasted",
    "Disobedience, but Happy Results",
    "A Religion as Old as the Bible",
    "My Marriage",
    "Boston — The Work of Full Salvation",
    "Early Fruit Gathered Home",
    "New and Unpleasant Revelations",
    "A Long-Lost Brother Found",
    "A Call to Preach the Gospel",
    "Heavenly Visitations Again",
    "Public Effort — Excommunication",
    "Women in the Gospel",
    "The Lord's Leading — Philadelphia",
    "A Visit to My Parents — Further Labors",
    "Color Indignities — General Conference",
    "Death of My Husband and Father",
    "Work in Various Places",
    'A "Threshing" Sermon',
    "My Cleveland Home — Later Labors",
    "A Word to My Christian Sisters",
    "Love not the World",
    "How to Obtain Sanctification",
]

#: A bare chapter marker on its own line: "CHAPTER XVII." — the body markers,
#: not the Contents entries (which carry the title and page number after the
#: numeral). Tolerates the OCR's mangled romans (XL for XI, XXL for XXI) by
#: accepting any roman-ish letter run, since we split on document order, not the
#: parsed number.
_MARKER = re.compile(r"^CHAPTER\s+[IVXLC]+\.?\s*$", re.I)


# The scan drops the hyphen from words broken across a line, leaving a space
# inside the word ("fright ened", "chil dren"). Each pair below rejoins one such
# word; all were found by the same rule (the second fragment is never itself a
# word, and the two joined ARE a word), so none can merge a real word pair.
_SPLITS = {
    "fright ened": "frightened", "them selves": "themselves", "chil dren": "children",
    "oppo sition": "opposition", "sal vation": "salvation", "col ored": "colored",
    "sis ter": "sister", "con stantly": "constantly", "won der": "wonder",
    "admo nition": "admonition", "com pany": "company", "emo tional": "emotional",
    "execu tion": "execution", "recog nize": "recognize", "dis pleased": "displeased",
    "impa tience": "impatience", "earn estly": "earnestly", "simplic ity": "simplicity",
    "invol untarily": "involuntarily", "anx iety": "anxiety", "cere mony": "ceremony",
    "sec ond": "second", "man ner": "manner", "consump tive": "consumptive",
    "trem blingly": "tremblingly", "enlight ened": "enlightened", "in fer": "infer",
    "anx ious": "anxious", "dis appointed": "disappointed", "nei ther": "neither",
    "supplica tion": "supplication", "imag ine": "imagine", "inter rupted": "interrupted",
    "vil lage": "village", "peo ple": "people", "dif ferent": "different",
    "tempta tion": "temptation", "con siderable": "considerable", "mon ster": "monster",
    "salva tion": "salvation", "physi cian": "physician", "tend ency": "tendency",
    "con tinue": "continue", "ful fillment": "fulfillment", "exe cuted": "executed",
    "instanta neous": "instantaneous", "delu sion": "delusion", "holi ness": "holiness",
    "leav ing": "leaving", "lodg ing": "lodging", "noth ing": "nothing",
    "num ber": "number", "prais ing": "praising", "requi site": "requisite",
    "sev eral": "several",
}

_SPLIT_RE = re.compile(
    r"\b(" + "|".join(k.replace(" ", r"\s+") for k in _SPLITS) + r")\b"
)


def _rejoin_splits(html: str) -> str:
    html = _SPLIT_RE.sub(lambda m: _SPLITS[_WS.sub(" ", m.group(0))], html)
    # The reverse slip: the scan hyphenated a COMPLETE word at a line end
    # ("ability to-\novercome"), so the reflow's end-of-line-hyphen join glued
    # "to" to the next word. Split the one case it produced.
    html = html.replace("ability toovercome", "ability to overcome")
    # A handful of badly-mangled words the audit's word checks don't catch (a
    # letter read as two, or an escaped stray mark), each resolved from context.
    for bad, good in _MANGLED.items():
        html = html.replace(bad, good)
    # "per son" → "person", but word-anchored: a bare replace would fuse
    # "harper songs" (no word boundary before "per" inside "harper").
    html = re.sub(r"\bper son\b", "person", html)
    return html


_MANGLED = {
    "quarterly ir.ee ting": "quarterly meeting",
    "as they go lf any one": "as they go. If any one",
    "and a nne speaker": "and a fine speaker",
    "told rne to go": "told me to go",
    "gave rne their reasons": "gave me their reasons",
    "became rny": "became my",
    "trav eling": "traveling",
    "uninterrupted pea<;e": "uninterrupted peace",
    "Tor six months": "For six months",
    "visited me one clay,": "visited me one day,",
    "a long, weari some journey": "a long, wearisome journey",
    "1849, 1 bade my mother": "1849, I bade my mother",
    "Ip any man love the world": "If any man love the world",
}


def _is_allcaps(line: str) -> bool:
    letters = _NON_LETTER.sub("", line)
    if len(letters) < 3:
        return False
    return sum(c.isupper() for c in letters) / len(letters) >= 0.75


def _furniture(line: str) -> bool:
    if not line:
        return True
    if not re.search(r"[A-Za-z0-9]", line):
        return True
    return bool(_BARE_NUM.match(line)) or _is_header(line) or _is_allcaps(line)


def _reflow(lines: list[str]) -> str:
    """`import_archive._reflow`, dropping bare ALL-CAPS running headers too."""
    paras: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        text = _HYPHEN_SPACE.sub(r"\1-\2", _WS.sub(" ", buf).strip())
        if text:
            paras.append(text)
        buf = ""

    for raw in lines:
        line = raw.strip()
        if _furniture(line):
            if buf.rstrip().endswith((".", "!", "?", "”", '"', ":", ";")):
                flush()
            continue
        if buf and _HYPHEN_EOL.search(buf.rstrip()):
            buf = _HYPHEN_EOL.sub(r"\1", buf.rstrip()) + line
        else:
            buf = f"{buf} {line}" if buf else line
    flush()
    return "".join(f"<p>{p}</p>" for p in paras)


def _marker_lines(lines: list[str]) -> list[int]:
    """Indices of the thirty body chapter markers, in document order.

    The Contents also lists "Chapter I — …", but those are mixed-case and carry
    a title, so the anchored all-caps pattern skips them; the first bare marker is
    the body's Chapter I.
    """
    return [i for i, ln in enumerate(lines) if _MARKER.match(ln.strip())]


def _first_two_letters_upper(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 2 and letters[0].isupper() and letters[1].isupper()


def _body_start(block: list[str]) -> int:
    """Skip the marker's garbled decorative title-line(s).

    Every chapter opens in small caps ("FROM this time…", "I WAS born…"), so the
    first line whose first two letters are both uppercase is the prose; the
    illegible title lines above it ("public ||fllot|f —") start lowercase and are
    dropped. Bounded so a chapter that opens differently isn't over-trimmed.
    """
    for j, line in enumerate(block[:6]):
        if _first_two_letters_upper(line.strip()):
            return j
    return 0


def _chapters() -> list[tuple[str, str]]:
    lines = fetch_text(ARCHIVE_ID).split("\n")
    marks = _marker_lines(lines)
    if len(marks) != len(TITLES):
        raise CommandError(
            f"found {len(marks)} chapter markers, expected {len(TITLES)} — the scan changed."
        )
    out: list[tuple[str, str]] = []
    for n, start in enumerate(marks):
        end = marks[n + 1] if n + 1 < len(marks) else len(lines)
        block = lines[start + 1 : end]
        body = _reflow(block[_body_start(block) :])
        out.append((TITLES[n], body))
    return out


class Command(BaseCommand):
    help = "Build Julia Foote's A Brand Plucked from the Fire (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{ARCHIVE_ID}",
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
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

        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(_rejoin_splits(body)))
            wc = word_count(body)
            if wc < 200:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
