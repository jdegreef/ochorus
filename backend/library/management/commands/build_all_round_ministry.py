"""Build Spurgeon's *An All-Round Ministry* from The Spurgeon Archive.

*An All-Round Ministry: Addresses to Ministers and Students* (Passmore &
Alabaster, 1900) gathers twelve of Spurgeon's Presidential Addresses to the
annual Conference of the Pastors' College, 1872–1890, published after his death
by his own house. There is no Gutenberg or CCEL edition; the one clean full text
is The Spurgeon Archive's transcription of the 1900 book (Midwestern Baptist
Theological Seminary), one page per address, ``misc/aarm01.php`` … ``aarm12.php``.

Why a bespoke command and not ``import_web``: those pages are late-1990s HTML
with the structure carried by IMAGES — every paragraph opens with an
``indent.gif`` spacer, each address's first letter is a drop-cap GIF
(``images/n.gif`` for "NOW"), and verse, section heads and run-in display lines
all share one ``<CENTER>`` tag. ``import_web.extract_page`` would lose the first
letter of every address and flatten the verse. So this command reads the
structure off the images and the context, and holds the handful of transcription
slips it repairs as a literal list below.

Dropped: the publishers' Prefatory Note (front matter — its facts live in the
book's description), and the 1900 editors' footnote in address 12, which only
advertises *The Salt-Cellars* ("2 vols.") that the sentence already names.
Kept: Spurgeon's own signed notes ("—C. H. S.") on addresses 8 and 10, set after
a rule at the close of the address as the source sets them.

Fixture-driven, no ``catalog.py`` entry; ``seed_books`` creates the book on the
next deploy from ``fixtures/content/books/an-all-round-ministry.en.json``. The
author ``charles-h-spurgeon`` already exists. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_all_round_ministry
"""

from __future__ import annotations

import html
import re
import time

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "an-all-round-ministry"
TITLE = "An All-Round Ministry"
SUBTITLE = "Addresses to Ministers and Students"
AUTHOR_SLUG = "charles-h-spurgeon"
PUBLICATION_YEAR = 1900
COVER_COLOR = "#7c4a1e"  # warm saddle brown — house-style cover ground
BASE = "https://archive.spurgeon.org/misc/"
SOURCE_URL = BASE + "aarm.php"

DESCRIPTION = (
    "Twelve of Charles Spurgeon's presidential addresses to the annual "
    "Conference of his Pastors' College, given between 1872 and 1890 to the "
    "hundreds of ministers and students he called his sons in the faith. "
    "Speaking with a freedom he allowed himself nowhere else, Spurgeon presses "
    "on preachers the faith, holiness, prayer, and courage their calling "
    "demands, and stands firm for the old gospel against the drift of his "
    "day. Written for ministers, but a bracing word for every servant of "
    "Christ — teacher, missionary, or believer — who would exercise an "
    "“all-round ministry.”"
)

ATTRIBUTION = (
    "Public domain — C. H. Spurgeon, An All-Round Ministry (London: Passmore & "
    "Alabaster, 1900), from the transcription at The Spurgeon Archive "
    "(archive.spurgeon.org). The publishers' prefatory note is omitted."
)

# The book's own Contents, in order: (page number, chapter title).
CHAPTERS = [
    ("01", "Faith"),
    ("02", "“Forward!”"),
    ("03", "Individuality, and Its Opposite"),
    ("04", "How to Meet the Evils of the Age"),
    ("05", "“A New Departure”"),
    ("06", "Light. Fire. Faith. Life. Love."),
    ("07", "Strength in Weakness"),
    ("08", "What We Would Be"),
    ("09", "Stewards"),
    ("10", "The Evils of the Present Time, and Our Object, Necessities, and Encouragements"),
    ("11", "The Preacher's Power, and the Conditions of Obtaining It"),
    ("12", "The Minister in These Times"),
]

