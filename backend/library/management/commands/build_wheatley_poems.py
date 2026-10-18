"""Build Phillis Wheatley's *Poems on Various Subjects, Religious and Moral* (1773).

Project Gutenberg #409 is a clean transcription, but every poem is a ``<pre>``
block: hard line breaks, verse paragraphs marked only by indentation, and the
author's footnotes set inside the verse as ``*``-led blocks. ``import_gutenberg``
would flatten that into prose and drop the short poems under its tiny-section
filter, so this command renders each poem itself:

- one chapter per poem, in the order of the 1773 printing, after a "Preface"
  chapter holding the publisher's preface, John Wheatley's letter and the
  Boston attestation ("To the Public") that prefaced the first edition;
- a blank line or a deeper indent starts a new verse paragraph (``<p>`` with
  ``<br/>`` between lines); a line the transcription wrapped is rejoined;
- a block opening with ``*``/``+`` is the author's note and is set in italics
  where it falls — Niobe's note marking where "another hand" takes over the
  verse is part of the record;
- stanza numerals (``I.``, ``II.`` …) stay, each as its own short paragraph.

The dedication page to the Countess of Huntingdon and the closing "FINIS" are
not carried. The wording is unchanged apart from two transcription slips in
the attestation's signatures (see ``_FIXES``).

Fixture-driven like every other book: ``seed_books`` creates it from
``fixtures/content/books/poems-on-various-subjects.en.json``. This command
GENERATES that fixture's rows reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_wheatley_poems
"""

from __future__ import annotations

import html
import re

from bs4 import Tag
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_gutenberg import content_root, fetch_html
from library.models import Author, Book, Chapter

SLUG = "poems-on-various-subjects"
TITLE = "Poems on Various Subjects, Religious and Moral"
AUTHOR_SLUG = "phillis-wheatley"
GUTENBERG_ID = "409"
COVER_COLOR = covers.ink_safe("#2f5d50")

AUTHOR_STUB = {"name": "Phillis Wheatley", "birth_year": 1753, "death_year": 1784}

DESCRIPTION = (
    "The first book of poems by an African American woman, printed in "
    "London in 1773 when its author was about twenty and still enslaved in "
    "Boston. Phillis Wheatley writes elegies for friends and ministers — "
    "George Whitefield among them — hymns to the morning and evening, a verse "
    "retelling of David and Goliath, meditations on providence, recollection "
    "and imagination, and the eight lines of “On Being Brought from Africa to "
    "America.” The first edition’s preface, her master’s letter and the "
    "attestation signed by eighteen Boston men, who vouched that she had "
    "written the poems herself, open the book."
)

ATTRIBUTION = (
    "Public domain — Phillis Wheatley's Poems on Various Subjects, Religious "
    "and Moral (London, 1773); text from Project Gutenberg (ebook 409). One "
    "poem per chapter in the order of the first edition; the dedication page "
    "is omitted and the wording is unchanged."
)

