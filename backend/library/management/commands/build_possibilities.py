"""Build E. M. Bounds's *The Possibilities of Prayer* (1923) from CCEL.

A clean re-import that REPLACES the earlier Internet Archive OCR edition
(`possibilitiesofp0000boun`). That scan was too degraded to correct piecemeal —
page numbers leaked mid-prose ("IOI To answer prayer"), a running header injected
into a sentence, systematic `.,,`/slash quote garble, and hundreds of
single-letter misreads ("Prayei", "answet", "peopie"). See the english-qa /
book-import skills: like *The Bruised Reed*, the right fix is a fresh source, not
a thousand string pairs.

CCEL hosts the 1923 Fleming H. Revell text (public domain — first published
1923) as a clean human transcription, but only in its LEGACY layout: sixteen
pages `possibility02.htm`…`possibility17.htm`, one chapter each. `import_ccel`,
written for the modern `<work>.toc.html` / `div#theText` scheme, cannot read the
legacy pages — which is exactly why an earlier pass reported the book "on neither
CCEL nor Gutenberg" and fell back to the OCR scan.

Each legacy page is `<h2>{roman}. {title}</h2>`, a `<blockquote>` epigraph
closing "-- AUTHOR", then prose in which paragraph breaks are marked by a `<br>`
plus a five-`&nbsp;` first-line indent (there are no `<p>` tags). Scripture
quotations set each verse as its own five-`&nbsp;` paragraph (kept, as the book
does); hymn stanzas are bracketed by blank `<br>&nbsp;<br>` separators with a
`<br>` per line and a heavier (or zero) indent, and are flattened to one
paragraph per stanza. `_paragraphs` reconstructs the `<p>` structure from those
signals: an exactly-five-`&nbsp;` indent opens a new paragraph, a blank separator
ends one, everything else continues the current one.

The sixteen chapters and their order — including the repeated "(Continued)"
titles — match the shipped fixture exactly, so translation parity is preserved by
construction. Fixture-driven (`seed_books` creates it on deploy, resolving the
existing `e-m-bounds` author from `authors.json`), idempotent, no `catalog.py`
entry — a stray `import_ccel`/`import_archive` would only mangle it.

    DJANGO_DEBUG=true uv run python manage.py build_possibilities
"""

from __future__ import annotations

import html as _html
import re
from time import sleep

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_ccel import fetch
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "possibilities-of-prayer"
TITLE = "The Possibilities of Prayer"
SUBTITLE = "How Far Believing Prayer Can Reach"
AUTHOR_SLUG = "e-m-bounds"
COVER_COLOR = "#324a6d"  # deep prayer-blue — house-style cover ground

#: CCEL legacy work. Chapter N is page N+1 (`possibility01.htm` is the title
#: page, `.._c.htm` the contents); `possibility02.htm` = chapter I.
PAGE_URL = "https://ccel.org/ccel/bounds/possibility/possibility{page:02d}.htm"
SOURCE_URL = "https://ccel.org/ccel/bounds/possibility/possibility.htm"

DESCRIPTION = (
    "Bounds's fullest case for what prayer can actually do. Ranging over the "
    "promises of Scripture, the recorded facts of answered prayer, and the "
    "history of God's dealings with praying men, he argues that prayer is no "
    "pious formality but a real force that moves the hand of God — reaching "
    "into providence, working wonders, and shaping the world. The companion "
    "volume to his other books on prayer, and the one most given to proof by "
    "story and instance."
)

ATTRIBUTION = (
    "Public domain — first published 1923 by Fleming H. Revell. Text from the "
    "Christian Classics Ethereal Library transcription "
    "(ccel.org/ccel/bounds/possibility)."
)

# The sixteen chapters, from the 1923 Contents. Order IS the reading order.
# V/VI and XI/XII repeat "(Continued)" exactly as the book does — a faithful
# duplicate. These match the shipped fixture titles verbatim.
TITLES = [
    "The Ministry of Prayer",
    "Prayer and the Promises",
    "Prayer and the Promises (Continued)",
    "Prayer—Its Possibilities",
    "Prayer—Its Possibilities (Continued)",
    "Prayer—Its Possibilities (Continued)",
    "Prayer—Its Wide Range",
    "Prayer—Facts and History",
    "Prayer—Facts and History (Continued)",
    "Answered Prayer",
    "Answered Prayer (Continued)",
    "Answered Prayer (Continued)",
    "Prayer Miracles",
    "Wonders of God Through Prayer",
    "Prayer and Divine Providence",
    "Prayer and Divine Providence (Continued)",
]

#: The Roman numeral that heads each chapter page, checked against the order so a
#: reshuffled CCEL TOC fails loud rather than mislabelling a chapter. The "."
#: disambiguates the prefixes ("III." never startswith "II.").
_ROMAN = [
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII",
    "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI",
]

_NAV = re.compile(r"(?i)<a\b")        # the bottom nav bar ends the prose region
_BR = re.compile(r"(?i)<br\s*/?>")
_NBSP = re.compile(r"&nbsp;|\xa0")

#: Literal fixes for the CCEL transcription itself (not our reflow). The one
#: below is a misplaced opening quote — the source sets it after "is" instead of
#: before "In", leaving an orphan close-quote (Phil. 4:6, ch. VIII). The only
#: such misplacement in the sixteen chapters.
_SOURCE_FIXES = [
    ('reading there is" In nothing be anxious,"', 'reading there is "In nothing be anxious,"'),
]


def _text(fragment: str) -> str:
    """Visible text of an HTML fragment: tags dropped, entities/&nbsp; resolved."""
    plain = re.sub(r"(?s)<[^>]+>", " ", fragment)
    plain = _html.unescape(plain).replace("\xa0", " ")
    return re.sub(r"\s+", " ", plain).strip()


