"""Build Blaise Pascal's *Provincial Letters* in Thomas M'Crie's translation.

The source is Project Gutenberg #73959, a scan of the 1856 New York printing
(Robert Carter & Brothers) of M'Crie's translation. www.gutenberg.org refuses
this environment's egress, so the HTML file is read from the GITenberg mirror of
the same ebook on GitHub.

Only Pascal is taken. M'Crie's preface, his 18,000-word historical
introduction and his 354 footnotes are left out — they are the translator's
controversy, not the author's — and so are the page numbers and the
publisher's catalogue that follows "THE END".

Each letter is one chapter, so the reader's chapter number IS the letter
number and "Letter XIII" can still be cited. That is why the short "Reply of
the Provincial" printed between Letters II and III is folded into the end of
Letter II under its own ``<h3>`` rather than given a chapter of its own. Each
letter's printed argument (the ALL-CAPS summary under the heading) is dropped
from the body; its lead clause becomes the chapter title. The dateline and,
from Letter XI on, the addressee are kept, as the opening lines of the letter.

Fixture-driven like every other book: ``seed_books`` creates it on the next
deploy from ``fixtures/content/books/provincial-letters.en.json``. This command
GENERATES that fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_provincial_letters
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter

SLUG = "provincial-letters"
TITLE = "The Provincial Letters"
SUBTITLE = "Translated by Thomas M'Crie"
AUTHOR_SLUG = "blaise-pascal"
GUTENBERG_ID = "73959"
SOURCE_HTML = (
    "https://raw.githubusercontent.com/GITenberg/"
    "The-provincial-letters-of-Blaise-Pascal-b-A-new-translation-with-historical-"
    "introduction-and-__73959/master/73959-h/73959-h.htm"
)
PUBLICATION_YEAR = 1657
COVER_COLOR = covers.ink_safe("#5a3e36")

AUTHOR_STUB = {"name": "Blaise Pascal", "birth_year": 1623, "death_year": 1662}

DESCRIPTION = (
    "In January 1656 the Sorbonne was about to condemn Antoine Arnauld, Pascal's "
    "friend at Port-Royal, and Pascal came to his defence in an anonymous letter "
    "“to a provincial,” a friend in the country. Seventeen more followed over the "
    "next fourteen months, passed hand to hand through Paris while the police "
    "hunted the printers. They begin as a comedy, with a puzzled outsider "
    "interviewing theologians who cannot say what their own words mean, and they "
    "grow into a fierce and serious attack on a morality that had learned to "
    "excuse almost anything. Pascal's charge is that the Jesuit casuists had made "
    "the gospel easy by emptying it, and his letters on murder, calumny and the "
    "love of God still ask what it costs to be honest before God. They are also "
    "the book that fixed modern French prose."
)

ATTRIBUTION = (
    "Public domain — Blaise Pascal's Provincial Letters (1656–1657), translated by "
    "Thomas M'Crie; text from Project Gutenberg (ebook 73959), from the 1856 New "
    "York printing. Each letter is a chapter, and the Provincial's reply is "
    "printed at the end of Letter II; the translator's preface, historical "
    "introduction and notes are not included."
)

# One per letter, in order: the lead clause of each letter's printed argument.
TITLES = [
    "Disputes in the Sorbonne and Proximate Power",
    "Of Sufficient Grace",
    "The Censure on M. Arnauld",
    "On Actual Grace and Sins of Ignorance",
    "The Jesuits' New System of Morals",
    "How the Casuists Elude the Authority of the Gospel",
    "The Method of Directing the Intention",
    "Corrupt Maxims Concerning Judges and Usurers",
    "Devotion Made Easy",
    "Palliatives Applied to Penance",
    "Ridicule a Fair Weapon Against Absurd Opinions",
    "On Alms-Giving and Simony",
    "How Easy It Is to Pass from Speculation to Practice",
    "The Maxims of the Jesuits on Murder",
    "On Calumny",
    "Calumnies Against Port-Royal",
    "The Author Vindicated from the Charge of Heresy",
    "No Heresy in the Church",
    "Fragment of a Nineteenth Letter",
]

_LETTER_HEAD = re.compile(r"^LETTER ([IVXL]+)\.$")
_REPLY_HEAD = "REPLY OF THE “PROVINCIAL” TO THE FIRST TWO LETTERS OF HIS FRIEND."
REPLY_TITLE = "Reply of the “Provincial” to the First Two Letters of His Friend"

# The addressee lines of Letters XI–XIX, printed in capitals.
ADDRESSEES = {
    "TO THE REVEREND FATHERS, THE JESUITS.": "To the Reverend Fathers, the Jesuits.",
    "TO THE REVEREND FATHERS OF THE SOCIETY OF JESUS.": (
        "To the Reverend Fathers of the Society of Jesus."
    ),
    "TO THE REVEREND FATHER ANNAT, JESUIT.": "To the Reverend Father Annat, Jesuit.",
}
# Centred blocks that are an argument (dropped) or an ornament (kept as a line).
ARGUMENT_CLASSES = {"c014", "c016", "c019", "c020"}
KEPT_CENTRED = {"✝ I. H. S."}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _source_sections() -> list[tuple[str, str]]:
    """``(heading, html)`` for every ``<h2>`` from Letter I to the end mark."""
    resp = requests.get(SOURCE_HTML, timeout=60)
    resp.raise_for_status()
    src = resp.content.decode("utf-8")
    try:
        start = src.index("<h2 class='c005'>LETTER I.</h2>")
        end = src.index("<div>THE END")
    except ValueError:
        raise CommandError("Letter I / THE END markers not found — the edition changed.") from None
    text = src[start:end]
    heads = list(re.finditer(r"<h2 class='c005'[^>]*>(.*?)</h2>", text, re.S))
    sections = []
    for n, m in enumerate(heads):
        stop = heads[n + 1].start() if n + 1 < len(heads) else len(text)
        heading = _norm(re.sub(r"<a [^>]*>.*?</a>|<[^>]+>", "", m.group(1)))
        sections.append((heading, text[m.end() : stop]))
    return sections


def _inline(node: Tag) -> str:
    """A block's contents as clean inline HTML: italics kept, furniture gone."""
    for a in node.select("a[href^='#f']"):  # footnote references
        a.decompose()
    for a in node.select("a[id]"):
        a.unwrap()
    for span in node.select("span.pageno"):
        span.decompose()
    for span in node.select("span"):
        span.unwrap()
    for tag in node.select("i, cite"):
        tag.name = "em"
        tag.attrs = {}
    return _norm(node.decode_contents())