#: (chapter title, the poem's source heading with spacing removed, lead-in
#: line carried from a heading too long to be a title). The second field is a
#: check, not a lookup: it must match the heading at that position, so a
#: re-flowed source fails the build instead of shifting every title by one.
POEMS: list[tuple[str, str, str]] = [
    ("To Maecenas", "TOMAECENAS", ""),
    ("On Virtue", "ONVIRTUE", ""),
    ("To the University of Cambridge, in New-England", "TOTHEUNIVERSITYOFCAMBRIDGE", ""),
    ("To the King’s Most Excellent Majesty, 1768", "TOTHEKING", ""),
    ("On Being Brought from Africa to America", "ONBEINGBROUGHTFROMAFRICA", ""),
    ("On the Death of the Rev. Dr. Sewell, 1769", "ONTHEDEATHOFTHEREVDRSEWELL", ""),
    ("On the Death of the Rev. Mr. George Whitefield, 1770", "ONTHEDEATHOFTHEREVMRGEORGEWHITEFIELD", ""),
    ("On the Death of a Young Lady of Five Years of Age", "ONTHEDEATHOFAYOUNGLADY", ""),
    ("On the Death of a Young Gentleman", "ONTHEDEATHOFAYOUNGGENTLEMAN", ""),
    ("To a Lady on the Death of Her Husband", "TOALADYONTHEDEATHOFHERHUSBAND", ""),
    ("Goliath of Gath", "GOLIATHOFGATH", ""),
    ("Thoughts on the Works of Providence", "THOUGHTSONTHEWORKSOFPROVIDENCE", ""),
    ("To a Lady on the Death of Three Relations", "TOALADYONTHEDEATHOFTHREERELATIONS", ""),
    ("To a Clergyman on the Death of His Lady", "TOACLERGYMAN", ""),
    ("An Hymn to the Morning", "ANHYMNTOTHEMORNING", ""),
    ("An Hymn to the Evening", "ANHYMNTOTHEEVENING", ""),
    ("Isaiah lxiii. 1–8", "ISAIAH", ""),
    ("On Recollection", "ONRECOLLECTION", ""),
    ("On Imagination", "ONIMAGINATION", ""),
    ("A Funeral Poem on the Death of C. E., an Infant of Twelve Months", "AFUNERALPOEM", ""),
    ("To Captain H———d, of the 65th Regiment", "TOCAPTAIN", ""),
    ("To the Right Honourable William, Earl of Dartmouth", "TOTHERIGHTHONOURABLEWILLIAM", ""),
    ("Ode to Neptune", "ODETONEPTUNE", ""),
    (
        "To a Lady on Her Coming to North-America with Her Son, for the Recovery of Her Health",
        "TOALADYONHERCOMING",
        "",
    ),
    (
        "To a Lady on Her Remarkable Preservation in an Hurricane in North-Carolina",
        "TOALADYONHERREMARKABLE",
        "",
    ),
    ("To a Lady and Her Children, on the Death of Her Son and Their Brother", "TOALADYANDHERCHILDREN", ""),
    (
        "To a Gentleman and Lady on the Death of the Lady’s Brother and Sister",
        "TOAGENTLEMANANDLADY",
        "And a child of the name of Avis, aged one year.",
    ),
    ("On the Death of Dr. Samuel Marshall, 1771", "ONTHEDEATHOFDRSAMUELMARSHALL", ""),
    (
        "To a Gentleman on His Voyage to Great-Britain for the Recovery of His Health",
        "TOAGENTLEMANONHISVOYAGE",
        "",
    ),
    (
        "To the Rev. Dr. Thomas Amory, on Reading His Sermons on Daily Devotion",
        "TOTHEREVDRTHOMASAMORY",
        "In which that duty is recommended and assisted.",
    ),
    ("On the Death of J. C., an Infant", "ONTHEDEATHOFJC", ""),
    ("An Hymn to Humanity", "ANHYMNTOHUMANITY", "To S. P. G. Esq."),
    ("To the Honourable T. H., Esq., on the Death of His Daughter", "TOTHEHONOURABLETH", ""),
    (
        "Niobe in Distress for Her Children Slain by Apollo",
        "NIOBEINDISTRESS",
        "From Ovid’s Metamorphoses, Book VI. and from a view of the painting of Mr. Richard Wilson.",
    ),
    ("To S. M., a Young African Painter, on Seeing His Works", "TOSMAYOUNGAFRICANPAINTER", ""),
    (
        "To His Honour the Lieutenant-Governor, on the Death of His Lady",
        "TOHISHONOURTHELIEUTENANTGOVERNOR",
        "March 24, 1773.",
    ),
    ("A Farewel to America", "AFAREWELTOAMERICA", "To Mrs. S. W."),
    ("A Rebus, by I. B.", "AREBUSBYIB", ""),
    ("An Answer to the Rebus", "ANANSWERTOTHEREBUS", "By the author of these poems."),
]

#: Transcription slips, checked against the 1773 printing's list of signatories.
_FIXES = [
    ("Mr. John Wheat ey, her Master", "Mr. John Wheatley, her Master"),
    ("The Rev. Mr. Saumel Mather", "The Rev. Mr. Samuel Mather"),
]

_NUMERAL = re.compile(r"^[IVXL]+\.$")
_NOTE = re.compile(r"^[*+]")