def _esc(text: str) -> str:
    """HTML-escape body text but keep straight quotes for `convert` to curl."""
    return _html.escape(text, quote=False)


def _normalize(text: str) -> str:
    """Collapse the CCEL spaced ellipsis to a single glyph.

    The transcription sets an elision as spaced dots — ". . ." for an ellipsis,
    ". . . ." for a sentence period followed by one — which read as spacing
    before punctuation. Match the ellipsis the reader (and the shipped edition)
    expect. The four-dot form is handled first so the three-dot rule cannot eat
    part of it.
    """
    text = re.sub(r"\.(?: \.){3}", ". …", text)
    text = re.sub(r"\.(?: \.){2}", "…", text)
    return text


def _lead(seg: str) -> int:
    """Count of leading `&nbsp;` on a `<br>`-delimited segment — its indent."""
    m = re.match(rf"\s*((?:{_NBSP.pattern})*)", seg)
    return len(_NBSP.findall(m.group(1)))


def _paragraphs(prose_html: str) -> list[str]:
    """Reconstruct paragraphs from the legacy `<br>` + `&nbsp;`-indent markup.

    A five-`&nbsp;` indent opens a new paragraph (a prose paragraph, or one
    scripture verse); a blank separator ends the current one; any other line
    (the chapter's first paragraph, or a hymn line at zero or heavy indent)
    continues the current buffer — so a whole hymn stanza flattens to one
    paragraph.
    """
    paras: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            paras.append(buf.strip())
        buf = ""

    for seg in _BR.split(prose_html):
        core = _text(seg)
        if not core:                 # blank separator: stanza / hard break
            flush()
            continue
        if _lead(seg) == 5:          # standard first-line indent: new paragraph
            flush()
            buf = core
        else:                        # first paragraph, or a verse/continuation line
            buf = f"{buf} {core}" if buf else core
    flush()
    return paras


def _epigraph(bq_html: str) -> str:
    """The `<blockquote>` epigraph → an italic quote paragraph + an attribution.

    Every epigraph closes "-- AUTHOR" in caps; the author is title-cased and set
    on its own line, as the shipped edition and the sibling Bounds books do.
    """
    text = _text(bq_html)
    quote, sep, author = text.rpartition(" -- ")
    if not sep:
        quote, sep, author = text.rpartition("--")
    if not sep:
        # No attribution separator: the whole line is the quote, not the author
        # (rpartition returns the string in its third slot when the sep is absent).
        quote, author = text, ""
    quote = _normalize(quote.strip())
    author = author.strip()
    out = f"<p><i>{_esc(quote)}</i></p>"
    if author:
        out += f"<p><i>— {_esc(author.title())}</i></p>"
    return out


def _fix_dropcap(paras: list[str]) -> list[str]:
    """Title-case the small-caps drop-cap opener ("THE ministry" → "The ...")."""
    if paras:
        paras[0] = re.sub(
            r"^([A-Z]{2,})\b", lambda m: m.group(1).capitalize(), paras[0], count=1
        )
    return paras


def _chapter_body(page_html: str) -> str:
    mb = re.search(r"(?is)<blockquote>(.*?)</blockquote>", page_html)
    if not mb:
        raise CommandError("no epigraph blockquote — the CCEL page changed.")
    after = page_html[mb.end():]
    nav = _NAV.search(after)
    prose_html = after[: nav.start()] if nav else after
    paras = _fix_dropcap(_paragraphs(prose_html))
    # Source fixes act on the whitespace-normalised paragraph text, not the raw
    # HTML (whose line wraps would defeat a literal match).
    for i, p in enumerate(paras):
        for bad, good in _SOURCE_FIXES:
            p = p.replace(bad, good)
        paras[i] = _normalize(p)
    body = _epigraph(mb.group(1)) + "".join(f"<p>{_esc(p)}</p>" for p in paras)
    return body


def _chapters() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for order, title in enumerate(TITLES, start=1):
        page = fetch(PAGE_URL.format(page=order + 1))
        mh = re.search(r"(?is)<h2>(.*?)</h2>", page)
        head = _text(mh.group(1)) if mh else ""
        if not head.upper().startswith(_ROMAN[order - 1] + "."):
            raise CommandError(
                f"ch {order}: page heading {head!r} is not {_ROMAN[order - 1]}. — "
                "the CCEL TOC changed."
            )
        out.append((title, _chapter_body(page)))
        sleep(0.5)  # be polite to CCEL
    return out


class Command(BaseCommand):
    help = "Rebuild Bounds's The Possibilities of Prayer from CCEL (dev DB)."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — seed the library first."
            ) from exc

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": SOURCE_URL,
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,  # cover_url deliberately untouched — the designed cover stays
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()

        # The CCEL transcription is uniformly straight-quoted; curl every mark
        # to the corpus's typographic style (English quotes with “ ”, so
        # outer_guillemets=False). `convert_work` is the wrong tool here — it
        # deliberately no-ops on a work that does not MIX styles — so call the
        # per-body converter directly and keep its punctuation-only guard.
        # Baking it into the build keeps the fixture curly and the rebuild
        # idempotent (QuoteStyleTests wants one consistent style).
        bodies = []
        for order, (_, body) in enumerate(chapters, start=1):
            settled = settled_chapter_body(SLUG, order, clean_fragment(body))
            curled, changed = convert(settled, outer_guillemets=False)
            if changed:
                assert_punctuation_only(settled, curled, f"{SLUG}.en[{order}]")
            bodies.append(curled)

        for order, ((title, _), body) in enumerate(
            zip(chapters, bodies, strict=True), start=1
        ):
            wc = word_count(body)
            if wc < 200:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