def _blocks(fragment: str, where: str) -> list[str]:
    soup = BeautifulSoup(fragment, "html.parser")
    out: list[str] = []
    for el in soup.find_all(["p", "div"]):
        if not isinstance(el, Tag) or el.find_parent(["p"]):
            continue
        classes = set(el.get("class") or [])
        if el.name == "p":
            if classes & ARGUMENT_CLASSES:
                continue
            out.append(f"<p>{_inline(el)}</p>")
        elif "c015" in classes:  # dateline
            out.append(f"<p>{_inline(el)}</p>")
        elif "nf-center" in classes:
            text = _norm(re.sub(r"\[\d+\]", "", el.get_text(" ")))
            if not text or classes & ARGUMENT_CLASSES:
                continue
            if text in ADDRESSEES:
                out.append(f"<p><em>{ADDRESSEES[text]}</em></p>")
            elif text in KEPT_CENTRED:
                out.append(f"<p>{text}</p>")
            else:
                raise CommandError(f"{where}: unexpected centred block {text!r}.")
        elif "lg-container-b" in classes:  # Le Moine's verses, one line per row
            lines = [_inline(line) for line in el.select("div.line")]
            out.append("<blockquote><p>" + "<br>".join(lines) + "</p></blockquote>")
    for leftover in soup.find_all(string=True):
        if isinstance(leftover, NavigableString) and leftover.parent is soup and leftover.strip():
            raise CommandError(f"{where}: loose text {leftover.strip()[:40]!r}.")
    if not out:
        raise CommandError(f"{where}: no text.")
    return out


def _chapters() -> list[tuple[str, str]]:
    sections = _source_sections()
    letters: list[list[str]] = []
    numerals = []
    for heading, fragment in sections:
        m = _LETTER_HEAD.match(re.sub(r"\[\d+\]", "", heading).strip())
        if m:
            numerals.append(m.group(1))
            letters.append(_blocks(fragment, f"Letter {m.group(1)}"))
        elif heading == _REPLY_HEAD:
            if len(letters) != 2:
                raise CommandError("the Provincial's reply is no longer after Letter II.")
            letters[-1] += [f"<h3>{REPLY_TITLE}</h3>", *_blocks(fragment, "Reply")]
        else:
            raise CommandError(f"unexpected section {heading!r}.")
    if len(letters) != len(TITLES):
        raise CommandError(f"expected {len(TITLES)} letters, found {len(letters)}: {numerals}.")
    return [(title, "".join(body)) for title, body in zip(TITLES, letters, strict=True)]


class Command(BaseCommand):
    help = "Build Pascal's Provincial Letters (M'Crie) in the dev DB; then serialize the fixture."

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
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, created = Book.objects.update_or_create(
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

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            # The nineteenth letter is a fragment Pascal never finished.
            if wc < (300 if order == len(TITLES) else 1000):
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:48]:48} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
