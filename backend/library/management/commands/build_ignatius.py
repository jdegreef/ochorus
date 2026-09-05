"""Build *The Epistles of Ignatius and His Life's Story* from CCEL + hand-written life chapters.

Ignatius's seven genuine letters survive in a **shorter (genuine)** and a
**longer (interpolated)** recension. CCEL's Ante-Nicene Fathers volume prints
BOTH on the same leaf pages, one after the other, with no way to separate them by
stem — so a plain ``import_ccel`` of ``schaff/anf01`` would double every chapter.
Instead this book takes **J. B. Lightfoot's** translation of the genuine seven
(``lightfoot/fathers`` on CCEL — single recension, one clean page per epistle,
public domain; Lightfoot d. 1889), each epistle imported as ONE chapter.

Ahead of the letters sit FIVE hand-written "life story" chapters (``life-N.html``,
composed under a strict no-invention brief from a sourced dossier), so the reader
meets the man before the mail. The book is fixture-driven and has no
``catalog.py`` entry (a stray ``import_ccel`` could not reproduce it); ``seed_books``
creates it (and the author, from ``authors.json``) on the next deploy. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_ignatius
"""

from __future__ import annotations

import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import DROP_SELECTORS, clean_fragment, clean_html, word_count
from library.management.commands.import_ccel import fetch, soup
from library.models import Author, Book, Chapter

SLUG = "epistles-of-ignatius"
TITLE = "The Epistles of Ignatius and His Life's Story"
SUBTITLE = "Seven Letters from the Road to Martyrdom"
AUTHOR_SLUG = "ignatius-of-antioch"
COVER_COLOR = "#5a3a63"  # deep episcopal violet — house-style cover ground

AUTHOR_STUB = {"name": "Ignatius of Antioch", "birth_year": 35, "death_year": 108}

# The genuine seven, in the order Ignatius wrote them (four from Smyrna, three
# from Troas), as single Lightfoot pages under lightfoot/fathers.
EPISTLES = [
    ("The Epistle to the Ephesians", "fathers.ii.iii"),
    ("The Epistle to the Magnesians", "fathers.ii.iv"),
    ("The Epistle to the Trallians", "fathers.ii.v"),
    ("The Epistle to the Romans", "fathers.ii.vi"),
    ("The Epistle to the Philadelphians", "fathers.ii.vii"),
    ("The Epistle to the Smyrnaeans", "fathers.ii.viii"),
    ("The Epistle to Polycarp", "fathers.ii.ix"),
]

# Filled from the life-chapter writer's report.
LIFE = [
    (1, "Antioch and the God-Bearer"),
    (2, "Condemned to the Beasts"),
    (3, "The Road to Rome, and the Ten Leopards"),
    (4, "The Heart of His Letters"),
    (5, "The Wheat of God"),
]
LIFE_DIR = Path("/tmp/ignatius")

DESCRIPTION = (
    "The seven letters of Ignatius of Antioch — written around AD 108 as he was "
    "carried under armed guard across Asia Minor to be thrown to the wild beasts "
    "at Rome — are the earliest Christian letters we have after the New Testament. "
    "In them a bishop on his way to death pleads for the unity of the church, "
    "defends the reality of Christ's flesh against those who denied it, calls the "
    "Lord's Supper “the medicine of immortality,” and longs to be “the wheat of "
    "God.” Five short chapters tell his life and set the stage; then the letters "
    "themselves, in J. B. Lightfoot's translation."
)

ATTRIBUTION = (
    "The epistles are public domain, in the translation of J. B. Lightfoot "
    "(*The Apostolic Fathers*), from the Christian Classics Ethereal Library — the "
    "genuine seven letters (the shorter recension), not the later interpolated or "
    "spurious versions. The five life chapters are an original Ochorus composition."
)

# Lightfoot's epistle pages mark each section with a heading like "IgnRom. 1" /
# "IgnRom. Prologue" and open with the ALL-CAPS running title; a letter reads as
# one continuous chapter, so these markers are dropped (the paragraph breaks keep
# the structure).
_SECTION_HEAD = re.compile(r"^Ign\w+\.\s*(?:Prologue|\d+)\s*$")


def _epistle_body(stem: str) -> str:
    s = soup(fetch(f"https://ccel.org/ccel/lightfoot/{stem}.html"))
    node = s.select_one("#theText") or s.select_one("[class*=contentSection]") or s.body
    if node is None:
        raise CommandError(f"{stem}: no content node")
    content = node.select_one("[class*=book-content]") or node
    for selector in DROP_SELECTORS:
        for furniture in content.select(selector):
            furniture.decompose()
    for h in content.find_all(["h1", "h2", "h3", "h4"]):
        t = h.get_text(" ", strip=True)
        if _SECTION_HEAD.match(t) or "EPISTLE OF IGNATIUS" in t.upper() or t.lower() == "contents":
            h.decompose()
    return clean_html(node)


def _life_body(n: int) -> str:
    path = LIFE_DIR / f"life-{n}.html"
    if not path.exists():
        raise CommandError(f"missing life chapter file: {path}")
    return path.read_text().strip()


def _chapters() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for n, title in LIFE:
        out.append((title, _life_body(n)))
    for title, stem in EPISTLES:
        out.append((title, _epistle_body(stem)))
    return out


class Command(BaseCommand):
    help = "Build The Epistles of Ignatius (dev DB) from CCEL Lightfoot + life chapters; then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()
        if len(chapters) != 12:
            raise CommandError(f"expected 12 chapters (5 life + 7 epistles), got {len(chapters)}")

        content = {
            "author": author, "title": TITLE, "subtitle": SUBTITLE,
            "description": DESCRIPTION, "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR, "source_url": "https://ccel.org/ccel/lightfoot/fathers",
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
            slug=SLUG, language="en", defaults=content,
            create_defaults={**content, "source_type": Book.SourceType.PUBLIC_DOMAIN,
                             "is_published": True, "sort_order": next_order},
        )
        book.chapters.all().delete()

        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 300:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
