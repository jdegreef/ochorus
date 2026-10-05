"""Build George MacDonald's *Unspoken Sermons*, Series I, II and III.

The source is Project Gutenberg #9057, the three series (1867, 1885, 1889) in
one volume. www.gutenberg.org refuses this environment's egress, so the
plain-text file is read from the GITenberg mirror of the same ebook on GitHub —
the route ``build_pensees`` takes. Only the sermons are taken: the Gutenberg
header and licence, the title page, the contents and the three short series
dedications are left out.

One book, thirty-six chapters — one per sermon, in the volume's order, each
titled with the sermon's own title. The series are noted in the description and
attribution rather than in the titles, since every sermon stands on its own.

How the plain text is read:

* each sermon opens with its Scripture text (two for "Light"), which becomes a
  ``<blockquote>``; the italics marking the verse are dropped there, as the
  quotation already sets it apart, and the reference keeps MacDonald's form
  ("St Mark ix. 33-37"), only taken out of capitals;
* ``_underscores_`` are MacDonald's italics, ``--`` his dashes;
* a block indented three or more spaces is verse (Dante, Milton, the old
  ballads) and keeps its line breaks; a block indented less is a prose
  quotation;
* the transcription's ``[Greek: …]`` transliterations are set in italics, and
  its six inline ``[Footnote: …]`` notes (MacDonald's own) are marked * † ‡
  and set at the end of their sermon.

Fixture-driven like every other book: ``seed_books`` creates it (and the author,
from ``authors.json``) on the next deploy from
``fixtures/content/books/unspoken-sermons.en.json``. This command GENERATES that
fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_unspoken_sermons
"""

from __future__ import annotations

import html
import re

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "unspoken-sermons"
TITLE = "Unspoken Sermons"
SUBTITLE = "Series I, II and III"
AUTHOR_SLUG = "george-macdonald"
GUTENBERG_ID = "9057"
SOURCE_TXT = (
    "https://raw.githubusercontent.com/GITenberg/"
    "Unspoken-Sermons-Series-I-II-and-III_9057/master/9057.txt"
)
PUBLICATION_YEAR = 1867
COVER_COLOR = covers.ink_safe("#3f5446")

AUTHOR_STUB = {"name": "George MacDonald", "birth_year": 1824, "death_year": 1905}

DESCRIPTION = (
    "George MacDonald called these sermons “unspoken” because they were never "
    "preached: he had lost his pulpit young, and wrote them instead, gathering "
    "them in three series in 1867, 1885 and 1889. In thirty-six meditations on "
    "the words of Jesus and the apostles he returns again and again to one "
    "conviction — that God is a Father whose love will not rest until his "
    "children are made like his Son. Here are “The Child in the Midst,” “The "
    "Consuming Fire,” “The Way,” “Abba, Father!” and “Self-Denial”: searching, "
    "tender and often startling pages, and the ones from which C. S. Lewis drew "
    "most of his anthology of the writer he called his master."
)

ATTRIBUTION = (
    "Public domain — George MacDonald's Unspoken Sermons, First Series (1867), "
    "Second Series (1885) and Third Series (1889); text from Project Gutenberg "
    "(ebook 9057). Each sermon is one chapter, in the order of the three series; "
    "the series dedications are not included, and MacDonald's six footnotes "
    "follow the sermons they belong to."
)

# The sermons in the volume's order, as the contents names them (title case).
# Series I: 1–12, Series II: 13–24, Series III: 25–36.
SERMONS = [
    "The Child in the Midst",
    "The Consuming Fire",
    "The Higher Faith",
    "It Shall Not Be Forgiven",
    "The New Name",
    "The Heart with the Treasure",
    "The Temptation in the Wilderness",
    "The Eloi",
    "The Hands of the Father",
    "Love Thy Neighbour",
    "Love Thine Enemy",
    "The God of the Living",
    "The Way",
    "The Hardness of the Way",
    "The Cause of Spiritual Stupidity",
    "The Word of Jesus on Prayer",
    "Man's Difficulty Concerning Prayer",
    "The Last Farthing",
    "Abba, Father!",
    "Life",
    "The Fear of God",
    "The Voice of Job",
    "Self-Denial",
    "The Truth in Jesus",
    "The Creation in Christ",
    "The Knowing of the Son",
    "The Mirrors of the Lord",
    "The Truth",
    "Freedom",
    "Kingship",
    "Justice",
    "Light",
    "The Displeasure of Jesus",
    "Righteousness",
    "The Final Unmasking",
    "The Inheritance",
]

