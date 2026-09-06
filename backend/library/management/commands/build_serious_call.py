"""Build William Law's *A Serious Call to a Devout and Holy Life* from CCEL.

CCEL's `law/serious_call` is Law's own 1728 text (public domain) as 24 chapters
(`serious_call.ii`–`serious_call.xxv`, "Chapter I." … "Chapter XXIV."), but the
TOC also carries three editorial **Appendices** (introductions from the Methuen
and Everyman editions, and a note on the electronic edition) plus indexes and
acknowledgements — none of them Law. A plain `import_ccel` keeps the appendices
(they are neither Contents/Title/Index that `is_front_matter` drops, nor a part
divider). So this command imports only the 24 leaves whose title begins
"Chapter" — Law's book, and nothing else.

Fixture-driven, no `catalog.py` entry; `seed_books` creates the book (and the
author, from `authors.json`) on the next deploy. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_serious_call
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import (
    clean_fragment,
    clean_html,
    clean_title,
    drop_furniture,
    normalize_words,
    restates_title,
    word_count,
)
from library.management.commands.import_ccel import (
    _is_ordinal_heading,
    fetch,
    soup,
    toc_sections,
)
from library.models import Author, Book, Chapter

SLUG = "a-serious-call"
TITLE = "A Serious Call to a Devout and Holy Life"
SUBTITLE = "Adapted to the State and Condition of All Orders of Christians"
AUTHOR_SLUG = "william-law"
SOURCE_REF = "law/serious_call"
COVER_COLOR = "#2e5d52"  # deep green — house-style cover ground

AUTHOR_STUB = {"name": "William Law", "birth_year": 1686, "death_year": 1761}

DESCRIPTION = (
    "William Law's 1728 masterpiece, one of the most influential devotional books "
    "in the English language — it turned the hearts of John Wesley, George "
    "Whitefield, and Samuel Johnson. Law's question is disarmingly simple: if we "
    "call ourselves Christians, why do we not live as though we believe it? With "
    "wit, unforgettable character sketches, and relentless warmth, he calls every "
    "reader — of every rank and calling — to a whole life devoted to God, ordered "
    "by prayer at the appointed hours and by the pursuit of humility, intercession, "
    "and resignation to the will of God."
)

ATTRIBUTION = (
    "Public domain — William Law's own text (1728), from the Christian Classics "
    "Ethereal Library. The later editors' appendices, indexes and acknowledgements "
    "are omitted."
)


# Every chapter page opens with a front-block the generic `extract_body` can't
# clear: the book title split across TWO <h2>s ("A SERIOUS CALL TO" / "A DEVOUT
# AND HOLY LIFE"), an <h3>CHAPTER N</h3>, and the chapter title restated as a
# <p> (not a heading) — plus blank spacers. Strip leading blocks that are a
# fragment of the book title, the chapter number, or the restated title, up to
# the first real prose block.
_BOOK_WORDS = normalize_words(TITLE)


def _is_frontblock(el, title: str) -> bool:
    text = el.get_text(" ", strip=True)
    if not text:
        return True
    if _is_ordinal_heading(text) or restates_title(text, title):
        return True
    n = normalize_words(text)
    return bool(n) and (n in _BOOK_WORDS or _BOOK_WORDS in n)


def _chapter_body(url: str, title: str) -> str:
    s = soup(fetch(url))
    node = s.select_one("#theText") or s.select_one("[class*=contentSection]") or s.body
    if node is None:
        raise CommandError(f"{url}: no content node")
    content = node.select_one("[class*=book-content]") or node
    drop_furniture(content)
    for el in list(content.find_all(["h1", "h2", "h3", "h4", "h5", "p"], recursive=True)):
        if _is_frontblock(el, title):
            el.decompose()
        else:
            break
    # Self-check: if CCEL ever re-flows these pages so the front-block strip
    # above misses (a reworded restated title, a new wrapper), the body would
    # open with the chapter title or "Chapter N" instead of Law's prose. Fail
    # the build loudly rather than ship a chapter that repeats its own heading.
    lead = normalize_words(content.get_text(" ", strip=True)[:200])
    tnorm = normalize_words(title)
    if lead.startswith("chapter ") or (tnorm and lead.startswith(tnorm[:60])):
        raise CommandError(f"front-block leaked into the body of {title!r} — check _chapter_body")
    return clean_html(node)


def _chapters() -> list[tuple[str, str]]:
    leaves = toc_sections(SOURCE_REF)
    if not leaves:
        raise CommandError(f"no sections found in the CCEL TOC for {SOURCE_REF}")
    out: list[tuple[str, str]] = []
    for url, raw_title in leaves:
        # Law's 24 chapters all read "Chapter I." … "Chapter XXIV."; the Title
        # Page, the three editorial Appendices, the indexes and the
        # acknowledgements do not — so this one test keeps his book and nothing
        # else.
        if not raw_title.strip().startswith("Chapter "):
            continue
        title = clean_title(raw_title)
        body = _chapter_body(url, title)
        if body:
            out.append((title, body))
    return out


class Command(BaseCommand):
    help = "Build William Law's A Serious Call from CCEL (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()
        if len(chapters) != 24:
            raise CommandError(f"expected 24 chapters, got {len(chapters)} — check the TOC filter")

        content = {
            "author": author, "title": TITLE, "subtitle": SUBTITLE,
            "description": DESCRIPTION, "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR, "source_url": "https://ccel.org/ccel/law/serious_call",
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
            if wc < 500:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:50]:50} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
