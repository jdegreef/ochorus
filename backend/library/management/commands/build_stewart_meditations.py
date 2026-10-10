"""Build *Meditations from the Pen of Mrs. Maria W. Stewart* (Washington, 1879).

The 1879 volume is Stewart's own late reprint of her Boston writings — the 1831
tract *Religion and the Pure Principles of Morality*, the fourteen Meditations
(1832) with their written prayers, and her four Boston addresses (1832–33) —
together with a new account of her "Sufferings During the War" and a front
section of letters and commendations written by OTHERS (Garrison, Louise C.
Hatton, Alexander Crummell, two Washington pastors and a notary).

Source: the transcription in Mary Mark Ockerbloom's *A Celebration of Women
Writers* (UPenn), which reproduces the 1879 printing with its own errata slip
already applied. That transcription was made over the Internet Archive OCR
(`meditationsfromp00stew`) and kept some of its misreads; every one fixed in
``FIXES`` was settled against the page images of that 1879 scan, cross-read with
an independent second OCR. Printer's slips the transcription keeps as ``sic``
("Wethersfied", "inquities", "plaintiff voices") are left exactly as printed —
and so are the two close-quotes the transcriber ADDED, which are removed here
because the 1879 page does not have them.

Chapters follow the book's order. The Meditations are short, self-contained
devotions (164–1,100 words, most with their prayer), so each is its own
chapter, the way a reader would take one a day; the five short chapters of
"Sufferings During the War" stay together as one memoir, as do the six letters
by others, under a title that says whose they are. The errata page is dropped
(its corrections are in the text) and the title page is the book row.

Fixture-driven like every other book: ``seed_books`` creates it from
``fixtures/content/books/meditations-maria-w-stewart.en.json``. This command
GENERATES that fixture's rows reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_stewart_meditations
"""

from __future__ import annotations

import html
import re

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.catalog import AUTHORS
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.titlecase import recase_title

SLUG = "meditations-maria-w-stewart"
TITLE = "Meditations from the Pen of Mrs. Maria W. Stewart"
SUBTITLE = "Presented in 1832 to the First African Baptist Church and Society of Boston"
AUTHOR_SLUG = "maria-w-stewart"
SOURCE_URL = (
    "https://digital.library.upenn.edu/women/stewart-maria/meditations/meditations.html"
)
SCAN = "meditationsfromp00stew"
PUBLICATION_YEAR = 1879
COVER_COLOR = "#3f4a5c"  # slate blue — house-style cover ground
USER_AGENT = "Mozilla/5.0 (Ochorus book import; +https://ochorus.com)"

DESCRIPTION = (
    "In 1879, near the end of her life, Maria W. Stewart reprinted the writings "
    "Garrison had published for her in Boston: her 1831 call to Religion and "
    "the Pure Principles of Morality, fourteen Meditations, many closing in a "
    "written prayer, and the four addresses she gave in Boston in 1832 and 1833. "
    "To them she added an account of her sufferings and labours during the Civil "
    "War, and letters from Garrison, Alexander Crummell and others who knew her."
)

ATTRIBUTION = (
    "Public domain — Washington: Enterprise Publishing Company, 1879, reprinting "
    "the Boston writings of 1831–1835. Text from the transcription in A "
    "Celebration of Women Writers (ed. Mary Mark Ockerbloom), corrected against "
    f"the 1879 scan (Internet Archive, {SCAN}); the book's own errata applied."
)