# Sermons that open with more than one Scripture text.
EPIGRAPH_BLOCKS = {"Light": 2}

# Transcription slips, each unambiguous and each checked to occur exactly the
# given number of times, so a changed edition fails loudly instead of quietly.
SOURCE_FIXES = [
    # The Greek word is υἱοθεσία (huiothesia); the transcriber's u was read
    # as n or v in five of its eight appearances.
    ("[Greek: _niothesia_]", "[Greek: _uiothesia_]", 1),
    ("[Greek: niothesia]", "[Greek: uiothesia]", 1),
    ("[Greek: viothesia]", "[Greek: uiothesia]", 3),
    ("[Greek:\nviothesia]", "[Greek:\nuiothesia]", 1),
    # "Room for the newly-made to live" — B for R.
    ("Boom for the newly-made", "Room for the newly-made", 1),
    # Job xiv. 13, quoted correctly in the next sermon's text.
    ("O that thou woudest hide", "O that thou wouldest hide", 1),
    # "So long as love is imperfect … That love only which fills the heart".
    ("That lore only\nwhich fills the heart", "That love only\nwhich fills the heart", 1),
    # A stray italic mark: the Scripture (Luke xii. 10) is italicised up to
    # "forgiven him", and the rest is MacDonald's own paraphrase.
    ("it shall not be forgiven_.\n", "it shall not be forgiven.\n", 1),
    # Romans viii. 15, set off by a single hyphen where every other text has two.
    ("Father._'-ROMANS", "Father._'--ROMANS", 1),
    # Luke xviii. 1, the capital I read for the numeral.
    ("ST. LUKE xviii. I.", "ST. LUKE xviii. 1.", 1),
    # Dante, Purgatorio xv. 73: "più" (set "piu" everywhere else) read as "pin".
    ("pin lassu", "piu lassu", 1),
    ("pin vi s' ama", "piu vi s' ama", 1),
]

_START = "UNSPOKEN SERMONS FIRST SERIES"
_END = "END OF THE THIRD SERIES."
# A sermon title: centred (deeply indented) capitals, usually with a stop.
_TITLE_LINE = re.compile(r"^ {10,}([A-Z][A-Z ,'!-]*[A-Z!])\.?$")
# The close of a series: everything after it, to the next title, is the next
# series' half-title and dedication.
_SERIES_END = re.compile(r"^ +END OF ")
_FOOTNOTE = re.compile(r"\s*\[Footnote: ([^\]]+)\]")
_GREEK = re.compile(r"\[Greek: ([^\]]+)\]")
# The dash that sets the reference off from the verse — the LAST double dash,
# followed by the start of a reference ("St", "MARK", "1 John", "II. Cor…").
_REF_SPLIT = re.compile(r"-{2,4}(?=[A-Z0-9])(?!.*-{2})")
# Footnote signs, the printer's order. Not numerals: the deploy's correction
# step strips every lone numbered ``<sup>`` as extraction residue
# (`corrections.strip_footnote_markers`). No sermon has more than three notes.
_SIGNS = ("*", "†", "‡")
_CAPS_WORD = re.compile(r"\b[A-Z]{2,}\b")


def _source_lines() -> list[str]:
    resp = requests.get(SOURCE_TXT, timeout=60)
    resp.raise_for_status()
    text = resp.text.replace("\r\n", "\n")
    for old, new, count in SOURCE_FIXES:
        if text.count(old) != count:
            raise CommandError(f"source fix {old!r}: expected {count}, found {text.count(old)}.")
        text = text.replace(old, new)
    lines = text.split("\n")
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == _START)
        end = next(i for i, ln in enumerate(lines) if ln.strip() == _END and i > start)
    except StopIteration:
        raise CommandError("start/end markers not found — the edition changed.") from None
    return lines[start + 1 : end]


