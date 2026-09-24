"""Build Arthur T. Pierson's *George Müller of Bristol* (1899).

Project Gutenberg #26522 is a clean transcription, but its layout defeats
``import_gutenberg`` (which makes THREE chapters of it): every heading sits in
its own wrapper ``<div>`` apart from the prose, the two front-matter pieces are
the only ``<h2>``s (so the heading picker splits on them), chapters I–III set
the chapter number and its title as two separate ``<h3>``s, and Appendix N's
title is likewise split off. So this command walks the body in order and cuts
at the book's own divisions — James Wright's Introduction, Pierson's Prefatory
Word, the 24 chapters and the Appendix (A–H, K–N; the edition has no I or J) —
38 chapters, exactly the printed Contents.

Dropped, as furniture rather than the book: the title page, the transcriber's
note on the umlaut, the Contents, the frontispiece and two plates, the
printer's "PRINTED IN THE UNITED STATES OF AMERICA", and one inline
transcriber's gloss. Kept as ``<h3>`` subheads: the Prefatory Word's heading
and the topic heads of Appendix N ("The Wise Sayings"). The one two-column
table (the paired "Let him follow Me" sayings, ch. XXIV) becomes a blockquote.
The wording is unchanged.

Fixture-driven like every other book: ``seed_books`` creates it (and the
author, from ``authors.json``) on deploy from
``fixtures/content/books/george-muller-of-bristol.en.json``. This command
GENERATES that fixture reproducibly; it is idempotent. The ``catalog.py`` entry
records the source and carries the author stub, but ``import_gutenberg`` skips
this slug (``BUILT_ELSEWHERE``) so a stray run can't re-chapter it into three.

    DJANGO_DEBUG=true uv run python manage.py build_george_muller_of_bristol
"""

from __future__ import annotations

import re

from bs4 import Tag
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.catalog import AUTHORS, BOOKS
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, clean_title, word_count
from library.management.commands.import_gutenberg import content_root, fetch_html
from library.models import Author, Book, Chapter

SLUG = "george-muller-of-bristol"
PUBLICATION_YEAR = 1899

DESCRIPTION = (
    "The authorized memoir of George Müller, written soon after his death by "
    "his friend Arthur T. Pierson and commended, in its introduction, by "
    "Müller's son-in-law and executor, James Wright. Drawing on Müller's own "
    "Narrative and the yearly reports of his work, Pierson follows the "
    "wayward student of Halle to his conversion, his call to Bristol, and the "
    "five great orphan houses on Ashley Down, where over ten thousand orphans "
    "were taken in without appeal to man and in sole dependence on God. He "
    "tells the story less for its chronology than for its lessons in holy "
    "living and serving, with one aim: to extend George Müller's witness to a "
    "prayer-hearing God, and so answer the question, \"Where is the Lord God "
    "of Elijah?\" An appendix gathers the Scriptures that moulded Müller and "
    "a treasury of his wise sayings."
)

ATTRIBUTION = (
    "Public domain — Arthur T. Pierson, George Müller of Bristol, and His "
    "Witness to a Prayer-Hearing God (Fleming H. Revell, 1899), with an "
    "introduction by James Wright; text from Project Gutenberg (ebook 26522). "
    "The wording is unchanged."
)

# The book's own Contents, in order. The heading label each chapter must open
# with is checked against this, so a changed edition fails loudly.
CHAPTERS: list[tuple[str, str]] = [
    ("Introduction", "Introduction by Mr. James Wright"),
    ("A Prefatory Word", "A Prefatory Word"),
    ("CHAPTER I", "From His Birth to His New Birth"),
    ("CHAPTER II", "The New Birth and the New Life"),
    ("CHAPTER III", "Making Ready the Chosen Vessel"),
    ("CHAPTER IV", "New Steps and Stages of Preparation"),
    ("CHAPTER V", "The Pulpit and the Pastorate"),
    # Müller's own book's title; quoted in the source, but stored titles carry no
    # quotation marks (`ingest.clean_title`).
    ("CHAPTER VI", "The Narrative of the Lord's Dealings"),
    ("CHAPTER VII", "Led of God into a New Sphere"),
    ("CHAPTER VIII", "A Tree of God's Own Planting"),
    ("CHAPTER IX", "The Growth of God's Own Plant"),
    ("CHAPTER X", "The Word of God and Prayer"),
    ("CHAPTER XI", "Trials of Faith, and Helpers to Faith"),
    ("CHAPTER XII", "New Lessons in God's School of Prayer"),
    ("CHAPTER XIII", "Following the Pillar of Cloud and Fire"),
    ("CHAPTER XIV", "God's Building: The New Orphan Houses"),
    ("CHAPTER XV", "The Manifold Grace of God"),
    ("CHAPTER XVI", "The Shadow of a Great Sorrow"),
    ("CHAPTER XVII", "The Period of World-Wide Witness"),
    ("CHAPTER XVIII", "Faith and Patience in Serving"),
    ("CHAPTER XIX", "At Evening-Time—Light"),
    ("CHAPTER XX", "The Summary of the Life-Work"),
    ("CHAPTER XXI", "The Church Life and Growth"),
    ("CHAPTER XXII", "A Glance at the Gifts and the Givers"),
    ("CHAPTER XXIII", "God's Witness to the Work"),
    ("CHAPTER XXIV", "Last Looks, Backward and Forward"),
    ("APPENDIX A", "Appendix A: Scripture Texts That Moulded George Müller"),
    ("APPENDIX B", "Appendix B: Apprehension of Truth"),
    ("APPENDIX C", "Appendix C: Separation from the London Society for "
                   "Promoting Christianity Among the Jews"),
    ("APPENDIX D", "Appendix D: The Scriptural Knowledge Institution for Home and Abroad"),
    ("APPENDIX E", "Appendix E: Reasons Which Led Mr. Müller to Establish an Orphan House"),
    ("APPENDIX F", "Appendix F: Arguments in Prayer for the Orphan Work"),
    ("APPENDIX G", "Appendix G: The Purchase of a Site, etc."),
    ("APPENDIX H", "Appendix H: God's Faithfulness in Providing"),
    ("APPENDIX K", "Appendix K: Further Recollections of Mr. Müller"),
    ("APPENDIX L", "Appendix L: Church Fellowship, Baptism, etc."),
    ("APPENDIX M", "Appendix M: Church Conduct"),
    ("APPENDIX N", "Appendix N: The Wise Sayings of George Müller"),
]

