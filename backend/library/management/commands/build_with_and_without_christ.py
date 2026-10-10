"""Build Sadhu Sundar Singh's *With and Without Christ* (1929).

"Incidents taken from the lives of Christians and of non-Christians which
illustrate the difference in lives lived with Christ and without Christ": six
chapters of short, headed narratives gathered on the Sadhu's travels, closing
with his own story before and after his conversion. Written in Urdu at Sabathu
in 1928 and translated with the help of the Rev. T. E. Riddle of Kharar, with
an Introduction by the Lord Bishop of Winchester. Public domain — first
published 1929 by Harper & Brothers, New York and London.

SOURCE. No transcription exists, so this is the OCR of a 1929 copy on the
Internet Archive (`gtu_32400001757206`), read from its hOCR so that paragraphs
follow the print's own first-line indents across page breaks
(`library.archive_hocr`):

* **Page furniture out.** A running head (the book's title on the verso, the
  chapter's short title on the recto, each with its folio) tops every page; a
  chapter's opening page carries its folio at the foot instead.
* **Chapters split at their markers** ("Chapter One" … "Chapter Six"); the
  capitals heading under each is dropped and the titles come from the Contents.
  Inside a chapter each incident is headed in capitals ("AN AMERICAN
  PROFESSOR"); those become `<h3>` in title case. The hymn closing the
  Introduction is set as verse by its fix.
* **OCR repairs from `data/with-and-without-christ/ocr_fixes.json`**: literal
  `(find, replace)` pairs per chapter, found by aligning this scan with other
  1929 copies (`withwithoutchris00sing_0`, `withwithoutchris00sing`,
  `withwithoutchris0000sund`) — a reading the other witnesses agree on beats
  the one that differs — and then by proofreading.

Fixture-driven like every other book: `seed_books` creates it on deploy from
`fixtures/content/books/with-and-without-christ.en.json`, resolving the
existing `sadhu-sundar-singh` author. No `catalog.py` entry. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_with_and_without_christ
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from html import escape
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.archive_hocr import (
    Line,
    caps_core,
    fetch_hocr,
    hyphenated_forms,
    is_folio,
    join_lines,
    margins,
    parse,
)
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.titlecase import recase_title

SLUG = "with-and-without-christ"
AUTHOR_SLUG = "sadhu-sundar-singh"
TITLE = "With and Without Christ"
SUBTITLE = (
    "Incidents Taken from the Lives of Christians and of Non-Christians"
)
PUBLICATION_YEAR = 1929
COVER_COLOR = "#2f5a4a"
ARCHIVE_ID = "gtu_32400001757206"
ATTRIBUTION = (
    "Public domain — first published 1929 by Harper & Brothers, New York and "
    "London; translated from the Urdu with the help of the Rev. T. E. Riddle, "
    "with an introduction by the Lord Bishop of Winchester. Text from the "
    "Internet Archive scan of a 1929 copy, checked against three other 1929 "
    "copies."
)
DESCRIPTION = (
    "“My aim in writing this book has been to show, by simple narrative, the "
    "Living Presence of Christ and His saving power in the lives of men.” "
    "Sadhu Sundar Singh sets side by side true stories gathered on his travels "
    "— pundits and sannyasis, professors and business men, Christians in name "
    "and Christians in deed — of lives lived without Christ and lives lived "
    "with Him, and closes with his own: the Sikh boy who burned a Gospel, and "
    "the vision of Christ that changed everything. With an introduction by the "
    "Bishop of Winchester."
)

#: The Contents, in order (the six chapters after the Preface and the
#: Introduction).
CHAPTER_TITLES = [
    "Non-Christians without Christ",
    "Non-Christians with Christ",
    "Christians without Christ",
    "Christians with Christ",
    "My Experience with and without Christ",
    "The Inner Life",
]
_ORDINALS = ["ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX"]
#: The running heads: the book's title (verso) and each chapter's short title
#: (recto), plus the front matter's.
_HEADS = [
    "WITH AND WITHOUT CHRIST", "PREFACE", "INTRODUCTION",
    "NON CHRISTIANS WITHOUT CHRIST", "NON CHRISTIANS WITH CHRIST",
    "CHRISTIANS WITHOUT CHRIST", "CHRISTIANS WITH CHRIST", "MY EXPERIENCE",
    "THE INNER LIFE",
]
#: The book's last words; the publisher's colophon follows.
_LAST_WORDS = "like our Father in Heaven."

_DATA = Path(__file__).resolve().parent / "data" / SLUG
#: A page's top and foot, in the scan's pixel rows (pages are ~2500 tall).
_TOP, _FOOT = 550, 1950
_SPACED_STOP = re.compile(r"(?<=[\w”’)]) +([;:!?])")
_FIRST_WORD = re.compile(r"^([A-Za-z]+)(?: ([A-Za-z]+))?")


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def _is_head(text: str) -> bool:
    """A running head, its folio (and an OCR'd folio like "I49") set aside."""
    words = text.split()
    if words and len(words[-1]) <= 3:
        words = words[:-1]
    if words and re.fullmatch(r"[\dIVXLivxl]{1,4}\S?", words[0]):
        words = words[1:]
    core = caps_core(" ".join(words))
    return bool(core) and max(_similar(core, h) for h in _HEADS) >= 0.75


def _is_noise(text: str) -> bool:
    """A speck the scanner read as a line ("—~", "/")."""
    return not re.search(r"[A-Za-z]{2}", text)


def _is_caps(text: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", text)
    return len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) > 0.9


def body_lines(lines: list[Line]) -> list[Line]:
    pages: dict[int, list[Line]] = {}
    for ln in lines:
        pages.setdefault(ln.page, []).append(ln)
    kept: list[Line] = []
    for _, page in sorted(pages.items()):
        # A running head is set in upper and lower case; a heading in capitals
        # at the top of a page opens the Preface or the Introduction.
        while page and page[0].y0 < _TOP and not _is_caps(page[0].text) and (
            _is_head(page[0].text) or is_folio(page[0].text) or _is_noise(page[0].text)
        ):
            page = page[1:]
        while page and page[-1].y0 > _FOOT and (is_folio(page[-1].text) or _is_noise(page[-1].text)):
            page = page[:-1]
        kept.extend(page)
    return kept


def split_book(lines: list[Line]) -> list[tuple[str, list[Line]]]:
    kept = body_lines(lines)

    def find(pred, start: int = 0, what: str = "") -> int:
        for i in range(start, len(kept)):
            if pred(kept[i].text):
                return i
        raise CommandError(f"no line {what} after line {start}")

    # The headings themselves are in capitals; the Contents lists them in
    # upper and lower case.
    pre = find(lambda t: t.strip() == "PREFACE", what="PREFACE")
    intro = find(lambda t: t.strip() == "INTRODUCTION", pre, "INTRODUCTION")
    marks = []
    for word in _ORDINALS:
        marks.append(find(lambda t, w=word: caps_core(t) == f"CHAPTER {w}",
                          marks[-1] if marks else intro, f"Chapter {word}"))
    end = find(lambda t: t.endswith(_LAST_WORDS), marks[-1], repr(_LAST_WORDS))
    # The Introduction's byline, and the book's half-title before chapter one.
    intro_body = [ln for ln in kept[intro + 1:marks[0]]
                  if not _is_caps(ln.text) and "BISHOP" not in ln.text.upper()]
    parts = [("Preface", kept[pre + 1:intro]), ("Introduction", intro_body)]
    for n, start in enumerate(marks):
        stop = marks[n + 1] if n + 1 < len(marks) else end + 1
        k = start + 1
        while k < stop and _is_caps(kept[k].text):
            k += 1
        head = " ".join(ln.text for ln in kept[start + 1:k])
        title = CHAPTER_TITLES[n]
        if _similar(caps_core(head), caps_core(title)) < 0.85:
            raise CommandError(f"ch {n + 1}: heading {head!r} does not read {title!r}")
        parts.append((title, kept[k:stop]))
    return parts


def _small_caps(para: str) -> str:
    """A chapter opens on a word in small capitals ("THOUGH Christians")."""
    m = _FIRST_WORD.match(para)
    if not m:
        return para
    first, second = m.group(1), m.group(2)
    words = first[0].upper() + first[1:].lower()
    if len(first) == 1 and second:
        words += " " + second.lower()
    elif second:
        words += " " + second
    return words + para[m.end():]


def _typeset(para: str) -> str:
    """The scan's spacing, not the author's text."""
    para = _SPACED_STOP.sub(r"\1", para)
    para = re.sub(r"([“‘]) +(?=\w)", r"\1", para)
    para = re.sub(r"(?<=[\w.,;:!?]) +([”’])(?!\w)", r"\1", para)
    return escape(para, quote=False)


def _head(text: str) -> str:
    words = " ".join(w[:1] + w[1:].lower() for w in text.split())
    return recase_title(words)


def _sections(body: list[Line], headed: bool) -> list[str | list[Line]]:
    """The body as runs of lines, broken by its capitals incident headings."""
    out: list[str | list[Line]] = [[]]
    for ln in body:
        if headed and _is_caps(ln.text):
            out += [ln.text, []]
        else:
            out[-1].append(ln)
    return out


def build_chapters(lines: list[Line]) -> list[tuple[str, str]]:
    margin = margins(lines)
    keep = hyphenated_forms(lines)
    out = []
    for n, (title, body) in enumerate(split_book(lines)):
        chapter = n >= 2  # not the Preface or the Introduction
        blocks: list[str] = []
        for part in _sections(body, chapter):
            if isinstance(part, str):
                blocks.append(f"<h3>{escape(_head(part), quote=False)}</h3>")
                continue
            paras = join_lines(part, margin, keep)
            if paras and chapter and not blocks:
                paras[0] = _small_caps(paras[0])
            blocks += [f"<p>{_typeset(p)}</p>" for p in paras]
        out.append((title, "".join(blocks)))
    return out


def _fixes() -> dict[str, list[list[str]]]:
    path = _DATA / "ocr_fixes.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def apply_fixes(order: int, html: str, fixes: dict[str, list[list[str]]]) -> str:
    """The data file's repairs for one chapter, each matching exactly once."""
    for find, replace in fixes.get(str(order), []):
        if html.count(find) != 1:
            raise CommandError(
                f"ch {order}: OCR fix {find!r} matches {html.count(find)} times, not once"
            )
        html = html.replace(find, replace)
    return html


class Command(BaseCommand):
    help = "Build Sadhu Sundar Singh's With and Without Christ from the 1929 scan."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — loaddata authors.json first."
            ) from None

        chapters = build_chapters(parse(fetch_hocr(ARCHIVE_ID)))
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

        fixes = _fixes()
        unknown = set(fixes) - {str(n) for n in range(1, len(chapters) + 1)}
        if unknown:
            raise CommandError(f"ocr_fixes.json names chapters that do not exist: {sorted(unknown)}")
        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            body = settled_chapter_body(SLUG, order, apply_fixes(order, body, fixes))
            wc = word_count(body)
            if wc < 150:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:58]:58} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"
        ))