def _key(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper().replace("Æ", "AE"))


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _render_verse(text: str, stanzaic: bool) -> list[str]:
    """One ``<pre>`` poem → ``<p>`` blocks (verse paragraphs, numerals, notes)."""
    out: list[str] = []
    for block in re.split(r"\n\s*\n", text.strip("\n")):
        lines = [ln.rstrip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        first = lines[0].strip()
        if _NOTE.match(first):
            out.append(f"<p><i>{_esc(' '.join(ln.strip() for ln in lines))}</i></p>")
            continue
        if len(lines) == 1 and _NUMERAL.match(first):
            out.append(f"<p>{first}</p>")
            continue
        paras: list[list[str]] = [[]]
        for raw in lines:
            line = raw.strip()
            prev = paras[-1][-1] if paras[-1] else ""
            # A transcription wrap: the previous line ran on without
            # punctuation and this one opens in lower case (“stood.).
            if prev and not re.search(r"[.,;:!?’”—)-]$", prev) and re.match(r"^[“‘]?[a-z]", line):
                paras[-1][-1] = f"{prev} {line.lstrip('“‘')}"
                continue
            # A deeper indent opens a verse paragraph in couplet poems; in
            # stanzaic ones the indent only staggers the short lines.
            if not stanzaic and paras[-1] and 3 <= _indent(raw) <= 5:
                paras.append([])
            paras[-1].append(line)
        out.extend("<p>" + "<br/>".join(_esc(ln) for ln in p) + "</p>" for p in paras if p)
    return out


def _poem_body(pres: list, lead: str) -> str:
    texts = [t for t in (p.get_text() for p in pres) if t.strip() and _key(t) != "FINIS"]
    stanzaic = any(_NUMERAL.match(ln.strip()) for t in texts for ln in t.split("\n"))
    parts = [f"<p><i>{_esc(lead)}</i></p>"] if lead else []
    for t in texts:
        parts.extend(_render_verse(t, stanzaic))
    return "".join(parts)


def _section(h) -> list:
    """The siblings after heading ``h`` up to the next h1/h2 or the PG footer."""
    nodes = []
    for sib in h.next_siblings:
        if not isinstance(sib, Tag):
            continue
        if sib.name in ("h1", "h2", "footer"):
            break
        nodes.append(sib)
    return nodes


def _prose(nodes) -> list[str]:
    return [
        f"<p>{' '.join(n.decode_contents().split())}</p>"
        for n in nodes
        if n.name == "p" and n.get_text(strip=True)
    ]


def _preface(order: list) -> str:
    def head(key):
        h = next((h for k, h in order if k == key), None)
        if h is None:
            raise CommandError(f"{key!r} heading not found — the edition changed.")
        return h

    pref = _section(head("PREFACE"))
    parts = _prose(pref)
    sig = next(n for n in pref if n.name == "h3")
    # John Wheatley's signature sits between the letter and its date line.
    date = parts.pop()
    parts += [f"<p>{_esc(sig.get_text(' ', strip=True).title())}</p>", date]

    public = _section(head("TOTHEPUBLIC"))
    parts.append("<h3>To the Public</h3>")
    parts += _prose(public)
    pre = next(n for n in public if n.name == "pre").get_text()
    # The signatures are printed in two columns (laymen | clergy); read them
    # column by column, not across the rows.
    names, right, notes = [], [], []
    for block in re.split(r"\n\s*\n", pre.strip("\n")):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip() and not set(ln.strip()) <= {"_"}]
        if not lines:
            continue
        if lines[0].startswith(("N. B.", "*")):
            notes.append(" ".join(lines))
            continue
        for ln in lines:
            left, _, other = ln.partition("|")
            names.append(left.strip())
            if other.strip():
                right.append(other.strip())
    parts.append("<p>" + "<br/>".join(_esc(n) for n in names + right) + "</p>")
    parts += [f"<p><i>{_esc(re.sub(r' +', ' ', n))}</i></p>" for n in notes]
    out = "".join(parts)
    for old, new in _FIXES:
        if out.count(old) != 1:
            raise CommandError(f"fix {old!r} matched {out.count(old)} times, not once — the edition changed.")
        out = out.replace(old, new)
    return out


def _chapters() -> list[tuple[str, str]]:
    root = content_root(fetch_html(GUTENBERG_ID))
    order = [(_key(h.get_text()), h) for h in root.find_all("h2")]

    # The poems follow the "P O E M S / O N / V A R I O U S S U B J E C T S"
    # half-title; every h2 after it is one poem.
    start = next(i for i, (k, _) in enumerate(order) if k == "VARIOUSSUBJECTS") + 1
    poems = [(k, h) for k, h in order[start:] if "PROJECTGUTENBERG" not in k]
    if len(poems) != len(POEMS):
        raise CommandError(f"expected {len(POEMS)} poems, found {len(poems)}.")

    chapters = [("Preface", _preface(order))]
    for (title, check, lead), (key, h) in zip(POEMS, poems, strict=True):
        if not key.startswith(check):
            raise CommandError(f"poem {title!r}: source heading is {key!r}, expected {check!r}…")
        pres = [n for n in _section(h) if n.name == "pre"]
        chapters.append((title, _poem_body(pres, lead)))
    return chapters


class Command(BaseCommand):
    help = "Build Phillis Wheatley's Poems on Various Subjects (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": "",
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "publication_year": 1773,
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
            if wc < 40:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:50]:50} {wc:>5} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