# Transcription slips, repaired against the sense of the sentence, as literal
# (chapter order, wrong, right) — each must match exactly once or the build
# fails, so a source change can't silently skip one.
FIXES: list[tuple[int, str, str]] = [
    # A quotation mark set on the wrong side of its space.
    (1, 'we are" looking for', 'we are "looking for'),
    (2, 'I do say," If', 'I do say, "If'),
    (4, 'all to say," Let us', 'all to say, "Let us'),
    (5, 'said to him," You may', 'said to him, "You may'),
    (6, 'will say," I have done', 'will say, "I have done'),
    (6, 'the Greeks," You Greeks', 'the Greeks, "You Greeks'),
    (5, 'old gospel," I can see', 'old gospel, "I can see'),
    (7, 'and said," I have been', 'and said, "I have been'),
    (11, 'He says," The Word', 'He says, "The Word'),
    (4, 'the word "brother" or" sister"', 'the word "brother" or "sister"'),
    (9, 'but to" occupy" till', 'but to "occupy" till'),
    (4, "that 'fact '—muddy", "that 'fact'—muddy"),
    (8, '"Follow me in all thing? And', '"Follow me in all things"? And'),
    # A stray full stop mid-sentence (a speck read as a point).
    (1, "came the. gladiators", "came the gladiators"),
    (2, "deep; but. if", "deep; but if"),
    (4, "The. mischief is in the Catechism and. the service", "The mischief is in the Catechism and the service"),
    (4, "and. those who like not", "and those who like not"),
    (4, "against a wall. and the other", "against a wall and the other"),
    (4, "wears away the. scabbard", "wears away the scabbard"),
    (5, "whole being will. deteriorate", "whole being will deteriorate"),
    (5, "he. has discoursed", "he has discoursed"),
    (6, "during a. very hot summer", "during a very hot summer"),
    (7, "strong behold. the weakness", "strong behold the weakness"),
    (7, "believed in. perfect men", "believed in perfect men"),
    (8, "yet I must. say this", "yet I must say this"),
    (10, "keep them all. from wandering", "keep them all from wandering"),
    (11, "My sons and. daughters", "My sons and daughters"),  # 2 Corinthians 6:18
    # Doubled or stray points.
    (6, "is complete:. I know", "is complete. I know"),
    (7, "of Paul,.yet in", "of Paul, yet in"),
    (7, "in our bones:, and we cannot", "in our bones, and we cannot"),  # Jeremiah 20:9
    (7, "again and again:, although", "again and again, although"),
    (8, "he gladly spend,:, and is spent", "he gladly spends, and is spent"),  # 2 Corinthians 12:15
    (9, "faithfulness,, we must", "faithfulness, we must"),
    (11, "the end of ourselves here.. If", "the end of ourselves here. If"),
    (11, "put up with it:; but", "put up with it; but"),
    (10, 'abiding city here"!.', 'abiding city here"!'),
    (4, "amusements which.moralists", "amusements which moralists"),
    (7, "a lowly spirit, whom; in.due time", "a lowly spirit, whom, in due time"),
    (8, "Some men present.an open", "Some men present an open"),
    (10, "fixed points,of faith", "fixed points of faith"),
    (1, "do not: feel alarmed", "do not feel alarmed"),
    (1, "traverse its, shades", "traverse its shades"),
    (1, "we defy the 'world's sneer", "we defy the world's sneer"),
    (7, "covers the: Armada", "covers the Armada"),
    # Misread or mistyped letters.
    (2, "I leave my joys, 1 leave my sins", "I leave my joys, I leave my sins"),
    (3, "eternal and onmipotent arm", "eternal and omnipotent arm"),
    (4, "true religion is no expemnent", "true religion is no experiment"),
    (7, "How self-con-tent he is", "How self-content he is"),
    (11, "RECEIVING OUR MESAGES", "RECEIVING OUR MESSAGES"),
    (11, "DELIVERING THE MESAGES ITSELF", "DELIVERING THE MESSAGE ITSELF"),
    # A compound's hyphen lost at a line end.
    (6, "whole burntofferings", "whole burnt-offerings"),
    (10, "a hightoned morality", "a high-toned morality"),
]


def _fetch(url: str) -> str:
    resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 (ochorus-import/1.0)"})
    resp.raise_for_status()
    return resp.text


_SMALL_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to"}


def _title_case(text: str) -> str:
    words = text.strip().rstrip(".").lower().split()
    out = []
    for i, w in enumerate(words):
        if i and w in _SMALL_WORDS:
            out.append(w)
        else:
            out.append("-".join(p[:1].upper() + p[1:] for p in w.split("-")))
    return " ".join(out)


def _lines(fragment: str) -> list[str]:
    return [ln.strip() for ln in re.split(r"<BR>", fragment, flags=re.I) if ln.strip()]


def _center_block(inner: str, title: str) -> str:
    """Render one ``<CENTER>`` block by what it is.

    Verse (it has line breaks, or opens with a quotation mark) → a blockquote,
    stanzas split on ``<P>``. The address's own title, displayed mid-sentence
    ("…if one line could contain it, it would be— HOW TO MEET THE EVILS OF THE
    AGE.") → a blockquote line, as set. Any other line is a section head →
    ``<h3>``, title-cased: those also complete a run-in sentence ("My subject
    is— THE EVILS OF THE PRESENT TIME."), but they divide the address, and
    address 8 sets SOUL-WINNERS, TEACHERS, FATHERS as one run of heads.
    """
    text = inner.strip()
    if re.search(r"<BR>", text, re.I) or text.startswith('"'):
        stanzas = [s for s in re.split(r"<P>", text, flags=re.I) if s.strip()]
        return "<blockquote>" + "".join(f"<p>{'<br/>'.join(_lines(s))}</p>" for s in stanzas) + "</blockquote>"
    if _words(text) == _words(title):
        return f"<blockquote><p>{text}</p></blockquote>"
    return f"<h3>{_title_case(text)}</h3>"


def _words(text: str) -> str:
    return " ".join(re.findall(r"[a-z]+", text.lower()))