# (old, new, expected count) on the raw transcription. Each was checked against
# the 1879 page image. The transcription kept these Internet Archive OCR misreads;
# the 1879 printing reads as `new`.
FIXES: list[tuple[str, str, int]] = [
    ("of coarse promised", "of course promised", 1),
    ('Trini"I:ty', "Trinity", 1),
    ("babes arc tainted", "babes are tainted", 1),
    ("'I'he devil", "The devil", 1),
    ("'I'o hear", "To hear", 1),
    ("roof of my month", "roof of my mouth", 1),
    ("The mighty work of\nof formation", "The mighty work of\nreformation", 1),
    ("Britons, put all", "Britons, but all", 1),
    ("\"'He that knoweth", '"He that knoweth', 1),
    ("Mrs, Stewart", "Mrs. Stewart", 2),
    ("Redeemer's hAnd,", "Redeemer's hand.", 1),
    ("right hAnd, Soon", "right hand. Soon", 1),
    # A double quote keyed as two apostrophes.
    ("''", '"', 11),
    # Close-quotes the transcriber added; the 1879 page has none.
    ('cut down;"<!-- close quotation added -->', "cut down;", 1),
    ('baptized with?"<!-- added close quote -->', "baptized with?", 1),
    # Punctuation: the OCR read the page's semicolons as colons, and so on.
    ("knowledge and\nimprovement.</P>", "knowledge and\nimprovement:</P>", 1),
    ("September, 1878, I called", "September, 1878; I called", 1),
    ("attending school: and", "attending school; and", 1),
    ("dressed: benches", "dressed; benches", 1),
    ("new shawl: went", "new shawl; went", 1),
    ("that thirsteth!", "that thirsteth,", 1),
    ("without price: turn ye", "without price; turn ye", 1),
    ("higher branches: and", "higher branches; and", 1),
    ("become united and let", "become united; and let", 1),
    ('impossible to say. "Thy will', 'impossible to say, "Thy will', 1),
    ("gathered up: but", "gathered up; but", 1),
    ("nature shakes.<BR>", "nature shakes,<BR>", 1),
    ("And now. Lord,", "And now, Lord,", 1),
    ("against the light: you", "against the light; you", 1),
    ("field? from whence", "field; from whence", 1),
    ("Southern slavery: for,", "Southern slavery; for,", 1),
    ("spirit of men: and", "spirit of men; and", 1),
    ("But. ah,", "But, ah,", 1),
    ("sake. Like many\n", "sake. Like many,\n", 1),
    ("beginning to flow, nor", "beginning to flow; nor", 1),
    ("Christian progress: and", "Christian progress; and", 1),
]

# Section markers in the transcription → how the book divides.
_SECTION = re.compile(r'<span class="chapter" id="([^"]+)"></span>')

# The printed caps lines (sub-titles, datelines, headings), set here in the
# book's own words with ordinary capitals.
_DATELINES = {
    "LECTURE": "Delivered at the Franklin Hall, Boston, September 21, 1832.",
    "FEMALE": "Delivered before the Afric-American Female Intelligence Society of Boston.",
    "ADDRESS": "Delivered at the African Masonic Hall, Boston, February 27, 1833.",
    "FAREWELL": "Delivered September 21, 1833.",
}
_TITLES = {
    "preface": "Preface",
    "letters": "Letters and Commendations from Her Friends",
    "I": "Sufferings During the War",
    "RELIGION": "Religion and the Pure Principles of Morality",
    "LECTURE": "Lecture Delivered at Franklin Hall",
    "FEMALE": "Address to the Afric-American Female Intelligence Society",
    "ADDRESS": "Address at the African Masonic Hall",
    "FAREWELL": "Farewell Address to Her Friends in the City of Boston",
}
_ROMAN = [
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "XIII",
    "XIV",
]


def fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    return resp.content.decode("latin-1")


def _apply_fixes(raw: str) -> str:
    for old, new, n in FIXES:
        found = raw.count(old)
        if found != n:
            raise CommandError(
                f"fix {old!r}: expected {n} match(es), found {found} — the source changed."
            )
        raw = raw.replace(old, new)
    return raw


def _smallcaps(m: re.Match) -> str:
    return m.group(1) + m.group(2).lower()