# Transcriber's glosses inlined into Pierson's prose — not his words.
SOURCE_DROPS = [" [Transcriber's note: unpaid debts]"]

_FRONT = {"Introduction", "A Prefatory Word"}
_LABEL = re.compile(r"^(CHAPTER [IVXL]+|APPENDIX [A-N])\b")
_HEADS = ["h1", "h2", "h3", "h4"]
_END = "PRINTED IN THE UNITED STATES OF AMERICA"


def _text(el) -> str:
    return " ".join(el.get_text(" ", strip=True).split())


def _heading(el: Tag) -> Tag | None:
    if el.name in _HEADS:
        return el
    return el.find(_HEADS) if el.name == "div" else None


def _sections(html: str) -> list[tuple[str, str]]:
    """(heading label, body html) per division, in the book's order."""
    for drop in SOURCE_DROPS:
        if drop not in html:
            raise CommandError(f"expected source text not found: {drop!r}")
        html = html.replace(drop, "")
    root = content_root(html)
    sections: list[tuple[str, list[str]]] = []
    started = in_toc = title_pending = False
    for el in root.children:
        if not isinstance(el, Tag):
            continue
        h = _heading(el)
        if h is not None:
            text = _text(h)
            if h.name == "h2" and text == "Table of Contents":
                in_toc = True
            elif h.name == "h2" and text in _FRONT:
                in_toc, started = False, True
                sections.append((text, []))
            elif h.name == "h1":
                in_toc = False  # the half-title after the Contents
            elif not started or in_toc:
                continue
            elif h.name == "h3" and (m := _LABEL.match(text)):
                sections.append((m.group(1), []))
                # CHAPTER I–III and APPENDIX N carry their title in the NEXT h3.
                title_pending = text == m.group(1)
            elif h.name == "h3" and title_pending:
                title_pending = False
            elif h.name == "h4":
                # The question the Prefatory Word closes on, set as a heading:
                # it ends the prose ("…an answer to the question:"), so it stays
                # a paragraph rather than becoming a subhead with nothing under it.
                sections[-1][1].append(f"<p>{text}</p>")
            else:
                sections[-1][1].append(f"<h3>{clean_title(text)}</h3>")
            continue
        if not started or in_toc:
            continue
        if el.name == "p":
            sections[-1][1].append(str(el))
        elif el.name == "table":
            cells = "".join(f"<p>{_text(td)}</p>" for td in el.find_all("td"))
            sections[-1][1].append(f"<blockquote>{cells}</blockquote>")
        elif el.name == "div" and not el.find(["img", "a", "br"]) and (text := _text(el)):
            if text == _END:
                break
            sections[-1][1].append(f"<h3>{clean_title(text)}</h3>")
    return [(label, "".join(parts)) for label, parts in sections]


class Command(BaseCommand):
    help = "Build Pierson's George Müller of Bristol (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        entry = next(b for b in BOOKS if b.slug == SLUG)
        sections = _sections(fetch_html(entry.source_ref))
        labels = [label for label, _ in sections]
        expected = [label for label, _ in CHAPTERS]
        if labels != expected:
            raise CommandError(f"divisions changed:\n  found    {labels}\n  expected {expected}")

        a = AUTHORS[entry.author_slug]
        author, created_author = Author.objects.get_or_create(
            slug=a.slug,
            defaults={"name": a.name, "bio": a.bio,
                      "birth_year": a.birth_year, "death_year": a.death_year},
        )
        if created_author:
            self.stdout.write(f"  (created author stub {a.slug!r} — real bio lives in authors.json)")

        content = {
            "author": author,
            "title": entry.title,
            "subtitle": entry.subtitle,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": entry.cover_color,
            "source_url": f"https://www.gutenberg.org/ebooks/{entry.source_ref}",
        }
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": next(i for i, b in enumerate(BOOKS) if b.slug == SLUG),
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, ((_, title), (_, body)) in enumerate(zip(CHAPTERS, sections, strict=True), start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 300:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:50]:50} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {entry.title!r} — {book.chapter_count} chapters, {total} words"
        ))