def _chapter_body(page: str, title: str, keep_note: bool) -> str:
    start = page.find('<IMG SRC="images/bar2.gif">')
    end = page.find("<hr/>", start)  # the site footer's rule (lower-case)
    if start < 0 or end < 0:
        raise CommandError("page layout changed — no title bar / footer rule found")
    c = page[start:end]
    c = c[c.index("</CENTER>") + len("</CENTER>"):]  # past the title block

    # Spurgeon's own end-note, after an upper-case <HR>.
    note = ""
    if "<HR>" in c:
        c, tail = c.split("<HR>", 1)
        m = re.search(r"<FONT[^>]*>(.*?)</FONT>", tail, re.S | re.I)
        if not m:
            raise CommandError("note rule with no note text")
        note = re.sub(r"\s+", " ", m.group(1)).strip()
    c = re.sub(r'<A href="/misc/aarm\d+\.php#note">\*</A>', "", c)

    # Drop-cap GIF → its letter; paragraph-indent spacers → nothing.
    c, n = re.subn(r'<IMG SRC="images/([a-z])\.gif" ALIGN=LEFT>', lambda m: m.group(1).upper(), c)
    if n != 1:
        raise CommandError(f"expected one drop-cap, found {n}")
    c = re.sub(r'<IMG SRC="images/indent\.gif"[^>]*>', "", c)
    if re.search(r"<IMG", c, re.I):
        raise CommandError("an unhandled image survives in the body")

    # Each <CENTER> block → a placeholder paragraph, rendered by context.
    blocks: list[str] = []

    def take(m: re.Match) -> str:
        blocks.append(_center_block(m.group(1), title))
        return f"<P>\x00{len(blocks) - 1}\x00<P>"

    c = re.sub(r"<CENTER>(.*?)</CENTER>", take, c, flags=re.S | re.I)

    parts: list[str] = []
    for seg in re.split(r"<BR>|<P>", c, flags=re.I):
        seg = re.sub(r"\s+", " ", seg).strip()
        if not seg:
            continue
        m = re.fullmatch(r"\x00(\d+)\x00", seg)
        parts.append(blocks[int(m.group(1))] if m else f"<p>{seg}</p>")
    if note and keep_note:
        parts.append(f"<hr/><p>Note.—{note}</p>")
    body = "".join(parts).replace("&nbsp;", " ").replace("&#160;", " ")
    return html.unescape(body).replace("\xa0", " ").replace("&", "&amp;")


class Command(BaseCommand):
    help = "Build Spurgeon's An All-Round Ministry from The Spurgeon Archive (dev DB); then serialize the fixture."

    @transaction.atomic  # a mid-run abort rolls back, never a partial book
    def handle(self, *args, **opts):
        author, created = Author.objects.get_or_create(
            slug=AUTHOR_SLUG,
            defaults={"name": "Charles H. Spurgeon", "birth_year": 1834, "death_year": 1892},
        )
        if created:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        bodies: list[tuple[str, str]] = []
        for num, title in CHAPTERS:
            try:
                page = _fetch(f"{BASE}aarm{num}.php")
            except requests.RequestException as exc:
                raise CommandError(f"fetch failed for address {num}: {exc}") from None
            bodies.append((title, _chapter_body(page, title, keep_note=num != "12")))
            time.sleep(0.5)

        # A closing quotation mark set off by a space before its question mark
        # or colon ("in order to be saved "?") — six times — would curl as an
        # OPENER. Close the space up.
        bodies = [(t, re.sub(r'(\w) "([?!:;,.])', r'\1"\2', b)) for t, b in bodies]

        for order, wrong, right in FIXES:
            title, body = bodies[order - 1]
            if body.count(wrong) != 1:
                raise CommandError(f"fix {wrong!r} matches {body.count(wrong)}× in ch {order}, expected 1")
            bodies[order - 1] = (title, body.replace(wrong, right))

        content = {
            "author": author, "title": TITLE, "subtitle": SUBTITLE,
            "description": DESCRIPTION, "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR, "source_url": SOURCE_URL,
        }
        book, was_created = Book.objects.update_or_create(
            slug=SLUG, language="en", defaults=content,
            create_defaults={**content, "source_type": Book.SourceType.PUBLIC_DOMAIN,
                             "is_published": True, "sort_order": book_sort_order(SLUG)},
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(bodies, start=1):
            body = clean_fragment(body)
            # The transcription is straight-quoted; curl to the corpus's
            # typographic style so QuoteStyleTests sees one consistent style.
            curled, changed = convert(body, outer_guillemets=False)
            if changed:
                assert_punctuation_only(body, curled, f"{SLUG}.en[{order}]")
            body = settled_chapter_body(SLUG, order, curled)
            chapter = Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            if chapter.word_count < 2000:
                raise CommandError(f"ch {order} ({title!r}): only {chapter.word_count} words — aborted.")
            total += chapter.word_count
            self.stdout.write(f"  ch {order:2}: {title[:60]:60} {chapter.word_count:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