def _normalize(raw: str) -> str:
    """Transcription markup → a narrow block vocabulary (p / h3 / blockquote / hr)."""
    t = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    # Small capitals: a full-size initial then the rest in small type.
    t = re.sub(
        r'<span style="font-size:medium">([A-Z])</span><span style="font-size:small">([A-Z.]+)</span>',
        _smallcaps,
        t,
    )
    # A verse epigraph set in a centred table → a blockquote.
    t = re.sub(
        r'<table class="center"><tr><td class="epigraph">(.*?)</table>',
        lambda m: "<blockquote>" + m.group(1) + "</blockquote>",
        t,
        flags=re.S | re.I,
    )
    t = re.sub(r"</?(span|a)\b[^>]*>", "", t, flags=re.I)
    t = re.sub(r"<(/?)I>", r"<\1em>", t)
    t = re.sub(r"<(HR|IMG)\b[^>]*>", "", t, flags=re.I)  # rules; the "The End" ornament
    t = t.replace("&nbsp;", "")
    return t


def _blocks(fragment: str) -> list[tuple[str, str]]:
    """Ordered (kind, inner-html) blocks: p / h3 / verse / letter."""
    out: list[tuple[str, str]] = []
    pat = re.compile(
        r'<div class="letter">|<H3[^>]*>(?P<h3>.*?)</H3>|<blockquote>(?P<bq>.*?)</blockquote>'
        r"|<P\b(?P<pattrs>[^>]*)>(?P<p>.*?)(?=</P>|<P\b|<blockquote>|<H3|</div>|$)",
        re.S | re.I,
    )
    for m in pat.finditer(fragment):
        if m.group(0).startswith("<div"):
            out.append(("letter", ""))
        elif m.group("h3") is not None:
            out.append(("h3", m.group("h3")))
        elif m.group("bq") is not None:
            out.append(("verse", m.group("bq")))
        else:
            out.append(("p", m.group("p")))
    return out


def _inline(s: str) -> str:
    s = re.sub(r"</?(P|div)\b[^>]*>", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    s = html.unescape(s)
    s = html.escape(s, quote=False)
    s = s.replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")
    return s.replace("&lt;BR&gt;", "<br/>")


def _verse(inner: str) -> str:
    lines = [_inline(x) for x in re.split(r"<BR\s*/?>", inner, flags=re.I)]
    lines = [x for x in lines if x]
    return "<blockquote><p>" + "<br/>".join(lines) + "</p></blockquote>"


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s))).strip()


def _render(blocks: list[tuple[str, str]], heading) -> str:
    """Blocks → body HTML. ``heading(text)`` maps a source <h3> to a kept
    sub-heading (str) or None to drop it."""
    parts: list[str] = []
    seen_letter = False
    for kind, inner in blocks:
        if kind == "letter":
            if seen_letter:
                parts.append("<hr/>")
            seen_letter = True
        elif kind == "h3":
            h = heading(_plain(inner))
            if h:
                parts.append(f"<h3>{h}</h3>")
        elif kind == "verse":
            parts.append(_verse(inner))
        else:
            text = _inline(inner)
            if not text:
                continue
            if text == "BIOGRAPHICAL SKETCH.":
                parts.append("<h3>Biographical Sketch</h3>")
            else:
                parts.append(f"<p>{text}</p>")
    return "".join(parts)


def _sub_heading(text: str) -> str | None:
    """Keep the in-text headings (Prayer, Introduction, Chapter I…) in title case."""
    t = text.rstrip(".").strip()
    m = re.fullmatch(r"CHAPTER ([IVX]+)", t)
    if m:
        return f"Chapter {m.group(1)}"
    if t.upper() in {"PRAYER", "INTRODUCTION"}:
        return t.title()
    return None


def _strip_caps_lead(blocks):
    """Drop the centred caps line that opens a section ("SUFFERINGS DURING THE
    WAR.", a lecture's dateline) — the chapter title or ``_DATELINES`` restates
    it in ordinary capitals."""
    out = list(blocks)
    i = next(k for k, (kind, _) in enumerate(out) if kind == "p")
    text = _plain(out[i][1])
    if text != text.upper():
        raise CommandError(f"expected a caps title line, found {text[:60]!r}")
    out.pop(i)
    return out