def _blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        if ln.strip():
            current.append(ln.rstrip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _join(lines: list[str]) -> str:
    """Rejoin hard-wrapped lines. A line ending in a dash or hyphen runs on."""
    out = ""
    for ln in (s.strip() for s in lines):
        if out and not out.endswith("-") and not ln.startswith("-"):
            out += " "
        out += ln
    return re.sub(r" {2,}", " ", out)


def _dashes(text: str) -> str:
    return re.sub(r"-{2,}", "—", text)


def _italicize(text: str, where: str) -> str:
    """``_…_`` -> ``<em>…</em>``; every span opens and closes in its block."""
    if text.count("_") % 2:
        raise CommandError(f"{where}: an italic span never closes: {text[:80]!r}")
    return re.sub(r"_([^_]+)_", r"<em>\1</em>", text)


def _recase_ref(ref: str) -> str:
    """'ST MATTHEW xxii. 39.' -> 'St Matthew xxii. 39.' — capitals only."""
    return _CAPS_WORD.sub(lambda m: m.group(0) if m.group(0) in {"II"} else m.group(0).title(), ref)


def _epigraph(block: list[str], notes: list[str], where: str) -> str:
    text = _join(block)
    text = _FOOTNOTE.sub(lambda m: _note(m, notes), text)
    m = _REF_SPLIT.search(text)
    if not m:
        raise CommandError(f"{where}: no Scripture reference in the opening text {text[:80]!r}")
    verse = text[: m.start()]
    ref = _recase_ref(text[m.end() :].replace("_", "").strip())
    verse = _marks(_dashes(html.escape(verse.replace("_", "").strip(), quote=False)))
    return f"<blockquote><p>{verse} — {html.escape(ref, quote=False)}</p></blockquote>"


def _note(m: re.Match, notes: list[str]) -> str:
    """Take a footnote out of the text, leaving a placeholder for its mark."""
    notes.append(m.group(1))
    return f"\x00{len(notes)}\x00"


def _marks(text: str) -> str:
    return re.sub("\x00(\\d+)\x00", lambda m: f"<sup>{_SIGNS[int(m.group(1)) - 1]}</sup>", text)


def _block_html(block: list[str], notes: list[str], where: str) -> str:
    indent = min(len(ln) - len(ln.lstrip()) for ln in block)
    if indent >= 3:
        # Verse: one line per line, its stanza a quotation.
        lines = [_dashes(html.escape(ln.strip(), quote=False)) for ln in block]
        return f"<blockquote><p>{_italicize('<br/>'.join(lines), where)}</p></blockquote>"
    text = _join(block)
    text = _FOOTNOTE.sub(lambda m: _note(m, notes), text)
    text = _GREEK.sub(lambda m: "_" + m.group(1).replace("_", "").strip() + "_", text)
    body = _marks(_italicize(_dashes(html.escape(text, quote=False)), where))
    return f"<blockquote><p>{body}</p></blockquote>" if indent else f"<p>{body}</p>"


def _sermon_html(title: str, lines: list[str]) -> str:
    blocks = _blocks(lines)
    n_epi = EPIGRAPH_BLOCKS.get(title, 1)
    notes: list[str] = []
    parts = [_epigraph(b, notes, title) for b in blocks[:n_epi]]
    parts += [_block_html(b, notes, title) for b in blocks[n_epi:]]
    if notes:
        parts.append("<hr/>")
        for i, note in enumerate(notes, start=1):
            body = _italicize(_dashes(html.escape(_join([note]), quote=False)), f"{title} note {i}")
            parts.append(f"<p><sup>{_SIGNS[i - 1]}</sup> {body}</p>")
    return "".join(parts)


def _chapters() -> list[tuple[str, str]]:
    lines = _source_lines()
    # Series half-titles and dedications are also centred capitals; keep only
    # the sermon titles, which must be exactly the contents, in order.
    wanted = [t.upper() for t in SERMONS]
    keep = [
        (i, m.group(1))
        for i, ln in enumerate(lines)
        if (m := _TITLE_LINE.match(ln)) and m.group(1) in wanted
    ]
    if [t for _, t in keep] != wanted:
        raise CommandError(f"sermon titles differ from the contents: {[t for _, t in keep]}")

    chapters: list[tuple[str, str]] = []
    for k, (start, _) in enumerate(keep):
        stop = keep[k + 1][0] if k + 1 < len(keep) else len(lines)
        body = lines[start + 1 : stop]
        cut = next((n for n, ln in enumerate(body) if _SERIES_END.match(ln)), None)
        if cut is not None:
            body = body[:cut]
        chapters.append((SERMONS[k], _sermon_html(SERMONS[k], body)))

    # Gutenberg's ASCII double quotes -> the corpus's curly ones (apostrophes
    # and MacDonald's single quotation marks stay straight, as across the
    # library). Only the marks may move.
    curled = []
    for n, (title, body) in enumerate(chapters, start=1):
        new, _ = convert(body, outer_guillemets=False)
        assert_punctuation_only(body, new, f"{SLUG}[{n}]")
        curled.append((title, new))
    return curled


class Command(BaseCommand):
    help = "Build MacDonald's Unspoken Sermons in the dev DB; then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://www.gutenberg.org/ebooks/{GUTENBERG_ID}",
        }
        book, created = Book.objects.update_or_create(
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

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 1000:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