def _chapters(raw: str) -> list[tuple[str, str]]:
    main = raw[
        raw.index('<section id="main">') : raw.index(
            "<!-- end of the main text section -->"
        )
    ]
    main = _apply_fixes(main)
    pieces = _SECTION.split(main)
    sections: dict[str, str] = {}
    for sid, frag in zip(pieces[1::2], pieces[2::2], strict=True):
        # "Sufferings During the War" marks each of its five chapters; one memoir.
        key = "I" if sid in {"II", "III", "IV", "V"} else sid
        sections[key] = sections.get(key, "") + frag
    expected = [
        "1",
        "preface",
        "letters",
        "I",
        "RELIGION",
        "MEDITATIONS",
        "LECTURE",
        "FEMALE",
        "ADDRESS",
        "FAREWELL",
    ]
    if list(sections) != expected:
        raise CommandError(
            f"unexpected sections {list(sections)} — the transcription changed."
        )

    out: list[tuple[str, str]] = []
    for sid in expected:
        if sid == "1":  # the errata slip — already applied to the text
            continue
        blocks = _blocks(_normalize(sections[sid]))
        # The Farewell's title and date sit in its heading, which is dropped.
        if sid in {"I", "LECTURE", "FEMALE", "ADDRESS"}:
            blocks = _strip_caps_lead(blocks)
        if sid == "MEDITATIONS":
            out.extend(_meditations(blocks))
            continue
        body = _render(blocks, _sub_heading)
        if sid == "RELIGION":
            body = "<p><em>The Sure Foundation on Which We Must Build.</em></p>" + body
        if sid in _DATELINES:
            body = f"<p><em>{_DATELINES[sid]}</em></p>" + body
        out.append((_TITLES[sid], body))
    return out


def _meditations(blocks) -> list[tuple[str, str]]:
    """The Meditations section → its Introduction + one chapter per Meditation."""
    groups: list[tuple[str, list]] = []
    for kind, inner in blocks:
        if kind == "h3":
            t = _plain(inner).rstrip(".")
            if t.startswith("MEDITATIONS"):
                groups.append(("Introduction to the Meditations", []))
                continue
            m = re.fullmatch(r"MEDITATION ([IVX]+)", t.upper())
            if m:
                groups.append((f"Meditation {m.group(1)}", []))
                continue
        groups[-1][1].append((kind, inner))
    names = [g[0] for g in groups]
    if names != ["Introduction to the Meditations"] + [
        f"Meditation {r}" for r in _ROMAN
    ]:
        raise CommandError(f"unexpected Meditations layout: {names}")
    return [(title, _render(bl, _sub_heading)) for title, bl in groups]


class Command(BaseCommand):
    help = "Build Maria W. Stewart's Meditations (1879) in the dev DB; then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        stub = AUTHORS[AUTHOR_SLUG]
        author, created_author = Author.objects.get_or_create(
            slug=AUTHOR_SLUG,
            defaults={
                "name": stub.name,
                "birth_year": stub.birth_year,
                "death_year": stub.death_year,
                "bio": stub.bio,
            },
        )
        if created_author:
            self.stdout.write(
                f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)"
            )

        chapters = _chapters(fetch(SOURCE_URL))
        if len(chapters) != 23:
            raise CommandError(f"expected 23 chapters, got {len(chapters)}")

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            # The byline already names her; the cover need not say it twice.
            "cover_title": "Meditations",
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "publication_year": PUBLICATION_YEAR,
            "source_url": f"https://archive.org/details/{SCAN}",
            "cover_url": f"/covers/{SLUG}.svg",
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

        for order, (title, body) in enumerate(chapters, start=1):
            title = recase_title(title)
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 150:
                raise CommandError(
                    f"ch {order} ({title!r}): only {wc} words — aborted."
                )
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:58]:58} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters")
        )
